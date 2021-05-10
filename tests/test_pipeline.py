from gallica_autobib.pipeline import BibtexParser, RisParser
import pytest
from pathlib import Path

test_bibliographies_bibtex = [
    """
    @Article{danielou30:_pour_augus,
      author =       {Jean Daniélou},
      title =        {Pour lire saint Augustin},
      journaltitle = {La Vie spirituelle},
      year =      1930,
      language =  {french},
      pages =     {135-57}}
"""
]
# volume =    24,

ids = ["pour-lire-augustin"]


@pytest.mark.parametrize("bibtex", test_bibliographies_bibtex, ids=ids)
def test_bibtex_parser(bibtex, file_regression, tmp_path, check_pdfs):
    parser = BibtexParser(tmp_path)
    parser.read(bibtex)
    status = parser.run()
    print(status)
    from devtools import debug

    debug(parser.results)
    with parser.results[0].open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )
    # TODO: regression check more than one file
