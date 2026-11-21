# Cooldown and test period

Fixed on 21 November 2026, before looking at any stock returns.

This note applies to both cluster rules (v1 in cluster_rule.md and v2 in
cluster_rule_v2.md). It does not change who counts as a cluster. It says how
repeat signals are handled and which years are tested.

## Cooldown

After a company produces a signal, new signals at the same company are ignored for
90 days. Without this, the same company could fire again a few days after its last
signal and be counted as a new, independent event.

The number 90 is a judgment, not taken from a source. Other values will be tested
and reported (for example 30 and 180).

Why it matters: the same companies show up with the same one-day pattern in
different quarters (for example SPG and BLND appear in both 2025 Q1 and 2026 Q3).
The reason has not been checked.

## Test period

Backtest signals: those with a signal date from 1 January 2022 to 31 December 2025
(16 quarters of SEC data, 2022 Q1 to 2025 Q4).

Signals from 2026 are not used in the backtest. They are too recent to have enough
future prices. They are for the live scanner only.

Reasons: companies that were later delisted are more often missing from Yahoo for
older years, so going further back adds survivorship bias. Earlier years can be
added later as a check on whether the result holds, and will be reported as such.

The forward-return horizons (for example 1, 3 and 12 months), the benchmark, the
holdout year and the cost assumption are not decided yet. They will be written in
a separate dated note before any return is calculated.

This note is not changed after seeing returns. Any later change gets a new dated
note, and all results are reported.
