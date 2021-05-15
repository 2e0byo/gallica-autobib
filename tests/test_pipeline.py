from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tempfile import TemporaryDirectory
from gallica_autobib import pipeline

import pytest
from gallica_autobib.pipeline import BibtexParser, InputParser, RisParser


@pytest.fixture()
def bibtex_parser():
    """A bibtex parser which downloads 1 page."""
    with TemporaryDirectory() as tmp_path:
        parser = BibtexParser(Path(tmp_path), fetch_only=1)
        yield parser


def mock_download_pdf(self, path, blocksize=100, trials=3, fetch_only=None):
    with (Path("tests/test_pdfs") / path.name).open("rb") as f:
        with path.open("wb") as o:
            o.write(f.read())
    return True


def mock_ark():
    return "https://gallica.bnf.fr/ark:/12148/bpt6k9735634r"


@pytest.fixture()
def mock_bibtex_parser(tmp_path, mocker):
    """A bibtex parser for the pour-lire-augustin result which neither searches nor downloads."""
    download_pdf = pipeline.GallicaResource.download_pdf
    ark = pipeline.GallicaResource.ark
    pipeline.GallicaResource.download_pdf = mock_download_pdf
    pipeline.GallicaResource.ark = mock_ark
    parser = pipeline.BibtexParser(tmp_path)
    yield parser
    pipeline.GallicaResource.download_pdf = download_pdf
    pipeline.GallicaResource.ark = ark


def test_pipeline_attrs(bibtex_parser):
    assert bibtex_parser.progress is None


test_bibliographies_bibtex = [
    """@Article{danielou30:_pour_augus,
      author =       {M.-D. Chenu},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      volume = 24,
      pages =     {135-57}}""",
    """@Article{garrigou-lagrange21:_la,
  author =       {Réginald Garrigou-Lagrange},
  title =        {La perfection de la charité},
  journaltitle = {La Vie spirituelle},
  year =      1921,
  language =  {french},
  volume =    2,
  pages =     {1--20}}""",
]

ids = ["pour-lire-augustin", "perfection"]

# downloads 1 page
@pytest.mark.parametrize("bibtex", test_bibliographies_bibtex, ids=ids)
def test_bibtex_parser(bibtex, file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path, fetch_only=1, clean=False)
    parser.read(bibtex)
    no = len(parser.records)
    assert not parser.progress
    parser.run()
    assert parser.progress == 1
    assert len(parser.executing) == no, "Parser executed other stuff."
    assert len(parser.results) == no, "Spurious entry in results."
    assert len(parser.results) == no, "Spurious accumulation of results."
    res = parser.results[0]
    with res.processed.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )
    assert str(parser.generate_outf(res.record.target)) == str(res.unprocessed).replace(
        ".pdf", "-1.pdf"
    )
    assert res.record.raw == bibtex
    assert res.record.kind == "bibtex"


def test_bibtex_parser_single_thread_clean(
    mock_bibtex_parser, file_regression, tmp_path, check_pdfs
):
    """Test the processing step only, mocking the others.

    Neither downloads nor searches.
    """
    parser = mock_bibtex_parser
    parser.read(test_bibliographies_bibtex[0])
    outf = parser.generate_outf(parser.records[0].target)
    result = parser.process_record(
        parser.records[0],
        outf,
        parser.process,
        True,
        fetch_only=parser.fetch_only,
        process_args=parser.process_args,
        download_args=parser.download_args,
    )
    assert not result.unprocessed
    assert not outf.exists()
    with result.processed.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_bibtex_parser_single_thread_no_clean(
    mock_bibtex_parser, file_regression, tmp_path, check_pdfs
):
    """Test not cleaning.

    Neither downloads nor searches."""
    parser = mock_bibtex_parser
    parser.read(test_bibliographies_bibtex[0])
    outf = parser.generate_outf(parser.records[0].target)
    result = parser.process_record(
        parser.records[0],
        outf,
        parser.process,
        False,
        fetch_only=parser.fetch_only,
        process_args=parser.process_args,
        download_args=parser.download_args,
    )
    assert result.processed != result.unprocessed
    assert result.unprocessed
    assert outf.exists()  # no need to regression check as same file as above.


