from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from gallica_autobib import cache


@pytest.fixture
def tmp_cache():
    with TemporaryDirectory() as tmp_path:
        cache.Cached.cachedir = Path(tmp_path) / "cache"
        yield cache.Cached


def test_cache(tmp_cache):
    cache = tmp_cache("test")
    with pytest.raises(KeyError):
        cache[7]
    cache[7] = "this"
    assert cache[7] == "this"
    cache[7] = dict(seven=7)
    assert cache[7] == dict(seven=7)
    del cache
    cache = tmp_cache("test")
    assert cache[7] == dict(seven=7)
    # test that we're dict-like
    assert cache.get(7) == dict(seven=7)
    assert cache.get(9, "oops") == "oops"
