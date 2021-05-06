import pytest
from gallica_autobib.module import Article, Book, Collection, Journal

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
        "query": 'bib.title all "la vie spirituelle" and bib.recordtype all "per" and bib.publicationdate all "1930" and bib.author "Daniélou"',
    }
]


def test_article():
    a = Article(
        journal_title="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
    )
    assert isinstance(a, Article)
    assert isinstance(a._source(), Journal)
    assert (
        a.get_query()
        == 'bib.title all "La vie spirituelle" and bib.recordtype all "per"'
    )
