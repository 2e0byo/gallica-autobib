import pytest
from pathlib import Path
from devtools import debug
from gallica_autobib.gallipy import Resource
from gallica_autobib.models import Article, Journal, Book, Collection
from gallica_autobib.query import GallicaResource


@pytest.fixture
def gallica_resource():
    target = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 158)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    source = Journal(
        year=[
            1919,
            1920,
            1921,
            1922,
            1923,
            1924,
            1925,
            1926,
            1927,
            1928,
            1929,
            1930,
            1931,
            1932,
            1933,
            1934,
            1935,
            1936,
            1937,
            1938,
            1939,
            1940,
            1941,
            1942,
            1943,
            1944,
            1945,
        ],
        publisher="Le Cerf (Paris)",
        ark="http://catalogue.bnf.fr/ark:/12148/cb34406663m",
        journaltitle="La Vie spirituelle, ascétique et mystique",
        number=None,
        volume=None,
    )
    yield GallicaResource(target, source)


def test_get_issue(gallica_resource):
    assert gallica_resource.get_issue()


def test_ark(gallica_resource):
    ark = gallica_resource.ark
    assert str(ark) == "ark:/12148/bpt6k9735634r"


def test_by_vol(gallica_resource):
    gallica_resource.target.volume = 24
    ark = gallica_resource.ark
    assert str(ark) == "ark:/12148/bpt6k9735634r"


def test_resource(gallica_resource):
    res = gallica_resource.resource
    assert isinstance(res, Resource)


def test_pnos(gallica_resource):
    assert 141 == gallica_resource.start_p
    assert 163 == gallica_resource.end_p


def test_generate_blocks(gallica_resource):
    expected = [(0, 5), (5, 5), (10, 5), (15, 5), (20, 1)]
    res = list(gallica_resource._generate_blocks(0, 20, 5))


def test_generate_short_block(gallica_resource):
    expected = [(0, 4)]
    res = list(gallica_resource._generate_blocks(0, 3, 100))
    assert res == expected


def test_download_pdf(gallica_resource, file_regression, tmp_path, check_pdfs):
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
    res = GallicaResource(book, book)


@pytest.mark.xfail
def test_journal():
    journal = Journal(journaltitle="j", year="1930")
    res = GallicaResource(journal, journal)


@pytest.mark.xfail
def test_collection():
    coll = Collection(title="t", author="a")
    res = GallicaResource(coll, coll)
