"""Handle our internal cache, which we use to avoid hammering Gallica's
servers, and to make our life easier when re-running."""
import sqlite3
from collections import UserDict
from functools import wraps
from hashlib import sha256
from logging import getLogger
from multiprocessing import Lock
from os import getenv
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, Optional

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
    """A cached resource."""

    def __init__(self, *args, enabled: bool = True, **kwargs):
        """Initialise a cached resource, cached in ram."""
        self.enabled = enabled
        super().__init__(*args, **kwargs)

    def __call__(self, fn: Callable) -> Callable:
        """Wrap a resource and optionally look it up in a cache."""

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.enabled:
                key = jsonpickle.dumps(
                    (*args, sorted(kwargs.items())), unpicklable=False
                )
                resp = self.get(key)
                if not resp:
                    logger.debug(f"Cache miss for {key}")
                    resp = fn(*args, **kwargs)
                    self[key] = resp
                else:
                    logger.debug(f"Cache hit for {key}")
                return resp
            return fn(*args, **kwargs)

        return wrapper


class FSMixin:
    cachedir = cachedir


class SQLCached(Cached, FSMixin):
    """A Cached resource in an sql table."""

    CACHEFN = "cache.db"
    write_lock = Lock()

    def __init__(self, cachename: str, *args: Any, **kwargs: Any) -> None:
        """Initialise a resource in the cache, stored in a separate table."""
        super().__init__(*args, **kwargs)
        self.tablename = cachename
        self.cachedir.mkdir(exist_ok=True, parents=True)
        cache = self.cachedir / self.CACHEFN
        logger.debug(f"Cache: {cache}")
        self.con = sqlite3.connect(cache)
        MAKE_TABLE = f'CREATE TABLE IF NOT EXISTS "{cachename}" (key TEXT PRIMARY KEY, value BLOB)'
        self.con.execute(MAKE_TABLE)
        self.con.commit()

    def __del__(self) -> None:
        """Cleanup."""
        self.con.close()

    def __delitem__(self, key: str):
        """Remove an item from the cache."""
        self.write_lock.acquire()
        DELETE = f'DELETE FROM "{self.tablename}" WHERE key = (?)'  # skipcq: BAN-B608
        try:
            self.con.execute(DELETE, (key,))
            self.con.commit()
        finally:
            self.write_lock.release()

    def __getitem__(self, key: str) -> Optional[Any]:
        """Get an item from the cache."""
        GET_ITEM = (
            f'SELECT value FROM "{self.tablename}" WHERE key = (?)'  # skipcq: BAN-B608
        )
        item = self.con.execute(GET_ITEM, (key,)).fetchone()
        if item:
            return jsonpickle.loads(item[0])
        raise KeyError(key)

    def __setitem__(self, key: str, val: Any) -> None:
        """Put an item in the cache."""
        self.write_lock.acquire()
        try:
            SET = f'REPLACE INTO "{self.tablename}" (key, value) VALUES (?,?)'
            self.con.execute(SET, (key, jsonpickle.dumps(val)))
            self.con.commit()
        finally:
            self.write_lock.release()


class FSCached(Cached, FSMixin):
    """A cache in the file system."""

    def __init__(self, cachename: str, *args, **kwargs):
        """Initialise a new file system cache."""
        self.wdir = self.cachedir / cachename
        self.wdir.mkdir(parents=True, exist_ok=True)
        super().__init__(*args, **kwargs)

    def _fn(self, key: str) -> Path:
        return self.wdir / sha256(key.encode()).hexdigest()

    def __delitem__(self, key: str):
        """Remove an item from the cache."""
        try:
            self._fn(key).unlink()
        except FileNotFoundError:
            raise KeyError(key)

    def __getitem__(self, key: str):
        """Get an item from the cache."""
        try:
            return self._fn(key).read_bytes()
        except FileNotFoundError:
            raise KeyError(key)

    def __setitem__(self, key: str, val: bytes):
        """Put an item in the cache."""
        self._fn(key).write_bytes(val)


response_cache_enabled = bool(getenv("RESPONSE_CACHE", False))
response_cache = SQLCached("responses", enabled=response_cache_enabled)

data_cache_enabled = bool(getenv("DATA_CACHE", False))
data_cache = FSCached("data", enabled=data_cache_enabled)
img_data_cache = FSCached("img_data", enabled=data_cache_enabled)


def download(url: str, **kwargs: Any) -> Optional[str]:
    """Download a resource, storing it in the cache if we are caching."""
    outdir = Path(kwargs.get("download_dir", "."))
    if data_cache_enabled:
        data = data_cache.get(url)
        if not data:
            with TemporaryDirectory() as tmpdir:
                kwargs["download_dir"] = tmpdir
                fn = downloader.download(url, **kwargs)
                assert fn
                with (Path(tmpdir) / fn).open("rb") as f:
                    data = f.read()
                data_cache[url] = data
        outf = outdir / kwargs["download_file"]
        with outf.open("wb") as f:
            f.write(data)
        return str(outf)
    return downloader.download(url, **kwargs)
