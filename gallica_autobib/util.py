from itertools import cycle
from typing import Iterable, Union

import roman
from PIL import Image


def pretty_page_range(pages: list[str]) -> str:
    """Prettify a page range."""
    ranges: list[dict] = []
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
                pp = [int(p)]
    ranges.append(dict(arabic=arabic, pages=pp))

    pretty = []
    for r in ranges:
        pp = [r["pages"][0]]
        arabic = r["arabic"]
        for pqr in r["pages"][1:]:
            if pqr == pp[-1] + 1:
                pp.append(pqr)
            else:
                pretty.append(prettify(pp, arabic))
                pp = [pqr]
        pretty.append(prettify(pp, arabic))

    return ", ".join(pretty)


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


def deprettify(rangestr: Union[str, int]) -> Union[list[int], int, None]:
    try:
        return int(rangestr)
    except ValueError:
        pass
    pages = []
    ranges = rangestr.split(",")  # type: ignore
    for r in ranges:
        try:
            start, end = r.replace("--", "-").split("-")
            ls, le = len(start), len(end)
            if le < ls:
                end = start[: ls - le] + end
            pages += list(range(int(start), int(end) + 1))
        except ValueError:
            pages.append(int(r))

    return pages if len(pages) > 1 else pages[0] if pages else None


def show(img: Image.Image, boxes: Iterable[tuple] = None) -> None:
    """Show an image with optional bounds drawn over it."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots()
    plt.imshow(img)
    if boxes:
        colours = ("red", "green", "orange", "blue", "violet")
        for bounds, colour in zip(boxes, cycle(colours)):
            box = ax.add_patch(
                Rectangle(
                    bounds[:2],
                    bounds[2] - bounds[0],
                    bounds[3] - bounds[1],
                    edgecolor=colour,
                    facecolor="none",
                    lw=0.5,
                )
            )
    plt.show()
