"""Handle our internal cache, which we use to avoid hammering Gallica's
servers, and to make our life easier when re-running."""
import sqlite3
from collections import UserDict
from functools import wraps
from logging import getLogger
from multiprocessing import Lock
from os import getenv
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Optional

import jsonpickle
from requests_downloader import downloader
from xdg import xdg_cache_home

if TYPE_CHECKING:  # pragma: nocover
    from .gallipy import Ark  # pragma: nocover

logger = getLogger(__name__)


# This needs to exist at module scope to prevent pytest from garbage-collecting it away.
if getenv("CLEANCACHE"):
    tmpdir = TemporaryDirectory()
    cachedir = Path(tmpdir.__enter__()) / "gallica_autobib"
else:
    cachedir = xdg_cache_home() / "gallica_autobib"  # TODO what happens if not on unix?


class Cached(UserDict):
    """Cached resource."""

    CACHEFN = "cache.db"
    cachedir = cachedir
    write_lock = Lock()

    def __init__(self, cachename: str, *args, **kwargs) -> None:
        """A resource in the cache, stored in a separate table."""
        self.tablename = cachename
        self.cachedir.mkdir(exist_ok=True, parents=True)
        cache = self.cachedir / self.CACHEFN
        logger.debug(f"Cache: {cache}")
        self.con = sqlite3.connect(cache)
        MAKE_TABLE = f'CREATE TABLE IF NOT EXISTS "{cachename}" (key TEXT PRIMARY KEY, value BLOB)'
        self.con.execute(MAKE_TABLE)
        self.con.commit()
        super().__init__(*args, **kwargs)

    def __del__(self) -> None:
        self.con.close()

    def __getitem__(self, key: str) -> Optional[Any]:
        GET_ITEM = f'SELECT value FROM "{self.tablename}" WHERE key = (?)'
        item = self.con.execute(GET_ITEM, (key,)).fetchone()
        if item:
            return jsonpickle.loads(item[0])
        else:
            raise KeyError(key)

    def __setitem__(self, key: str, val: Any) -> None:
        self.write_lock.acquire()
        try:
            SET = f'REPLACE INTO "{self.tablename}" (key, value) VALUES (?,?)'
            self.con.execute(SET, (key, jsonpickle.dumps(val)))
            self.con.commit()
        finally:
            self.write_lock.release()


def cache_factory(cachename: str, enabled: bool) -> callable:
    _cache = Cached(cachename)

    def decorator(fn: callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if enabled:
                key = jsonpickle.dumps(
                    (*args, sorted(kwargs.items())), unpicklable=False
                )
                resp = _cache.get(key)
                if not resp:
                    resp = fn(*args, **kwargs)
                    _cache[key] = resp
                return resp
            else:
                return fn(*args, **kwargs)

        return wrapper

    return decorator


response_cache_enabled = bool(getenv("RESPONSE_CACHE", False))
response_cache = cache_factory("responses", response_cache_enabled)

data_cache_enabled = bool(getenv("DATA_CACHE", False))
_data_cache = Cached("data")
img_data_cache = cache_factory("img_data", data_cache_enabled)


def download(url, **kwargs):
    outdir = Path(kwargs.get("download_dir", "."))
    if data_cache_enabled:
        data = _data_cache.get(url)
        if not data:
            with TemporaryDirectory() as tmpdir:
                kwargs["download_dir"] = tmpdir
                fn = downloader.download(url, **kwargs)
                assert fn
                with (Path(tmpdir) / fn).open("rb") as f:
                    data = f.read()
                _data_cache[url] = data
        outf = outdir / kwargs["download_file"]
        with outf.open("wb") as f:
            f.write(data)
        return str(outf)
    else:
        return downloader.download(url, **kwargs)
