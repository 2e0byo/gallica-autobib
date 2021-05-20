"""Handle our internal cache, which we use to avoid hammering Gallica's
servers, and to make our life easier when re-running."""
from sqlitedict import SqliteDict
import jsonpickle
from typing import Optional, TYPE_CHECKING, Any
from xdg import xdg_cache_home

if TYPE_CHECKING:  # pragma: nocover
    from .gallipy import Ark  # pragma: nocover


class Cached:
    """Cached resource."""

    cachedir = xdg_cache_home() / "gallica_autobib"  # TODO what happens if not on unix?
    CACHEFN = "cache.db"

    def __init__(self, cachename: str) -> None:
        """A resource in the cache, stored in a separate table."""
        if not self.cachedir.exists():
            self.cachedir.mkdir()
        cache = self.cachedir / self.CACHEFN
        self.sqldict = SqliteDict(
            tablename=cachename,
            encode=jsonpickle.dumps,
            decode=jsonpickle.loads,
            autocommit=True,
            filename=str(cache),
        )

    def __getitem__(self, key: int) -> Optional[Any]:
        try:
            return self.sqldict[key]
        except KeyError:
            return None

    def __setitem__(self, key: int, val: any) -> None:
        self.sqldict[key] = val

    def __delitem__(self, key: int) -> None:
        del self.sqldict[key]
