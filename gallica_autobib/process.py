"""
Extract image from pdf without resampling.

Modified from

https://github.com/mstamy2/PyPDF2/blob/master/Scripts/pdf-image-extractor.py

itself modified from

https://stackoverflow.com/questions/2693820/extract-images-from-pdf-without-resampling-in-python
"""
from PyPDF4.pdf import PageObject
from PIL import Image, ImageOps, ImageChops
from typing import Tuple, Any
import numpy as np

from io import BytesIO


class ExtractionError(Exception):
    pass


def extract_image(page: PageObject) -> Tuple[Image, str]:
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
                    filter_ = xObject[obj]["/Filter"][0]

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


def filter_algorithm_brute_force(img):
    img = ImageOps.autocontrast(img)
    img = ImageOps.posterize(img, 5)
    img = ImageOps.grayscale(img).point(filter_point)
    img = ImageOps.autocontrast(img)
    return img


def deanomalise(data: list) -> int:
    mean = np.mean(data)
    std = np.std(data)
    data = [x for x in data if abs(x - mean) < 2 * std]
    return round(np.mean(data))


def get_crop_bounds(img: Image.Image) -> Tuple:
    """Get crop bounds for text on page.

    The algorithm:
      1. grayscales and thresholds the image
      2. find the side with a vertical black line and crops it out
      3. crops to content
    This is not very robust, but Gallica is quite standardised in its pdfs.

    Args:
      img: Image.Image: The image to process.

    Returns:
      A tuple of the rectangle to crop to.
    """
    img = ImageOps.grayscale(img)
    img = img.point(lambda p: p > 128 and 255)  # threshold image

    # detect continuous side of image
    threshold = 50
    midpoint = round(img.height / 2)
    lower = midpoint - 20
    upper = midpoint + 20
    first_left = []
    first_right = []
    for height in (midpoint, lower, upper):
        print(height)
        for i in range(img.width):
            if img.getpixel((i, height)) < threshold:
                first_left.append(i)
                break
        for i in range(img.width - 1, 0, -1):
            if img.getpixel((i, height)) < threshold:
                first_right.append(i)
                break
    first_left = deanomalise(first_left)
    first_right = deanomalise(first_right)
    lh_page = first_left < first_right
    if lh_page:
        crop = first_left + 10
        img = img.crop((crop, 0, img.width, img.height))
    else:
        crop = first_right + 10
        img = img.crop((0, 0, img.width - crop, img.height))
    # crop to border
    bg = Image.new(img.mode, img.size, 255)
    diff = ImageChops.difference(img, bg)
    left, lower, right, upper = diff.getbbox()
    if lh_page:
        return (left + crop, lower, right, upper)
    else:
        return (left, lower, right - crop, upper)
