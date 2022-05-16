# Matching

## Gallica's APIs

Gallica has excellent API support. In fact, it has far too *much* API support:
there seem to be several ways to get most information from it. The apis are
documented extensively [online](https://api.bnf.fr/). What is more impressive is
the list of available
[bindings](https://api.bnf.fr/fr/wrapper-python-pour-les-api-gallica). Of these
bindings we use [gallipy](https://github.com/GeoHistoricalData/gallipy) simply
because it seemed the easiest to get going. Gallipy has no search capabilities,
so we handle the search directly at the SRU endpoint with
[sruthi](https://github.com/metaodi/sruthi).

(Incidentally, the reason Gallica has such good API access is that one thing the
French Government gets *right* is API access. See
https://api.gouv.fr/rechercher-api for an idea of quite how much data is
available.)

## Search Algorithm

Gallica Autobib was originally written to handle the specific case of fetching
journal articles.  As far as I can tell the BNF only indexes physical holdings,
i.e. you can ask it what journals it has, but not what articles they contain.
Sometimes those holdings have TOCs, but the TOCs are extracted from the holding
itself (possibly with manual intervention) and are thus not necessarily
massively useful, as well as not being ubiquitous.

### Article Search Algorithm

Currently this is the only algorithm implemented, although the other record
types will be added later.

We break the problem into several steps:

1. find the right journal.  Gallica has very reliable metadata, and we can trust
   it not to list the same journal under two different ids.
2. find the right issue of this journal, i.e. the issue containing the article
   we want.
   
Frequently step 1. succeeds and step 2. fails because Gallica doesn't hold the
issue we want (particularly with the war years).  Theoretically we should detect
this condition properly and report on it, but for now we just fail.

Finding the right issue is trickier, because we can't trust the year properly.
Years can be off in general and journals are frequently collected into volumes,
which for some reason seem to be offset by half a year. So for a journal in 1936
there are _three_ years to search: 1935, in case the original number was
published in 1936 but part of a volume starting in 1935, 1936, and 1937 (in case
the converse of the first case holds).  So we get the TOC of all three journals,
and parse it.  Unfortunately now we discover that Gallica's API excellence is
only skin-deep: the TOC is only available in an XML more akin to HTML than a
machine-friendly index to a document.  So it has to be scraped, and then we look
to see whether or not there is an article with the right title beginning on the
right page: if so, the issue is a match.

If this fails (perhaps because there is no TOC) we try fetching the page the
article *ought* to be on, and doing a fuzzy search for the title. (Fortunately
Gallica provides a pagination api to convert page numbers into views.
Unfortunately it returns unstructured html, with the conversion as a bunch of
cells in a list, so we iterate over them. We don't do this often enough for it
to be worth building a mapping.) If this matches we try a fuzzy search for the
author on the first page of the article, and the last if that fails. These
matches are scored as the levenshtein distance (ratio) of the longest matching
fuzzy string against the target, so matching 'de la' will not cause a false
positive. On the other hand for authors with short names you really do need to
supply them the way they sign themselves, since there's no automagic way to work
out an abbreviation (at any rate, no _easy_ way to do it which wouldn't trigger
false positives without a much cleverer heuristic than Levenshtein distance).
For long/obscure names this shouldn't be a problem. As an example,
*Marie-Dominique Chenu* failed for *M.-D. Chenu*, but *Réginald
Garrigou-Lagrange* matched *R. Garrigou-Lagrange O. P.* without any difficulty.
(Can you tell I'm a theologian?)

This text matching uses the ocr text endpoint.  Unfortunately, this returns the
unformatted plaintext *wrapped in an html document*.  The server crashes[^1] if you
requests `text/plain` or `application/xml`, but if you ask for
`application/json` it serves up the same html page in a json object (without
decomposing it at all).  So out comes [Beautiful
Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) again, and we can
get the text back out of the html.  This is not quite [using a regex to parse
html](https://stackoverflow.com/questions/1732348/regex-match-open-tags-except-xhtml-self-contained-tags/1732454#1732454),
though actually the source is simple enough we could probably do that.  Let's
not, though.

### Matching other resources

Is rather easier, since we basically just use the journal matching algorithm
above.  All the pieces are in place to do this, but it has not yet been tested,
as I have not yet wanted to fetch a book or journal which Gallica holds.

## Match() objects

We could have just put this algorithm in a function somewhere.  But tuning
heuristics when everything's in a function gets difficult, so we use `Match()`
objects to keep track of the various different criteria.  Currently everything
gets equal weighting, but this will doubtless require tuning as time goes on.
We also set a minimum threshold below which to fail.

[^1]: Note, crashes, and gives a very unhelpful error message.
