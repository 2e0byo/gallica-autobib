from gallica_autobib import cache
from tempfile import TemporaryDirectory
from pathlib import Path
import pytest


@pytest.fixture
def tmp_cache():
    with TemporaryDirectory() as tmp_path:
        cache.Cached.cachedir = Path(tmp_path) / "cache"
        yield cache.Cached


def test_cache(tmp_cache):
    print(tmp_cache.cachedir)
    cache = tmp_cache("test")
    print(cache.cachedir)
    assert not cache[7]
    cache[7] = "this"
    assert cache[7] == "this"
    cache[7] = dict(seven=7)
    assert cache[7] == dict(seven=7)
    del cache
    cache = tmp_cache("test")
    assert cache[7] == dict(seven=7)
