# Decision rule: what counts as evidence

Fixed on 22 November 2026, before any stock return has been calculated.

Applies to the design in backtest_design.md.

## What counts as evidence of an edge

All of the following must hold, using the v1 signals and the 3-month primary horizon,
with stocks that stop trading valued at their last available price and the 1% round-trip
cost taken off:

1. Main test (signals dated 2022 to 2024): the median excess return is above zero
   against both SPY and IWM.
2. The same holds when only the first signal per company is used.
3. The same holds in the held-out 2025 signals, which are looked at once, at the end,
   whatever the main test showed.

## What counts as mixed

If some of the three conditions hold and others do not, the result is reported as mixed.
No edge is claimed.

## What does not count

- A positive mean without a positive median.
- A result that appears only at the 1-month or 12-month horizon.
- A result that appears only before costs.
- A result in one group picked after looking, such as one rule version or one year.

## Always shown alongside the headline

- The results with stocks that stopped trading dropped, and counted as a 100% loss. If the
  sign of the median flips under either treatment, that is stated next to the headline.
- v2 and the one-trade-date group, as comparisons.
- The share of signals with no price for the whole horizon.

## Limits of any conclusion

Even if all three conditions hold, this does not show the signal can be traded for a
profit. Small companies can be hard to buy and sell at the assumed cost, and companies
that disappeared from Yahoo before the data was collected are missing from the older
years.

This note is not changed after seeing returns. Any later change gets a new dated note,
and all results are reported.
