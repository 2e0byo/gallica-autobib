"""Pipeline to match and convert."""
from .parsers import parse_bibtex, parse_ris
from .models import Article
from .query import Query, GallicaResource
from pathlib import Path
from typing import TextIO, Union, Optional
from . import process
from multiprocessing import Pool, Queue
import typer
from jinja2 import Environment, PackageLoader, select_autoescape
from collections import namedtuple
from slugify import slugify

env = Environment(
    loader=PackageLoader("gallica_autobib", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

_ProcessArgs = namedtuple(
    "_ProcessArgs", ["record", "process_args", "download_args", "outf", "process"]
)


class InputParser:
    """Class to parse input.  This base class should be subclassed."""

    def __init__(
        self,
        outdir: Path,
        output_template=None,
        process_args: dict = None,
        download_args: dict = None,
        process: bool = True,
    ):
        self.records = []
        self.raw = []
        self.len_records = 0
        self.results = None
        self.process = process
        if output_template:
            self.output_template = output_template
        else:
            self.output_template = env.get_template("output.txt")
        self.process_args = process_args if process_args else {}
        self.download_args = download_args if download_args else {}
        self._outfs = []

    @property
    def progress(self):
        """Progress in matching or failing."""
        return len(self._done) / self.len_records

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read input data."""
        raise NotImplementedError

    def generate_outf(self, result):
        outf = self.outdir / slugify(f"{result.author} {result.title}.pdf")
        i = 0
        while outf in self.outfs:
            i += 1
            outf = self.outdir / slugify(f"{result.author} {result.title} {i}.pdf")
        self.outfs.append(outf)
        return outf

    def run(self, processes=6) -> str:

        with Pool(processes=processes) as pool:
            results = []
            tasks = [
                self._ProcessArgs(
                    record,
                    self.process_args,
                    self.download_args,
                    self.generate_outf(record),
                    self.process,
                )
                for record in self.records
            ]
            for res in typer.progressbar(pool.imap(self.process_record, tasks)):
                results.append(res)

            self.results = [x.get() for x in x in results]

        return self.output_template.render(self.status)

    def generate_output(self):
        """Generate report using template."""

    @staticmethod
    def process_record(args: namedtuple) -> Optional[Path]:
        """
        Run pipeline on item, returning a path if it succeeds or None if it fails.

        """
        query = Query(args.record)
        match = query.run()
        if not match:
            return None
        match = GallicaResource(match)
        match.download_pdf(args.outf, **args.download_args)
        if args.process:
            process.process_pdf(args.outf, **args.process_args)
        return args.outf


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


class PipelineError(Exception):
    pass


class Item:
    """Class to match an item in our bibliography through the pipeliine"""

    def __init__(
        self,
        target: Union[Article],
        outf: Path,
        download_args: dict = {},
        process_args: dict = None,
    ) -> None:
        """Setup item to try to retrieve target."""
        self.target = target
        self.query = Query(target)
        self.match = None
        self._status = None
        self.download_args = {}
        self.outf = outf
        self.process_args = (
            {"preserve_text": False} if not process_args else process_args
        )

    def _throw(self):
        raise Exception(self._status[-1])

    def run(self, process=True, process_args: dict = {}) -> Optional[Path]:
        """
        Run pipeline on item, returning a path if it succeeds or None if it fails.

        Args:
          process:  (Default value = True)
          process_args: dict:  (Default value = {})

        Returns:

        """
        self._status.append("Querying")
        self.match = self.query.run()
        if not self.match:
            self._status.append("Failed to match")
            return None
        self.match = GallicaResource(self.match)

        self._status.append("Matched")
        self._status.append("Downloading")
        self.match.download_pdf(self.outf, **self.download_args)
        if process:
            process.process_pdf(self.outf, **self.process_args)
        return self.outf


# convert to func
