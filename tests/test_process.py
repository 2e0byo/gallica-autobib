from collections import namedtuple
from pathlib import Path

import pytest
from gallica_autobib.process import (
    ExtractionError,
    deanomalise,
    detect_spine,
    extract_image,
    filter_algorithm_brute_force,
    generate_filename,
    get_crop_bounds,
    prepare_img,
    process_pdf,
)
from PIL import Image
from PyPDF4 import PdfFileReader


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
    ImgTest(Path("tests/test_process/tiff.pdf"), "tiff"),
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
    bbox = (46, 116, 841, 1393)
    res = get_crop_bounds(img)
    for i, val in enumerate(bbox):
        assert abs(res[i] - val) < 7


def test_crop_bounds_rh():
    inf = "tests/test_process/rh.jpg"
    img = Image.open(inf)
    bbox = (161, 158, 899, 1394)
    res = get_crop_bounds(img)
    for i, val in enumerate(bbox):
        assert abs(res[i] - val) < 7


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
    "tests/test_process/tiff-000.tif",
]


@pytest.mark.parametrize("inf", filter_tests)
def test_filter_brute_force(inf, image_regression, tmp_path):
    img = Image.open(inf)
    img = img.crop(get_crop_bounds(img))
    if img.mode != "1":
        img = filter_algorithm_brute_force(img)

    img.save(f"{tmp_path}/test.jpg")
    with (tmp_path / f"test.jpg").open("rb") as f:
        image_regression.check(f.read())


def test_process_pdf_no_preserve(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    process_pdf(inf, tmp_path / "test1.pdf", has_cover_page=True)
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
    process_pdf(inf, preserve_text=True, has_cover_page=True)
    with (tmp_path / "processed-test.pdf").open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


@pytest.mark.xfail
def test_process_pdf_equal_size(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    process_pdf(inf, tmp_path / "test1.pdf", equal_size=True, has_cover_page=True)
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
