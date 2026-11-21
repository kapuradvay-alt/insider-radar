# Cluster rule

Fixed on 21 November 2026, before looking at any stock returns.

A cluster is when, at one company:
- at least 3 different insiders bought
- each insider's purchases filed on the same day add up to at least $10,000
- all of those filings fall within 14 days of each other

Who counts: officers and directors only (the SEC relationship field contains
"Officer" or "Director"). Pure 10% owners are excluded.

Which trades count: open-market purchases (code P) that pass the cleaning rules
in src/clean.py.

Signal date: the filing date of the purchase that completes the cluster. That is
the first day the market could know about it.

Planned sensitivity tests, reported whatever the result: 2 or 4 insiders, 7 or 30
days, and other minimum amounts.

This rule is not changed after seeing returns. Any later change gets a new dated
version, and both results are reported.
