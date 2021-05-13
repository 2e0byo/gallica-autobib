"""Fns to process.  These are wrapped in a class in pipeline, which is probably what you want."""
import logging
from collections import namedtuple
from io import BytesIO
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageChops, ImageOps
from PyPDF4 import PdfFileReader, PdfFileWriter
from PyPDF4.pdf import PageObject

logger = logging.getLogger(__name__)


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
    else:
        raise ExtractionError("No image found.")


def filter_point(point: int) -> int:
    """Filter a point.

    If point is below threshold, divide it by divisor. If above, multiple it by
    multiplier. This is a crude but effective way of skewing an image to
    black-and-white without actually thresholding it.

    """
    if point < 160:
        return round(point / 1.2)
    else:
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
    else:
        crop = first_right - 10
        return _results(False, crop, (0, 0, img.width - crop, img.height))


def prepare_img(img: Image.Image, threshold: int = 60) -> Image.Image:
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.point(lambda p: p > threshold and 255)


def get_crop_bounds(img: Image.Image) -> Tuple:
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
    # ImageShow.show(img)
    # res = detect_spine(img)
    # logger.debug(res.lh_page)
    # crop out corner errors
    x = 40
    img = img.crop((x, x, img.width - x, img.height - x))

    # crop to border
    bg = Image.new(img.mode, img.size, 255)
    diff = ImageChops.difference(img, bg)

    left, upper, right, lower = diff.getbbox()
    left += x - 10
    upper += x - 10
    right += x + 10
    lower += x + 10
    return (left, upper, right, lower)


def generate_filename(candidate: Path) -> Path:
    """Generate a filename which doesn't exist on the disk.  This is not atomic."""
    orig = candidate
    i = 0
    while candidate.exists():
        stem = orig.stem
        candidate = orig.with_stem(f"{stem}-{i}")
        i += 1
    return candidate


def process_pdf(
    pdf: Path,
    outf: Path = None,
    preserve_text: bool = False,
    equal_size: bool = False,
    skip_existing: bool = False,
) -> Path:
    """Process a pdf.

    Note that currently preserve_text implies not editing the image, and
    equal_size is unimplemented.

    Args:
      pdf: Path: The pdf file to crop.
      outf: Path: The output path. Default is to calculate.
      preserve_text: bool: Preserve OCRd text.  (Default value = False)
      equal_size: Make all pages equal sized.  (Default value = False)
      skip_existing: Whether to skip existing files.  (Default value = False)

    Returns:
      A Path() object pointing to the cropped pdf.

    """
    if equal_size:
        raise NotImplementedError("Equal sizes not yet implemented.")

    if not outf:
        if skip_existing:
            outf = pdf.with_stem(f"processed-{pdf.stem}")
        else:
            outf = generate_filename(pdf.with_stem(f"processed-{pdf.stem}"))
    if outf.exists():
        logger.info("Skipping already processed file.")
        return outf
    reader = PdfFileReader(str(pdf))

    if preserve_text:
        logger.debug("Preserving text.")
        writer = PdfFileWriter()
        for page in reader.pages:
            img, _ = extract_image(page)
            bbox = get_crop_bounds(img)
            scale = page.mediaBox.getWidth() / img.width
            page.cropBox.lowerLeft = (bbox[0] * scale, bbox[1] * scale)
            page.cropBox.upperRight = (bbox[2] * scale, bbox[3] * scale)
            writer.addPage(page)
        with outf.open("wb") as f:
            writer.write(f)
    else:
        logger.debug("Not preserving text.")
        imgs = []
        for i, page in enumerate(reader.pages):
            logger.debug(f"Processing page {i}")
            img, _ = extract_image(page)
            bbox = get_crop_bounds(img)
            img = img.crop(bbox)
            if img.mode != "1":
                img = filter_algorithm_brute_force(img)
            imgs.append(img)
        imgs[0].save(
            str(outf), "PDF", resolution=100.0, save_all=True, append_images=imgs[1:]
        )

    logger.info(f"Finished processing {str(outf)}")
    return outf
