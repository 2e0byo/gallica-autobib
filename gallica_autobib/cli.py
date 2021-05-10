import typer
from .pipeline import BibtexParser, RisParser
from pathlib import Path


class AutoBibError(Exception):
    pass


app = typer.Typer()


@app.command()
def process_bibliograpy(
    bibfile: Path,
    outdir: Path,
    post_process: bool = True,
    preserve_text: bool = False,
    processes: int = 6,
    clean: bool = True,
):
    """
    Process a bibliography file.

    Args:
      bibfile: Path: The bibliography file to process.
      outdir: Path: The directory to save output in.
      post-process: bool: Whether to post-process pdfs.  (Default value = True)
      preserve_text: bool: Whether to preserve text in pdfs (implies only cropping them.)  (Default value = False)
      processes: int: Number of processes to run in parallel
      clean: bool: Remove original file if successful.

    Returns:

    """
    process_args = {"preserve_text": preserve_text}
    download_args = {}
    args = dict(
        outdir=outdir,
        process_args=process_args,
        download_args=download_args,
        process=post_process,
        clean=clean,
    )
    if bibfile.suffix == ".bib":
        parser = BibtexParser(**args)
    elif bibfile.suffix == ". w bbris":
        parser = RisParser(**args)
    else:
        raise AutoBibError("Input is not bibtex or ris.")

    with bibfile.open() as f:
        parser.read(f)
    report = parser.run()
    print(report)


if __name__ == "__main__":
    app()