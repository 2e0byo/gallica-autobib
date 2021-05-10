"""
Extract image from pdf without resampling.

Modified from

https://github.com/mstamy2/PyPDF2/blob/master/Scripts/pdf-image-extractor.py

itself modified from

https://stackoverflow.com/questions/2693820/extract-images-from-pdf-without-resampling-in-python
"""
from PyPDF4.pdf import PageObject
from PyPDF4 import PdfFileReader, PdfFileWriter
from PIL import Image, ImageOps, ImageChops
from typing import Tuple, Any
import numpy as np
from devtools import debug
from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from io import BytesIO


class ExtractionError(Exception):
    pass


def extract_image(page: PageObject) -> Tuple[Image.Image, str]:
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
        return point / 1.2
    else:
        return point * 2


_results = namedtuple("results", ("lh_page", "crop", "bbox"))


def filter_algorithm_brute_force(img):
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


def detect_spine(img: Image.Image) -> Tuple[bool, Tuple]:
    threshold = 50
    midpoint = round(img.height / 2)
    lower = midpoint - 20
    upper = midpoint + 20
    first_left = []
    first_right = []
    for height in (midpoint, lower, upper):
        for i in range(img.width):
            if img.getpixel((i, height)) < threshold:
                first_left.append(i)
                break
        for i in range(img.width - 1, 0, -1):
            if img.getpixel((i, height)) < threshold:
                first_right.append(img.width - i)
                break

    assert first_left
    assert first_right
    first_left = deanomalise(first_left)
    first_right = deanomalise(first_right)
    if first_left < first_right:
        crop = first_left + 10
        return _results(True, crop, (crop, 0, img.width, img.height))
    else:
        crop = first_right - 10
        return _results(False, crop, (0, 0, img.width - crop, img.height))


def prepare_img(img: Image.Image, threshold=75) -> Image.Image:
    img = ImageOps.grayscale(img)
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

    img = prepare_img(img)
    res = detect_spine(img)
    res = _results(res[0], 0, res[2])
    # img = img.crop(res.bbox)

    # crop to border
    bg = Image.new(img.mode, img.size, 255)
    diff = ImageChops.difference(img, bg)
    left, lower, right, upper = diff.getbbox()
    left -= 10
    lower -= 10
    right += 10
    upper += 10
    return (left, lower, right, upper)
    # if res.lh_page:
    #     return _results(res.lh_page, res.crop, (left + res.crop, lower, right, upper))
    # else:
    #     return _results(res.lh_page, res.crop, (left, lower, right - res.crop, upper))


def crop_pdf(
    pdf: Path, outf: Path = None, preserve_text: bool = False, equal_size: bool = False
) -> Path:
    """Crop a pdf.

    Note that currently preserve_text implies not editing the image, and
    equal_size is unimplemented.

    Args:
      pdf: Path: The pdf file to crop.
      outf: Path: The output path. Default is to calculate.
      preserve_text: bool: Preserve OCRd text.  (Default value = False)
      equal_size: Make all pages equal sized.  (Default value = False)

    Returns:
      A Path() object pointing to the cropped pdf.

    """
    if equal_size:
        raise NotImplementedError("Equal sizes not yet implemented.")

    reader = PdfFileReader(str(pdf))

    if not outf:
        outf = pdf.with_stem(f"cropped-{pdf.stem}")
        i = 0
        while outf.exists():
            outf = outf.with_stem(f"{outf.stem-{i}}")
            i += 1

    if preserve_text:
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
        imgs = []
        for i, page in enumerate(reader.pages):
            img, _ = extract_image(page)
            bbox = get_crop_bounds(img)
            img = img.crop(bbox)
            imgs.append(filter_algorithm_brute_force(img))
        imgs[0].save(
            str(outf), "PDF", resolution=100.0, save_all=True, append_images=imgs[1:]
        )

    return outf
