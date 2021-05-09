from gallica_autobib.process import extract_image, ExtractionError
import pytest
from PyPDF4 import PdfFileReader
from pathlib import Path
from collections import namedtuple
from tempfile import TemporaryDirectory
from devtools import debug


def test_extract_no_image():
    with pytest.raises(ExtractionError, match=".*No image.*"):
        reader = PdfFileReader("tests/test_process/test-blank.pdf")
        page1 = reader.getPage(0)
        extract_image(page1)


ImgTest = namedtuple("ImgTest", ("testfile", "type"))

test_image_pdf = [
    ImgTest(Path("tests/test_process/test5.pdf"), "png"),
    ImgTest(Path("tests/test_process/test2.pdf"), "jpg"),
    ImgTest(Path("tests/test_process/test3.pdf"), "jp2"),
    # ImgTest(Path("tests/test_process/test4.pdf"), "tiff"),
]


@pytest.mark.parametrize("img_test", test_image_pdf)
def test_extract_image(img_test, image_regression):
    with img_test.testfile.open("rb") as f:
        reader = PdfFileReader(f)
        page1 = reader.getPage(0)
        img, type_ = extract_image(page1)
        assert type_ == img_test.type
    with TemporaryDirectory() as tmpdir:
        outf = Path(f"{tmpdir}/test.{type_}")
        img.save(str(outf))
        with outf.open("rb") as f:
            image_regression.check(f.read())
