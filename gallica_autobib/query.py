import imghdr
import logging
import unicodedata
from collections import namedtuple
from functools import total_ordering
from io import BytesIO
from pathlib import Path
from re import search
from time import sleep
from typing import (
    TYPE_CHECKING,
    Any,
    Generator,
    List,
    Optional,
    OrderedDict,
    Tuple,
    Union,
)

import requests
import sruthi
from bs4 import BeautifulSoup
from fuzzysearch import find_near_matches
from fuzzywuzzy import fuzz
from PIL import Image
from pydantic.utils import Representation
from PyPDF4 import PageRange, PdfFileMerger
from sruthi.response import SearchRetrieveResponse

from . import gallipy
from .cache import Cached, download, img_data_cache, response_cache
from .gallipy import Ark, Resource
from .models import Article, Book, Collection, GallicaBibObj, Journal

if TYPE_CHECKING:  # pragma: nocover
    from pydantic.typing import ReprArgs  # pragma: nocover


gallipy.helpers.fetch = response_cache(gallipy.helpers.fetch)


Pages = OrderedDict[str, OrderedDict[str, OrderedDict]]
ark_cache = Cached("ark")
source_match_cache = Cached("source_match")
ocr_cache = Cached("ocr_bounds")
UnscaledPageData = namedtuple(
    "UnscaledPageData", ["upper", "lower", "total_width", "total_height"]
)


class MatchingError(Exception):
    pass


class DownloadError(Exception):
    pass


def make_string_boring(unicodestr: str) -> Optional[str]:
    """Return unicode str as ascii for fuzzy matching."""
    if not unicodestr:
        return None
    normal = unicodedata.normalize("NFKD", unicodestr)
    return normal.lower().strip()


@total_ordering
class Match(
    Representation,
):
    """Object representing a match."""

    def __init__(self, target: Any, candidate: Any):
        self.target = target
        self.candidate = candidate
        self._score: Optional[float] = None

    @property
    def score(self) -> float:
        if not self._score:
            self._score = self._calculate_score()
        return self._score

    @property
    def confidence(self) -> str:
        return f"{self.score*100:2.4} %"

    def _calculate_score(self) -> float:
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
                    raise NotImplementedError(
                        f"Unable to compare {v} of type {type(v)} with {candidate_v} of type {type(candidate_v)}"
                    )

            if isinstance(v, list):
                matches = []
                if isinstance(candidate_v, list):
                    matches = [1 if i in candidate_v else 0 for i in v]
                elif candidate_v in v:
                    matches.append(1 / len(v))  # type: ignore
                else:
                    matches.append(0)
                vals[k] = sum(matches) / len(matches)

        self._vals = vals
        return sum(v for _, v in vals.items()) / len(vals)

    def __lt__(self, other: "Match") -> bool:
        return self.score < other.score

    def __gt__(self, other: "Match") -> bool:
        return self.score > other.score

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Match):
            return NotImplemented
        return self.score == other.score

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()  # type: ignore


class GallicaSRU(
    Representation,
):
    """Class to interact wtih Gallica"""

    URL = "http://catalogue.bnf.fr/api/SRU"

    def __init__(self) -> None:
        self.client = sruthi.Client(url=self.URL, record_schema="dublincore")

    @response_cache
    def fetch_query(self, query: str) -> SearchRetrieveResponse:
        return self.client.searchretrieve(query)

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()  # type: ignore


