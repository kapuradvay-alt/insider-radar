"""Insider cluster-buy radar: a small Streamlit page.

Run on your computer:   streamlit run app.py
It reads only small files committed to the repository (app_data/ and results/).
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Insider cluster-buy radar", layout="wide")

HERE = Path(__file__).parent
signals = pd.read_csv(HERE / "app_data" / "signals_latest.csv", parse_dates=["signal_date"])
meta = json.loads((HERE / "app_data" / "meta.json").read_text())

st.title("Insider cluster-buy radar")
st.error(
    "**Not investment advice.** In our own test of 2022-2025 (SEC Form 4 data), stocks that had "
    "these cluster buys did **not** beat the S&P 500 or a small-cap index over three months after "
    "costs. This page is a monitor with its evidence attached, not a list of recommendations."
)

tab1, tab2, tab3 = st.tabs(["Recent cluster buys", "What the backtest found", "Limits and method"])

# ---------------------------------------------------------------- tab 1
with tab1:
    st.subheader("Recent cluster buys")
    st.caption(
        f"Based on SEC Form 4 filings from {meta['filings_from']} to {meta['filings_to']} "
        f"(data: {meta['source']}; built {meta['built_on']}). The list is rebuilt by hand, not "
        "automatically, so filings after the last date above are not included."
    )
    st.write(
        "A **cluster** is at least 3 different officers or directors of the same company each buying "
        "at least $10,000 of its stock in the open market, with all filings inside 14 days. "
        "The signal date is the day the cluster became public (the filing date)."
    )
    c1, c2 = st.columns(2)
    min_ins = c1.slider("Minimum number of insiders", 3, int(signals["insiders"].max()), 3)
    multi = c2.checkbox("Only clusters whose purchases happened on 2 or more different days", value=False)
    view = signals[signals["insiders"] >= min_ins]
    if multi:
        view = view[view["trade_dates"] >= 2]
    st.write(f"**{len(view)}** of {len(signals)} clusters shown.")
    view = view.assign(price_spread=view["price_spread"] - 1)       # 1.021 -> 0.021, shown as 2.1%
    shown = view.rename(columns={
        "ticker": "Ticker", "company": "Company", "signal_date": "Signal date",
        "insiders": "Insiders", "trade_dates": "Trade days", "price_spread": "Price gap",
        "total_value": "Total bought ($)", "edgar_link": "SEC filings"})
    # Styler shows $ and thousands commas but keeps the column numeric, so sorting still works
    styled = shown.style.format({
        "Signal date": "{:%Y-%m-%d}",
        "Total bought ($)": "${:,.0f}",
        "Price gap": "{:.1%}",
    })
    st.dataframe(
        styled,
        hide_index=True,
        column_config={"SEC filings": st.column_config.LinkColumn(display_text="open")},
    )
    with st.expander("How to read the columns"):
        st.write(
            "- **Trade days:** on how many different days the purchases in the cluster happened. "
            "In our test, clusters where everyone bought on a single day did worse than clusters "
            "spread over several days. This is an exploratory finding, not a tested claim.\n"
            "- **Price gap:** how much higher the highest purchase price in the cluster was than the "
            "lowest. 0.0% means everyone paid the same price.\n"
            "- **Total bought:** very large totals, or a large price gap, can come from share "
            "offerings or private placements and not ordinary market buying. We have not checked "
            "individual cases.\n"
            "- **SEC filings:** opens the company's Form 4 list on sec.gov so you can check the "
            "original filings yourself."
        )

# ---------------------------------------------------------------- tab 2
with tab2:
    st.subheader("What the backtest found")
    st.write(
        "Every signal was tested the same way: buy at the close of the first trading day after the "
        "filing, sell 63 trading days (about 3 months) later, and compare with the S&P 500 (SPY) and a "
        "small-cap index (IWM) over the same dates. Returns include a 1% round-trip trading cost, which is "
        "a placeholder assumption. The rules and the definition of success were written down before the "
        "returns were calculated."
    )
    table = pd.DataFrame(
        [["Main test (signals in 2022-2024)", 965, "-2.5%", "-1.2%", "44% / 47%"],
         ["Held-out (signals in 2025, looked at once)", 393, "-4.3%", "-5.2%", "42% / 39%"]],
        columns=["Period", "Signals", "Median excess vs SPY", "Median excess vs IWM", "Beat SPY / IWM"],
    )
    st.dataframe(table, hide_index=True)
    st.write(
        "**Excess return** is the stock's return minus the benchmark's over the same dates. The **median** "
        "is the typical signal. A negative number means the typical signal lagged the benchmark."
    )
    st.info(
        "**Verdict under our pre-set rule: no evidence of an edge.** The main test, the one-signal-per-company "
        "check and the held-out year all had negative medians against both benchmarks. Nine variations of the "
        "rule gave the same answer, though they share most of their signals, so they are not nine independent "
        "confirmations."
    )
    st.write(
        "**Averages look better than medians.** Before costs, the average excess return in the main test is "
        "positive (+1.8% vs SPY, +3.1% vs IWM) because a few big winners pull it up, while the typical signal "
        "lags. Our rule does not count a positive average without a positive median."
    )
    st.write(
        "**How certain is it?** In the main test, the 95% range for the median excess return was -5.6% to +0.1% "
        "vs SPY and -4.1% to +1.0% vs IWM. Against small caps the result cannot be told apart from zero."
    )
    with st.expander("Full result files"):
        for f in ["backtest_main_2026-11-22.txt", "backtest_holdout_2026-11-22.txt",
                  "uncertainty_main_2026-11-22.txt", "sensitivity_main_2026-11-22.txt"]:
            p = HERE / "results" / f
            if p.exists():
                st.markdown(f"**{f}**")
                st.code(p.read_text(), language=None)

# ---------------------------------------------------------------- tab 3
with tab3:
    st.subheader("Limits")
    st.write(
        "- **Survivorship bias.** Yahoo had prices for 66% of tickers in 2022 Q1 and 93% in 2025 Q4. Companies "
        "that later disappeared (delisting, bankruptcy, takeover, ticker change) are missing from older years, "
        "which probably flatters the results. That direction is reasoning, not something we measured.\n"
        "- **Costs** are a flat 1% placeholder. Small companies can cost more to trade.\n"
        "- **Signals are not independent.** Some companies appear many times, and signals bunch in time, so "
        "statistics that treat them as independent overstate confidence.\n"
        "- **Ticker reuse** (a ticker later used by a different company) was not checked.\n"
        "- **Scope.** The result applies to this signal definition, this period and these data only. It says "
        "nothing about insider buying in general or about other markets.\n"
        "- **Not automatic.** The list is rebuilt when the project owner runs the update. It is current "
        "only up to the 'filings to' date shown on the first tab. Recent filings use the SEC's daily "
        "filing lists; older ones use the SEC's quarterly files (checked against each other on three days: "
        "identical). Two filings (out of about 17,000) could not be downloaded from the SEC."
    )
    st.subheader("Method")
    st.write(
        "Data: SEC Insider Transactions Data Sets (Form 4), open-market purchases (code P) by officers and "
        "directors, 2022 Q1 to 2025 Q4. 108,542 purchases were reduced to 62,170 after cleaning (ticker, price "
        "and shares, filing within 0 to 10 days of the trade, original filings only, and a price within 0.5x "
        "to 2x of Yahoo's closing price that day). The full method, rules and code are in the project "
        "repository on GitHub (kapuradvay-alt/insider-radar)."
    )

st.caption("Student research project, built with help from Claude (Anthropic).")
