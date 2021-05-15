# pygallica-autobib

<p align="center">
    <em>Automatically match Bibliographies against bnf.gallica.fr!</em>
</p>

<p align="center">
<a href="https://github.com/2e0byo/pygallica-autobib/actions?query=workflow%3ATest" target="_blank">
    <img src="https://github.com/2e0byo/pygallica-autobib/workflows/Test/badge.svg" alt="Test">
</a>
<a href="https://github.com/2e0byo/pygallica-autobib/actions?query=workflow%3APublish" target="_blank">
    <img src="https://github.com/2e0byo/pygallica-autobib/workflows/Publish/badge.svg" alt="Publish">
</a>
<a href="https://dependabot.com/" target="_blank">
    <img src="https://flat.badgen.net/dependabot/2e0byo/pygallica-autobib?icon=dependabot" alt="Dependabot Enabled">
</a>
<a href="https://codecov.io/gh/2e0byo/pygallica-autobib" target="_blank">
    <img src="https://img.shields.io/codecov/c/github/2e0byo/pygallica-autobib?color=%2334D058" alt="Coverage">
</a>
<a href="https://pypi.org/project/gallica-autobib" target="_blank">
    <img src="https://img.shields.io/pypi/v/gallica-autobib?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/gallica-autobib/" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/gallica-autobib.svg" alt="Python Versions">
</a>
</p>

## Overview

`pygallica-autobib` will match your bibliographies against the French National
Library and download articles as pdfs if possible, optionally post-processing
them.  Whilst it obviously cannot download articles which Gallica does not hold,
it strives to achieve a 100% match rate. If you find an article it does not
match, please [report a bug](https://github.com/2e0byo/pygallica-autobib/issues).

Features:

- Input in RIS or Bibtex format
- Output report generated with a jinja template (templates for org-mode, html
  and plaintext supplied)


## Online Demo

There is an [online demo](https://phd.2e0byo.co.uk/gallica) with a very basic
interface, allowing

## Installation

You need python >= 3.9 (but if anyone needs to use this with an older python,
open an issue and I will refactor the few incompatible statements).  Then
install as usual:

```bash
pipx install gallica-autobib # prefered, if you have pipx, or
python -m pip install gallica-autobib
```

## Standalone Usage

```bash
gallica-autobib my-bibliography.bib pdfs # match my-bibliography and put files in ./pdfs
gallica-autobib --help
```

## As a library
```python

from pathlib import Path
from gallica_autobib.models import Article
from gallica_autobib.query import Query, GallicaResource

target = Article(
    journaltitle="La Vie spirituelle",
    author="M.-D. Chenu",
    pages=list(range(547, 552)),
    volume=7,
    year=1923,
    title="Ascèse et péché originel",
)
query = Query(target)
candidate = Query.run().candidate # get candidate journal
gallica_resource = GallicaResource(candidate, source)
ark = gallica_resource.ark # match candidate article
gallica_resource.download_pdf(Path("article.pdf"))
```

or if you just want to do what the cli does:

```python
from pathlib import Path
from gallica_resource.pipeline import BibtexParser

parser = BibtexParser(Path("outdir"))

with Path("articles.bib").open() as f:
    parser.read(f)

parser.run()
for result in parser.results:
    print(result)
```

for more advanced usage see the documentation and the test suite.


## Developing

```bash

# ensure you have Poetry installed
pip install --user poetry

# install all dependencies (including dev)
poetry install
```

When your feature is ready, open a PR.

## Testing
We use pytest and mypy.  You may want to focus on getting unit tests passing
first:

```bash
poetry run pytest --cov=gallica_autobib --cov-report html --cov-branch tests
```

If you have started a shell with `poetry shell` you can drop the `poetry run`.

When unittests are passing you can run the whole suite with:

```bash
poetry run scripts/test.sh
```

Note that tests will only pass fully if `/tmp/` exists and is writeable, and if
`poppler` and `imagemagick` are installed.  This is due to the use of
`pdf-diff-visually` and the rather hackish template tests.
 
You may wish to check your formatting first with

```bash
poetry run scripts/format.sh
```

Alternatively, just open a premature PR to run the tests in CI.  Note that this
is rather slow.

## Plausibly Askable Questions

### Why don't you also check xyz.com?
Because I don't know about it.  Open an issue and I'll look into it.

### Why don't you use library xyz for image processing?
Probably because I don't know about it.  This is a quick tool written to help me
research.  Submit a PR and I'll happily update it.

### Why is the code so verbose?
It is rather object-oriented.  It might be rather over engineered. It was
written in a hurry and the design evolved as it went along.  On the other hand,
it should be easier to extend.

### Why not just extend pygallica?
I mean to submit the SRU stuff as an extension to `pygallica`

