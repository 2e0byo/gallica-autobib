import pytest
from gallica_autobib.parsers import parse_bibtex, ParsingError
from gallica_autobib.models import Article


def test_invalid_bibtex():
    with pytest.raises(ParsingError, match="Unable to parse"):
        parse_bibtex("loadanonsensestring")
        parse_bibtex(None)


def test_article():
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
