import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from logging import getLogger
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import BaseModel


class TocLine(BaseModel):
    author: str
    title: str
    start_pages: list[int]
    end_pages: list[int]


logger = getLogger(__name__)


class Parser(ABC):
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.logger = getLogger(self.__class__.__qualname__)

    def concat(self, tags: list[Tag]) -> str:
        return ", ".join(t for x in tags if (t := x.text.strip()))

    @abstractmethod
    def parse_soup(self) -> Iterable[TocLine]:
        pass

    def parse(self) -> list[TocLine]:
        l = list(self.parse_soup())
        return l

    def parse_pages(self, s: str) -> tuple[list[int], list[int]]:
        components = re.split("[,;&]|et", s)
        start_pages, end_pages = [], []
        for c in components:
            start, *end = c.split("-")
            if start.strip():
                start_pages.append(int(start))
            if end:
                end_pages.append(int(end[0]))
        return start_pages, end_pages

    @abstractmethod
    def matches(self) -> bool:
        """Determine if we can parse the given soup or not."""

    @staticmethod
    def despace(s: str) -> str:
        return re.sub(r"  +", " ", s).strip()

    def try_split_author_title(self, combined: str) -> tuple:
        """Sometimes we're just supposed to guess.

        Try to guess, but if we fail, just duplicate the string for both;
        hopefully it will match properly with fuzzy matching later.
        """
        combined = combined.replace("\n", "")
        regexs = (
            re.compile(r"(?P<author>.+?)\.* - (?P<title>.+)"),
            re.compile(r"(?P<author>.+)\. (?P<title>.+)"),
        )
        for regex in regexs:
            if match := regex.search(combined):
                author = self.despace(match.group("author"))
                title = self.despace(match.group("title"))
                return author, title
        self.logger.debug(
            f"Unable to parse {combined} into author /title.  Perhaps add another regex."
        )
        return combined, combined


class TitleXrefPersnameParser(Parser):
    """Parser for the <container>/../{seg/{xref, title},xref} format."""

    def matches(self) -> bool:
        return all(
            (
                self.soup.find("xref"),
                self.soup.find("persName"),
                self.soup.find("title"),
            )
        )

    def parse_soup(self) -> Iterable[TocLine]:
        done = set()
        for title in self.soup.find_all("title"):
            container = title.parent.parent
            # may have multiple titles in same container
            if container in done:
                continue
            titles = container.find_all("title")
            persNames = container.find_all("persName")
            xrefs = container.find_all("xref")
            if not titles or not xrefs or not persNames:
                continue
            start_pages, end_pages = self.parse_pages(self.concat(xrefs))
            done.add(container)
            yield TocLine(
                author=self.concat(persNames),
                title=self.concat(titles),
                start_pages=start_pages,
                end_pages=end_pages,
            )


class ItemSegParser(Parser):
    """Parser for the list/item/seg format."""

    def matches(self) -> bool:
        return bool(self.soup.find_all("item"))

    def parse_soup(self) -> Iterable[TocLine]:
        for row in self.soup.find_all("item"):
            segs = row.find_all("seg")
            if len(segs) != 1:
                self.logger.debug(f"Skipping line {row.prettify()}")
            xrefs = row.find_all("xref")
            author, title = self.try_split_author_title(self.concat(segs))
            start_pages, end_pages = self.parse_pages(self.concat(xrefs))
            try:
                yield TocLine(
                    author=author,
                    title=title,
                    start_pages=start_pages,
                    end_pages=end_pages,
                )
            except Exception:
                breakpoint()


class TrParser(Parser):
    """Parser for the tr/td format."""

    def matches(self) -> bool:
        return bool(self.soup.find_all("td"))

    def parse_soup(self) -> Iterable[TocLine]:
        for row in self.soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) != 3:
                self.logger.debug(f"Unable to parse {row}.")
                continue
            author, title, pages = (self.concat(x) for x in tds)
            if not title:
                author, title = self.try_split_author_title(author)
            start_pages, end_pages = self.parse_pages(pages)
            if not pages:
                self.logger.debug(f"Unable to parse {row}.")
                continue
            yield TocLine(
                author=author, title=title, start_pages=start_pages, end_pages=end_pages
            )


from collections import Counter
from pathlib import Path

c = Counter()

outdir = Path("/home/john/volatile-tmp/xmls")
for d in {"row", "item", "tr"}:
    current = [x.stem for x in (outdir / d).glob("*.xml")]
    if current:
        c[d] = int(max(current))


# TODO use a better dispatcher once we don't need to log
def parse_xml_toc(xml: str) -> list[TocLine]:
    soup = BeautifulSoup(xml, "xml")
    parser = TitleXrefPersnameParser(soup)
    if parser.matches():
        c["row"] += 1
        Path(outdir, "row", f"{c['row']:04}.xml").write_text(soup.prettify())
        return parser.parse()

    parser = ItemSegParser(soup)
    if parser.matches():
        c["item"] += 1
        Path(outdir, "item", f"{c['item']:04}.xml").write_text(soup.prettify())
        return parser.parse()

    parser = TrParser(soup)
    if parser.matches():
        c["tr"] += 1
        Path(outdir, "tr", f"{c['tr']:04}.xml").write_text(soup.prettify())
        return parser.parse()
    else:
        breakpoint()
        raise NotImplementedError("Other toc")
