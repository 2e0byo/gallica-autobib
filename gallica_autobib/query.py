import io

import logging
import unicodedata
from functools import total_ordering
from pathlib import Path
from re import search
from time import sleep
from traceback import print_exception
from typing import Any, List, Literal, Optional, Union
import imghdr

import sruthi
from fuzzywuzzy import fuzz
from pydantic.utils import Representation
from PyPDF4 import PageRange, PdfFileMerger, PdfFileReader, PdfFileWriter
from sruthi.response import SearchRetrieveResponse
from requests_downloader import downloader

from .gallipy import Ark, Resource
from .gallipy.monadic import Either
from .models import Article, Book, Collection, GallicaBibObj, Journal


def make_string_boring(unicodestr: str) -> str:
    """Return unicode str as ascii for fuzzy matching."""
    if not unicodestr:
        return None
    normal = unicodedata.normalize("NFKD", unicodestr)
    return normal.lower().strip()


@total_ordering
class Match(Representation):
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
        vals = {}
        candidate = self.candidate
        for k, v in self.target.dict().items():
            candidate_v = getattr(candidate, k)
            if v and not candidate_v:
                vals[k] = 0.5

            if isinstance(v, str):
                vals[k] = (
                    fuzz.ratio(make_string_boring(v), make_string_boring(candidate_v))
                    / 100
                )
            if isinstance(v, int):
                if not candidate_v:
                    vals[k] = 0.5
                    continue
                if isinstance(candidate_v, int):
                    vals[k] = 1 if candidate_v == v else 0
                elif isinstance(candidate_v, list):
                    vals[k] = 1 if v in candidate_v else 0
                else:
                    raise NotImplementedError(v, candidate_v)

            if isinstance(v, list):
                if isinstance(candidate_v, list):
                    matches = [1 if i in candidate_v else 0 for i in v]
                elif candidate_v in v:
                    matches.append(1 / len(v))
                else:
                    matches.append(0)
                vals[k] = sum(matches) / len(matches)

        self._vals = vals
        return sum(v for _, v in vals.items()) / len(vals)

    def __lt__(self, other):
        return self.score < other.score

    def __gt__(self, other):
        return self.score > other.score

    def __eq__(self, other):
        return self.score == other.score

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()


class GallicaSRU(Representation):
    """Class to interact wtih Gallica"""

    URL = "http://catalogue.bnf.fr/api/SRU"

    def __init__(self):
        self.client = sruthi.Client(url=self.URL, record_schema="dublincore")

    def fetch_query(self, query: str) -> SearchRetrieveResponse:
        return self.client.searchretrieve(query)

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()


class Query(GallicaSRU, Representation):
    """Class to represent a query"""

    def __init__(self, target):
        super().__init__()
        self.target = target._source()
        self.fetcher = GallicaSRU()

    @staticmethod
    def get_at_str(obj: Union[str, list]):
        if not obj:
            return obj
        if isinstance(obj, str):
            return obj
        else:
            return obj[0]

    def resp_to_obj(self, resp: dict) -> GallicaBibObj:
        """Convert resp to GallicaBibObj"""
        resp["ark"] = self.get_at_str(resp["identifier"])
        # could use a Language() obj to internationalise this
        resp["language"] = resp["language"][1]
        resp["type"] = resp["type"][0]["text"]
        resp["publisher"] = self.get_at_str(resp["publisher"])
        resp["title"] = self.get_at_str(resp["title"])
        # resp["publisher"] = resp["publisher"][0]
        # resp["title"] = resp["title"][0]
        obj = GallicaBibObj.parse_obj(resp).convert()
        return obj

    def run(self, give_up=50) -> Any:
        """Try to get best match."""
        query = self.target.generate_query()
        try:
            resps = self.fetcher.fetch_query(query)
        except Exception as e:
            print_exception(e)
            return None

        matches = []
        for i, resp in enumerate(resps[:give_up]):
            candidate = self.resp_to_obj(resp)
            match = Match(self.target, candidate)
            matches.append(match)
            for m in matches:  # use a real loop so as to update _score
                if i < 3:
                    break
                if m.score > 0.7:
                    break

        if not matches:
            return None

        return max(matches)

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()


