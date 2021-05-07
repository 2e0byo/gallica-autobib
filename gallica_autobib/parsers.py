"""Parsers for input data in various formats."""
import bibtexparser
import rispy
from .models import Article, Book, Collection
from typing import Union, List
from devtools import debug


class ParsingError(Exception):
    pass


def parse_bibtex(bibtex: str) -> List[Union[Article, Book, Collection]]:
    try:
        db = bibtexparser.loads(bibtex)
    except Exception:
        raise ParsingError("Unable to parse")
    parsed = []
    for record in db.entries:
        pages = record["pages"]
        if "i" in pages.lower():
            raise NotImplementedError("Don't yet handle roman numerals")
        try:
            start, end = pages.split("-")
            if int(end) < int(start):
                end = f"{start[0]}{end}"
            record["pages"] = list(range(int(start), int(end) + 1))
        except ValueError:
            record["pages"] = [record["pages"]]

        type_ = record["ENTRYTYPE"]
        mapping = {"article": Article, "book": Book, "collection": Collection}
        if type_ in mapping:
            parsed.append(mapping[type_].parse_obj(record))
        else:
            raise ParsingError("Unable to parse")
    return parsed


def parse_ris(ris: str) -> List[Union[Article, Book, Collection]]:
    db = rispy.loads(ris)
    for record in db:
        record["author"] = record["first_authors"]
        mapping = {"ART": Article, "BOOK": Book, "COLL": Collection}
        type_ = record["type_of_reference"]
        if type_ in mapping:
            return mapping[type_].parse_obj(record)
        else:
            raise ParsingError("Unable to parse")
