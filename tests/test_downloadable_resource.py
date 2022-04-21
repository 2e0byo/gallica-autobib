import pytest
from gallica_autobib.query import DownloadableResource


@pytest.mark.web
def test_set_max_pages():
    ark = "https://gallica.bnf.fr/ark:/12148/bpt6k65545564"
    resource = DownloadableResource()
    resource.ark = ark
    resource.set_max_pages()
    assert 1 == resource.start_p
    assert 154 == resource.end_p
