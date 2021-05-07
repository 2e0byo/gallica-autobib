import pytest
from gallica_autobib.module import (
    Article,
    Book,
    Collection,
    Journal,
    Match,
    BibBase,
    make_string_boring,
    Query,
    GallicaBibObj,
)
from devtools import debug

strings = [["asciitest", "asciitest"], [None, None]]


@pytest.mark.parametrize("inp,out", strings)
def test_boring_string(inp, out):
    assert make_string_boring(inp) == out


candidates = [
    {
        "data": dict(
            journal_title="La vie spirituelle",
            type="per",
            year=1930,
            author="Daniélou",
            title=None,
            publisher=None,
        ),
        "query": 'bib.title all "la vie spirituelle" and bib.recordtype all "per" and bib.publicationdate all "1930" and bib.author all "Daniélou"',
    }
]


def test_article():
    a = Article(
        journal_title="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    assert isinstance(a, Article)
    assert isinstance(a._source(), Journal)
    assert (
        a.generate_query()
        == 'bib.publicationdate all "1930" and bib.title all "La vie spirituelle" and bib.recordtype all "per"'
    )
    assert a._source().translate()["title"] == "La vie spirituelle"


def test_book():
    a = Book(title="Title", publisher="Cerf", year=1901, author="me")
    assert isinstance(a, Book)
    assert a._source() is a
    assert a._source().translate() == {
        k: v for k, v in dict(a).items() if k != "editor"
    }


def test_collection():
    a = Collection(title="Title", publisher="Cerf", year=1901, author="me")
    assert isinstance(a, Collection)
    assert a._source() is a
    assert a._source().translate() == {
        k: v for k, v in dict(a).items() if k != "editor"
    }


def test_match_duplicate():
    a = Article(
        journal_title="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    b = a.copy()
    m = Match(a, b)
    assert m.score == 1


def test_close_match():
    a = Journal(journal_title="La vie spirituelle", year=1930)
    b = Journal(
        journal_title="La vie spirituelle, ascétique et mystique",
        year=list(range(1920, 1950)),
    )
    m = Match(a, b)
    assert m.score > 0.7


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


@pytest.mark.parametrize("kwargs,outstr", query_candidates)
def test_assemble_query(kwargs, outstr):
    assert BibBase.assemble_query(kwargs=outstr)


@pytest.fixture
def query():
    a = Article(
        journal_title="La vie spirituelle",
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
    assert resp.journal_title == data["title"]
    assert resp.publisher == data["publisher"]


def test_get_at_str():
    a = Article(
        journal_title="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    q = Query(a)
    assert q.get_at_str("this") == "this"
    assert q.get_at_str(["this"]) == "this"
    assert q.get_at_str(["this", "that"]) == "this"
    assert q.get_at_str(None) is None
    assert q.get_at_str([None, "this"]) is None

    l = [
        "http://catalogue.bnf.fr/ark:/12148/cb34406663m",
        "ISSN 09882480",
    ]
    assert q.get_at_str(l) == "http://catalogue.bnf.fr/ark:/12148/cb34406663m"
