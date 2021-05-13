# package imports
from typing import List, Optional, Union

from pydantic import BaseModel, Field

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

    publicationdate: Union[int, List[int]] = Field(None, alias="year")
    publisher: Optional[str] = None
    ark: Optional[str] = None

    @staticmethod
    def assemble_query(**kwargs: dict) -> str:
        """Put together an sru query from a dict."""
        return " and ".join(f'{k} all "{v}"' for k, v in kwargs.items())

    def _source(self) -> "RecordTypes":
        return self  # type: ignore

    def translate(self) -> dict:
        return self.dict(exclude={"editor"})

    def generate_query(self) -> str:
        """Get query str"""
        source = self._source()
        data = source.translate()
        data["recordtype"] = record_types[type(source).__name__]

        data = {f"bib.{k}": v for k, v in data.items() if v and k in VALID_QUERIES}

        return self.assemble_query(**data)


class AuthorTitleMixin:
    def name(self, short: Optional[int] = None) -> str:
        if short is not None:
            n = f"{self.title} ({self.author})"  # type: ignore
        else:
            n = f"{self.title[:short]} ({self.author[:short]})"  # type: ignore
        return n


class Book(BibBase, AuthorTitleMixin):
    title: str
    author: str
    editor: Optional[str] = None


class Collection(BibBase, AuthorTitleMixin):
    title: str
    author: str
    editor: Optional[str] = None


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
    number: Optional[int] = None
    volume: Optional[int] = None

    def translate(self) -> dict:
        data = self.dict(exclude={"journaltitle"})
        data["title"] = self.journaltitle
        return data

    def name(self, short: Optional[int] = None) -> str:
        if short is not None:
            n = f"{self.journaltitle[:short]} {self.publicationdate}"
        else:
            n = f"{self.journaltitle} {self.publicationdate}"
        n += f" vol. {self.volume}" if self.volume else ""
        n += f" n. {self.number}" if self.number else ""
        return n


class Article(BibBase, AuthorTitleMixin):
    """An article."""

    title: str
    journaltitle: str
    pages: List[str]
    author: str
    editor: Optional[str] = None
    number: Union[None, int, List[int]] = None
    volume: Union[None, int, List[int]] = None
    physical_pages: Optional[List[int]] = None

    def _source(self) -> Journal:
        return Journal.parse_obj(self.dict(by_alias=True))


class GallicaBibObj(BaseModel):
    """Class to represent Gallica's response."""

    ark: str
    title: str
    publisher: str
    language: str
    type: str
    date: str

    def convert(self) -> "RecordTypes":
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
                data["year"] += list(range(int(start), int(end) + 1))  # type: ignore
            except ValueError:
                data["year"].append(int(r))  # type: ignore
        return type_to_class[self.type].parse_obj(data)


type_to_class = {"publication en série imprimée": Journal}

RecordTypes = Union[Article, Collection, Book, Journal]
