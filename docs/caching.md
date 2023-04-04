# Caching

## Ratelimiting

Gallica appears to defend its resources quite aggressively.

- too many requests for *any* endpoint will result in a _resource temporarily
  unavailable_ error.
- too many requests for a *document* will result either in a timeout, or in the
  document being replaced with a png (sic!) containing the text (in French)
  'resource unavailable; please try again later'.  Presumably this is designed
  to catch out scripts trying to mirror the service, since a browser will just
  display the image.
- service speed appears to be batched, i.e. the first n. queries are quite
  quick, the next n. slower, and so on.
  
We try to work around these issues with a proper downloader with exponential
backoff (replacing `gallipy`'s use of requests), a *long* (5 min!) pause if we
detect the png ratelimiting, and by caching as much as possible.  Gallica is a
wonderful service and it would be a pity to ddos it, although one would think a
catalogue api should be able to handle large numbers of parallel queries.

## File caching

If `--no-clean` is specified to the cli (or `clean` is set to `False`) the
original pdf will be left around. If a pdf of the desire name exists the
download will be skipped. If `skip_existing=True` is passed on the cli or set in
`process_args`, an existing processed pdf will cause processing to be skipped.
These measures speed up repeated queries *massively*.

## Match caching

Match caching is implemented with an sqlite database `~/.cache/gallica_autobib/`
which uses the `repr()` of the *target* as a key (alright, it uses a `SHA1` hash
of the target's `repr()`).  So *any* changes in the target (i.e. any changes in
the bibliography you supply for this entry) will result in a rematch.  This is
the simplest way to ensure reliability.

Enough data is cached to prevent the `GallicaResource()` object doing any
requests.  The entire `Match()` object is cached, as output templates can use it
directly.

Sometimes you may wish to update the cache: in this case running with
`--ignore-cache` will cause it to be overwritten.

## Response and Data caching

Finally, for testing, it is possible to cache nearly[^1] every single response from
gallica's servers.  This has the great advantage for testing that the entire
test suite runs a lot quicker.  On the other hand it's probably a *bad* idea for
most usecases, and is thus disabled by default.  At the time of writing the test
suite takes 31s with a warm match cache and 6 parallel workers (using
xdist). This drops only to 21s with both response and data caching.

Response caching is enabled if the `RESPONSE_CACHE` environment variable is set.
Data caching (pdfs) is enabled if the `DATA_CACHE` environment variable is set.
Once again these caches are *not* intended for use in production. In particular,
note that these caches currently have *no eviction strategy*.

Setting `--ignore-cache` overrides anything set in the environment.

[^1]: It would make no sense to cache the HEAD request which is used to see if a
      pdf download is possible.  Thus the testsuite will not run fully offline.
