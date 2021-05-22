import logging
from pathlib import Path
from typing import Dict, Optional

import typer

from . import __version__
from .pipeline import BibtexParser, RisParser

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
def process_bibliograpy(
    bibfile: Path = typer.Argument(..., help="Bibliographic file to read."),
    outdir: Path = typer.Argument(..., help="Output directory."),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback
    ),
    post_process: bool = typer.Option(True, help="Post-process download."),
    preserve_text: bool = typer.Option(True, help="Preserve text in post processing."),
    processes: int = typer.Option(
        6,
        help="Number of processes to run.  We are largely network bound so > nproc might make sense.",
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
    """
    Process a bibliography file.

    """
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
    report = parser.run()
    if out:
        with out.open("w") as f:
            f.write(report)
    else:
        print(report)


if __name__ == "__main__":
    app()
