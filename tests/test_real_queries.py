from gallica_autobib.module import Query, Article


def test_match_query():
    a = Article(
        journal_title="La vie spirituelle",
        pages=list(range(135, 138)),
        title="Pour lire saint Augustin",
        author="Daniélou",
        year=1930,
    )
    q = Query(a)
    resp = q.run()
    assert resp.target
    assert resp.candidate.journal_title == "La vie spirituelle, ascétique et morale"
