# package imports
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, List
from .query import assemble_query

record_types = {
    "Article": None,
    "Journal": "per",
    "Book": "mon",
    "Collection": "col"
    # "Collection:", ["rec", "col", "ens"]
}


class BibBase(BaseModel):
    """Properties shared with all kinds of bibliographic items."""

    publicationdate: int = Field(None, alias="year")
    publisher: str = None

    def _source(self):
        return self

    def translate(self):
        data = self.dict(exclude={"editor"})

    def get_query(self) -> str:
        """Get query str"""
        exclude = {"editor"}
        source = self._source()
        data = source.translate()
        data["recordtype"] = record_types[type(source).__name__]
        print(data)

        data = {f"bib.{k}": v for k, v in data.items() if v}

        return assemble_query(**data)


class Article(BibBase):
    """An article."""

    title: str
    journal_title: str
    pages: Union[int, List]
    author: str
    editor: str = None

    def _source(self):
        return Journal.parse_obj(self.dict())


class Book(BibBase):
    title: str
    author: str
    editor: str = None


class Collection(BibBase):
    title: str
    author: str
    editor: str = None


class Journal(BibBase):
    journal_title: str

    def translate(self):
        data = self.dict(exclude={"journal_title"})
        data["title"] = self.journal_title
        return data
