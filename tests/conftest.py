import logging
import shutil
from pathlib import Path

import pytest
from diff_pdf_visually import pdfdiff
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
        year=list(range(1919, 1946)),
        publisher="Le Cerf (Paris)",
        ark="http://catalogue.bnf.fr/ark:/12148/cb34406663m",
        journaltitle="La Vie spirituelle, ascétique et mystique",
    )
    yield GallicaResource(target, source)