class Query(
    GallicaSRU,
    Representation,
):
    """Class to represent a query"""

    def __init__(self, target: Union[Article, Journal, Book, Collection]) -> None:
        super().__init__()
        self.target = target._source()
        self.fetcher = GallicaSRU()
        self.logger = logging.getLogger(f"QU {target.name(short=6)}")
        self.skip_match_score = 0.7

    @staticmethod
    def get_at_str(obj: Union[str, List[str]]) -> Optional[str]:
        if not obj:
            return None
        if isinstance(obj, str):
            return obj
        return obj[0]

    def resp_to_obj(self, resp: dict) -> GallicaBibObj:
        """Convert resp to GallicaBibObj"""
        resp["ark"] = self.get_at_str(resp["identifier"])
        # could use a Language() obj to internationalise this
        resp["language"] = resp["language"][1]
        resp["type"] = resp["type"][0]["text"]
        if "publisher" in resp.keys():
            resp["publisher"] = self.get_at_str(resp["publisher"])
        resp["title"] = self.get_at_str(resp["title"])
        obj = GallicaBibObj.parse_obj(resp).convert()
        return obj  # type: ignore

    def run(self, give_up: int = 50) -> Any:
        """Try to get best match."""
        self.logger.debug("Generting query")
        query = self.target.generate_query()
        self.logger.debug("Fetching query")
        resps = self.fetcher.fetch_query(query)
        self.logger.debug(f"Got {len(list(resps))} candidates.")
        matches = []
        for i, resp in enumerate(resps[:give_up]):
            candidate = self.resp_to_obj(resp)
            candidate_match = Match(self.target, candidate)
            matches.append(candidate_match)
            if i > 3:
                if any(m.score > self.skip_match_score for m in matches):
                    break

        if not matches:
            self.logger.debug("Failed to match.")
            return None

        candidate_match = max(matches)
        self.logger.debug(f"Matched. {repr(candidate_match)}")
        return candidate_match

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()  # type: ignore


