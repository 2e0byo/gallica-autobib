import pytest
from devtools import debug
from gallica_autobib.gallipy import Resource
from gallica_autobib.models import Article, Journal
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


def test_extract(gallica_resource, file_regression):
    gallica_resource.target.pages = gallica_resource.target.pages[:3]
    either = gallica_resource.extract()
    assert not either.is_left
    f = either.value
    file_regression.check(f, binary=True, extension=".pdf")
