import pytest
from gallica_autobib import util

page_ranges = [
    [[str(i) for i in range(217, 248)], "217--47"],
    [[str(i) for i in range(1, 11)], "1--10"],
    [[str(i) for i in range(450, 456)], "450--5"],
    [[str(i) for i in range(450, 470)], "450--69"],
    [["10", "11", "12", "13", "17", "18", "19"], "10--3, 17--9"],
    [["i", "ii", "iii"], "i--iii"],
    [["1", "2", "i", "ii", "iii"], "1--2, i--iii"],
]


@pytest.mark.parametrize("inp,oup", page_ranges)
def test_page_ranges(inp, oup):
    assert util.pretty_page_range(inp) == oup


@pytest.mark.parametrize("inp,oup", page_ranges[:4])
def test_deprettify(inp, oup):
    pretty = util.pretty_page_range(inp)
    assert util.deprettify(pretty) == [int(i) for i in inp]
