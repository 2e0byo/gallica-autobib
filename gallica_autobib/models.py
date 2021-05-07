# package imports
from pydantic import BaseModel, Field
from pydantic.utils import Representation
from typing import Optional, Literal, Union, List, Any
from traceback import print_exception
from functools import total_ordering
from .gallipy import Resource, Ark


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
    ark: str = None

    @staticmethod
    def assemble_query(**kwargs) -> str:
        """Put together an sru query from a dict."""
        return " and ".join(f'{k} all "{v}"' for k, v in kwargs.items())

    def _source(self):
        return self

    def translate(self):
        return self.dict(exclude={"editor"})

    def generate_query(self) -> str:
        """Get query str"""
        exclude = {"editor"}
        source = self._source()
        data = source.translate()
        data["recordtype"] = record_types[type(source).__name__]
        print(data)

        data = {f"bib.{k}": v for k, v in data.items() if v}

        return self.assemble_query(**data)


class Article(BibBase):
    """An article."""

    title: str
    journal_title: str
    pages: List[str]
    author: str
    editor: str = None
    number: int = None
    volume: int = None

    def _source(self):
        return Journal.parse_obj(self.dict(by_alias=True))


class Book(BibBase):
    title: str
    author: str
    editor: str = None


class Collection(BibBase):
    title: str
    author: str
    editor: str = None


class Journal(BibBase):
    """A Journal

    args:
      journal_title: the title of the journal
      year: Union[list, int]: the year(s) of publication
      number: number
      volume: vol
    """

    journal_title: str
    publicationdate: Union[list, int] = Field(alias="year")
    number: int = None
    volume: int = None

    def translate(self):
        data = self.dict(exclude={"journal_title"})
        data["title"] = self.journal_title
        return data


class GallicaBibObj(BaseModel):
    """Class to represent Gallica's response."""

    ark: str
    title: str
    publisher: str
    language: str
    type: str
    date: str

    def convert(self):
        """Return the right kind of model."""
        data = {
            "ark": self.ark,
            "title": self.title,
            "journal_title": self.title,
            "publisher": self.publisher,
            "year": [],
        }
        for r in self.date.split(","):
            try:
                start, end = r.split("-")
                data["year"] += list(range(int(start), int(end) + 1))
            except ValueError:
                data["year"].append(int(r))
        return type_to_class[self.type].parse_obj(data)


type_to_class = {"publication en série imprimée": Journal}
