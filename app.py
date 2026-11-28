"""Insider cluster-buy radar: a small Streamlit page.

Run on your computer:   streamlit run app.py
It reads only small files committed to the repository (app_data/ and results/).
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Insider cluster-buy radar", page_icon="📡", layout="wide")

HERE = Path(__file__).parent
signals = pd.read_csv(HERE / "app_data" / "signals_latest.csv", parse_dates=["signal_date"])
meta = json.loads((HERE / "app_data" / "meta.json").read_text())

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; max-width: 1200px;}
    h1 {font-size: 2.2rem !important; letter-spacing: -0.5px; margin-bottom: 0;}
    .subtitle {color: #9FB0C8; margin: 0.2rem 0 1.1rem 0; font-size: 1.05rem;}
    [data-testid="stMetric"] {background: #131D33; border: 1px solid #22304D;
                              border-radius: 12px; padding: 14px 18px;}
    [data-testid="stMetricLabel"] {opacity: 0.75;}
    .stTabs [data-baseweb="tab"] {font-size: 1.02rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

filings_to = pd.Timestamp(meta["filings_to"])
built_on = pd.Timestamp(meta["built_on"])
today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
age_days = (today - filings_to).days

st.title("Insider cluster-buy radar")
st.markdown(
    '<div class="subtitle">When several company insiders buy their own stock within days of each other, '
    "does the stock do well afterwards? A monitor of recent cases, with our test of the idea attached.</div>",
    unsafe_allow_html=True,
)
st.warning(
    "**Not investment advice.** In our own test of 2022-2025 (SEC Form 4 data), stocks that had "
    "these cluster buys did **not** beat the S&P 500 or a small-cap index over three months after "
    "costs. This page is a monitor with its evidence attached, not a list of recommendations."
)
if age_days >= 5:
    st.error(
        f"This list may be out of date. The newest filing in it is from {filings_to:%d %b %Y}, "
        f"{age_days} days ago, so the daily update has probably failed."
    )

tab1, tab2, tab3 = st.tabs(["Recent cluster buys", "What the backtest found", "Limits and method"])

# ---------------------------------------------------------------- tab 1
with tab1:
    week = signals[signals["signal_date"] > filings_to - pd.Timedelta(days=7)]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Clusters in the list", f"{len(signals):,}")
    m2.metric("Newest filing included", f"{filings_to:%d %b %Y}")
    m3.metric("New in the last 7 days", f"{len(week):,}")
    m4.metric("List rebuilt", f"{built_on:%d %b %Y}")
    newest_signal = signals["signal_date"].max() if len(signals) else None
    if newest_signal is not None and newest_signal < filings_to:
        st.info(
            f"Filings are read up to **{filings_to:%d %b %Y}**. The newest cluster in the table below "
            f"completed on **{newest_signal:%d %b %Y}**; no new cluster has completed since. "
            "That is normal: the table is sorted by cluster date, not by how recently the app was updated, "
            "and the SEC takes no filings on US holidays."
        )
    st.caption(
        f"SEC Form 4 filings from {meta['filings_from']} to {meta['filings_to']}. "
        "A scheduled job rebuilds the list every weekday evening (US time). "
        "Insiders usually file within two business days of a trade, so the list lags the trades by a few days."
    )

    with st.expander("What counts as a cluster?"):
        st.write(
            "A **cluster** is at least 3 different officers or directors of the same company each buying "
            "at least $10,000 of its stock in the open market, with all filings inside 14 days. "
            "The signal date is the day the cluster became public (the filing date)."
        )

    f1, f2, f3 = st.columns([1.3, 1.7, 1.6])
    period = f1.selectbox("Period", ["Everything since 1 July", "Last 7 days", "Last 30 days"])
    top = int(signals["insiders"].max()) if len(signals) else 3
    min_ins = f2.slider("Minimum number of insiders", 3, top, 3) if top > 3 else 3
    query = f3.text_input("Search ticker or company", placeholder="e.g. COHR or Coherent")
    multi = st.checkbox("Only clusters whose purchases happened on 2 or more different days", value=False)

    view = signals[signals["insiders"] >= min_ins]
    if period == "Last 7 days":
        view = view[view["signal_date"] > filings_to - pd.Timedelta(days=7)]
    elif period == "Last 30 days":
        view = view[view["signal_date"] > filings_to - pd.Timedelta(days=30)]
    if multi:
        view = view[view["trade_dates"] >= 2]
    if query.strip():
        q = query.strip().lower()
        view = view[view["ticker"].astype(str).str.lower().str.contains(q, regex=False)
                    | view["company"].astype(str).str.lower().str.contains(q, regex=False)]
    st.write(f"**{len(view)}** of {len(signals)} clusters shown.")

    def note(row):
        parts = []
        if row["trade_dates"] == 1:
            parts.append("single trade day")
        if row["total_value"] >= 10_000_000:
            parts.append("total over $10M")
        return " · ".join(parts)

    view = view.assign(price_spread=view["price_spread"] - 1)       # 1.021 -> 0.021, shown as 2.1%
    view["note"] = view.apply(note, axis=1) if len(view) else ""
    shown = view.rename(columns={
        "ticker": "Ticker", "company": "Company", "signal_date": "Signal date",
        "insiders": "Insiders", "trade_dates": "Trade days", "price_spread": "Price gap",
        "total_value": "Total bought ($)", "note": "Note", "edgar_link": "SEC filings"})
    shown = shown[["Ticker", "Company", "Signal date", "Insiders", "Trade days", "Price gap",
                   "Total bought ($)", "Note", "SEC filings"]]
    # Styler shows $ and thousands commas but keeps the column numeric, so sorting still works
    styled = shown.style.format({
        "Signal date": "{:%Y-%m-%d}",
        "Total bought ($)": "${:,.0f}",
        "Price gap": "{:.1%}",
    })
    st.dataframe(
        styled,
        hide_index=True,
        height=min(620, 40 + 35 * max(len(shown), 1)),
        column_config={"SEC filings": st.column_config.LinkColumn(display_text="open")},
    )
    st.download_button(
        "Download this table (CSV)",
        data=shown.drop(columns=["SEC filings"]).to_csv(index=False).encode("utf-8"),
        file_name=f"insider_clusters_{meta['filings_to']}.csv",
        mime="text/csv",
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
            "- **Note:** only states facts visible in the table: all purchases on one trade day, or a "
            "total above $10 million. It is a prompt to look closer, not a judgement.\n"
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
    st.caption("Median excess return after a 1% trading cost, in percentage points. Below zero = the typical signal lagged the benchmark.")
    st.bar_chart(
        pd.DataFrame({"vs S&P 500 (SPY)": [-2.5, -4.3], "vs small caps (IWM)": [-1.2, -5.2]},
                     index=["Main test (2022-2024)", "Held-out (2025)"]),
    )
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
        "- **Updated by a scheduled job, not in real time.** A GitHub job rebuilds the list on weekday "
        "evenings (US time) from the SEC's daily filing lists, and it can run late or fail. Insiders usually file within "
        "two business days after they trade, so the list always lags the trades by a few days. Recent "
        "filings use the SEC's daily lists; older ones use the SEC's quarterly files (checked against each "
        "other on three days: identical). Two filings (out of about 19,000 read since 1 October) could not be downloaded from the SEC."
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
