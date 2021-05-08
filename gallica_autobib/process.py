"""
Extract image from pdf without resampling.

Modified from

https://github.com/mstamy2/PyPDF2/blob/master/Scripts/pdf-image-extractor.py

itself modified from

https://stackoverflow.com/questions/2693820/extract-images-from-pdf-without-resampling-in-python
"""
from PyPDF4.pdf import PageObject
from PIL import Image
from typing import Tuple, Any


class ExtractionError(Exception):
    pass


def extract_image(page: PageObject) -> Tuple[Any, str]:

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
                    if xObject[obj]["/Filter"] == "/FlateDecode":
                        data = Image.frombytes(mode, size, data)
                        type_ = "png"
                    elif xObject[obj]["/Filter"] == "/DCTDecode":
                        type_ = "jpg"
                    elif xObject[obj]["/Filter"] == "/JPXDecode":
                        type_ = "jp2"
                    elif xObject[obj]["/Filter"] == "/CCITTFaxDecode":
                        type_ = "tiff"
                else:
                    type_ = "png"
                    data = Image.frombytes(mode, size, data)
                return data, type_
    else:
        raise ExtractionError("No image found.")
