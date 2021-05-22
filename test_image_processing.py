from bs4 import BeautifulSoup
import numpy as np
from PIL import ImageOps
from gallica_autobib.gallipy import Resource
from gallica_autobib.process import extract_image
from PyPDF4 import PdfFileReader
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Rectangle
from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])
Box = namedtuple("Box", ["upper", "lower"])

ark = "https://gallica.bnf.fr/ark:/12148/bpt6k65545564"
r = Resource(ark)


def fetch_stuff(pno):
    pg = r.content_sync(startview=pno, nviews=1, mode="pdf").value
    reader = PdfFileReader(BytesIO(pg))
    data, type_ = extract_image(reader.getPage(2))
    ocr = r.ocr_data_sync(view=pno).value
    soup = BeautifulSoup(ocr.decode())
    upper_bound = [0, 0]
    lower_bound = [0, 0]
    page = soup.find("page")
    height, width = int(page.get("height")), int(page.get("width"))
    xscale = data.height / height
    yscale = data.width / width
    height *= yscale
    printspace = soup.find("printspace")
    text_height = round(int(printspace.get("height")) * yscale)
    text_width = round(int(printspace.get("width")) * xscale)
    vpos = int(printspace.get("vpos")) * yscale
    hpos = int(printspace.get("hpos")) * xscale
    upper = Point(round(hpos), round(vpos))
    return upper, text_height, text_width, data, height


def gen_doc_data():
    pno = 128
    upper, text_height, text_width, data, height = fetch_stuff(pno)
    fig, ax = plt.subplots()
    plt.imshow(data)

    text_box = ax.add_patch(
        Rectangle(
            upper, text_width, text_height, edgecolor="red", facecolor="none", lw=2
        )
    )
    fig.savefig(
        "docs/img/content_box.svg", bbox_inches="tight", transparent=True, dpi=72
    )

    ax2 = ax.twiny()
    a = np.array(ImageOps.grayscale(data))
    mean = a.mean(axis=1)
    ax2.plot(mean, range(len(mean)), label="mean")

    gradient = np.gradient(mean) + 70
    ax2.plot(gradient, range(len(gradient)), color="green", label="differential")
    plt.legend()
    fig.savefig("docs/img/mean.svg", bbox_inches="tight", transparent=True, dpi=72)
    gstd = np.std(gradient)
    gmean = gradient.mean()
    ax2.vlines([gmean - 1.5 * gstd, gmean + 1.5 * gstd], 0, data.height, color="orange")
    fig.savefig(
        "docs/img/mean_bounds.svg", bbox_inches="tight", transparent=True, dpi=72
    )

    search = round(height * 0.05)
    upper_bound = upper.y - search
    search_height = text_height + 2 * search
    search_upper = Point(upper.x, upper_bound)
    search_box = ax.add_patch(
        Rectangle(
            search_upper,
            text_width,
            search_height,
            edgecolor="green",
            facecolor="none",
            lw=1,
        )
    )
    fig.savefig("docs/img/search.svg", bbox_inches="tight", transparent=True, dpi=72)

    upper_search = gradient[upper_bound : upper.y]
    lower_search = gradient[upper.y + text_height : upper_bound + search_height]
    lower_thresh = gmean - 1.5 * gstd
    upper_thresh = gmean + 1.5 * gstd
    peaked = 0
    for up, x in enumerate(reversed(upper_search)):
        if not peaked and x >= upper_thresh:
            peaked = 1
        if peaked and x <= lower_thresh:
            peaked = 2
            print("Line above detected.")
            break

    up = up if peaked == 2 else 0
    peaked = 0
    for down, x in enumerate(lower_search):
        if not peaked and x <= lower_thresh:
            peaked = 1
        if peaked and x >= upper_thresh:
            peaked = 2
            print("Line below detected.")
            break
    down = down if peaked == 2 else 0

    final_upper = Point(upper.x, upper.y - up)
    final_height = text_height + up + down

    search_box = ax.add_patch(
        Rectangle(
            final_upper,
            text_width,
            final_height,
            edgecolor="pink",
            facecolor="none",
            lw=1,
        )
    )
    fig.savefig("docs/img/searched.svg", bbox_inches="tight", transparent=True, dpi=72)

    stretch = round(height * 0.005)
    streched_upper = Point(final_upper[0] - stretch, final_upper[1] - 2 * stretch)
    stretched_width = text_width + 2 * stretch
    stretched_height = final_height + 4 * stretch
    fig, ax = plt.subplots()
    plt.imshow(data)

    final_box = ax.add_patch(
        Rectangle(
            streched_upper,
            stretched_width,
            stretched_height,
            edgecolor="black",
            facecolor="none",
            lw=1,
        )
    )
    fig.savefig("docs/img/stretched.svg", bbox_inches="tight", transparent=True, dpi=72)


def process_page(pno):
    upper, text_height, text_width, data, height = fetch_stuff(pno)
    fig, ax = plt.subplots()
    plt.imshow(data)

    text_box = ax.add_patch(
        Rectangle(
            upper, text_width, text_height, edgecolor="red", facecolor="none", lw=2
        )
    )
    ax2 = ax.twiny()
    a = np.array(ImageOps.grayscale(data))
    mean = a.mean(axis=1)

    gradient = np.gradient(mean) + 70
    ax2.plot(gradient, range(len(gradient)), color="green", label="differential")
    gstd = np.std(gradient)
    gmean = gradient.mean()
    ax2.vlines([gmean - 1.5 * gstd, gmean + 1.5 * gstd], 0, data.height, color="orange")

    search = round(height * 0.05)
    upper_bound = upper.y - search
    search_height = text_height + 2 * search
    search_upper = Point(upper.x, upper_bound)
    search_box = ax.add_patch(
        Rectangle(
            search_upper,
            text_width,
            search_height,
            edgecolor="green",
            facecolor="none",
            lw=1,
        )
    )

    upper_search = gradient[upper_bound : upper.y]
    lower_search = gradient[upper.y + text_height : upper_bound + search_height]
    lower_thresh = gmean - 1.5 * gstd
    upper_thresh = gmean + 1.5 * gstd
    peaked = 0
    for up, x in enumerate(reversed(upper_search)):
        if not peaked and x >= upper_thresh:
            peaked = 1
        if peaked and x <= lower_thresh:
            peaked = 2
            print("Line above detected.")
            break

    up = up if peaked == 2 else 0
    peaked = 0
    for down, x in enumerate(lower_search):
        if not peaked and x <= lower_thresh:
            peaked = 1
        if peaked and x >= upper_thresh:
            peaked = 2
            print("Line below detected.")
            break
    down = down if peaked == 2 else 0

    final_upper = Point(upper.x, upper.y - up)
    final_height = text_height + up + down

    search_box = ax.add_patch(
        Rectangle(
            final_upper,
            text_width,
            final_height,
            edgecolor="pink",
            facecolor="none",
            lw=1,
        )
    )

    stretch = round(height * 0.005)
    streched_upper = Point(final_upper[0] - stretch, final_upper[1] - 2 * stretch)
    stretched_width = text_width + 2 * stretch
    stretched_height = final_height + 4 * stretch

    final_box = ax.add_patch(
        Rectangle(
            streched_upper,
            stretched_width,
            stretched_height,
            edgecolor="black",
            facecolor="none",
            lw=1,
        )
    )


gen_doc_data()
# process_page(128)
# process_page(136)
# process_page(79)
# process_page(136)
