# Sensitivity tests

Fixed on 22 November 2026, before any sensitivity result was calculated.

Timing, stated plainly: this note was written after the main-test result for the base
rule was known (see results/backtest_main_2026-11-22.txt). The list of tests (2 or 4
insiders, 7 or 30 days, other minimum amounts, cooldowns of 30 and 180 days) was
already declared in cluster_rule.md and cooldown_and_period.md. The two minimum amounts
below ($0 and $50,000) were chosen when this note was written.

## The grid

Each variant changes one setting from the base rule and leaves the rest as in v1
(3 insiders, 14 days, $10,000 per insider, 90-day cooldown):

- 2 insiders, and 4 insiders
- 7-day window, and 30-day window
- no minimum amount, and a $50,000 minimum
- cooldown of 30 days, and of 180 days

Measured exactly as the headline result: signals dated before 2025, 3-month horizon,
stocks that stop trading valued at their last price, 1% round-trip cost, excess return
against SPY and IWM. The 2025 held-out set is not used.

## How the results will be read

- All 8 variants and the base are reported, whatever they show.
- With 8 variants, one or two crossing zero by chance would not be surprising. A single
  variant with a positive median is not a finding and does not change the conclusion.
- A variant counts as a possible edge only if its median excess return is above zero
  against both SPY and IWM, and the 95% range from resampling months sits entirely
  above zero for both. Any such variant would be labelled exploratory and would need
  to hold in the 2025 held-out set, which is looked at once.
- If no variant meets that, the conclusion from the base rule stands.

This note is not changed after seeing sensitivity results. Any later change gets a new
dated note, and all results are reported.
