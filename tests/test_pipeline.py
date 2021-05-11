from gallica_autobib.pipeline import BibtexParser, RisParser, InputParser, _ProcessArgs
import pytest
from pathlib import Path
import shutil

test_bibliographies_bibtex = [
    """
    @Article{danielou30:_pour_augus,
      author =       {Jean Daniélou},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      volume = 24,
      pages =     {135-57}}
"""
]

ids = ["pour-lire-augustin"]


@pytest.mark.parametrize("bibtex", test_bibliographies_bibtex, ids=ids)
def test_bibtex_parser(bibtex, file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path)
    parser.read(bibtex)
    assert parser.progress == 0
    status = parser.run()
    assert parser.progress == 1
    with parser.results[0].open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )
    assert str(parser.generate_outf(parser.records[0])) == str(
        parser._outfs[0]
    ).replace(".pdf", "-1.pdf")


def test_bibtex_parser_single_thread_clean(file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path)
    parser.read(test_bibliographies_bibtex[0])
    args = _ProcessArgs(
        parser.records[0],
        parser.process_args,
        parser.download_args,
        parser.generate_outf(parser.records[0]),
        parser.process,
        parser.clean,
    )
    outf = parser.process_record(args)
    assert not args.outf.exists()
    with outf.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_bibtex_parser_single_thread_no_clean(file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path)
    parser.read(test_bibliographies_bibtex[0])
    parser.clean = False
    args = _ProcessArgs(
        parser.records[0],
        parser.process_args,
        parser.download_args,
        parser.generate_outf(parser.records[0]),
        parser.process,
        parser.clean,
    )
    outf = parser.process_record(args)
    assert outf != args.outf
    assert args.outf.exists()
    with outf.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_bibtex_parser_single_thread_no_process(file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path)
    parser.read(test_bibliographies_bibtex[0])
    parser.process = False
    args = _ProcessArgs(
        parser.records[0],
        parser.process_args,
        parser.download_args,
        parser.generate_outf(parser.records[0]),
        parser.process,
        parser.clean,
    )
    outf = parser.process_record(args)
    assert outf == args.outf
    with outf.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


report_types = ["output.txt", "output.org"]


@pytest.fixture
def fixed_tmp_path():
    path = Path("/tmp/pytest-template-tmpdir/")
    if path.exists():
        raise Exception("tmpdir exists")
    path.mkdir()
    yield path
    shutil.rmtree(path)


@pytest.mark.parametrize("template", report_types)
def test_templates(template, file_regression, fixed_tmp_path):
    parser = BibtexParser(fixed_tmp_path, output_template=template)
    parser.read(test_bibliographies_bibtex[0])
    report = parser.run()
    file_regression.check(report)


test_bibliographies_ris = [
    [
        """
TY  - JOUR
TI  - Une opinion inconnue de l'école de Gilbert de la Porrée
AU  - Chenu, M-D
JO  - Revue d'Histoire Ecclésiastique
VL  - 26
IS  - 2
SP  - 347
EP  - 353
SN  - 0035-2381
PY  - 1930
PB  - Université catholique de Louvain.
ER  -
    """,
        False,
    ],
    [
        """
TY  - JOUR
TI  - La surnaturalisation des vertus
AU  - Jean Daniélou
T2  - Bulletin Thomiste
PY  - 1932
SP  - 93
EP  - 96
ER  -
""",
        False,
    ],
]

ris_ids = ["inconnue", "surnaturalisation"]


from devtools import debug


@pytest.mark.parametrize("ris, status", test_bibliographies_ris, ids=ris_ids)
def test_ris_parser(ris, status, file_regression, tmp_path, check_pdfs):
    parser = RisParser(tmp_path)
    parser.read(ris)
    debug(parser.records)
    report = parser.run()
    if status:
        assert "Output:" in report
        with parser.results[0].open("rb") as f:
            file_regression.check(
                f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
            )
    else:
        assert "Failed to match :(" in report


def test_base_parser():
    parser = InputParser(Path("."))
    with pytest.raises(NotImplementedError):
        parser.read("Inputstr")
