# Cluster rule v2

Fixed on 21 November 2026, before looking at any stock returns.

v2 is v1 (see cluster_rule.md) plus one extra requirement. v1 stays the main rule
and is not replaced. Both versions are tested and both results are reported.

## What is added

The purchases that make up the cluster must fall on at least 2 different trade
dates (the date the insider actually bought, not the filing date).

Everything else is the same as v1: at least 3 different officers or directors,
each with at least $10,000 filed on the same day, all filings within 14 days,
open-market purchases (code P) that pass src/clean.py, signal date = filing date
of the purchase that completes the cluster.

## Why

In the 2026 Q3 data, 40 of the 99 v1 clusters have every purchase on a single
trade date, and 33 of those are also within 2% in price (src/cluster_check.py).
That pattern is consistent with an offering, a private placement or a plan
purchase, where the buyers are not making independent decisions. It is also
consistent with several insiders buying on the first day a trading window opens,
which can be real conviction. The data cannot tell these apart, so v2 is a test of
the concern, not a claim that one-day clusters are bad.

On 2026 Q3, v2 leaves 59 of the 99 clusters.

The reason for v2 is the independence of the buying decisions. It was chosen from
the cluster counts and trade dates only, before any returns were looked at.

## Reporting

Both v1 and v2 are reported in the final results, whichever looks better. One-day
clusters are also reported on their own as a comparison group.

This rule is not changed after seeing returns. Any later change gets a new dated
version, and all results are reported.
