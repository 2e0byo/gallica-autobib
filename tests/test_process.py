from gallica_autobib.process import extract_image, ExtractionError
import pytest
from PyPDF4 import PdfFileReader
from pathlib import Path


def test_extract_image(image_regression):
    with Path("tests/test_process/test.pdf").open("rb") as f:
        reader = PdfFileReader(f)
        page1 = reader.getPage(1)
        img, type_ = extract_image(page1)
    image_regression.check(img)


def test_extract_no_image():
    with pytest.raises(ExtractionError, match=".*No image.*"):
        reader = PdfFileReader("tests/test_process/test-blank.pdf")
        page1 = reader.getPage(0)
        extract_image(page1)
