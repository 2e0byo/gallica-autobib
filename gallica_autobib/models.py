import datetime
from hashlib import sha1
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field
from slugify import slugify

from .templating import env, latex_env
from .util import prettify, pretty_page_range

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

    def __hash__(self) -> int:
        return hash(repr(self))

    def key(self) -> str:
        return sha1(repr(self).encode()).hexdigest()

    @staticmethod
    def assemble_query(**kwargs: dict) -> str:
        """Put together an sru query from a dict."""
        return " and ".join(f'{k} all "{v}"' for k, v in kwargs.items())

    def _source(self) -> "RecordTypes":
        return self  # type: ignore

    def translate(self) -> dict:
        return self.dict(exclude={"editor"})

    @staticmethod
    def format_query_item(item: Union[list, str]) -> str:
        if isinstance(item, list):
            return " ".join(str(x) for x in item)
        else:
            return item

    def generate_query(self) -> str:
        """Get query str"""
        source = self._source()
        data = source.translate()
        data["recordtype"] = record_types[type(source).__name__]

        data = {
            f"bib.{k}": self.format_query_item(v)
            for k, v in data.items()
            if v and k in VALID_QUERIES
        }

        return self.assemble_query(**data)

    @property
    def omit(self) -> Union[Tuple[str], Tuple]:
        return ()

    def bibtex_transform(self) -> dict:
        return {k: v for k, v in self.dict(by_alias=True).items() if k not in self.omit}

    def bibtex(self) -> str:
        props = self.bibtex_transform()
        name = type(self).__name__.lower()
        if "pages" in props.keys():
            props["pages"] = pretty_page_range(props["pages"])
        if "year" in props.keys() and isinstance(props["year"], list):
            props["year"] = prettify(props["year"], True)
        return latex_env.get_template(f"{name}.bib").render(rep=props, obj=self)

    def ris(self) -> str:
        args = {k: v for k, v in dict(self).items() if k not in self.omit}
        args["name"] = type(self).__name__.lower()
        return env.get_template(f"{args['name']}.ris").render(rep=args, obj=self)


class HasTitle(BibBase):
    title: str
    subtitle: Optional[str]


class AuthorTitleMixin:
    def name(self, short: Optional[int] = None, slug: bool = False) -> str:
        if short is None:
            n = f"{self.title} ({self.author})"  # type: ignore
        else:
            n = f"{self.title[:short]} ({self.author[:short]})"  # type: ignore
        if slug:
            return slugify(n)
        else:
            return n


class HasPublisher(HasTitle):
    publisher: Optional[str] = None
    location: Optional[str] = None
    page_count: Optional[int] = None

    def bibtex_transform(self) -> dict:
        props = super().bibtex_transform()
        if self.page_count:
            props["note"] = f"{self.page_count} pp."
        return props


class Book(HasPublisher, AuthorTitleMixin):
    author: str
    editor: Optional[str] = None


class Collection(HasPublisher, AuthorTitleMixin):
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

    def name(self, short: Optional[int] = None, slug: bool = False) -> str:
        if short is not None:
            n = f"{self.journaltitle[:short]} {self.publicationdate}"
        else:
            n = f"{self.journaltitle} {self.publicationdate}"
        n += f" vol. {self.volume}" if self.volume else ""
        n += f" n. {self.number}" if self.number else ""
        if slug:
            return slugify(n)
        else:
            return n


class Article(HasTitle, AuthorTitleMixin):
    """An article."""

    journaltitle: str
    pages: List[str]
    author: str
    editor: Optional[str] = None
    number: Union[None, int, List[int]] = None
    volume: Union[None, int, List[int]] = None
    physical_pages: Optional[List[int]] = None

    def _source(self) -> Journal:
        return Journal.parse_obj(self.dict(by_alias=True))


class NewspaperArticle(BibBase, AuthorTitleMixin):
    """A newspaper article, which has no page range.
    This is actually a kind of journal."""

    journaltitle: str
    date: datetime.date
    author: str
    title: str


class GallicaBibObj(BaseModel):
    """Class to represent Gallica's response."""

    ark: str
    title: str
    language: str
    type: str
    date: str
    publisher: Optional[str] = None

    @staticmethod
    def safe_convert(thing: str) -> Optional[int]:
        try:
            return int(thing)
        except ValueError:
            return None

    def convert(self) -> "RecordTypes":
        """Return the right kind of model."""
        data = {
            "ark": self.ark,
            "title": self.title,
            "journaltitle": self.title,
            "publisher": self.publisher,
            "year": [],
        }  # type: ignore
        for r in self.date.split(","):
            split = r.split("-")
            if len(split) > 1:
                if len(split) > 2:
                    raise Exception(f"Unable to handle date {r}")
                start, end = (self.safe_convert(x) for x in split)
                if not start and not end:
                    raise Exception(f"Unable to handle date {r}")
                if start and end:
                    data["year"] += list(range(int(start), int(end) + 1))  # type: ignore
                else:
                    data["year"] = start if start else end  # type: ignore
            else:
                data["year"].append(int(r))  # type: ignore
        return type_to_class[self.type].parse_obj(data)


type_to_class = {"publication en série imprimée": Journal}

RecordTypes = Union[Article, Collection, Book, Journal]
