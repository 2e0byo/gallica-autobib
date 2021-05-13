import logging
from pathlib import Path
from typing import Dict

import typer

from .pipeline import BibtexParser, RisParser

logger = logging.getLogger(__name__)


class AutoBibError(Exception):
    pass


log_level = [logging.NOTSET, logging.ERROR, logging.DEBUG]
app = typer.Typer()


@app.command()
def process_bibliograpy(
    bibfile: Path,
    outdir: Path,
    post_process: bool = True,
    preserve_text: bool = False,
    processes: int = 6,
    clean: bool = True,
    template: Path = None,
    verbosity: int = 1,
    out: Path = None,
) -> None:
    """
    Process a bibliography file.

    Args:
      bibfile: Path: The bibliography file to process.
      outdir: Path: The directory to save output in.
      post-process: bool: Whether to post-process pdfs.  (Default value = True)
      preserve_text: bool: Whether to preserve text in pdfs (implies only cropping them.)  (Default value = False)
      processes: int: Number of processes to run in parallel
      clean: bool: Remove original file if successful.
      template: Path: Template to render output.
      verbosity: int: Verbosity between 0 and 3, (Default value = 3)
      out: Path: Path to save report to.  Default to stdout.

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
        output_template=template,
    )
    if bibfile.suffix == ".bib":
        logger.debug("Detected bibtex.")
        parser = BibtexParser(**args)  # type: ignore
    elif bibfile.suffix == ".ris":
        logger.debug("Detected ris.")
        parser = RisParser(**args)  # type: ignore
    else:
        raise AutoBibError("Input is not bibtex or ris.")

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
