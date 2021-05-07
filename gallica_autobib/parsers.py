"""Parsers for input data in various formats."""
import bibtexparser
import rispy
from .models import Article, Book, Collection
from typing import Union, List


class ParsingError(Exception):
    pass


def parse_bibtex(bibtex: str) -> List[Union[Article, Book, Collection]]:
    db = bibtexparser.loads(bibtex)
    for record in db:
        type_ = record["ENTRYTYPE"]
        mapping = {"article": Article, "book": Book, "collection": Collection}
        if type_ in mapping:
            return mapping[type_].parse_obj(record)
        else:
            raise ParsingError("Unable to parse")


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
