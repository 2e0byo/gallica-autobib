from collections import namedtuple
from pathlib import Path

import pytest
from gallica_autobib.process import (ExtractionError, crop_bounds, deanomalise,
                                     detect_spine, extract_image,
                                     filter_algorithm_brute_force,
                                     generate_filename, ocr_crop_bounds,
                                     prepare_img, process_pdf)
from gallica_autobib.query import UnscaledPageData
from PIL import Image, ImageOps
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
        image_regression.check(f.read(), diff_threshold=0.2)


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


bounds_tests = [
    ("tests/test_process/test_get_bounds2.jpg", (558, 32, 2034, 2008)),
    ("tests/test_process/rh.jpg", (161, 158, 899, 1394)),
    ("tests/test_process/lh.jpg", (46, 116, 841, 1393)),
    ("tests/test_process/test_get_bounds.jpg", (558, 32, 2034, 2008)),
]


def show(img, bounds):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots()
    plt.imshow(img)
    box = ax.add_patch(
        Rectangle(
            bounds[:2],
            bounds[2] - bounds[0],
            bounds[3] - bounds[1],
            edgecolor="red",
            facecolor="none",
            lw=2,
        )
    )
    plt.show()


@pytest.mark.parametrize("f, bbox", bounds_tests)
def test_get_crop_bounds(f, bbox):
    img = Image.open(f)
    bounds = crop_bounds(img)
    # handy when setting up new testcases for test-driven
    # show(img, bounds)
    assert bounds == pytest.approx(bbox, rel=7)


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
    img = img.crop(crop_bounds(img))
    if img.mode != "1":
        img = filter_algorithm_brute_force(img)

    img.save(f"{tmp_path}/test.jpg")
    with (tmp_path / f"test.jpg").open("rb") as f:
        image_regression.check(f.read(), diff_threshold=0.2)


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


def test_process_pdf_equal_size(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    process_pdf(inf, tmp_path / "test1.pdf", equal_size=True, has_cover_page=True)
    with (tmp_path / "test1.pdf").open("rb") as f:
        file_regression.check(
            f.read(), extension=".pdf", binary=True, check_fn=check_pdfs
        )


def test_process_pdf_equal_size_preserve(file_regression, tmp_path, check_pdfs):
    inf = Path("tests/test_gallica_resource/test_download_pdf.pdf")
    process_pdf(
        inf,
        tmp_path / "test1.pdf",
        equal_size=True,
        has_cover_page=True,
        preserve_text=True,
    )
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


def test_ocr_crop():
    img = Image.open("tests/test_process/aug-000.jpg")
    img = ImageOps.grayscale(img)
    ocr_bounds = UnscaledPageData((20, 20), (100, 200), 300, 500)
    upper, lower = ocr_crop_bounds(img, ocr_bounds)
    assert upper.x == 63
    assert upper.y == 63
    assert lower.x == 307
    assert lower.y == 657