class GallicaResource(Representation):
    """A resource on Gallica."""

    BASE_TIMEOUT = 60

    def __init__(
        self, target: Union[Article, Book, Collection, Journal], source: Journal
    ):
        if any(isinstance(target, x) for x in (Book, Collection, Journal)):
            raise NotImplementedError("We only handle article for now")

        self.target = target
        self.source = source
        a = Ark.parse(source.ark)
        if a.is_left:
            raise a.value
        self.series_ark = a.value
        self._ark = None
        self._resource = None  # so we can pass resource around
        self.logger = logging.getLogger(type(self).__name__)  # maybe more precise.
        self._start_p = None
        self._end_p = None
        self._pages = None

    @property
    def ark(self):
        """Ark for the final target."""
        if not self._ark:
            if isinstance(self.source, Journal):
                self.get_issue()
            else:
                self._ark = self.series_ark

        return self._ark

    def check_vol_num(self, res):
        either = res.oairecord_sync()
        if either.is_left:
            raise either.value
        oai = either.value
        desc = oai["results"]["notice"]["record"]["metadata"]["oai_dc:dc"][
            "dc:description"
        ]
        desc = desc[1]
        vol = search(r".*T([0-9]+)", desc)
        vol = int(vol.group(1)) if vol else None
        no = search(r".*N([0-9]+)", desc)
        no = int(no.group(1)) if no else None
        if self.target.volume and self.target.volume == vol:
            return True
        if self.target.number and self.target.volume == no:
            return True
        return False

    def check_page_range(self, issue):
        """Check to see if page range in given issue."""
        either = issue.pagination_sync()
        if either.is_left:
            raise either.value
        pnos = either.value["livre"]["pages"]["page"]
        target = self.target.pages[0]
        if any(p["numero"] == target for p in pnos):
            return True
        else:
            return False

    def get_issue(self):
        """Get the right issue."""
        issues = Resource(self.series_ark).issues_sync(
            self.target._source().publicationdate
        )
        arks = []
        if issues.is_left:
            raise issues.value
        for detail in issues.value["issues"]["issue"]:
            arks.append(Ark(naan=self.series_ark.naan, name=detail["@ark"]))
        if self.target._source().volume or self.target._source().number:
            self.logger.debug("Trying to match by volume")
            for ark in arks:
                issue = Resource(ark)
                if self.check_vol_num(issue):
                    self._ark = ark
                    return ark
        self.logger.debug("Trying to match by page range.")
        for ark in arks:
            issue = Resource(ark)
            if self.check_page_range(issue):
                self._ark = ark
                return ark
        raise Exception("Failed to find matching issue")

    @property
    def resource(self):
        """Resource()"""
        if not self._resource:
            self._resource = Resource(self.ark)
            self._resource.timeout = self.BASE_TIMEOUT
        return self._resource

    @property
    def timeout(self):
        "Timeout in url requests."
        return self.resource.timeout

    @timeout.setter
    def timeout(self, val: int):
        self.resource.timeout = val
        return self.resource

    @property
    def pages(self):
        if not self._pages:
            either = self.resource.pagination_sync()
            if either.is_left:
                raise either.value
            self._pages = either.value
        return self._pages

    def get_physical_pno(self, logical_pno: str) -> int:
        """Get the physical pno for a logical pno."""
        pages = self.pages
        pnos = pages["livre"]["pages"]["page"]
        # sadly we have to do it ourselves
        for p in pnos:
            if p["numero"] == logical_pno:
                break
        return p["ordre"]

    @property
    def start_p(self):
        """Physical page we start on."""
        if not self._start_p:
            self._start_p = int(self.get_physical_pno(self.target.pages[0]))
        return self._start_p

    @property
    def end_p(self):
        """Physical page we end on."""
        if not self._end_p:
            self._end_p = int(self.get_physical_pno(self.target.pages[-1]))
        return self._end_p

    def download_pdf(self, path: Path, blocksize: int = 100, trials: int = 3) -> None:
        """Download a resource as a pdf in blocks to avoid timeout."""
        partials = []
        try:
            for i, (start, length) in enumerate(
                self._generate_blocks(self.start_p, self.end_p, blocksize)
            ):

                fn = path.with_suffix(f".pdf.{i}")
                status = self._fetch_block(start, length, trials, fn)
                if not status:
                    raise Exception("Failed to download.")
                with fn.open("rb") as f:
                    with Path("/tmp/test.pdf").open("wb") as o:
                        o.write(f.read())
                partials.append(fn)
            self._merge_partials(path, partials)
        finally:
            for fn in partials:
                fn.unlink()
        assert partials

    @staticmethod
    def _generate_blocks(start, end, size):
        """Generate Blocks"""
        beginnings = range(start, end + 1, size)
        for i in beginnings:
            length = end - i + 1 if i + size > end else size  # truncate last block
            yield (i, length)

    @staticmethod
    def _merge_partials(path: Path, partials: List[Path]) -> None:
        """Merge partial files"""
        merger = PdfFileMerger()
        for i, fn in enumerate(partials):
            args = {"pages": PageRange("2:")}  # if i else {}
            merger.append(str(fn.resolve()), **args)
        with path.open("wb") as f:
            merger.write(f)

    def _fetch_block(self, startview: int, nviews: int, trials: int, fn: Path) -> bool:
        """Fetch block."""
        url = self.resource.content_sync(
            startview=startview, nviews=nviews, url_only=True
        )
        for i in range(trials):
            status = downloader.download(
                url,
                download_file=str(fn.resolve()),
                timeout=120,
            )
            if status:
                if imghdr.what(fn):
                    print("We got ratelimited, sleeping for 5 minutes.")
                    sleep(60 * 5)
                else:
                    return True
            sleep(2 ** (i + 1))
        return status

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()
