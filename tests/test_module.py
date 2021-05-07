import pytest
from gallica_autobib.models import (
    Article,
    Book,
    Collection,
    Journal,
    BibBase,
    GallicaBibObj,
)
from devtools import debug


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
