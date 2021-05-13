"""Pipeline to match and convert."""
import logging
from collections import namedtuple
from multiprocessing import Pool
from pathlib import Path
from typing import List, Optional, TextIO, Tuple, Union
from urllib.error import URLError

import typer
from jinja2 import Environment, PackageLoader, Template, select_autoescape
from slugify import slugify

from . import process
from .models import RecordTypes
from .parsers import parse_bibtex, parse_ris
from .query import DownloadError, GallicaResource, MatchingError, Query

logger = logging.getLogger(__name__)

env = Environment(
    loader=PackageLoader("gallica_autobib", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

_ProcessArgs = namedtuple(
    "_ProcessArgs",
    [
        "record",
        "process_args",
        "download_args",
        "outf",
        "process",
        "clean",
        "fetch_only",
    ],
)


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
    ):
        self.records: List[RecordTypes] = []
        self.raw: List[str] = []
        self.len_records: int = 0
        self.process = process
        self.process_args = process_args if process_args else {}
        self.download_args = download_args if download_args else {}
        self._outfs: List[Path] = []
        self.outdir = outdir
        self.clean = clean
        self.results: List[Union[Path, None, bool]] = []
        self.scores: List[Optional[float]] = []
        self.output_template: Template = output_template  # type: ignore
        self.match = None
        self.fetch_only = fetch_only

    @property
    def successful(self) -> int:
        return len([x for x in self.results if x])

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def output_template(self) -> Template:
        return self._output_template

    @output_template.setter
    def output_template(self, output_template: Union[str, Path] = None) -> None:
        if isinstance(output_template, str):
            self._output_template = env.get_template(output_template)
        elif isinstance(output_template, Path):
            self._output_template = Template(output_template.open().read())
        else:
            self._output_template = env.get_template("output.txt")

    @property
    def progress(self) -> float:
        """Progress in matching or failing."""
        return len(self.results) / self.len_records

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

    def run(self, processes: int = 6) -> str:

        logger.debug("Generating tasks.")
        with Pool(processes=processes) as pool:
            tasks = [
                _ProcessArgs(
                    record,
                    self.process_args,
                    self.download_args,
                    self.generate_outf(record),
                    self.process,
                    self.clean,
                    self.fetch_only,
                )
                for record in self.records
            ]
            with typer.progressbar(pool.imap(self.process_record, tasks)) as progress:
                for res in progress:
                    self.results.append(res[0])
                    self.scores.append(res[1])

        return self.output_template.render(obj=self)

    @staticmethod
    def process_record(
        args: _ProcessArgs,
    ) -> Tuple[Union[Path, None, bool], Optional[float]]:
        """
        Run pipeline on item, returning a path if it succeeds or None if it fails.

        """
        query = Query(args.record)
        match = query.run()
        if not match:
            logger.info(f"No match found for {args.record.author} {args.record.title}")
            return None, None
        match = GallicaResource(args.record, match.candidate)
        try:
            logger.debug("Starting download.")
            match.download_pdf(
                args.outf, fetch_only=args.fetch_only, **args.download_args
            )
            score = match.confidence
        except MatchingError as e:
            logger.info(f"Failed to find match. ({e})")
            return False, None
        except (URLError, DownloadError) as e:
            logger.info(f"Failed to download. {e}")
            return False, score
        if args.process:
            logger.debug("Processing...")
            outf = process.process_pdf(args.outf, **args.process_args)
            if args.clean:
                logger.debug("Deleting original file.")
                args.outf.unlink()
            return outf, score
        else:
            return args.outf, score


class BibtexParser(InputParser):
    """Class to parse bibtex."""

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read a bibtex file-like object and convert to records.

        Args:
          stream: Union[TextIO: stream to read
          str]: string to parse.

        """
        self.records, self.raw = parse_bibtex(stream)
        self.len_records = len(self.records)


class RisParser(InputParser):
    """Class to parse ris."""

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read a ris file-like object and convert to records.

        Args:
          stream: Union[TextIO: stream to read
          str]: string to parse.

        """
        self.records, self.raw = parse_ris(stream)
        self.len_records = len(self.records)
