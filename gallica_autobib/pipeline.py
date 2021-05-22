"""Pipeline to match and convert."""
import asyncio
import logging
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from time import sleep
from typing import List, Literal, Optional, TextIO, Union
from urllib.error import URLError

from jinja2 import Template
from pydantic import BaseModel
from slugify import slugify

from .models import RecordTypes
from .parsers import parse_bibtex, parse_ris
from .process import process_pdf
from .query import (
    DownloadError,
    GallicaResource,
    Match,
    MatchingError,
    Query,
    source_match_cache,
)
from .templating import env

logger = logging.getLogger(__name__)


class Record(BaseModel):
    """Input"""

    target: RecordTypes
    raw: str
    kind: Literal["bibtex", "ris"]


class Result(BaseModel):
    """Result of an pipeline run."""

    record: Record
    match: Optional[Match] = None
    unprocessed: Optional[Path] = None
    processed: Optional[Path] = None
    errors: Optional[List[str]] = None
    status: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True


class InputParser:
    """Class to parse input.  This base class should be subclassed."""

    def __init__(
        self,
        outdir: Path,
        output_template: Union[str, Path] = None,
        process_args: dict = None,
        download_args: dict = None,
        process: bool = True,
        clean: bool = True,
        fetch_only: Optional[int] = None,
        ignore_cache: bool = False,
    ):
        self.records: List[Record] = []
        self.raw: List[str] = []
        self.len_records: int = 0
        self.process = process
        self.process_args = process_args if process_args else {}
        self.download_args = download_args if download_args else {}
        self._outfs: List[Path] = []
        self.outdir = outdir
        self.clean = clean
        self._results: List[Union[Path, None, bool]] = []
        self.output_template: Template = output_template  # type: ignore
        self.fetch_only = fetch_only
        self._pool: Optional[ProcessPoolExecutor] = None
        self.processes = 6
        self.executing: List[Future] = []
        self.ignore_cache = ignore_cache
        self.suppress_cover_page: bool = False

    @property
    def successful(self) -> int:
        return len([x for x in self.results if x])

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def results(self) -> List[Union[Path, None, bool]]:
        for x in self.executing:
            if x.done():
                res = x.result()
                if res not in self._results:
                    self._results.append(res)
        return self._results

    @property
    def output_template(self) -> Template:
        return self._output_template

    @output_template.setter
    def output_template(self, output_template: Union[str, Path] = None) -> None:
        if isinstance(output_template, str):
            self._output_template = env.get_template(f"output.{output_template}")
        elif isinstance(output_template, Path):
            self._output_template = Template(output_template.open().read())
        else:
            self._output_template = env.get_template("output.txt")

    @property
    def progress(self) -> Optional[float]:
        """Progress in matching or failing."""
        if not self.executing:
            return None
        return len([x for x in self.executing if x.done()]) / len(self.executing)

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read input data."""
        raise NotImplementedError

    def generate_outf(self, result: RecordTypes) -> Path:

        outf = self.outdir / (slugify(f"{result.name()}") + ".pdf")
        i = 0
        while outf in self._outfs:
            i += 1
            outf = self.outdir / (slugify(f"{result.name()} {i}") + ".pdf")
        self._outfs.append(outf)
        return outf

    def pool(self, pool: Optional[ProcessPoolExecutor] = None) -> ProcessPoolExecutor:
        """Create or register pool, or return pool if extant."""
        if pool:
            if self._pool:
                self.pool.shutdown(wait=True)  # type: ignore
            self._pool = pool
        elif not pool:
            self._pool = ProcessPoolExecutor(self.processes)
        return self._pool  # type: ignore

    def run(self) -> str:
        """Run query, blocking until finished.

        Returns:
          Rendered report.
        """

        logger.debug("Generating tasks.")
        self.executing = self._send_records()
        while self.progress < 1:  # type: ignore
            sleep(1)
        return self.report()

    def _send_records(self) -> List[Future]:
        """Send records to pool."""
        return [
            self.pool().submit(
                self.process_record,
                record,
                self.generate_outf(record.target),
                self.process,
                self.clean,
                fetch_only=self.fetch_only,
                process_args=self.process_args,
                download_args=self.download_args,
                cache=not self.ignore_cache,
                suppress_cover_page=self.suppress_cover_page,
            )
            for record in self.records
        ]

    async def submit(self) -> str:
        """Submit query to pool.

        This is designed for use in web servers which may wish to use a
        centrally defined pool shared between n queries.

        Returns:
          Rendered report.

        """
        logger.debug("Submitting tasks")
        futures = self._send_records()
        self.executing = futures
        await asyncio.gather(*[asyncio.wrap_future(f) for f in futures])
        return self.report()

    def report(self) -> str:
        return self.output_template.render(obj=self)

    @staticmethod
    def process_record(
        record: Record,
        outf: Path,
        process: bool,
        clean: bool,
        fetch_only: Optional[bool] = None,
        process_args: Optional[dict] = None,
        download_args: Optional[dict] = None,
        cache: bool = True,
        suppress_cover_page: bool = False,
    ) -> Result:
        """
        Run pipeline on item, returning a Result() object.

        """

        key = record.target.key()
        match = source_match_cache[key] if cache else None
        if not match:
            query = Query(record.target)
            match = query.run()
        args = dict(record=record)  # type: ignore
        if not process_args:
            process_args = {}
        if not download_args:
            download_args = {}

        if not match:
            logger.info(f"No match found for {record.target.name}")
            args["status"] = None  # type: ignore
            return Result.parse_obj(args)

        logger.debug("Generating gallica resource.")
        gallica_resource = GallicaResource(record.target, match.candidate, cache=cache)
        gallica_resource.suppress_cover_page = suppress_cover_page
        if not download_args:
            download_args = {}
        try:
            logger.debug("Starting download.")
            gallica_resource.download_pdf(outf, fetch_only=fetch_only, **download_args)
            args["match"] = gallica_resource.match  # type: ignore
        except MatchingError as e:
            logger.info(f"Failed to match. ({e})")
            args["errors"] = [str(e)]  # type: ignore
            args["status"] = None  # type: ignore
            return Result.parse_obj(args)

        except (URLError, DownloadError) as e:
            logger.info(f"Failed to download. {e}")
            args["errors"] = [str(e)]  # type: ignore
            args["status"] = False  # type: ignore
            return Result.parse_obj(args)

        args["status"] = True  # type: ignore

        if process:
            logger.debug("Processing...")
            processed = process_pdf(
                outf, has_cover_page=not suppress_cover_page, **process_args
            )
            args["processed"] = processed  # type: ignore
            if clean:
                logger.debug("Deleting original file.")
                outf.unlink()
            else:
                args["unprocessed"] = outf  # type: ignore
            return Result.parse_obj(args)

        else:
            args["unprocessed"] = outf  # type: ignore
            return Result.parse_obj(args)


class BibtexParser(InputParser):
    """Class to parse bibtex."""

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read a bibtex file-like object and convert to records.

        Args:
          stream: Union[TextIO: stream to read
          str]: string to parse.

        """
        records, raw = parse_bibtex(stream)
        self.records = [
            Record(target=records[i], raw=raw[i], kind="bibtex")
            for i in range(len(records))
        ]


class RisParser(InputParser):
    """Class to parse ris."""

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read a ris file-like object and convert to records.

        Args:
          stream: Union[TextIO: stream to read
          str]: string to parse.

        """
        records, raw = parse_ris(stream)
        self.records = [
            Record(target=records[i], raw=raw[i], kind="ris")
            for i in range(len(records))
        ]
