import logging
from pathlib import Path
from typing import Dict, Optional

import typer

from . import __version__
from .pipeline import BibtexParser, RisParser
from .process import process_pdf
from .query import DownloadableResource

logger = logging.getLogger(__name__)


class AutoBibError(Exception):
    pass


log_level = [logging.NOTSET, logging.ERROR, logging.DEBUG]
app = typer.Typer()


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"Gallica-Autobib Version: {__version__}")
        raise typer.Exit()


@app.command()
def process(
    bibfile: Path = typer.Argument(..., help="Bibliographic file to read."),
    outdir: Path = typer.Argument(..., help="Output directory."),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback
    ),
    post_process: bool = typer.Option(True, help="Post-process download."),
    ocr_bounds: bool = typer.Option(
        True, help="Use galllica ocr bounds for cropping if possible (best)."
    ),
    preserve_text: bool = typer.Option(True, help="Preserve text in post processing."),
    processes: int = typer.Option(
        6,
        help="Number of processes to run.  We are largely network bound so > nproc might make sense.",
    ),
    one_thread: bool = typer.Option(
        False, help="Run everything in main thread for debugging."
    ),
    clean: bool = typer.Option(True, help="Clean up intermediate files."),
    template: Path = typer.Option(None, help="Path to output template to use."),
    template_format: str = typer.Option(
        None,
        help="Which internal template to use.  Ignored if a template path is provided.",
    ),
    verbosity: int = typer.Option(1, help="Verbosity between 0 and 2."),
    out: Path = typer.Option(None, help="Output path for report.  Default is STDOUT."),
    ignore_cache: bool = typer.Option(
        False,
        help="Ignore cache and rematch.  Note this will overwrite the cache with any matches.",
    ),
    suppress_cover_page: bool = typer.Option(
        False, help="Suppress Gallica's cover page."
    ),
) -> None:
    """Process a bibliography file."""
    process_args = {"preserve_text": preserve_text}
    download_args: Dict[str, bool] = {}
    logging.basicConfig(level=log_level[verbosity])

    args = dict(
        outdir=outdir,
        process_args=process_args,
        download_args=download_args,
        process=post_process,
        clean=clean,
        output_template=template if template else template_format,
        ignore_cache=ignore_cache,
        ocr_bounds=ocr_bounds,
    )
    if bibfile.suffix == ".bib":
        logger.debug("Detected bibtex.")
        parser = BibtexParser(**args)  # type: ignore
    elif bibfile.suffix == ".ris":
        logger.debug("Detected ris.")
        parser = RisParser(**args)  # type: ignore
    else:
        raise AutoBibError("Input is not bibtex or ris.")

    parser.processes = processes
    parser.suppress_cover_page = suppress_cover_page
    with bibfile.open() as f:
        parser.read(f)
    if one_thread:
        print("Ignoring process count and running everything in main thread...")
        report = parser.sync_run()
    else:
        report = parser.run()
    if out:
        with out.open("w") as f:
            f.write(report)
    else:
        print(report)


@app.command()
def fetch(
    ark: str = typer.Argument(..., help="Ark for the resource to fetch."),
    outf: Path = typer.Argument(..., help="Output path."),
    post_process: bool = typer.Option(True, help="Post-process download."),
    preserve_text: bool = typer.Option(True, help="Preserve text in post processing."),
    clean: bool = typer.Option(True, help="Clean up intermediate files."),
    verbosity: int = typer.Option(1, help="Verbosity between 0 and 2."),
    suppress_cover_page: bool = typer.Option(
        False, help="Suppress Gallica's cover page."
    ),
) -> None:
    """Fetch a single resource to a pdf."""

    process_args = {"preserve_text": preserve_text}
    download_args: Dict[str, bool] = {}

    logging.basicConfig(level=log_level[verbosity])
    logger = logging.getLogger("CLI")

    resource = DownloadableResource()
    resource.ark = ark
    resource.set_max_pages()
    resource.download_pdf(outf)
    if post_process:
        logger.debug("Processing...")
        processed = process_pdf(
            outf,
            has_cover_page=True,
            suppress_pages=range(2) if suppress_cover_page else None,
            preserve_text=preserve_text,
        )
        if clean:
            logger.debug("Deleting original file.")
            outf.unlink()
        print(f"Output written to {processed}")
    if outf.exists():
        print(f"Original file at {outf}")


if __name__ == "__main__":
    app()
