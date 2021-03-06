"""Fns to process.  These are wrapped in a class in pipeline, which is probably what you want."""
import logging
from collections import namedtuple
from collections.abc import Collection
from functools import partial
from io import BytesIO
from itertools import filterfalse
from numbers import Real
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING, Iterable, Tuple

import numpy as np
from PIL import Image, ImageChops, ImageOps
from PyPDF4 import PdfFileReader, PdfFileWriter
from PyPDF4.pdf import PageObject, RectangleObject
from tqdm import tqdm

# from util import show

logger = logging.getLogger(__name__)

Point = namedtuple("Point", ["x", "y"])
Bbox = namedtuple("Bbox", ["ux", "uy", "lx", "ly"])

if TYPE_CHECKING:
    from .query import UnscaledPageData


class ExtractionError(Exception):
    pass


def extract_image(page: PageObject) -> Tuple[Image.Image, str]:
    """
    Extract image from pdf without resampling.

    Modified from
    https://github.com/mstamy2/PyPDF2/blob/master/Scripts/pdf-image-extractor.py
    itself modified from
    https://stackoverflow.com/questions/2693820/extract-images-from-pdf-without-resampling-in-python
    """
    if "/XObject" in page["/Resources"]:
        xObject = page["/Resources"]["/XObject"].getObject()

        for obj in xObject:
            if xObject[obj]["/Subtype"] == "/Image":
                size = (xObject[obj]["/Width"], xObject[obj]["/Height"])
                data = xObject[obj].getData()
                if xObject[obj]["/ColorSpace"] == "/DeviceRGB":
                    mode = "RGB"
                else:
                    mode = "P"

                if "/Filter" in xObject[obj]:
                    filter_ = xObject[obj]["/Filter"]
                    if isinstance(filter_, list):
                        filter_ = filter_[0]

                    if filter_ == "/FlateDecode":
                        data = Image.frombytes(mode, size, data)
                        type_ = "png"
                    elif filter_ == "/DCTDecode":
                        type_ = "jpg"
                    elif filter_ == "/JPXDecode":
                        type_ = "jp2"
                    elif filter_ == "/CCITTFaxDecode":
                        type_ = "tiff"
                    else:
                        continue
                else:
                    type_ = "png"
                    data = Image.frombytes(mode, size, data)
                if isinstance(data, bytes):
                    data = Image.open(BytesIO(data))
        assert data
        assert type_
        logger.debug(f"Extracted image of kind {type_}.")
        return data, type_
    raise ExtractionError("No image found.")


def filter_point(point: int) -> int:
    """Filter a point.

    If point is below threshold, divide it by divisor. If above, multiple it by
    multiplier. This is a crude but effective way of skewing an image to
    black-and-white without actually thresholding it.

    """
    if point < 160:
        return round(point / 1.2)
    return round(point * 2)


_results = namedtuple("_results", ("lh_page", "crop", "bbox"))


def filter_algorithm_brute_force(img: Image.Image) -> Image.Image:
    img = ImageOps.autocontrast(img)
    img = ImageOps.posterize(img, 5)
    img = ImageOps.grayscale(img).point(filter_point)
    img = ImageOps.autocontrast(img)
    return img


def deanomalise(data: list) -> int:
    mean = np.mean(data)
    std = np.std(data)
    if not std:
        return data[0]
    data = [x for x in data if abs(x - mean) < 1.5 * std]
    return round(np.mean(data))


def detect_spine(img: Image.Image) -> _results:
    logger.debug("Detecting spine")
    threshold = 40
    midpoint = round(img.height / 2)
    lower = midpoint - 20
    upper = midpoint + 20
    first_lefts = []
    first_rights = []
    for height in (midpoint, lower, upper):
        for i in range(img.width):
            if img.getpixel((i, height)) < threshold:
                first_lefts.append(i)
                break
        for i in range(img.width - 1, 0, -1):
            if img.getpixel((i, height)) < threshold:
                first_rights.append(img.width - i)
                break

    assert first_lefts
    assert first_rights
    first_left = deanomalise(first_lefts)
    first_right = deanomalise(first_rights)
    if first_left < first_right:
        crop = first_left + 10
        return _results(True, crop, (crop, 0, img.width, img.height))
    crop = first_right - 10
    return _results(False, crop, (0, 0, img.width - crop, img.height))


def prepare_img(img: Image.Image, threshold: int = 60) -> Image.Image:
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.point(lambda p: p > threshold and 255)


