import logging
import shutil
from pathlib import Path

import pytest
from diff_pdf_visually import pdfdiff

logging.basicConfig(level=logging.DEBUG)
from gallica_autobib.models import Article, Journal
from gallica_autobib.query import GallicaResource


@pytest.fixture
def check_pdfs():
    def check(a, b):
        assert pdfdiff(a, b, threshold=30), f"Pdf files {a} and {b} differ"

    yield check


@pytest.fixture(scope="module")
def fixed_tmp_path():
    path = Path("/tmp/pytest-template-tmpdir/")
    if path.exists():
        raise Exception("tmpdir exists")
    path.mkdir()
    yield path
    shutil.rmtree(path)


@pytest.fixture
def gallica_resource():
    target = Article(
        journaltitle="La vie spirituelle",
        pages=list(range(135, 158)),
        title="Pour lire saint Augustin",
        author="M.-D. Chenu",
        year=1930,
    )
    source = Journal(
        year=[
            1919,
            1920,
            1921,
            1922,
            1923,
            1924,
            1925,
            1926,
            1927,
            1928,
            1929,
            1930,
            1931,
            1932,
            1933,
            1934,
            1935,
            1936,
            1937,
            1938,
            1939,
            1940,
            1941,
            1942,
            1943,
            1944,
            1945,
        ],
        publisher="Le Cerf (Paris)",
        ark="http://catalogue.bnf.fr/ark:/12148/cb34406663m",
        journaltitle="La Vie spirituelle, ascétique et mystique",
        number=None,
        volume=None,
    )
    yield GallicaResource(target, source)
