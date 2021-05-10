import pytest
from diff_pdf_visually import pdfdiff


@pytest.fixture
def check_pdfs():
    def check(a, b):
        assert pdfdiff(a, b), f"Pdf files {a} and {b} differ"

    yield check
