from copy import deepcopy

import pytest
from gallica_autobib.models import Article, Book, Journal
from gallica_autobib.query import GallicaSRU, Match, Query, make_string_boring

strings = [["asciitest", "asciitest"], [None, None]]


@pytest.mark.parametrize("inp,out", strings)
def test_boring_string(inp, out):
    assert make_string_boring(inp) == out


def test_match_duplicate():
    a = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    b = a.copy()
    m = Match(a, b)
    assert m.score == 1


def test_close_match():
    a = Journal(journaltitle="La vie spirituelle", year=1930)
    b = Journal(
        journaltitle="La vie spirituelle, ascétique et mystique",
        year=list(range(1920, 1950)),
    )
    m = Match(a, b)
    assert m.score > 0.7


def test_match_repr(data_regression):
    a = Journal(journaltitle="La vie spirituelle", year=1930)
    b = Journal(
        journaltitle="La vie spirituelle, ascétique et mystique",
        year=list(range(1920, 1950)),
    )
    m = Match(a, b)
    data_regression.check(repr(m))


def test_sort_match():
    a = Journal(journaltitle="La vie spirituelle", year=1930)
    c = Journal(journaltitle="La vie spirituelle", year=1931)
    b = Journal(
        journaltitle="La vie spirituelle, ascétique et mystique",
        year=list(range(1920, 1950)),
    )
    d = Journal(
        journaltitle="La vie spirituelle, ascétique et mystique",
        year=1930,
    )
    f = Journal(
        journaltitle="La vie spirituelle, ascétique et mystique",
        year=list(range(1940, 1950)),
    )
    m1 = Match(a, b)
    m2 = Match(a, c)
    assert m1 == deepcopy(m1)
    assert m1 > m2
    assert m2 < m1
    assert Match(b, a) < Match(b, d)
    assert m1 > Match(a, f)


def test_equal_ignore_extra_data():
    a = Journal(journaltitle="La vie spirituelle", year=1930)
    c = Journal(journaltitle="La vie spirituelle", year=1931)
    e = Journal(journaltitle="La vie spirituelle", year=1931, number=2)
    assert Match(a, e) == Match(a, c)


def test_missing_editor():
    a = Book(
        title="My very long title",
        year=1960,
        publisher="Cerf",
        author="me",
        editor="you",
    )
    b = Book(title="My very long title", year=1960, publisher="Cerf", author="me")
    m = Match(a, b)
    assert m.score > 0.7


query_candidates = [
    [
        {"title": "La vie spirituelle", "recordtype": "per"},
        'bib.title all "la vie spirituelle" and bib.recordtype all "per',
    ],
    [{"title": "la vie spirituelle"}, 'bib.title all "la vie spirituelle'],
]


@pytest.fixture
def query():
    a = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    q = Query(a)
    yield q


def test_bibobj(query):
    data = {
        "schema": "dc",
        "identifier": [
            "http://catalogue.bnf.fr/ark:/12148/cb34406663m",
            "ISSN 09882480",
        ],
        "title": "La Vie spirituelle, ascétique et mystique",
        "publisher": "Le Cerf (Paris)",
        "date": "1919-1945",
        "language": ["fre", "français"],
        "type": [
            {"lang": "fre", "text": "publication en série imprimée"},
            {"lang": "eng", "text": "printed serial"},
            {"lang": "eng", "text": "text"},
        ],
    }
    resp = query.resp_to_obj(data.copy())
    assert isinstance(resp, Journal)
    assert resp.ark == data["identifier"][0]
    assert len(resp.ark) > 1
    assert resp.journaltitle == data["title"]
    assert resp.publisher == data["publisher"]


def test_get_at_str(query):
    assert query.get_at_str("this") == "this"
    assert query.get_at_str(["this"]) == "this"
    assert query.get_at_str(["this", "that"]) == "this"
    assert query.get_at_str(None) is None
    assert query.get_at_str([None, "this"]) is None

    l = [
        "http://catalogue.bnf.fr/ark:/12148/cb34406663m",
        "ISSN 09882480",
    ]
    assert query.get_at_str(l) == "http://catalogue.bnf.fr/ark:/12148/cb34406663m"


def test_gallica_sru():
    g = GallicaSRU()

    assert [k for k, v in g.__repr_args__()] == ["client"]