def crop_bounds(img: Image.Image) -> Bbox:
    """Get crop bounds for text on page.

    The algorithm:
      1. grayscales and thresholds the image aggressively
      3. crops to slightly wider than content
    This is not very robust, but Gallica is quite standardised in its pdfs.

    We don't bother with spine detection as it seems to work fine without it
    using a very aggressive thresholding.

    Args:
      img: Image.Image: The image to process.

    Returns:
      A tuple of the rectangle to crop to.

    """
    if img.mode != "1":
        img = prepare_img(img)
    # img.show()
    # res = detect_spine(img)
    # logger.debug(res.lh_page)
    # crop out corner errors
    MARGIN_PIXELS = 40
    img = img.crop(
        (
            MARGIN_PIXELS,
            MARGIN_PIXELS,
            img.width - MARGIN_PIXELS,
            img.height - MARGIN_PIXELS,
        )
    )

    # crop to border
    bg = Image.new(img.mode, img.size, 255)
    diff = ImageChops.difference(img, bg)

    GROW_PIXELS = 10
    bbox = diff.getbbox()
    if bbox:
        left, upper, right, lower = diff.getbbox()
    else:
        left, upper, right, lower = img.getbbox()

    # show(img, [diff.getbbox()])
    left += MARGIN_PIXELS - GROW_PIXELS
    upper += MARGIN_PIXELS - GROW_PIXELS
    right += MARGIN_PIXELS + GROW_PIXELS
    lower += MARGIN_PIXELS + GROW_PIXELS
    return Bbox(left, upper, right, lower)


def ocr_crop_bounds(img: Image, ocr: "UnscaledPageData") -> Bbox:
    """Get crop from Gallica's ocr data, looking for omitted pno."""
    if img.mode not in {"1", "L"}:
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
    xscale = img.height / ocr.total_height
    yscale = img.width / ocr.total_width
    upper = Point(round(ocr.upper[0] * xscale), round(ocr.upper[1] * xscale))
    lower = Point(round(ocr.lower[0] * yscale), round(ocr.lower[1] * yscale))
    img_array = np.array(img)
    mean = img_array.mean(axis=1)
    gradient = np.gradient(mean)
    gstd = np.std(gradient)
    gmean = gradient.mean()

    search = round(img.height * 0.05)
    upper_bound = round(upper.y - search)
    lower_bound = round(lower.y + search)
    upper_search = gradient[upper.y : upper_bound : -1]
    lower_search = gradient[lower.y : lower_bound]

    thresh = 1.5
    lower_diff_thresh = gmean - thresh * gstd
    upper_diff_thresh = gmean + thresh * gstd

    peaked = 0
    for up, x in enumerate(upper_search):
        if not peaked and x >= upper_diff_thresh:
            peaked = 1
        elif peaked and x <= lower_diff_thresh:
            peaked = 2
            break

    up = up if peaked == 2 else 0  # skipcq: PYL-W0631

    peaked = 0
    for down, x in enumerate(lower_search):
        if not peaked and x <= lower_diff_thresh:
            peaked = 1
        if peaked and x >= upper_diff_thresh:
            peaked = 2
            break

    down = down if peaked == 2 else 0  # skipcq: PYL-W0631

    GROW_PIXELS = 10
    bbox = Bbox(
        upper.x - GROW_PIXELS,
        upper.y - up - GROW_PIXELS,
        lower.x + GROW_PIXELS,
        lower.y + down + GROW_PIXELS,
    )
    # show(img, [bbox, Bbox(upper.x, upper.y - search, lower.x, lower.y + search)])
    return bbox


def generate_filename(candidate: Path) -> Path:
    """Generate a filename which doesn't exist on the disk.  This is not atomic."""
    orig = candidate
    i = 0
    while candidate.exists():
        stem = orig.stem
        candidate = orig.with_stem(f"{stem}-{i}")
        i += 1
    return candidate


def extract_page(page: PageObject) -> Tuple[Image.Image, Bbox, float]:
    img, _ = extract_image(page)
    scale = page.mediaBox.getWidth() / img.width
    crop_bbox = crop_bounds(img)
    return img, crop_bbox, scale


def _setbox(box: RectangleObject, xdiff: Real, ydiff: Real) -> None:
    from devtools import debug

    debug(box, xdiff, ydiff)
    curr = box.lowerLeft
    box.lowerLeft = (curr[0] - xdiff, curr[1] - ydiff)
    curr = box.upperRight
    box.upperRight = (curr[0] + xdiff, curr[1] + ydiff)


