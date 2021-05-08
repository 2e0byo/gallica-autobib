import pytest
from gallica_autobib.models import Article
from gallica_autobib.parsers import ParsingError, parse_bibtex, parse_ris


def test_invalid_bibtex():
    with pytest.raises(ParsingError, match="Unable to parse"):
        parse_bibtex("loadanonsensestring")
        parse_bibtex(None)


def test_invalid_ris():
    with pytest.raises(ParsingError, match="Unable to parse"):
        parse_ris("loadanonsensestring")
        parse_ris(None)


def test_bib_article():
    bib = """
    @Article{danielou30:_pour_augus,
      author =       {Jean Daniélou},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      volume =    24,
      pages =     {135-57}}
    """
    art = Article(
        journaltitle="La Vie spirituelle",
        pages=list(range(135, 158)),
        title="Pour lire saint Augustin",
        author="Jean Daniélou",
        year=1930,
        language="french",
        volume=24,
    )
    assert parse_bibtex(bib)[0] == art


def test_bib_article_one_page():
    bib = """
    @Article{danielou30:_pour_augus,
      author =       {Jean Daniélou},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      volume =    24,
      pages =     12}
    """
    art = Article(
        journaltitle="La Vie spirituelle",
        pages=[12],
        title="Pour lire saint Augustin",
        author="Jean Daniélou",
        year=1930,
        language="french",
        volume=24,
    )
    assert parse_bibtex(bib)[0] == art


def test_bib_article_roman():
    bib = """
    @Article{danielou30:_pour_augus,
      author =       {Jean Daniélou},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      volume =    24,
      pages =     {i-xi}}
    """
    art = Article(
        journaltitle="La Vie spirituelle",
        pages=["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi"],
        title="Pour lire saint Augustin",
        author="Jean Daniélou",
        year=1930,
        language="french",
        volume=24,
    )
    assert parse_bibtex(bib)[0] == art


def test_bib_inbook():
    bib = """
    @inbook{danielou30:_pour_augus,
      author =       {Jean Daniélou},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      volume =    24,
      pages =     {i-xi},
      url={http://nonsuch.org}
    }
    """
    with pytest.raises(ParsingError, match=".*Unsupported.*"):
        parse_bibtex(bib)


def test_ris_article():
    ris = """
TY  - JOUR
TI  - HENRI BREMOND E IL MODERNISMO
AU  - Savignano, Armando
C1  - Full publication date: ottobre-dicembre 1982
DB  - JSTOR
EP  - 649
IS  - 4
PB  - Vita e Pensiero – Pubblicazioni dell’Università Cattolica del Sacro Cuore
PY  - 1982
SN  - 00356247, 18277926
SP  - 627
T2  - Rivista di Filosofia Neo-Scolastica
UR  - http://www.jstor.org/stable/43061043
VL  - 74
Y2  - 2021/05/07/
ER  - 
    """
    art = Article(
        journaltitle="Rivista di Filosofia Neo-Scolastica",
        volume=74,
        pages=list(range(627, 650)),
        title="HENRI BREMOND E IL MODERNISMO",
        author="Savignano, Armando",
        year="1982",
        publisher="Vita e Pensiero – Pubblicazioni dell’Università Cattolica del Sacro Cuore",
        number=4,
    )
    assert parse_ris(ris)[0] == art


def test_ris_other():
    ris = """
TY  - ABST
TI  - HENRI BREMOND E IL MODERNISMO
AU  - Savignano, Armando
C1  - Full publication date: ottobre-dicembre 1982
DB  - JSTOR
EP  - 649
IS  - 4
PB  - Vita e Pensiero – Pubblicazioni dell’Università Cattolica del Sacro Cuore
PY  - 1982
SN  - 00356247, 18277926
SP  - 627
T2  - Rivista di Filosofia Neo-Scolastica
UR  - http://www.jstor.org/stable/43061043
VL  - 74
Y2  - 2021/05/07/
ER  - 
    """
    with pytest.raises(ParsingError, match=".*Unsupported.*"):
        parse_ris(ris)
