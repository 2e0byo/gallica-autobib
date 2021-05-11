"""Pipeline to match and convert."""
from .parsers import parse_bibtex, parse_ris
from .models import Article
from .query import Query, GallicaResource
from pathlib import Path
from typing import TextIO, Union, Optional
from . import process
from multiprocessing import Pool, Queue
import typer
from jinja2 import (
    Environment,
    PackageLoader,
    select_autoescape,
    Template,
    FileSystemLoader,
)
from collections import namedtuple
from slugify import slugify
from urllib.error import URLError

env = Environment(
    loader=PackageLoader("gallica_autobib", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

_ProcessArgs = namedtuple(
    "_ProcessArgs",
    ["record", "process_args", "download_args", "outf", "process", "clean"],
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
    ):
        self.records = []
        self.raw = []
        self.len_records = 0
        self.results = None
        self.process = process
        self.process_args = process_args if process_args else {}
        self.download_args = download_args if download_args else {}
        self._outfs = []
        self.outdir = outdir
        self.clean = clean
        self.results = []
        self.output_template = output_template

    @property
    def output_template(self):
        return self._output_template

    @output_template.setter
    def output_template(self, output_template: Union[str, Path] = None):
        if isinstance(output_template, str):
            self._output_template = env.get_template(output_template)
        elif isinstance(output_template, Path):
            self._output_template = Template(output_template.open().read())
        else:
            self._output_template = env.get_template("output.txt")

    @property
    def progress(self):
        """Progress in matching or failing."""
        return len(self.results) / self.len_records

    def read(self, stream: Union[TextIO, str]) -> None:
        """Read input data."""
        raise NotImplementedError

    def generate_outf(self, result):
        outf = self.outdir / (slugify(f"{result.author} {result.title}") + ".pdf")
        i = 0
        while outf in self._outfs:
            i += 1
            outf = self.outdir / (
                slugify(f"{result.author} {result.title} {i}") + ".pdf"
            )
        self._outfs.append(outf)
        return outf

    def run(self, processes=6) -> str:

        with Pool(processes=processes) as pool:
            results = []
            tasks = [
                _ProcessArgs(
                    record,
                    self.process_args,
                    self.download_args,
                    self.generate_outf(record),
                    self.process,
                    self.clean,
                )
                for record in self.records
            ]
            with typer.progressbar(pool.imap(self.process_record, tasks)) as progress:
                for res in progress:
                    self.results.append(res)

        return self.output_template.render(obj=self)

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
        match = GallicaResource(args.record, match.candidate)
        try:
            match.download_pdf(args.outf, **args.download_args)
        except URLError as e:

            from traceback import print_exc
            from devtools import debug

            return False
        if args.process:
            outf = process.process_pdf(args.outf, **args.process_args)
            if args.clean:
                args.outf.unlink()
            return outf
        else:
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
