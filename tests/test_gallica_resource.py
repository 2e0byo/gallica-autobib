import pickle
from pathlib import Path
from re import search
from typing import Union

import pytest
from gallica_autobib.gallipy import Ark, Resource
from gallica_autobib.gallipy.ark import ArkParsingError
from gallica_autobib.models import Article, Book, Collection, Journal
from gallica_autobib.query import GallicaResource, Query


@pytest.fixture(scope="session")
def pages():
    inf = Path("tests/test_gallica_resource/pages.pickle")
    with inf.open("rb") as f:
        yield pickle.load(f)


def test_ark(gallica_resource):
    ark = gallica_resource.ark
    assert get_ark(ark) == get_ark("ark:/12148/bpt6k9735634r")


def test_by_vol(gallica_resource):
    gallica_resource.target.volume = 24
    ark = gallica_resource.ark
    assert get_ark(ark) == get_ark("ark:/12148/bpt6k9735634r")


def test_resource(gallica_resource):
    res = gallica_resource.resource
    assert isinstance(res, Resource)


@pytest.mark.web
def test_pnos(gallica_resource):
    assert 141 == gallica_resource.start_p
    assert 163 == gallica_resource.end_p


def test_generate_blocks(gallica_resource):
    list(gallica_resource._generate_blocks(0, 20, 5))


def test_generate_short_block(gallica_resource):
    expected = [(0, 4)]
    res = list(gallica_resource._generate_blocks(0, 3, 100))
    assert res == expected


@pytest.mark.web
@pytest.mark.download
def test_download_pdf(gallica_resource, file_regression, tmp_path, check_pdfs):
    gallica_resource.ark  # trigger search before we edit pages
    gallica_resource.target.pages = gallica_resource.target.pages[:3]

    outf = tmp_path / "test.pdf"
    gallica_resource.download_pdf(outf)
    with outf.open("rb") as f:
        file_regression.check(
            f.read(), binary=True, extension=".pdf", check_fn=check_pdfs
        )


@pytest.mark.xfail
def test_book():
    book = Book(title="t", author="s", editor="e")
    GallicaResource(book, book)


@pytest.mark.xfail
def test_journal():
    journal = Journal(journaltitle="j", year="1930")
    GallicaResource(journal, journal)


@pytest.mark.xfail
def test_collection():
    coll = Collection(title="t", author="a")
    GallicaResource(coll, coll)


def test_invalid_ark():
    source = Journal(journaltitle="j", year="1930", ark="notavalidark")
    target = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 158)),
        title="Pour lire saint Augustin",
        author="M.-D. Chenu",
        year=1930,
    )
    with pytest.raises(ArkParsingError):
        GallicaResource(target, source)


def test_repr(gallica_resource, data_regression):
    data_regression.check(repr(gallica_resource))


candidates = [
    [
        Article(
            journaltitle="La Vie spirituelle",
            author="M.-D. Chenu",
            pages=list(range(547, 552)),
            volume=7,
            year=1923,
            title="Ascèse et péché originel",
        ),
        dict(ark="ark:/12148/bpt6k97356214"),
    ],
    [
        Article(
            journaltitle="La Vie spirituelle",
            author="Réginald Garrigou-lagrange",
            year=1921,
            title="La perfection de la charité",
            volume=2,
            pages=list(range(1, 21)),
        ),
        dict(ark="ark:/12148/bpt6k9736026f"),
    ],
]


def get_ark(arkstr: Union[str, Ark]):
    """Reliable way of matching arks."""
    return search(r".*(ark:/.*)", str(arkstr)).group(1)


@pytest.mark.web
@pytest.mark.parametrize("candidate, params", candidates)
def test_real_queries_no_toc(candidate, params):
    source = Query(candidate).run().candidate
    gallica_resource = GallicaResource(candidate, source)
    gallica_resource.consider_toc = False
    assert get_ark(gallica_resource.ark) == get_ark(params["ark"])


@pytest.mark.web
@pytest.mark.parametrize("candidate, params", candidates)
def test_real_queries_toc(candidate, params):
    source = Query(candidate).run().candidate
    gallica_resource = GallicaResource(candidate, source)
    assert get_ark(gallica_resource.ark) == get_ark(params["ark"])


def test_parse_description_range(gallica_resource):
    desc = "1922/10 (A4,T7,N37)-1923/03 (A4,T7,N42)."
    resp = gallica_resource.parse_description(desc)
    assert resp["year"] == [1922, 1923]
    assert resp["volume"] == 7
    assert resp["number"] == list(range(37, 43))


def test_parse_description_shorthand(gallica_resource):
    desc = "1924/04 (A5,T10)-1924/09."
    resp = gallica_resource.parse_description(desc)
    assert resp["year"] == 1924
    assert resp["volume"] == 10
    assert resp["number"] is None


def test_parse_description_range_everywhere(gallica_resource):
    desc = "1922/10 (A4,T7,N37)-1923/03 (A4,T8,N42)."
    resp = gallica_resource.parse_description(desc)
    assert resp["year"] == [1922, 1923]
    assert resp["volume"] == [7, 8]
    assert resp["number"] == list(range(37, 43))


def test_parse_description(gallica_resource):
    desc = "1922/10 (A4,T7,N37)."
    resp = gallica_resource.parse_description(desc)
    assert resp["year"] == 1922
    assert resp["volume"] == 7
    assert resp["number"] == 37


def test_parse_no_description(gallica_resource):
    desc = ""
    resp = gallica_resource.parse_description(desc)
    assert all(v is None for k, v in resp.items())


def test_parse_partial_description(gallica_resource):
    desc = "1922/10 (T7)."
    resp = gallica_resource.parse_description(desc)
    assert resp["year"] == 1922
    assert resp["volume"] == 7
    assert resp["number"] is None


def test_physical_pno(gallica_resource, pages):
    resp = gallica_resource.get_physical_pno("10", pages=pages)
    assert resp == "16"


def test_last_pno(gallica_resource, pages):
    resp = gallica_resource.get_last_pno(pages)
    assert resp == "676"


def test_ocr_bounds(gallica_resource, data_regression):
    gallica_resource.ark  # trigger search before we edit pages
    gallica_resource.target.pages = gallica_resource.target.pages[:3]
    bounds = gallica_resource.ocr_bounds
    data_regression.check([x._asdict() for x in bounds])


@pytest.mark.xfail
def test_ocr_find_article_in_journal(gallica_resource):
    ark = "ark:/12148/bpt6k9737289z"
    target = Article(
        title="La contemplation mystique requiert-elle des idées infuses ?",
        journaltitle="La Vie spirituelle, ascétique et mystique (Supplément)",
        year=1922,
        pages=list(range(1, 22)),
        author="Réginald Garrigou-Lagrange",
    )
    journal = Resource(ark)
    pages = journal.pagination_sync().value
    assert not gallica_resource.ocr_find_article_in_journal(journal, pages)
    gallica_resource.target = target
    assert gallica_resource.ocr_find_article_in_journal(journal, pages)
