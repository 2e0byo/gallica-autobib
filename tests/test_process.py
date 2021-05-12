from gallica_autobib.process import (
    generate_filename,
    filter_algorithm_brute_force,
    extract_image,
    ExtractionError,
    get_crop_bounds,
    deanomalise,
    detect_spine,
    prepare_img,
    process_pdf,
)
import pytest
from PyPDF4 import PdfFileReader
from pathlib import Path
from collections import namedtuple
from devtools import debug
from PIL import Image, ImageOps


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
    ImgTest(Path("tests/test_gallica_resource/test_download_pdf.pdf"), "jpg"),
    ImgTest(Path("tests/test_process/tiff.pdf"), "tiff"),
    # ImgTest(Path("tests/test_process/test4.pdf"), "tiff"),
]


@pytest.mark.parametrize("img_test", test_image_pdf)
def test_extract_image(img_test, image_regression, tmp_path):
    with img_test.testfile.open("rb") as f:
        reader = PdfFileReader(f)
        page1 = reader.getPage(0)
        img, type_ = extract_image(page1)
        assert type_ == img_test.type
    outf = tmp_path / f"test.{type_}"
    img.save(str(outf))
    with outf.open("rb") as f:
        image_regression.check(f.read())


def test_deanomalise():
    assert deanomalise([0, 1, 1, 5]) == 1
    assert deanomalise([1, 1, 1]) == 1
    assert deanomalise([12]) == 12


def test_detect_spine():
    inf = "tests/test_process/lh.jpg"
    img = Image.open(inf)
    img = prepare_img(img, 128)
    assert detect_spine(img).lh_page
    inf = "tests/test_process/rh.jpg"
    img = Image.open(inf)
    img = prepare_img(img, 128)
    assert not detect_spine(img).lh_page


def test_crop_bounds_lh():
    inf = "tests/test_process/lh.jpg"
    img = Image.open(inf)
    assert get_crop_bounds(img) == (46, 151, 783, 1389)


def test_crop_bounds_rh():
    inf = "tests/test_process/rh.jpg"
    img = Image.open(inf)
    assert get_crop_bounds(img) == (162, 165, 896, 1391)


filter_tests = [
    "tests/test_process/rh.jpg",
    "tests/test_process/lh.jpg",
    "tests/test_process/aug-000.jpg",
    "tests/test_process/aug-001.jpg",
    "tests/test_process/aug-002.jpg",
    "tests/test_process/aug-020.jpg",
    "tests/test_process/ascese-000.jpg",
    "tests/test_process/ascese-001.jpg",
    "tests/test_process/rais-003.jpg",
    "tests/test_process/rais-004.jpg",
]


@pytest.mark.parametrize("inf", filter_tests)
def test_filter_brute_force(inf, image_regression, tmp_path):
    img = Image.open(inf)
    img = img.crop(get_crop_bounds(img))
    img = filter_algorithm_brute_force(img)

    img.save(f"{tmp_path}/test.jpg")
    with (tmp_path / f"test.jpg").open("rb") as f:
        image_regression.check(f.read())


def test_process_pdf_no_preserve(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    process_pdf(inf, tmp_path / "test1.pdf")
    with (tmp_path / "test1.pdf").open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_process_pdf_preserve(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    with inf.open("rb") as i:
        with (tmp_path / "test.pdf").open("wb") as f:
            f.write(i.read())
    inf = tmp_path / "test.pdf"
    process_pdf(inf, preserve_text=True)
    with (tmp_path / "processed-test.pdf").open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


@pytest.mark.xfail
def test_process_pdf_equal_size(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    process_pdf(inf, tmp_path / "test1.pdf", equal_size=True)
    with (tmp_path / "test1.pdf").open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_generate_filename(tmp_path):
    start = tmp_path / "test-1.txt"
    outf = generate_filename(start)
    with outf.open("w") as f:
        f.write("-")
    outf = generate_filename(start)
    assert outf == tmp_path / "test-1-0.txt"
    with outf.open("w") as f:
        f.write("!-")
    outf = generate_filename(start)
    assert outf == tmp_path / "test-1-1.txt"
    start = tmp_path / "augustin.pdf"
    outf = generate_filename(start)
    with outf.open("w") as f:
        f.write("=")
    outf = generate_filename(start)
    assert outf == tmp_path / "augustin-0.pdf"