class DownloadableResource(Representation):
    """A downloadable resouce on Gallica."""

    BASE_TIMEOUT = 60

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        self._ark: Optional[Union[str, Ark]] = None
        self._start_p: Optional[int] = None
        self._end_p: Optional[int] = None
        self._resource: Optional[Resource] = None  # so we can pass resource around
        self._pages: Optional[Pages] = None
        self.logger = logging.getLogger("DR")
        self.trials: int = 7
        self.suppress_cover_page: bool = False
        self._backoff = 0

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()  # type: ignore

    def set_max_pages(self) -> None:
        """Set maximum page range to download all pages."""
        either = self.resource.pagination_sync()
        if either.is_left:
            raise either.value

        res = either.value
        pages = int(res["livre"]["structure"]["nbVueImages"])
        self.start_p = 1
        self.end_p = pages

    @property
    def ark(self) -> Optional[Union[str, Ark]]:
        return self._ark

    @ark.setter
    def ark(self, val: str) -> None:
        res = Ark.parse(val)
        if res.is_left:
            raise res.value
        self._ark = res.value

    @property
    def resource(self) -> Resource:
        """Resource()"""
        if not self._resource:
            self._resource = Resource(self.ark)
            self._resource.timeout = self.BASE_TIMEOUT
        return self._resource

    @property
    def start_p(self) -> int:
        if not self._start_p:
            raise ValueError("Start page not set")
        return self._start_p

    @start_p.setter
    def start_p(self, val: int) -> None:
        self._start_p = val

    @property
    def end_p(self) -> int:
        if not self._end_p:
            raise ValueError("Start page not set")
        return self._end_p

    @end_p.setter
    def end_p(self, val: int) -> None:
        self._end_p = val

    @property
    def pages(self) -> Optional[Pages]:
        """Physical pages in volume."""
        if not self._pages:
            either = self.resource.pagination_sync()
            if either.is_left:
                raise either.value
            self._pages = either.value
        return self._pages

    def get_physical_pno(self, logical_pno: str, pages: Pages = None) -> int:
        """Get the physical pno for a logical pno."""
        if not pages:
            pages = self.pages
        pnos = pages["livre"]["pages"]["page"]  # type: ignore
        if not pnos:
            raise ValueError("No page numbers present.")
        # sadly we have to do it ourselves
        for p in pnos:
            if p["numero"] == logical_pno:
                break
        return p["ordre"]

    @img_data_cache
    @staticmethod
    def fetch_image(resource: Resource, pno: int) -> bytes:
        """Fetch image from resource as bytes.

        This method is used as a fallback where we can't get the data any other
        way.
        """
        either = resource.iiif_data_sync(view=pno)
        if either.is_left:
            raise either.value
        return either.value

    @staticmethod
    def pdf_unavailable(url: str) -> bool:
        """Work out if we can get the pdf or need to fall back on the images."""
        return requests.head(url).status_code == 451

    def download_pdf(
        self,
        path: Path,
        blocksize: int = 100,
        fetch_only: int = None,
    ) -> bool:
        """Download a resource as a pdf in blocks to avoid timeout.

        If http 451 is encountered, fall back on the image api (ignoring blocks)."""
        partials = []

        if path.exists():
            return True
        try:
            if not self.start_p or not self.end_p:
                raise Exception("No pages.")

            trial_url = self.resource.content_sync(
                startview=self.start_p, nviews=1, url_only=True
            )
            if self.pdf_unavailable(trial_url):
                self.logger.warn(
                    f"Failed to download with {trial_url}; falling back to image"
                )

                partials = self.download_pdf_images(path, fetch_only)
            else:
                self.logger.debug("Getting pdf with pdf chunk downloader.")
                fetch = (
                    self.end_p + fetch_only - 1
                    if fetch_only is not None
                    else self.end_p
                )
                partials = self.download_pdf_chunks(
                    path, blocksize, self.start_p, fetch
                )

            self._merge_partials(path, partials)
        finally:
            for fn in partials:
                fn.unlink()
        assert partials
        return False

    @staticmethod
    def get_pdf_url(outf: Path, blocksize: int, fetch_only: int = None) -> bool:
        pass

    def download_pdf_chunks(
        self, path: Path, blocksize: int, start_p: int, fetch: int
    ) -> list[Path]:
        """Download pdf in chunks, saving to path."""
        partials = []
        for i, (start, length) in enumerate(
            self._generate_blocks(start_p, fetch, blocksize)
        ):

            fn = path.with_suffix(f".pdf.{i}")
            status = self._fetch_block(start, length, fn)
            if not status:
                raise DownloadError("Failed to download.")
            partials.append(fn)
        return partials

    def download_pdf_images(self, path: Path, fetch_only: int = None) -> list[Path]:
        """Download a resource as a pdf using the iif image endpoint."""
        fetch = fetch_only - 1 if fetch_only is not None else self.end_p
        end_p = self.start_p + fetch
        partials = []

        for pno in range(self.start_p, end_p + 1):
            self.logger.debug(f"Fetching page {pno} as image")
            data = self.fetch_image(self.resource, pno)
            # load img
            fn = path.parent / f"pg{pno}.pdf"
            img = Image.open(BytesIO(data))
            img.save(fn, "PDF")
            partials.append(fn)

        return partials

    @staticmethod
    def _generate_blocks(start: int, end: int, size: int) -> Generator:
        """Generate Blocks"""
        beginnings = range(start, end + 1, size)
        for i in beginnings:
            length = end - i + 1 if i + size > end else size  # truncate last block
            yield (i, length)

    def _merge_partials(self, path: Path, partials: List[Path]) -> None:
        """Merge partial files"""
        merger = PdfFileMerger()
        for i, fn in enumerate(partials):
            if self.suppress_cover_page:
                args = {"pages": PageRange("2:")}  # if i else {}
            else:
                args = {"pages": PageRange("2:")} if i else {}
            merger.append(str(fn.resolve()), **args)
        with path.open("wb") as f:
            merger.write(f)

    def _fetch_block(self, startview: int, nviews: int, fn: Path) -> bool:
        """Fetch block."""
        url = self.resource.content_sync(
            startview=startview, nviews=nviews, url_only=True
        )
        for i in range(self.trials):
            status = download(
                url,
                download_file=str(fn.resolve()),
                timeout=120,
            )
            if status:
                if imghdr.what(fn):
                    print("We got ratelimited, backing off")
                    self._backoff += 1
                    if self._backoff > 9:
                        raise Exception("We got ratelimited.")
                    sleep(2**self._backoff)
                else:
                    self._backoff = 0
                    return True
            sleep(2 ** (i + 1))
        return False


