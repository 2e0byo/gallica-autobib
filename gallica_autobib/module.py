# package imports
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, List, Any
from .query import assemble_query
import fuzzywuzzy as fuzz
import unicodedata

record_types = {
    "Article": None,
    "Journal": "per",
    "Book": "mon",
    "Collection": "col"
    # "Collection:", ["rec", "col", "ens"]
}

type_to_class = {"publication en série imprimée": Journal}


def make_string_boring(unicodestr: str) -> str:
    """Return unicode str as ascii for fuzzy matching."""
    normal = unicodedata.normalize("NFKD", unicodestr)
    return normal.decode("uft-8").lower().strip()


class BibBase(BaseModel):
    """Properties shared with all kinds of bibliographic items."""

    publicationdate: int = Field(None, alias="year")
    publisher: str = None
    ark: str = None

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
        for k, v in self.target.dict():
            if v and not candidate.k:
                vals.append(0)

            if isinstance(v, str):
                vals.append(
                    fuzz.ratio(make_string_boring(v), make_string_boring(candidate.k))
                )
            if isinstance(v, int):
                if isinstance(candidate.k, int):
                    vals.append(1 if candidate.k == v else 0)
                elif isinstance(candidate.k, list):
                    vals.append(1 if v in candidate.k else 0)
                else:
                    raise NotImplementedError

            if isinstance(v, list):
                if isinstance(candidate.k, list):
                    matches = [1 if i in candidate.k else 0 for i in v]
                    vals.append(sum(matches) / len(matches))
                elif candidate.k in v:
                    matches.append(1 / len(v))
                else:
                    matches.append(0)

        return sum(vals) / len(vals)
