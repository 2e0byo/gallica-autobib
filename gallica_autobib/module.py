# package imports
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, List, Any
from fuzzywuzzy import fuzz
import unicodedata
from .query import GallicaFetcher
import sruthi
from sruthi.response import SearchRetrieveResponse
from traceback import print_exception
from functools import total_ordering


record_types = {
    "Article": None,
    "Journal": "per",
    "Book": "mon",
    "Collection": "col"
    # "Collection:", ["rec", "col", "ens"]
}


def make_string_boring(unicodestr: str) -> str:
    """Return unicode str as ascii for fuzzy matching."""
    if not unicodestr:
        return None
    normal = unicodedata.normalize("NFKD", unicodestr)
    return normal.lower().strip()


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
    pages: Union[int, List]
    author: str
    editor: str = None

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
    journal_title: str
    publicationdate: Union[list, int] = Field(alias="year")

    def translate(self):
        data = self.dict(exclude={"journal_title"})
        data["title"] = self.journal_title
        return data


class GallicaBibObj(BaseModel):
    """Class to represent Gallica's response."""

    identifier: str
    title: str
    publisher: str
    language: str
    type: str
    date: str

    def convert(self):
        """Return the right kind of model."""
        data = {
            "ark": self.identifier[0],
            "title": self.title,
            "publisher": self.publisher,
            "date": [],
        }
        for r in date.split(","):
            try:
                start, end = r.split("-")
                data["date"].append(list(range(int(start), int(end) + 1)))
            except ValueError:
                data["date"].append(int(r))
        t = self.type[0]["text"]
        return type_to_class[t].from_obj(data)


type_to_class = {"publication en série imprimée": Journal}


@total_ordering
class Match:
    """Object representing a match."""

    def __init__(self, target: Any, candidate: Any):
        self.target = target
        self.candidate = candidate
        self._score = None

    @property
    def score(self):
        if not self._score:
            self._score = self._calculate_score()
        return self._score

    def _calculate_score(self):
        """Calculate the score for a given match."""
        vals = []
        candidate = self.candidate
        for k, v in self.target.dict().items():
            if v and not getattr(candidate, k):
                vals.append(0.5)

            if isinstance(v, str):
                vals.append(
                    fuzz.ratio(
                        make_string_boring(v), make_string_boring(getattr(candidate, k))
                    )
                    / 100
                )
            if isinstance(v, int):
                if isinstance(getattr(candidate, k), int):
                    vals.append(1 if getattr(candidate, k) == v else 0)
                elif isinstance(getattr(candidate, k), list):
                    vals.append(1 if v in getattr(candidate, k) else 0)
                else:
                    raise NotImplementedError

            if isinstance(v, list):
                if isinstance(getattr(candidate, k), list):
                    matches = [1 if i in getattr(candidate, k) else 0 for i in v]
                    vals.append(sum(matches) / len(matches))
                elif getattr(candidate, k) in v:
                    matches.append(1 / len(v))
                else:
                    matches.append(0)
        print(vals)

        return sum(vals) / len(vals)

    def __lt__(self, other):
        return self.score < other.score

    def __gt__(self, other):
        return self.score > other.score

    def __eq__(self, other):
        return self.score == other.score


class GallicaFetcher:
    """Class to interact wtih Gallica"""

    URL = "http://catalogue.bnf.fr/api/SRU"

    def __init__(self):
        self.client = sruthi.Client(url=self.URL, record_schema="dublincore")

    def fetch_query(self, query: str) -> SearchRetrieveResponse:
        return self.client.searchretrieve(query)


class Query(GallicaFetcher):
    """Class to represent a query"""

    def __init__(self, target):
        super().__init__()
        self.target = target
        self.fetcher = GallicaFetcher()

    def run(self, give_up=100) -> Any:
        """Try to get best match."""
        query = self.target.generate_query()
        try:
            resps = self.fetcher.fetch_query(query)
        except Exception as e:
            print_exception(e)
            return None

        matches = []
        for resp in resps[:give_up]:
            candidate = GallicaBibObj.from_obj(resp).convert()
            match = Match(self.target, candidate)
            matches.append(match)
            if any(m.score > 0.7 for m in matches):
                break

        if not matches:
            return None

        return max(matches)
