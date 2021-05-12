# package imports
from functools import total_ordering
from traceback import print_exception
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from pydantic.utils import Representation

from .gallipy import Ark, Resource

record_types = {
    "Article": None,
    "Journal": "per",
    "Book": "mon",
    "Collection": "col"
    # "Collection:", ["rec", "col", "ens"]
}

VALID_QUERIES = (
    "anywhere",
    "author",
    "title",
    "subject",
    "doctype",
    "recordtype",
    "status",
    "recordid",
    "persistentid",
    "ean",
    "isbn",
    "issn",
    "ismn",
    "isrc",
    "comref",
    "otherid",
    "abstract",
    "authorRole",
    "cote",
    "date",
    "dewey",
    "digitized",
    "FrenchNationalBibliography",
    "fuzzyIsbn",
    "isni",
    "language",
    "LegalDepositType",
    "LegalDepositDate",
    "local",
    "publicationdate",
    "publicationplace",
    "publisher",
    "serialtitle",
    "set",
    "technicaldata",
    "unimarc:doctype",
    "col2bib",
    "ens2bib",
    "rec2bib",
    "author2bib",
    "subject2bib",
    "work2bib",
    "creationdate",
    "lastmodificationdate",
)


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

        data = {f"bib.{k}": v for k, v in data.items() if v and k in VALID_QUERIES}

        return self.assemble_query(**data)


class Article(BibBase):
    """An article."""

    title: str
    journaltitle: str
    pages: List[str]
    author: str
    editor: str = None
    number: int = None
    volume: int = None
    physical_pages: List[int] = None

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
      journaltitle: the title of the journal
      year: Union[list, int]: the year(s) of publication
      number: number
      volume: vol
    """

    journaltitle: str
    publicationdate: Union[list, int] = Field(alias="year")
    number: int = None
    volume: int = None

    def translate(self):
        data = self.dict(exclude={"journaltitle"})
        data["title"] = self.journaltitle
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
            "journaltitle": self.title,
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
