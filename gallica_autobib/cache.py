"""Handle our internal cache, which we use to avoid hammering Gallica's
servers, and to make our life easier when re-running."""
import sqlite3
from typing import TYPE_CHECKING, Any, Optional

import jsonpickle
from xdg import xdg_cache_home

if TYPE_CHECKING:  # pragma: nocover
    from .gallipy import Ark  # pragma: nocover


class Cached:
    """Cached resource."""

    cachedir = xdg_cache_home() / "gallica_autobib"  # TODO what happens if not on unix?
    CACHEFN = "cache.db"

    def __init__(self, cachename: str) -> None:
        """A resource in the cache, stored in a separate table."""
        self.tablename = cachename
        if not self.cachedir.exists():
            self.cachedir.mkdir()
        cache = self.cachedir / self.CACHEFN
        self.con = sqlite3.connect(cache)
        MAKE_TABLE = f'CREATE TABLE IF NOT EXISTS "{cachename}" (key TEXT PRIMARY KEY, value BLOB)'
        self.con.execute(MAKE_TABLE)
        self.con.commit()

    def __del__(self) -> None:
        self.con.close()

    def __getitem__(self, key: str) -> Optional[Any]:
        GET_ITEM = f'SELECT value FROM "{self.tablename}" WHERE key = (?)'
        item = self.con.execute(GET_ITEM, (key,)).fetchone()
        if item:
            return jsonpickle.loads(item[0])
        else:
            return None

    def __setitem__(self, key: str, val: Any) -> None:
        SET = f'REPLACE INTO "{self.tablename}" (key, value) VALUES (?,?)'
        self.con.execute(SET, (key, jsonpickle.dumps(val)))
        self.con.commit()
