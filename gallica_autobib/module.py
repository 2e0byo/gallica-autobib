# package imports
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, List
from .query import assemble_query


class BibBase(BaseModel):
    """Properties shared with all kinds of bibliographic items."""

    publicationdate: int = Field(None, alias="year")
    publisher: str = None
    title: str = None
    source = None

    def __post_init__(self):
        if not self.source:
            self.source = self
        else:
            self.source = self.source(**self.dict())

    def get_query(self) -> str:
        """Get query str"""
        exclude = {"editor"}
        data = self.source.dict(by_alias=False, exclude=exclude)

        data = {k: v for k, v in data if v}

        return assemble_query(data)


class Article(BibBase):
    """An article."""

    journal_title: str = None
    recordtype = "per"
    pages: Union[int, List]
    author: str
    editor: str = None
    source = Journal


class Book(BibBase):
    recordtype = "mon"
    author: str
    editor: str = None


class Collection(BibBase):
    recordtype = ["rec", "col", "ens"]
    author: str
    editor: str = None


class Journal(BibBase):
    recordtype = "per"


class BibRecord(BaseModel):
    """Model to represent a bibliographic record."""

    recordtype: Literal["mon", "per", "rec", "col", "ens", "his"] = Field(alias="type")
