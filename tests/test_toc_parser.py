from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from gallica_autobib import toc_parser

test_dir = Path(__file__).with_suffix("")


@pytest.mark.parametrize("fn", ["cell_seg", "item_seg", "item_seg2", "tr", "cell_seg2"])
def test_toc_parser(fn, data_regression):
    data = (test_dir / f"{fn.replace('_', '-')}.xml").read_text()
    res = toc_parser.parse_xml_toc(data)
    data_regression.check([dict(x) for x in res])
