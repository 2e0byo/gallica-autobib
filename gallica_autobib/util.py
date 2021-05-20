from typing import Union
import roman


def pretty_page_range(pages: list[Union[str, int]]) -> str:
    """Prettify a page range."""
    ranges = []
    try:
        int(pages[0])
        arabic = True
    except ValueError:
        arabic = False

    pp = []
    for p in pages:
        if arabic:
            try:
                pp.append(int(p))
            except ValueError:
                ranges.append(dict(arabic=arabic, pages=pp))
                arabic = False
                pp = [roman.fromRoman(p.upper())]
        else:
            try:
                pp.append(roman.fromRoman(p.upper()))
            except roman.InvalidRomanNumeralError:
                ranges.append(dict(arabic=arabic, pages=pp))
                arabic = True
                pp = [p]
    ranges.append(dict(arabic=arabic, pages=pp))

    pretty = []
    for r in ranges:
        pp = [r["pages"][0]]
        arabic = r["arabic"]
        for p in r["pages"][1:]:
            if p == pp[-1] + 1:
                pp.append(p)
            else:
                pretty.append(prettify(pp, arabic))
                pp = [p]
        pretty.append(prettify(pp, arabic))

    return "pp. " + ", ".join(pretty)


def prettify(pages: list[int], arabic: bool) -> str:
    """Pages is a continuous range of ints."""
    if arabic:
        start = str(pages[0])
        end = str(pages[-1])
        if len(start) == len(end):
            end = "".join(end[i] for i in range(len(end)) if end[i] != start[i])
        return f"{start}--{end}"
    else:
        # for now we don't do anything clever with roman numerals, although
        # combining is possible.
        return f"{roman.toRoman(pages[0]).lower()}--{roman.toRoman(pages[-1]).lower()}"
