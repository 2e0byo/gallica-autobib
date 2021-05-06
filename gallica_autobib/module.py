# package imports
from pydantic import BaseModel
from typing import Optional, Literal, Union, List


class BibRecord(BaseModel):
    """Model to represent a bibliographic record."""

    title: str
    type: Literal["mon", "per", "rec", "col", "ens", "his"]
    year: int
    pages: Union[int, List] = None
    author: str
    editor: str = None
