"""Test parsers for various things gallica returns.

Wouldn't it be nice if apis returned machine-readable data?!
"""
import pytest
from pathlib import Path
from devtools import debug

test_tocs = ["toc-no-cells.xml", "toc-with-cells.xml"]


@pytest.mark.parametrize("xml", test_tocs)
def test_parse_toc(data_regression, gallica_resource, xml):
    with (Path("tests/test_parse_gallica") / xml).open() as f:
        data_regression.check(gallica_resource.parse_gallica_toc(f.read().strip()))
