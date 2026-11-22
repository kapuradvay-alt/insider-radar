# Backtest design

Fixed on 21 November 2026, before any stock return has been calculated.

Applies to the cluster rules in cluster_rule.md (v1) and cluster_rule_v2.md (v2),
with the cooldown and test period in cooldown_and_period.md.

## Signals tested

- Main test: v1 signals with a signal date from 1 Jan 2022 to 31 Dec 2024.
- Held-out test: signals dated in 2025. Nobody looks at 2025 returns until everything
  else in this note is fixed and the 2022-2024 work is finished. 2025 is then looked at
  once, and the result is reported whatever it shows.
- Also reported: v2 signals, and the one-trade-date signals on their own as a
  comparison group.
- Also reported: the same results using only the first signal per company, because
  repeat signals at the same company are not independent observations.

## Entry and exit

- Entry: the close of the first trading day after the signal date. The signal date is
  the filing date, and nobody could act on it earlier.
- Primary horizon: 3 months, the close 63 trading days after the entry day.
- Secondary horizons, reported but not used for the conclusion: 1 month (21 trading
  days) and 12 months (252 trading days). The 12-month figure is not available for
  late signals yet.
- Returns use split- and dividend-adjusted prices (Yahoo "Adj Close"), not the raw
  closes used in the cleaning step, because splits distort raw closes.

## Benchmarks

- S&P 500 (SPY) and a small-cap index (IWM), over exactly the same dates as each trade.
- Excess return = the stock's return minus the benchmark's return over the same dates.

## What is reported

- Number of signals, and how many have prices for the whole horizon.
- Mean and median return and excess return, and the share of signals that beat each
  benchmark. Median is shown because returns are skewed.
- Results after costs: 1% round trip as the main assumption, with 0.5% and 2% as
  sensitivity. The 1% is a placeholder assumption, not a sourced figure.
- Sensitivity tests, whatever the result: 2 or 4 insiders, 7 or 30 days, other minimum
  amounts, and cooldowns of 30 and 180 days.

## Stocks that stop trading

Some stocks will stop having prices inside the horizon (delisting, takeover, bankruptcy,
ticker change). They will be counted and reported, and results shown three ways:
1. those signals dropped,
2. the last available price used as the exit,
3. those signals counted as a loss of 100%.

Companies that disappeared from Yahoo before the data was collected are missing from
the older quarters altogether. Yahoo had prices for 66% of tickers in 2022 Q1 and 93%
in 2025 Q4. This likely makes older results look better than a real investor's
experience. It will be stated as a limit.

## Not covered

No claim is made that this works as a trading strategy. Small companies can be hard to
trade, and the data has the limits listed above.

This note is not changed after seeing returns. Any later change gets a new dated
note, and all results are reported.
