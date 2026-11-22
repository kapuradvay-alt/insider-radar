# insider-radar

**Question:** when several officers or directors of a US-listed company buy its shares in the open market within a short time, does the stock beat the market over the next three months?

**Answer from this test: no.** Using SEC Form 4 data for 2022 to 2025, these "cluster buys" did not beat the S&P 500 (SPY) or a small-cap index (IWM) after a 1% trading cost, in the main test or in a held-out year. See the limits below before reading anything into that.

This is a student research project, not investment advice.

## Results

Signal = at least 3 different officers or directors each buying at least $10,000 within 14 days (full rules in [`docs/cluster_rule.md`](docs/cluster_rule.md)). Entry is the close of the first trading day after the filing. Exit is 63 trading days later. Returns are split- and dividend-adjusted. Stocks that stop trading are valued at their last price.

| Period | Signals | Median excess vs SPY | Median excess vs IWM | Beat SPY / IWM |
|---|---|---|---|---|
| Main test (signals in 2022-2024) | 965 | -2.5% | -1.2% | 44% / 47% |
| Held-out (signals in 2025, looked at once) | 393 | -4.3% | -5.2% | 42% / 39% |

All figures are after a 1% round-trip cost, which is a placeholder assumption, not a measured number. The medians are also negative before costs (main: -1.5% vs SPY and -0.2% vs IWM; held-out: -3.3% and -4.2%).

- **Averages look better than medians.** Before costs, the mean excess return in the main test is +1.8% vs SPY and +3.1% vs IWM, but a few big winners (the best signal returned +689% in three months) pull the mean up while the typical signal lags. The success rule written beforehand does not count a positive mean without a positive median.
- **Uncertainty (main test).** 95% ranges for the median excess return, resampling months: -5.6% to +0.1% vs SPY and -4.1% to +1.0% vs IWM ([`results/uncertainty_main_2026-11-22.txt`](results/uncertainty_main_2026-11-22.txt)). Against small caps, the result cannot be told apart from zero.
- **Nine rule variants** (2 or 4 insiders, 7 or 30 days, no minimum or $50,000, cooldown of 30 or 180 days) all gave negative medians against both benchmarks ([`results/sensitivity_main_2026-11-22.txt`](results/sensitivity_main_2026-11-22.txt)). They share most of their signals, so they are not nine independent confirmations.
- **Exploratory, not a tested claim:** clusters where every purchase happened on a single trade date did worse than clusters spread over several dates, in both periods (median excess vs SPY before cost: -2.9% vs -1.1% in the main test, -5.4% vs -2.7% in 2025). One-day clusters may include offerings or plan purchases. This was not checked.

All result files are in [`results/`](results/).

## How it was tested

1. **Data:** SEC [Insider Transactions Data Sets](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets), 16 quarters (2022 Q1 to 2025 Q4). Only open-market purchases (transaction code P) by officers and directors.
2. **Cleaning** ([`src/clean.py`](src/clean.py)). Purchases left after each step, summed over the 16 quarters:

   | Step | Rows left |
   |---|---|
   | Purchases (code P, one row per trade) | 108,542 |
   | Has a real ticker | 104,690 |
   | Has price and shares above 0 | 103,907 |
   | Filed 0 to 10 days after the trade | 92,516 |
   | Original Form 4 only (no amendments) | 91,420 |
   | Trade price within 0.5x to 2x of Yahoo's close that day | 62,170 |

   (The "0 to 10 days" step was "up to 10 days" in the first run. The 0 lower bound was added later and the data was rebuilt with it.)
3. **Signals** ([`src/clusters.py`](src/clusters.py), [`src/make_signals.py`](src/make_signals.py)): the rule above, with a 90-day cooldown per company ([`docs/cooldown_and_period.md`](docs/cooldown_and_period.md)). 1,359 signals (966 before 2025, 393 in 2025). A second version requiring purchases on 2 or more trade dates is in [`docs/cluster_rule_v2.md`](docs/cluster_rule_v2.md).
4. **Backtest** ([`src/backtest.py`](src/backtest.py)): design in [`docs/backtest_design.md`](docs/backtest_design.md), success rule in [`docs/decision_rule.md`](docs/decision_rule.md), sensitivity grid in [`docs/sensitivity_tests.md`](docs/sensitivity_tests.md). The rules were written down before the returns were calculated. The 2025 signals were locked behind a flag until the end.

### A note on the order of commits

The decision rule and the sensitivity grid were committed to this repository before the results they govern. The backtest design note was written on 21 November 2026, before any return was calculated (the file's modification time shows this), but it was only committed afterwards, together with the held-out result, so the git history alone does not prove its timing. The sensitivity note was written after the main-test result was known, and says so.

## Limits

- **Survivorship bias.** Yahoo had prices for 66% of the tickers in 2022 Q1 and 93% in 2025 Q4. Companies that later disappeared (delisting, bankruptcy, takeover, ticker change) are missing from the older years. No signal in the final list stopped trading inside its horizon, because those companies never made it in. This probably flatters the results, since failures are missing. The direction is my reasoning, not something I measured, and takeovers at a premium are missing too.
- **Ticker reuse** (a ticker later used by a different company) was not checked.
- **Costs** are a flat 1% placeholder. Small companies can cost more to trade.
- **Code P may include private purchases**, not only open-market ones. Not checked.
- **Signals are not independent.** Several companies produce many signals over time, and signals bunch in time. Statistics that treat them as independent overstate the confidence. The month-resampled ranges are the honest ones.
- **Yahoo data** comes from an unofficial wrapper (yfinance), and the Yahoo coverage gap above affects the data. The price-validation step discards trades far from Yahoo's close, so foreign listings and currency mismatches are dropped (a hypothesis, not checked).
- **Scope.** The result applies to this signal definition, this period and these data only. It says nothing about insider buying in general, about other markets, or about insiders who have private information.

## Reproduce it

Python with pandas, numpy, yfinance and requests, run from the project folder (data is not committed):

```
python src/get_quarters.py you@example.com 2022 2025        # SEC download and cleaning; the SEC asks for a contact email
python src/make_signals.py data/people_2022_2025.csv
python src/get_price_history.py data/signals_2022_2025.csv
python src/backtest.py                                       # main test; 2025 stays locked
python src/uncertainty.py
python src/sensitivity.py make
python src/get_price_history.py data/signals_sensitivity.csv --add
python src/sensitivity.py run
```

Yahoo data changes over time, so a rerun may not match exactly.

Built by a finance student with help from Claude (Anthropic).