def test_bibtex_parser_single_thread_no_process(
    mock_bibtex_parser, file_regression, tmp_path, check_pdfs
):
    """Test not processing.

    Neither downloads nor searches.
    """
    parser = mock_bibtex_parser
    parser.read(test_bibliographies_bibtex[0])
    outf = parser.generate_outf(parser.records[0].target)
    result = parser.process_record(
        parser.records[0],
        outf,
        False,
        parser.clean,
        fetch_only=parser.fetch_only,
        process_args=parser.process_args,
        download_args=parser.download_args,
    )
    assert not result.processed
    assert result.unprocessed
    assert outf.exists()
    sourcefile = Path("tests/test_pdfs") / outf.name
    assert result.unprocessed.stat().st_size == sourcefile.stat().st_size


@pytest.fixture(scope="module")
def parser(fixed_tmp_path):
    """A parser which has loaded something but won't actually download it."""
    tmpf = fixed_tmp_path / "pour-lire-saint-augustin-m-d-chenu.pdf"
    outf = fixed_tmp_path / "processed-pour-lire-saint-augustin-m-d-chenu.pdf"
    with outf.open("w") as f:
        f.write("-")
    with tmpf.open("w") as f:
        f.write("-")
    args = dict(skip_existing=True)
    parser = BibtexParser(fixed_tmp_path, process_args=args, fetch_only=1)
    parser.process_args = {"skip_existing": True}
    parser.read(test_bibliographies_bibtex[0])
    parser.run()
    yield parser


report_types = ["output.txt", "output.org", "output.html"]


@pytest.mark.parametrize("template", report_types)
def test_templates(parser, template, file_regression, fixed_tmp_path):
    """Test templates.  Runs queries to generate templates.  Doesn't download."""
    parser.output_template = template
    report = parser.report()
    file_regression.check(report)


test_bibliographies_ris = [
    [
        """TY  - JOUR
TI  - Une opinion inconnue de l'école de Gilbert de la Porrée
AU  - M.-D. Chenu
JO  - Revue d'Histoire Ecclésiastique
VL  - 26
IS  - 2
SP  - 347
EP  - 353
SN  - 0035-2381
PY  - 1930
PB  - Université catholique de Louvain.
ER  -""",
        False,
    ],
    [
        """TY  - JOUR
TI  - La surnaturalisation des vertus
AU  - M.-D. Chenu
T2  - Bulletin Thomiste
PY  - 1932
SP  - 93
EP  - 96
ER  -""",
        False,
    ],
]

ris_ids = ["inconnue", "surnaturalisation"]


from devtools import debug


@pytest.mark.parametrize("ris, status", test_bibliographies_ris, ids=ris_ids)
def test_ris_parser(ris, status, file_regression, tmp_path, check_pdfs):
    """Would download if any matched---but they don't.

    This fn can be replaced with an equivalence test on the generated objects between bibtex and ris."""
    parser = RisParser(tmp_path, fetch_only=1)
    parser.read(ris)
    debug(parser.records)
    report = parser.run()
    if status:
        assert "Processed:" in report
        with parser.results[0].open("rb") as f:
            file_regression.check(
                f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
            )
    else:
        assert "Failed to match :(" in report
    res = parser.results[0]
    assert res.record.raw == ris
    assert res.record.kind == "ris"


def test_base_parser():
    parser = InputParser(Path("."))
    with pytest.raises(NotImplementedError):
        parser.read("Inputstr")


# downloads 1 page
@pytest.mark.asyncio
async def test_submit(mock_bibtex_parser, file_regression, check_pdfs):
    mock_bibtex_parser.process = False
    pool = ProcessPoolExecutor(1)
    mock_bibtex_parser.read(test_bibliographies_bibtex[-1])
    mock_bibtex_parser.pool(pool)
    assert mock_bibtex_parser.progress is None
    await mock_bibtex_parser.submit()
    assert mock_bibtex_parser.progress
    for result in mock_bibtex_parser.results:
        outf = result.unprocessed
        sourcef = Path("tests/test_pdfs") / outf.name
        assert outf.stat().st_size == sourcef.stat().st_size
        assert result.record.kind == "bibtex"
