# pygallica-autobib

<p align="center">
    <em>Automatically match Bibliographies against bnf.gallica.fr!</em>
</p>

<p align="center">
<a href="https://github.com/2e0byo/pygallica-autobib/actions?query=workflow%3ATest" target="_blank">
    <img src="https://github.com/2e0byo/pygallica-autobib/workflows/Test/badge.svg" alt="Test">
</a>
<a href="https://github.com/2e0byo/pygallica-autobib/actions?query=workflow%3APublish" target="_blank">
    <img src="https://github.com/2e0byo/pygalln=dependabot" alt="Dependabot Enabled">
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


## Standalone Usage

```bash
gallica-autobib my-bibliography.bib pdfs # match my-bibliography and put files in ./pdfs
gallica-autobib --help
```

## As a library
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

Gallica-Autobib is capable of much more than this. For more information, see the
[homepage](2e0byo.github.io/pygallica-autobib).

