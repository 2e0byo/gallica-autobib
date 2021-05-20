import pytest
from gallica_autobib.models import Article, BibBase, Book, Collection, Journal


def test_article():
    a = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="M.-D. Chenu",
        year=1930,
    )
    assert isinstance(a, Article)
    assert isinstance(a._source(), Journal)
    assert (
        a.generate_query()
        == 'bib.publicationdate all "1930" and bib.title all "La vie spirituelle" and bib.recordtype all "per"'
    )
    assert a._source().translate()["title"] == "La vie spirituelle"
    assert isinstance(a.pages, list)
    assert isinstance(a.pages[0], str)
    assert a.name() == "Pour lire saint Augustin (M.-D. Chenu)"
    assert a.name(short=4) == "Pour (M.-D)"


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


def test_bibtex_render_article(file_regression):
    a = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="M.-D. Chenu",
        year=1930,
        volume=12,
        number=1,
    )
    file_regression.check(a.bibtex(), extension=".bib")
