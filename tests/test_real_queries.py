import pytest
from gallica_autobib.models import Article
from gallica_autobib.query import Query


@pytest.mark.web
def test_match_query():
    a = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    q = Query(a)
    resp = q.run()
    assert resp.target
    assert resp.candidate.journaltitle == "La Vie spirituelle, ascétique et mystique"


candidates = [
    [
        Article(
            journaltitle="La Vie spirituelle",
            author="Jean Daniélou",
            pages=list(range(547, 552)),
            volume=7,
            year=1923,
            title="Ascèse et péché originel",
        ),
        dict(ark="http://catalogue.bnf.fr/ark:/12148/cb34406663m"),
    ]
]


@pytest.mark.web
@pytest.mark.parametrize("candidate,params", candidates)
def test_queries(candidate, params):
    q = Query(candidate)
    resp = q.run()
    assert resp.target
    assert resp.candidate.ark == params["ark"]
