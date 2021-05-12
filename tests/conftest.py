import pytest
import logging
from diff_pdf_visually import pdfdiff
from pathlib import Path
import shutil

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def check_pdfs():
    def check(a, b):
        assert pdfdiff(a, b, threshold=70), f"Pdf files {a} and {b} differ"

    yield check


@pytest.fixture()
def fixed_tmp_path():
    path = Path("/tmp/pytest-template-tmpdir/")
    if path.exists():
        raise Exception("tmpdir exists")
    path.mkdir()
    yield path
    shutil.rmtree(path)
