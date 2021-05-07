from devtools import debug
from gallica_autobib.models import Article
from gallica_autobib.query import Query


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
