# package imports
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, List
from .query import assemble_query


class BibBase(BaseModel):
    """Properties shared with all kinds of bibliographic items."""

    publicationdate: int = Field(None, alias="year")
    publisher: str = None
    title: str = None

    def _source(self):
        return self

    def get_query(self) -> str:
        """Get query str"""
        exclude = {"editor"}
        data = self._source().dict(by_alias=False, exclude=exclude)
        data["record_type"] = self._source().record_type

        data = {k: v for k, v in data if v}

        return assemble_query(data)


class Article(BibBase):
    """An article."""

    journal_title: str = None
    pages: Union[int, List]
    author: str
    editor: str = None

    def _source(self):
        if not self.source:
            self.source = Journal.parse_obj(self.dict())
        return self.source


class Book(BibBase):
    author: str
    editor: str = None

    def _source(self):
        self.recordtype = "mon"
        return self


class Collection(BibBase):
    author: str
    editor: str = None

    def _source(self):
        self.recordtype = ["rec", "col", "ens"]
        return self


class Journal(BibBase):
    def _source(self):
        self.recordtype = "per"
        return self


class BibRecord(BaseModel):
    """Model to represent a bibliographic record."""

    recordtype: Literal["mon", "per", "rec", "col", "ens", "his"] = Field(alias="type")
