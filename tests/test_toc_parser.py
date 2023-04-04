from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from gallica_autobib import toc_parser

test_dir = Path(__file__).with_suffix("")


@pytest.mark.parametrize(
    "fn",
    [
        "cell-seg.xml",
        "item-seg.xml",
        "item-seg2.xml",
        "item-seg3.xml",
        "tr.xml",
        "cell-seg2.xml",
    ],
)
def test_toc_parser(fn, data_regression):
    data = (test_dir / fn).read_text()
    res = toc_parser.parse_xml_toc(data)
    data_regression.check([dict(x) for x in res])