class GallicaResource(DownloadableResource):
    """A matched resource on gallica."""

    def __init__(
        self,
        target: Union[Article, Book, Collection, Journal],
        source: Union[Journal, Book, Collection],
        cache: bool = True,
        **kwargs: dict[str, Any],
    ):
        super().__init__(**kwargs)
        if any(isinstance(target, x) for x in (Book, Collection, Journal)):
            raise NotImplementedError("We only handle article for now")
        if any(isinstance(source, x) for x in (Book, Collection)):
            raise NotImplementedError("We only handle fetching from journals")
        self.logger = logging.getLogger(f"GR {target.name(short=6)}")

        self.target = target
        self.key = target.key()
        self.source = source
        a = Ark.parse(source.ark)
        if a.is_left:
            raise a.value
        self.series_ark = a.value
        self._ark = ark_cache.get(self.key) if cache else None
        self.logger.debug(f"Ark is {self._ark}, {self.key}")
        self.consider_toc = True
        self.source_match = source_match_cache.get(self.key) if cache else None
        self.logger.debug(f"Source match is {self.source_match}")
        self.minimum_confidence = 0.5
        self._desired_pages: Optional[List[int]] = None
        self._ocr_bounds = ocr_cache.get(self.key) if cache else None

    @DownloadableResource.ark.getter  # type: ignore
    def ark(self) -> Optional[Union[str, Ark]]:
        """Ark for the final target."""
        if not self._ark:
            self.get_ark()
        return self._ark

    def get_ark(self) -> None:
        if isinstance(self.source, Journal):
            self.logger.debug("No ark, Finding best match.")
            self.source_match = self.get_best_article_match()
            source_match_cache[self.key] = self.source_match
            if self.source_match:
                self._ark = self.source_match.candidate.ark
            else:
                raise MatchingError("Unable to match.")
        else:
            self._ark = self.source.ark
        ark_cache[self.key] = self._ark
        self.logger.debug(f"Saving ark {self.key} = {ark_cache[self.key]}")

    @property
    def match(self) -> Optional[Match]:
        """The Match() object representing our choice.

        This will trigger a match even if we use a cached download. (However if
        we have a cached match and have not disabled caching, we will use
        that.)

        """
        if not self.source_match:
            if not self.ark:
                raise MatchingError("Target has no ark!")
            source_match_cache[self.key] = self.source_match
        return self.source_match

    def get_possible_issues(self) -> List[OrderedDict]:
        """Get possible issues.

        We go a year in each direction since sometimes collections of issues
        are made for two years.
        """
        self.logger.debug("Getting possible issues.")
        source = self.target._source()
        issues = []
        years = []
        if isinstance(source.publicationdate, list):
            for year in source.publicationdate:
                years += list(range(year - 1, year + 2))
        else:
            years = list(range(source.publicationdate - 1, source.publicationdate + 2))
        for year in set(years):
            issue = Resource(self.series_ark).issues_sync(str(year))
            if not issue.is_left:
                issues.append(issue.value)
            else:
                self.logger.debug(f"unable to fetch year {year}")
        if not issues:
            raise MatchingError("Failed to find any matching issues")

        details = []
        for year in issues:
            detail = year["issues"]["issue"]
            if isinstance(detail, list):
                details += detail
            else:
                details.append(detail)
        return details

    @classmethod
    def parse_description(cls, desc: str) -> dict:
        """Parse a dublincore description as retrieved from galllica."""
        resp = dict(year=None, volume=None, number=None)
        if "-" in desc:
            start, end = [cls.parse_description(x) for x in desc.split("-")]
            for k, v in start.items():
                end_v = end[k]
                if not end_v or v == end_v:
                    continue
                start[k] = list(range(v, end_v + 1))
            return start
        resp["year"] = search(r"([0-9][0-9][0-9][0-9])", desc)  # type: ignore
        resp["volume"] = search(r"T([0-9]+)", desc)  # type: ignore
        resp["number"] = search(r"N([0-9]+)", desc)  # type: ignore
        resp.update({k: int(v.group(1)) for k, v in resp.items() if v})  # type: ignore
        return resp

    def ocr_find_article_in_journal(
        self, journal: Resource, pages: OrderedDict
    ) -> bool:
        """Use ocr to find an article in a journal.

        The algorithm:

         1. determines the physical page number of the first page of the article
         2. fetches this page as text (the physical page number = the view number)
         3. does a fuzzy search on this page for the title
         4. if it matches, looks for the author's name on the page
         5. if not found, gets the view number of the last page of the article and fetches that
         6. looks for the author's name on this page

        This is a good deal simpler than trying to parse an ocrd text back into
        individual articles, which is probably a non-starter.
        """
        target: Article = self.target  # type: ignore
        start_p = self.get_physical_pno(target.pages[0], pages)
        start_page = make_string_boring(self.fetch_text(journal, start_p))
        if not start_page:
            return False

        title = make_string_boring(target.title)
        author = make_string_boring(target.author)
        matches = find_near_matches(title, start_page, max_l_dist=2)
        if not matches:
            self.logger.debug("Failed to find title on page")
            return False
        if matches := find_near_matches(author, start_page, max_l_dist=5):
            if fuzz.ratio(matches[0].matched, author) > 80:
                return True
        else:
            self.logger.debug("Failed to find author on first page.")
        end_p = self.get_physical_pno(target.pages[-1], pages)
        end_page = make_string_boring(self.fetch_text(journal, end_p))
        if matches := find_near_matches(author, end_page, max_l_dist=5):
            if fuzz.ratio(matches[0].matched, author) > 80:
                return True
        self.logger.debug("Failed to find author on last page.")
        return False

    @classmethod
    def fetch_text(cls, resource: Resource, pno: int) -> str:
        """Fetch text from resource as str."""
        either = resource.content_sync(startview=pno, nviews=1, mode="texteBrut")
        if either.is_left:
            raise either.value
        soup = BeautifulSoup(either.value, "xml")
        return " ".join(x.text for x in soup.hr.next_siblings if not x.name == "hr")

    def toc_find_article_in_journal(
        self, journal: Resource, toc: str, pages: Pages, data: dict
    ) -> List[Article]:
        """Find article in journal using journal's toc.

        This is preferable to relying on fuzzy matching ocr, but not all
        journals have tocs.

        Currently we build _all possible articles_ and return them all. This is
        probably redundant, and we could adopt the strategy of
        `ocr_find_article_in_journal` i.e. predict and see if the prediction
        holds.

        """
        target: Article = self.target  # type: ignore
        target_start_p = str(target.pages[0])
        entries = [x for x in self.parse_gallica_toc(toc) if x[0] == target_start_p]
        entries.sort(key=lambda x: int(x[0]))
        articles = []
        for i, x in enumerate(entries):
            args = data.copy()
            start_p, title = x
            try:
                author, title = search(r"(.+?)\.* - (.+)", title).groups()  # type: ignore
            except AttributeError:
                try:
                    author, title = search(r"(.+?)\. (.+)", title).groups()  # type: ignore
                except AttributeError:
                    self.logger.debug(f"Unable to parse toc entry {x[1]}")
                    author = ""

            args["author"] = author.strip()
            args["title"] = title.strip()
            try:
                end_p = int(entries[i + 1][0]) - 1
            except IndexError:
                end_p = self.get_last_pno(pages)  # type: ignore
            args["pages"] = list(range(int(start_p), int(end_p) + 1))
            physical_start_p = self.get_physical_pno(start_p, pages)
            physical_end_p = self.get_physical_pno(str(end_p), pages)
            args["physical_pages"] = list(
                range(int(physical_start_p), int(physical_end_p) + 1)
            )
            articles.append(Article.parse_obj(args))

        return articles

    @staticmethod
    def parse_gallica_toc(xml: str) -> List[Tuple[str, str]]:
        """Parse Gallica' toc xml.  There are, needless to say, *several* forms."""
        soup = BeautifulSoup(xml, "xml")
        toc = []
        if soup.find("row"):
            for row in soup.find_all("row"):
                title = pno = None
                if seg := row.find("seg"):
                    title = seg.text.strip()
                if xref := row.find("xref"):
                    pno = xref.text.strip()
                if title and pno:
                    toc.append((pno, title))
        else:
            for item in soup.find_all("item"):
                if not item.find("seg"):
                    continue
                toc.append((item.xref.text.strip(), item.seg.text.strip()))
        return toc

    def get_article_candidates(self) -> List[Match]:
        """Generate match objs for each article in the corresponding issues.

        Returns:
          A list of Match() objects in order of decreasing score.
        """
        self.logger.debug("Generating article candidates")
        details = self.get_possible_issues()
        matches = []
        for detail in details:
            self.logger.debug(f"Considering {detail['#text']}")
            data = {}
            ark = Ark(naan=self.series_ark.naan, name=detail["@ark"])
            issue = Resource(ark)

            either = issue.oairecord_sync()
            if either.is_left:
                raise either.value
            oai = either.value
            dublin = oai["results"]["notice"]["record"]["metadata"]["oai_dc:dc"]
            description = dublin["dc:description"][1]
            data.update(self.parse_description(description))
            data["journaltitle"] = dublin["dc:title"]
            data["publisher"] = dublin["dc:publisher"]
            data["ark"] = dublin["dc:identifier"]

            either = issue.pagination_sync()
            if either.is_left:
                raise either.value
            pages = either.value

            articles = []
            if self.consider_toc and not (either := issue.toc_sync()).is_left:
                articles = self.toc_find_article_in_journal(
                    issue, either.value, pages, data
                )
                matches += [Match(self.target, a) for a in articles]
            if not articles:
                if self.ocr_find_article_in_journal(issue, pages):
                    args = dict(self.target)
                    args.update(data)
                    matches.append(Match(self.target, Article.parse_obj(args)))

            matches.sort(reverse=True)
            if matches and matches[0].score > 0.7:
                break

        return matches[:5]

    def get_best_article_match(self) -> Optional[Match]:
        """Get best available article match."""
        matches = self.get_article_candidates()
        for match in matches:
            if match.score < self.minimum_confidence:
                self.logger.debug(
                    f"Match score {match.score} below"
                    "minimum threshold {self.minimum_confidence}"
                )
                return None
            res = Resource(match.candidate.ark)
            either = res.content_sync(1, 1, "texteBrut")
            if not either.is_left:
                self._resource = res
                return match
            self.logger.debug(f"Skipping unavailable match {match.candidate}")

        return None

    @property
    def desired_pages(self) -> List[int]:
        """The pages we want to get from the target, as views (physical pnos)."""
        if not self._desired_pages:
            if hasattr(self.target, "pages"):
                self._desired_pages = [
                    self.get_physical_pno(p) for p in self.target.pages  # type: ignore
                ]
            else:
                pages = self.pages
                self._desired_pages = [int(p["ordre"]) for p in pages]  # type: ignore

        return self._desired_pages

    @property
    def ocr_bounds(self) -> List[UnscaledPageData]:
        """Text box from Gallica's ocr for every page."""
        if not self._ocr_bounds:
            bounds = []
            for pno in self.desired_pages:
                soup = self.get_ocr_data(pno)
                page = soup.find("Page")
                height, width = int(page.get("HEIGHT")), int(page.get("WIDTH"))
                printspace = soup.find("PrintSpace")
                text_height = int(printspace.get("HEIGHT"))
                text_width = int(printspace.get("WIDTH"))
                vpos = int(printspace.get("VPOS"))
                hpos = int(printspace.get("HPOS"))
                bounds.append(
                    UnscaledPageData(
                        (hpos, vpos),
                        (hpos + text_width, vpos + text_height),
                        width,
                        height,
                    )
                )
            self._ocr_bounds = bounds
        return self._ocr_bounds

    def get_ocr_data(self, pno: int) -> BeautifulSoup:
        """Get ocr data from Gallica for pno."""
        self.logger.debug(f"Getting ocr data for page {pno}")
        for _ in range(self.trials):
            either = self.resource.ocr_data_sync(view=pno)
            if not either.is_left:
                return BeautifulSoup(either.value.decode(), "xml")
        raise DownloadError(f"Failed to fetch ocr data for p {pno}")

    @property
    def timeout(self) -> int:
        "Timeout in url requests."
        return self.resource.timeout

    @timeout.setter
    def timeout(self, val: int) -> None:
        self.resource.timeout = val

    @staticmethod
    def get_last_pno(pages: Pages) -> str:
        """Get last page number of internal volume."""
        pnos = pages["livre"]["pages"]["page"]
        if not pnos:
            raise ValueError("No page numbers present.")
        for p in reversed(pnos):
            if p["pagination_type"] == "A":
                break
        return p["ordre"]

    @DownloadableResource.start_p.getter  # type: ignore
    def start_p(self) -> Optional[int]:
        """Physical page we start on."""
        if not self._start_p:
            self._start_p = int(self.get_physical_pno(self.target.pages[0]))  # type: ignore
        return self._start_p

    @DownloadableResource.end_p.getter  # type: ignore
    def end_p(self) -> Optional[int]:
        """Physical page we end on."""
        if not self._end_p:
            try:
                self._end_p = int(self.get_physical_pno(self.target.pages[-1]))  # type: ignore
            except AttributeError:
                pass
        return self._end_p

    def __repr_args__(self) -> "ReprArgs":
        return ((k, repr(v)) for k, v in self.__dict__.items())  # type: ignore
