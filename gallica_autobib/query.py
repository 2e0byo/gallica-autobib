from .models import GallicaBibObj
from pydantic.utils import Representation
from traceback import print_exception
import sruthi
from fuzzywuzzy import fuzz
import unicodedata


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
                if isinstance(candidate_v, int):
                    vals[k] = 1 if candidate_v == v else 0
                elif isinstance(candidate_v, list):
                    vals[k] = 1 if v in candidate_v else 0
                else:
                    raise NotImplementedError

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


class GallicaFetcher(Representation):
    """Class to interact wtih Gallica"""

    URL = "http://catalogue.bnf.fr/api/SRU"

    def __init__(self):
        self.client = sruthi.Client(url=self.URL, record_schema="dublincore")

    def fetch_query(self, query: str) -> SearchRetrieveResponse:
        return self.client.searchretrieve(query)

    def __repr_args__(self) -> "ReprArgs":
        return self.__dict__.items()


class Query(GallicaFetcher, Representation):
    """Class to represent a query"""

    def __init__(self, target):
        super().__init__()
        self.target = target._source()
        self.fetcher = GallicaFetcher()

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
            print(resp)
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