def scale_page(page: PageObject, max_width: int, max_height: int) -> None:

    xdiff = max(0, (max_width - page.mediaBox.getWidth()) / 2)
    ydiff = max(0, (max_height - page.mediaBox.getHeight()) / 2)
    _setbox(page.mediaBox, xdiff, ydiff)

    xdiff = (max_width - page.cropBox.getWidth()) / 2
    ydiff = (max_height - page.cropBox.getHeight()) / 2
    _setbox(page.cropBox, xdiff, ydiff)


def crop_page(page: PageObject, bbox: Bbox) -> None:
    height = float(page.cropBox.getHeight())
    page.cropBox.lowerLeft = (bbox[0], height - bbox[3])
    page.cropBox.upperRight = (bbox[2], height - bbox[1])


def process_image(img: Image.Image, bbox: Bbox) -> Image.Image:
    img = img.crop(bbox)
    if img.mode != "1":
        img = filter_algorithm_brute_force(img)
    return img


def iterpages(writer: PdfFileWriter) -> Iterable[PageObject]:
    """Bizarrely `PdfFileWriter` objects are not iterable."""
    for i in range(writer.getNumPages()):
        yield writer.getPage(i)


def process_pdf(
    pdf: Path,
    outf: Path = None,
    preserve_text: bool = False,
    equal_size: bool = False,
    skip_existing: bool = False,
    has_cover_page: bool = False,
    ocr_data: "UnscaledPageData" = None,
    suppress_pages: Collection = None,
    progress: bool = False,
) -> Path:
    """Process a pdf.

    Args:
      pdf: Path: The pdf file to crop.
      outf: Path: The output path. Default is to calculate.
      preserve_text: bool: Preserve OCRd text.  (Default value = False)
      equal_size: Make all pages equal sized.  (Default value = False)
      skip_existing: Whether to skip existing files.  (Default value = False)
      has_cover_page: bool: Whether we have a cover page to resize (Default value=False)
      ocr_data: UnscaledPageData: ocr data for this page if available. (Default value = None)

    Returns:
      A Path() object pointing to the cropped pdf.

    """
    if not outf:
        if skip_existing:
            outf = pdf.with_stem(f"processed-{pdf.stem}")
        else:
            outf = generate_filename(pdf.with_stem(f"processed-{pdf.stem}"))
    if outf.exists():
        logger.info("Skipping already processed file.")
        return outf

    progressbar = partial(tqdm, disable=not progress)

    reader = PdfFileReader(str(pdf))

    pages = reader.pages
    writer = PdfFileWriter()
    if has_cover_page:
        pages = pages[2:]
        if suppress_pages:
            suppress_pages = [x - 2 for x in suppress_pages]

    if preserve_text:
        logger.info("Preserving text so only cropping.")
    else:
        logger.info("Not preserving text; will process images.")

    if not suppress_pages:
        suppress_pages = ()

    interesting_pages = filterfalse(lambda x: x[0] in suppress_pages, enumerate(pages))  # type: ignore

    max_width, max_height = 0, 0
    tmpfiles = []

    # crop pages
    for pno, page in progressbar(interesting_pages):

        img, crop_bbox, scale = extract_page(page)
        if ocr_data:
            crop_bbox = ocr_crop_bounds(img, ocr_data[pno])

        if not preserve_text:
            img = process_image(img, crop_bbox)
            tmpf = SpooledTemporaryFile()
            tmpfiles.append(tmpf)
            img.save(tmpf, "PDF", resolution=100.0)
            tmp_reader = PdfFileReader(tmpf)
            page = tmp_reader.getPage(0)
            bbox = Bbox(*(float(x) for x in page.mediaBox))
        else:
            bbox = Bbox(*(x * scale for x in crop_bbox))

        crop_page(page, bbox)
        writer.addPage(page)

        max_width = max(max_width, page.cropBox.getWidth())
        max_height = max(max_height, page.cropBox.getHeight())

    if equal_size:
        for page in iterpages(writer):
            scale_page(page, max_width, max_height)

    # insert cover page
    if has_cover_page:
        scale_x = max_width / reader.getPage(0).mediaBox.getWidth()
        scale_y = max_height / reader.getPage(0).mediaBox.getHeight()
        scale = min(scale_x, scale_y)

        for pno in range(2):
            page = reader.getPage(pno)
            writer.insertBlankPage(width=max_width, height=max_height, index=pno)
            writer.getPage(pno).mergeScaledPage(page, scale)

    with outf.open("wb") as f:
        writer.write(f)

    for tmpf in tmpfiles:
        tmpf.close()

    logger.info(f"Finished processing {str(outf)}")
    return outf
