"""Parsers for input data in various formats."""
from typing import List, TextIO, Tuple, Union

import bibtexparser
import rispy
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from roman import fromRoman, toRoman

from .models import Article, Book, Collection, RecordTypes

parser = BibTexParser()
parser.customization = convert_to_unicode


class ParsingError(Exception):
    pass


def parse_bibtex(bibtex: Union[str, TextIO]) -> Tuple[List[RecordTypes], List[str]]:
    try:
        if isinstance(bibtex, str):
            db = bibtexparser.loads(bibtex, parser=parser)
            rawlines = bibtex.split("\n")
        else:
            db = bibtexparser.load(bibtex, parser=parser)
            bibtex.seek(0)  # type: ignore
            rawlines = (x.strip("\n") for x in bibtex.readlines())  # type: ignore
    except Exception:
        raise ParsingError("Unable to parse")
    parsed = []
    for record in db.entries:
        pages = record["pages"]
        if isinstance(pages, list):
            continue

        roman = "i" in pages.lower()
        lower = "i" in pages
        try:
            pages = pages.replace("--", "-")
            start, end = pages.split("-")
            startno = fromRoman(start.upper()) if roman else int(start)
            endno = fromRoman(end.upper()) if roman else int(end)
            if not roman and endno < startno:
                endno = int(f"{start[0]}{end}")
            record["pages"] = list(range(startno, endno + 1))
            if roman:
                record["pages"] = [
                    toRoman(x).lower() if lower else toRoman(x) for x in record["pages"]
                ]
        except ValueError:
            record["pages"] = [record["pages"]]

        type_ = record["ENTRYTYPE"]
        mapping = {"article": Article, "book": Book, "collection": Collection}
        if type_ in mapping:
            parsed.append(mapping[type_].parse_obj(record))
        else:
            raise ParsingError("Unsupported type")

    raw = []
    entry: List[str] = []
    for line in rawlines:
        if line.strip().startswith("@"):
            if entry:
                raw.append("\n".join(line for line in entry if line.strip()))
            entry = [line]
        elif line.strip():
            entry.append(line)

    raw.append("\n".join(line for line in entry if line.strip()))

    return parsed, raw  # type: ignore


def parse_ris(ris: Union[str, TextIO]) -> Tuple[List[RecordTypes], List[str]]:
    try:
        if isinstance(ris, str):
            db = rispy.loads(ris)
            rawlines = ris.split("\n")
        else:
            db = rispy.load(ris)
            ris.seek(0)  # type: ignore
            rawlines = (x.strip("\n") for x in ris.readlines())  # type: ignore
    except Exception:
        raise ParsingError("Unable to parse")
    parsed = []

    for record in db:
        record["pages"] = list(
            range(int(record["start_page"]), int(record["end_page"]) + 1)
        )
        record["author"] = "and".join(record["authors"])
        try:
            record["journaltitle"] = record["journal_name"]
        except KeyError:
            record["journaltitle"] = record["secondary_title"]
        mapping = {"JOUR": Article, "BOOK": Book, "COLL": Collection}
        type_ = record["type_of_reference"]
        if type_ in mapping:
            parsed.append(mapping[type_].parse_obj(record))
        else:
            raise ParsingError("Unsupported type")

    raw = []
    entry = []
    for line in rawlines:
        if not line.strip():
            continue
        if line.strip().startswith("ER"):
            entry.append(line)
            raw.append("\n".join(entry))
            entry = []
        else:
            entry.append(line)

    return parsed, raw  # type: ignore
