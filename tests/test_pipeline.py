from pathlib import Path

import pytest
from gallica_autobib.pipeline import BibtexParser, InputParser, RisParser
from tempfile import TemporaryDirectory


@pytest.fixture(scope="module")
def bibtex_parser():
    with TemporaryDirectory() as tmp_path:
        parser = BibtexParser(Path(tmp_path), fetch_only=1)
        yield parser


def test_pipeline_attrs(bibtex_parser):
    assert bibtex_parser.progress is None


test_bibliographies_bibtex = [
    """
    @Article{danielou30:_pour_augus,
      author =       {M.-D. Chenu},
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
def test_bibpiwuocessedtex_parser(bibtex, file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path, fetch_only=1, clean=False)
    parser.read(bibtex)
    no = len(parser.records)
    assert not parser.progress
    parser.run()
    assert parser.progress == 1
    assert len(parser.executing) == no, "Parser executed other stuff."
    assert len(parser.results) == no, "Spurious entry in results."
    assert len(parser.results) == no, "Spurious accumulation of results."
    with parser.results[0].processed.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )
    assert str(parser.generate_outf(parser.results[0].record.target)) == str(
        parser.results[0].unprocessed
    ).replace(".pdf", "-1.pdf")


def test_bibtex_parser_single_thread_clean(file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path, fetch_only=1)
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


def test_bibtex_parser_single_thread_no_clean(file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path, fetch_only=1)
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
    assert outf.exists()
    with result.processed.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_bibtex_parser_single_thread_no_process(file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path, fetch_only=1)
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
    with result.unprocessed.open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


# report_types = ["output.txt", "output.org", "output.html"]


# @pytest.fixture()
# def parser(fixed_tmp_path):
#     """A parser which has loaded something but won't actually download it."""
#     tmpf = fixed_tmp_path / "m-d-chenu-pour-lire-saint-augustin.pdf"
#     outf = fixed_tmp_path / "processed-m-d-chenu-pour-lire-saint-augustin.pdf"
#     with outf.open("w") as f:
#         f.write("-")
#     with tmpf.open("w") as f:
#         f.write("-")
#     args = dict(skip_existing=True)
#     parser = BibtexParser(fixed_tmp_path, process_args=args, fetch_only=1)
#     parser.read(test_bibliographies_bibtex[0])
#     yield parser


# @pytest.mark.parametrize("template", report_types)
# def test_templates(parser, template, file_regression, fixed_tmp_path):
#     parser.output_template = None
#     parser.output_template = template
#     report = parser.run()
#     file_regression.check(report)


# test_bibliographies_ris = [
#     [
#         """
# TY  - JOUR
# TI  - Une opinion inconnue de l'école de Gilbert de la Porrée
# AU  - M.-D. Chenu
# JO  - Revue d'Histoire Ecclésiastique
# VL  - 26
# IS  - 2
# SP  - 347
# EP  - 353
# SN  - 0035-2381
# PY  - 1930
# PB  - Université catholique de Louvain.
# ER  -
#     """,
#         False,
#     ],
#     [
#         """
# TY  - JOUR
# TI  - La surnaturalisation des vertus
# AU  - M.-D. Chenu
# T2  - Bulletin Thomiste
# PY  - 1932
# SP  - 93
# EP  - 96
# ER  -
# """,
#         False,
#     ],
# ]

# ris_ids = ["inconnue", "surnaturalisation"]


# from devtools import debug


# @pytest.mark.parametrize("ris, status", test_bibliographies_ris, ids=ris_ids)
# def test_ris_parser(ris, status, file_regression, tmp_path, check_pdfs):
#     parser = RisParser(tmp_path, fetch_only=1)
#     parser.read(ris)
#     debug(parser.records)
#     report = parser.run()
#     if status:
#         assert "Output:" in report
#         with parser.results[0].open("rb") as f:
#             file_regression.check(
#                 f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
#             )
#     else:
#         assert "Failed to match :(" in report


# def test_base_parser():
#     parser = InputParser(Path("."))
#     with pytest.raises(NotImplementedError):
#         parser.read("Inputstr")
