"""Streamlit web UI for Alpha Picks FA.

Run with:
    streamlit run app.py
"""

import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from alpha_picks_history import ALPHA_PICKS, stats, sector_breakdown
from data_fetcher import fetch_ticker, fetch_universe
from scorer import apply_filters, score
from next_picks import rank_next_picks
from screener import load_universe
from fair_value import composite_fair_value
from financial_analysis import (
    get_statements, income_summary, balance_summary, cashflow_summary,
    growth_rates, margin_trend, piotroski_f_score, health_ratios,
)
from sensitivity import sensitivity_matrix, implied_assumptions
from peer_compare import find_peers, compare_peers, relative_rank
from alerts import evaluate_single, evaluate_portfolio, bulk_fair_value


st.set_page_config(
    page_title="Alpha Picks FA",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { font-size: 2.5rem; font-weight: 700; margin-bottom: 0; }
    .subtitle { color: #888; margin-top: 0; }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        padding: 1rem; border-radius: 8px; color: white;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white; border: none; padding: 0.6rem;
        font-weight: 600; border-radius: 6px;
    }
    .stButton > button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)


# ── Cache wrappers ────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch_ticker(symbol: str):
    return fetch_ticker(symbol)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_screen(universe_tuple: tuple) -> pd.DataFrame:
    raw = fetch_universe(list(universe_tuple))
    filtered = apply_filters(raw)
    return score(filtered)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_fair_value(symbol: str, dr: float, gr):
    return composite_fair_value(symbol, discount_rate=dr, growth_rate=gr)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_sensitivity(symbol: str):
    return sensitivity_matrix(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_implied(symbol: str):
    return implied_assumptions(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_peers(symbol: str):
    peers = find_peers(symbol)
    df = compare_peers(symbol, peers)
    ranks = relative_rank(df, symbol)
    return df, ranks


@st.cache_data(ttl=1800, show_spinner=False)
def cached_evaluate(symbol: str, universe_tuple: tuple):
    uni_df = cached_screen(universe_tuple)
    return evaluate_single(symbol, peer_universe=uni_df)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_evaluate_portfolio(tickers: tuple, universe_tuple: tuple):
    uni_df = cached_screen(universe_tuple)
    return evaluate_portfolio(list(tickers), peer_universe=uni_df)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_bulk_fv(tickers: tuple):
    return bulk_fair_value(list(tickers))


# ── Header ────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📈 Alpha Picks FA</div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">DIY Quant Screener — เลียนแบบและพัฒนาต่อจาก Seeking Alpha Alpha Picks</p>',
            unsafe_allow_html=True)
st.divider()


# ── Sidebar navigation ────────────────────────────────────────────
with st.sidebar:
    st.header("🎛️ Menu")
    page = st.radio(
        "เลือกหน้า",
        ["📊 Dashboard", "🔍 Analyze หุ้นเดี่ยว", "💰 Fair Value (FA)",
         "🔬 Sensitivity", "🏆 Peer Compare", "🚨 Buy/Sell Alerts",
         "📋 Screen Universe", "🎯 Next Picks", "📜 Alpha Picks History"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**🔧 Settings**")
    universe_choice = st.selectbox(
        "Universe", ["universe_small.txt (50 ตัว)", "universe.txt (100+ ตัว)", "Custom"]
    )
    if universe_choice.startswith("Custom"):
        custom_input = st.text_area("ใส่ ticker (คั่นด้วย comma หรือบรรทัด)",
                                     value="AAPL, MSFT, NVDA, AMD")
    st.divider()
    st.caption("Data: yfinance · ฟรี · ไม่ต้อง API key")


def get_universe() -> list[str]:
    if universe_choice.startswith("Custom"):
        text = custom_input.replace(",", "\n")
        return [t.strip().upper() for t in text.split() if t.strip()]
    fname = universe_choice.split()[0]
    return load_universe(fname)


# ──────────────────────────────────────────────────────────────────
# PAGE 1: Dashboard
# ──────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    s = stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Picks", s["count"])
    c2.metric("Avg Return", f"{s['avg_return']:.1f}%")
    c3.metric("Win Rate", f"{s['win_rate']:.1f}%")
    c4.metric("Best Pick", f"+{s['best']:.0f}%")

    st.subheader("📊 Sector Allocation")
    sb = sector_breakdown()
    sec_df = pd.DataFrame(
        [{"Sector": k, "Count": v[0], "Percent": v[1]} for k, v in sb.items()]
    )
    fig = px.bar(
        sec_df.sort_values("Count"), x="Count", y="Sector",
        orientation="h", color="Percent", color_continuous_scale="Viridis",
        text="Count",
    )
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🏆 Top Returns")
    df = pd.DataFrame(
        ALPHA_PICKS,
        columns=["Ticker", "Date", "Return %", "Sector", "Rating", "Weight %"],
    ).sort_values("Return %", ascending=False).head(15)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────────
# PAGE 2: Analyze single stock
# ──────────────────────────────────────────────────────────────────
elif page == "🔍 Analyze หุ้นเดี่ยว":
    st.subheader("🔍 วิเคราะห์หุ้นรายตัว")

    col1, col2 = st.columns([3, 1])
    ticker = col1.text_input("ใส่ ticker", value="CRDO", key="single_tk").upper().strip()
    col2.write("")
    col2.write("")
    go_btn = col2.button("🚀 Analyze", key="analyze_btn")

    if go_btn and ticker:
        with st.spinner(f"กำลังดึงข้อมูล {ticker}..."):
            d = cached_fetch_ticker(ticker)
        if d is None:
            st.error(f"ไม่พบข้อมูลสำหรับ {ticker}")
        else:
            h = d.pop("history")
            if not h.empty and len(h) > 252:
                d["return_3m"]  = (h["Close"].iloc[-1] / h["Close"].iloc[-63]  - 1) * 100
                d["return_6m"]  = (h["Close"].iloc[-1] / h["Close"].iloc[-126] - 1) * 100
                d["return_12m"] = (h["Close"].iloc[-1] / h["Close"].iloc[-252] - 1) * 100

            # Single-row scoring won't work standalone — score against universe
            with st.spinner("กำลังเทียบกับ universe..."):
                uni_df = cached_screen(tuple(get_universe()))
            if ticker not in uni_df["symbol"].values:
                # Append and re-score
                from data_fetcher import fetch_universe as _fu
                full = pd.concat([uni_df, pd.DataFrame([{**d}])], ignore_index=True)
                full = score(apply_filters(full))
            else:
                full = uni_df
            row = full[full["symbol"] == ticker]
            if row.empty:
                st.warning("หุ้นไม่ผ่าน filter (market cap/price/volume) — แสดงข้อมูลดิบ")
                st.json({k: v for k, v in d.items() if k != "history"})
            else:
                row = row.iloc[0]

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("ราคา", f"${row['price']:.2f}")
                c2.metric("Market Cap", f"${row['market_cap']/1e9:.1f}B")
                c3.metric("Composite", f"{row['composite']:.1f}")
                c4.metric("Rating", row["rating"])

                st.subheader("📊 Factor Scores")
                factors = ["valuation", "growth", "profitability", "momentum", "revisions"]
                vals = [row[f] for f in factors]
                fig = go.Figure(go.Scatterpolar(
                    r=vals, theta=[f.capitalize() for f in factors],
                    fill="toself", line=dict(color="#7c3aed"),
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(range=[0, 100])),
                    height=400, showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("📈 Price Chart (1Y)")
                if not h.empty:
                    fig2 = px.line(h.reset_index(), x=h.index.name or "Date", y="Close")
                    fig2.update_layout(height=300)
                    st.plotly_chart(fig2, use_container_width=True)


# ──────────────────────────────────────────────────────────────────
# PAGE 3: Full screen
# ──────────────────────────────────────────────────────────────────
elif page == "📋 Screen Universe":
    st.subheader("📋 Screen ทั้ง Universe")
    top_n = st.slider("Top N", 5, 50, 20)

    if st.button("🔍 เริ่ม Screen", key="screen_btn"):
        uni = get_universe()
        progress = st.progress(0.0, text=f"กำลังดึง {len(uni)} หุ้น...")
        with st.spinner("กำลังคำนวณ factor scores..."):
            df = cached_screen(tuple(uni))
        progress.progress(1.0, text="เสร็จแล้ว!")

        st.success(f"✅ ผ่าน filter: {len(df)} ตัว · แสดง Top {top_n}")
        top = df.head(top_n).copy()
        cols = ["symbol", "name", "sector", "price", "market_cap",
                "valuation", "growth", "profitability", "momentum",
                "revisions", "composite", "rating"]
        cols = [c for c in cols if c in top.columns]
        display = top[cols].copy()
        display["market_cap"] = display["market_cap"].apply(
            lambda x: f"${x/1e9:.1f}B" if pd.notna(x) else "-"
        )
        for c in ["valuation", "growth", "profitability", "momentum",
                  "revisions", "composite"]:
            if c in display.columns:
                display[c] = display[c].round(1)

        st.dataframe(display, use_container_width=True, hide_index=True)

        csv = top.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "screen.csv", "text/csv")


# ──────────────────────────────────────────────────────────────────
# PAGE 4: Next Picks
# ──────────────────────────────────────────────────────────────────
elif page == "🎯 Next Picks":
    st.subheader("🎯 หา Alpha Picks ตัวต่อไป")
    st.caption("จัดอันดับโดย: composite quant score + cosine similarity กับ "
               "winners เดิม + theme bonus (Industrials/IT/Materials)")
    top_n = st.slider("Top N", 5, 30, 15)

    if st.button("🚀 หา Candidates", key="next_btn"):
        uni = get_universe()
        with st.spinner(f"กำลัง screen {len(uni)} หุ้น..."):
            df = cached_screen(tuple(uni))
        with st.spinner("กำลังคำนวณ similarity..."):
            picks = rank_next_picks(df, top_n=top_n)

        st.success(f"🎯 พบ candidates {len(picks)} ตัว")

        for i, (_, row) in enumerate(picks.iterrows(), 1):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.markdown(f"**#{i} · {row['symbol']}** — {row['name']}")
                c1.caption(f"{row['sector']} · ${row['price']:.2f}")
                c2.metric("Alpha Score", f"{row['alpha_score']:.1f}")
                c3.metric("Composite", f"{row['composite']:.1f}")
                c4.metric("Rating", row["rating"])

                with st.expander("📊 Factor breakdown"):
                    cols = st.columns(5)
                    for col, f in zip(cols, ["valuation", "growth",
                                              "profitability", "momentum", "revisions"]):
                        col.metric(f.capitalize(), f"{row[f]:.0f}")

        csv = picks.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "next_picks.csv", "text/csv")


# ──────────────────────────────────────────────────────────────────
# PAGE: Fair Value (FA)
# ──────────────────────────────────────────────────────────────────
elif page == "💰 Fair Value (FA)":
    st.subheader("💰 Fair Value Analysis — ประเมินมูลค่าที่แท้จริง")
    st.caption("รวม DCF + Multiples + Graham + EPV + Piotroski F-Score + งบการเงิน 3-4 ปี")

    col1, col2 = st.columns([3, 1])
    fv_ticker = col1.text_input("Ticker", value="AAPL", key="fv_tk").upper().strip()
    col2.write(""); col2.write("")
    fv_btn = col2.button("💰 Valuate", key="fv_btn")

    with st.expander("⚙️ DCF Assumptions (ปรับได้)"):
        c1, c2, c3 = st.columns(3)
        dcf_discount = c1.slider("Discount rate (%)", 6.0, 15.0, 10.0, 0.5) / 100
        dcf_growth = c2.slider("FCF growth rate (%) — เว้นว่าง = auto", 0.0, 30.0, 0.0, 1.0)
        dcf_growth_v = (dcf_growth / 100) if dcf_growth > 0 else None
        c3.write(""); c3.caption("Terminal growth: 2.5% (default)")

    if fv_btn and fv_ticker:
        with st.spinner(f"กำลังคำนวณ fair value ของ {fv_ticker}..."):
            try:
                fv = composite_fair_value(
                    fv_ticker,
                    discount_rate=dcf_discount,
                    growth_rate=dcf_growth_v,
                )
            except Exception as e:
                st.error(f"Error: {e}")
                fv = None

        if fv and fv.get("composite_fair_value"):
            # ── Verdict header ──
            cur = fv["current_price"]
            fair = fv["composite_fair_value"]
            mos = fv["margin_of_safety_pct"]

            st.markdown(f"### {fv['verdict']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ราคาปัจจุบัน", f"${cur:.2f}")
            c2.metric("Fair Value", f"${fair:.2f}")
            c3.metric("Margin of Safety", f"{mos:+.1f}%",
                      delta=f"{'undervalued' if mos > 0 else 'overvalued'}")
            upside = (fair / cur - 1) * 100 if cur else 0
            c4.metric("Upside/Downside", f"{upside:+.1f}%")

            # ── Bar chart of all models ──
            st.subheader("📊 เปรียบเทียบ Fair Value แต่ละโมเดล")
            model_data = []
            for key, m in fv["models"].items():
                v = m.get("fair_value")
                if v and v > 0:
                    model_data.append({"Model": m["method"], "Fair Value": v,
                                        "Weight": fv["weights"].get(key, 0) * 100})
            if model_data:
                mdf = pd.DataFrame(model_data)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=mdf["Model"], y=mdf["Fair Value"],
                    text=[f"${v:.2f}" for v in mdf["Fair Value"]],
                    textposition="outside",
                    marker_color=["#4f46e5", "#7c3aed", "#ec4899", "#f59e0b"],
                ))
                fig.add_hline(y=cur, line_dash="dash", line_color="red",
                              annotation_text=f"ราคาปัจจุบัน ${cur:.2f}")
                fig.add_hline(y=fair, line_dash="dot", line_color="green",
                              annotation_text=f"Composite ${fair:.2f}")
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            # ── DCF details ──
            with st.expander("🔬 DCF Model Details"):
                dcf = fv["models"]["dcf"]
                if dcf.get("error"):
                    st.warning(dcf["error"])
                else:
                    st.write("**Assumptions:**")
                    a = dcf["assumptions"]
                    st.write(f"- FCF base: ${a['fcf_base']/1e9:.2f}B")
                    st.write(f"- Growth rate: {a['growth_rate']*100:.1f}%/year (years 1-{a['high_growth_years']})")
                    st.write(f"- Terminal growth: {a['terminal_growth']*100:.1f}%")
                    st.write(f"- Discount rate (WACC): {a['discount_rate']*100:.1f}%")
                    proj = pd.DataFrame(dcf["projections"])
                    proj["fcf"] = proj["fcf"].apply(lambda x: f"${x/1e9:.2f}B")
                    proj["pv"] = proj["pv"].apply(lambda x: f"${x/1e9:.2f}B")
                    st.dataframe(proj, hide_index=True, use_container_width=True)

            # ── Multiples details ──
            with st.expander("📏 Multiples Valuation Details"):
                m = fv["models"]["multiples"]
                st.write(f"**Sector**: {m['sector']}")
                st.write(f"**P/E target multiple**: {m['pe_multiple']}x")
                st.write(f"**EV/EBITDA target multiple**: {m['ev_multiple']}x")
                if m.get("pe_value"):
                    st.write(f"- P/E-based fair value: ${m['pe_value']:.2f}")
                if m.get("ev_ebitda_value"):
                    st.write(f"- EV/EBITDA-based fair value: ${m['ev_ebitda_value']:.2f}")

            st.divider()

            # ── Financial Statements ──
            st.subheader("📑 งบการเงิน 3-4 ปี")
            with st.spinner("กำลังดึงงบ..."):
                stmts = get_statements(fv_ticker)

            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                ["📈 Income", "💼 Balance", "💵 Cash Flow", "📊 Margins", "🏆 Piotroski"]
            )

            with tab1:
                inc_df = income_summary(stmts["income"])
                if not inc_df.empty:
                    st.dataframe(inc_df.map(
                        lambda x: f"${x/1e9:.2f}B" if pd.notna(x) and abs(x) > 1e6
                                  else (f"${x:.2f}" if pd.notna(x) else "-")
                    ), use_container_width=True)
                gr = growth_rates(stmts["income"])
                if gr:
                    st.write("**Growth Rates:**")
                    cols = st.columns(len(gr))
                    for col, (k, v) in zip(cols, gr.items()):
                        col.metric(
                            k.upper(),
                            f"{v.get('cagr', 0):.1f}% CAGR" if v.get('cagr') else "n/a",
                            delta=f"{v.get('yoy', 0):.1f}% YoY" if v.get('yoy') else None,
                        )

            with tab2:
                bs_df = balance_summary(stmts["balance"])
                if not bs_df.empty:
                    st.dataframe(bs_df.map(
                        lambda x: f"${x/1e9:.2f}B" if pd.notna(x) else "-"
                    ), use_container_width=True)

            with tab3:
                cf_df = cashflow_summary(stmts["cashflow"])
                if not cf_df.empty:
                    st.dataframe(cf_df.map(
                        lambda x: f"${x/1e9:.2f}B" if pd.notna(x) else "-"
                    ), use_container_width=True)

            with tab4:
                mt = margin_trend(stmts["income"])
                if not mt.empty:
                    st.dataframe(mt, use_container_width=True)
                    fig = go.Figure()
                    for idx in mt.index:
                        fig.add_trace(go.Scatter(
                            x=mt.columns, y=mt.loc[idx], mode="lines+markers", name=idx,
                        ))
                    fig.update_layout(height=350, yaxis_title="%")
                    st.plotly_chart(fig, use_container_width=True)

            with tab5:
                with st.spinner("กำลังคำนวณ Piotroski F-Score..."):
                    pf = piotroski_f_score(fv_ticker)
                c1, c2 = st.columns(2)
                c1.metric("F-Score", f"{pf['score']}/9")
                c2.metric("Quality", pf["rating"])
                for d in pf["details"]:
                    st.write(d)

            st.divider()
            st.subheader("📋 Health Ratios")
            hr = health_ratios(fv_ticker)
            cols = st.columns(4)
            i = 0
            for k, v in hr.items():
                if v is None:
                    continue
                if isinstance(v, float):
                    if "Margin" in k or "Yield" in k or "ROE" in k or "ROA" in k or "Ratio" in k and abs(v) < 5:
                        disp = f"{v*100:.2f}%" if abs(v) < 5 else f"{v:.2f}"
                    else:
                        disp = f"{v:.2f}"
                else:
                    disp = str(v)
                cols[i % 4].metric(k, disp)
                i += 1

        elif fv:
            st.error("ไม่สามารถคำนวณ fair value ได้ — ข้อมูลไม่เพียงพอ (ต้องมี FCF + EPS เป็นบวก)")
            st.json({k: v.get("error", "ok") for k, v in fv["models"].items()})


# ──────────────────────────────────────────────────────────────────
# PAGE: Sensitivity Analysis
# ──────────────────────────────────────────────────────────────────
elif page == "🔬 Sensitivity":
    st.subheader("🔬 DCF Sensitivity Analysis")
    st.caption("ดู Fair Value เปลี่ยนยังไงเมื่อปรับ discount rate และ growth rate")

    c1, c2 = st.columns([3, 1])
    s_ticker = c1.text_input("Ticker", value="NVDA", key="sens_tk").upper().strip()
    c2.write(""); c2.write("")
    s_btn = c2.button("🔬 วิเคราะห์", key="sens_btn")

    if s_btn and s_ticker:
        with st.spinner("กำลังคำนวณ matrix..."):
            try:
                matrix = cached_sensitivity(s_ticker)
                implied = cached_implied(s_ticker)
            except Exception as e:
                st.error(f"Error: {e}")
                matrix = None

        if matrix is not None and not matrix.empty:
            current = implied.get("current_price")
            if current:
                st.metric("ราคาปัจจุบัน", f"${current:.2f}")

            st.subheader("📊 Fair Value Matrix")
            st.caption("แถว = Discount Rate (WACC), คอลัมน์ = Growth Rate")

            def color_cell(v):
                if pd.isna(v) or current is None:
                    return ""
                diff = (v - current) / current * 100
                if diff >= 30:   return "background-color: #14532d; color: white"
                if diff >= 10:   return "background-color: #166534; color: white"
                if diff >= -10:  return "background-color: #713f12; color: white"
                if diff >= -30:  return "background-color: #7f1d1d; color: white"
                return "background-color: #450a0a; color: white"

            styled = matrix.style.format("${:.0f}").map(color_cell)
            st.dataframe(styled, use_container_width=True)
            st.caption("🟢 เขียวเข้ม = undervalued มาก · 🔴 แดงเข้ม = overvalued มาก")

            st.divider()
            st.subheader("🎯 Implied Market Expectations")
            ig = implied.get("implied_growth_at_10pct_discount")
            if ig is not None:
                c1, c2 = st.columns(2)
                c1.metric("Implied Growth Rate", f"{ig:.1f}%/year",
                          help="ที่ discount=10% ตลาดคิดว่าหุ้นต้องโตเท่านี้ ราคาถึงจะ fair")
                c2.info(implied.get("interpretation", ""))
            else:
                st.warning("ไม่สามารถคำนวณ implied growth ได้")


# ──────────────────────────────────────────────────────────────────
# PAGE: Peer Compare
# ──────────────────────────────────────────────────────────────────
elif page == "🏆 Peer Compare":
    st.subheader("🏆 Peer Comparison")
    st.caption("เทียบหุ้นกับคู่แข่งใน sector — หา relative value")

    c1, c2 = st.columns([3, 1])
    p_ticker = c1.text_input("Ticker", value="NVDA", key="peer_tk").upper().strip()
    c2.write(""); c2.write("")
    p_btn = c2.button("🏆 เทียบ", key="peer_btn")

    if p_btn and p_ticker:
        with st.spinner(f"กำลังหา peers ของ {p_ticker}..."):
            try:
                df, ranks = cached_peers(p_ticker)
            except Exception as e:
                st.error(f"Error: {e}")
                df = None

        if df is not None and not df.empty:
            st.success(f"พบ {len(df)} ตัวให้เปรียบเทียบ")

            display = df.copy()
            for c in ["Price", "Mkt Cap (B)", "P/E (fwd)", "P/S", "EV/EBITDA",
                      "PEG", "Rev Growth %", "Op Margin %", "ROE %", "D/E", "Div Yield %"]:
                if c in display.columns:
                    display[c] = display[c].round(2)

            def highlight_target(row):
                if row["Ticker"] == p_ticker:
                    return ["background-color: #1e3a5f; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.dataframe(
                display.style.apply(highlight_target, axis=1),
                use_container_width=True, hide_index=True,
            )

            if ranks:
                st.divider()
                st.subheader(f"🎯 Ranking ของ {p_ticker} เทียบ peers")
                cols = st.columns(3)
                for i, (metric, info) in enumerate(ranks.items()):
                    with cols[i % 3]:
                        rank, of = info["rank"], info["of"]
                        emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "📊"
                        st.metric(
                            f"{emoji} {metric}",
                            f"#{rank}/{of}",
                            delta=f"{info['value']:.2f}",
                            delta_color="off",
                        )

                st.divider()
                st.subheader("📊 Visual Comparison")
                metric_pick = st.selectbox(
                    "เลือก metric",
                    [c for c in ["P/E (fwd)", "EV/EBITDA", "Rev Growth %",
                                  "Op Margin %", "ROE %"] if c in df.columns],
                )
                fig = px.bar(
                    df.sort_values(metric_pick, ascending=metric_pick in ["P/E (fwd)", "EV/EBITDA"]),
                    x="Ticker", y=metric_pick,
                    color=df["Ticker"] == p_ticker,
                    color_discrete_map={True: "#7c3aed", False: "#475569"},
                )
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────────
# PAGE: Buy/Sell Alerts
# ──────────────────────────────────────────────────────────────────
elif page == "🚨 Buy/Sell Alerts":
    st.subheader("🚨 Buy/Sell Alert Engine")
    st.caption("รวม Composite Quant + Margin of Safety + Piotroski + Momentum → Alert")

    mode = st.radio(
        "โหมด",
        ["🎯 หุ้นเดี่ยว", "📁 Portfolio (หลายตัว)", "💰 Bulk Fair Value"],
        horizontal=True,
    )

    if mode == "🎯 หุ้นเดี่ยว":
        c1, c2 = st.columns([3, 1])
        a_ticker = c1.text_input("Ticker", value="NVDA", key="alert_tk").upper().strip()
        c2.write(""); c2.write("")
        a_btn = c2.button("🚨 เช็ค Alert", key="alert_btn")

        if a_btn and a_ticker:
            with st.spinner(f"กำลังประเมิน {a_ticker}..."):
                try:
                    uni = get_universe()
                    r = cached_evaluate(a_ticker, tuple(uni))
                except Exception as e:
                    st.error(f"Error: {e}")
                    r = None

            if r:
                alert = r.get("alert", "⚪ HOLD")
                if "STRONG BUY" in alert:
                    st.success(f"# {alert}")
                elif "BUY" in alert:
                    st.success(f"## {alert}")
                elif "STRONG SELL" in alert:
                    st.error(f"# {alert}")
                elif "SELL" in alert:
                    st.error(f"## {alert}")
                else:
                    st.info(f"## {alert}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("ราคา", f"${r['current_price']:.2f}" if r.get("current_price") else "n/a")
                c2.metric("Fair Value", f"${r['fair_value']:.2f}" if r.get("fair_value") else "n/a")
                c3.metric("MoS %", f"{r['margin_of_safety']:+.1f}%" if r.get("margin_of_safety") else "n/a")
                c4.metric("Composite", f"{r['composite']:.0f}" if r.get("composite") else "n/a")

                c1, c2 = st.columns(2)
                c1.metric("F-Score", f"{r['piotroski']}/9" if r.get("piotroski") is not None else "n/a")
                c2.metric("Momentum", f"{r['momentum']:.0f}" if r.get("momentum") else "n/a")

                st.subheader("📋 เหตุผล")
                for reason in r.get("alert_reason", []):
                    st.write(f"- {reason}")

                if r.get("warnings"):
                    with st.expander("⚠️ Warnings"):
                        for w in r["warnings"]:
                            st.warning(w)

    elif mode == "📁 Portfolio (หลายตัว)":
        st.write("ใส่ ticker (คั่นด้วย comma หรือบรรทัด)")
        port_input = st.text_area(
            "Tickers", value="NVDA, AAPL, MSFT, GOOGL, AMZN, KGC, BRK.B",
            height=100,
        )
        if st.button("🚨 ประเมินทั้ง Portfolio", key="port_btn"):
            tickers = [t.strip().upper() for t in port_input.replace(",", "\n").split() if t.strip()]
            if tickers:
                with st.spinner(f"กำลังประเมิน {len(tickers)} หุ้น..."):
                    try:
                        uni = get_universe()
                        df = cached_evaluate_portfolio(tuple(tickers), tuple(uni))
                    except Exception as e:
                        st.error(f"Error: {e}")
                        df = None

                if df is not None and not df.empty:
                    counts = df["Alert"].value_counts()
                    cols = st.columns(min(len(counts), 5))
                    for i, (alert, n) in enumerate(counts.items()):
                        cols[i % len(cols)].metric(alert, n)

                    st.divider()
                    display = df.copy()
                    for c in ["Price", "FairValue", "MoS %", "Composite", "Momentum"]:
                        if c in display.columns:
                            display[c] = pd.to_numeric(display[c], errors="coerce").round(2)
                    st.dataframe(display, use_container_width=True, hide_index=True)

                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Download CSV", csv, "alerts.csv", "text/csv")

    else:  # Bulk Fair Value
        st.caption("คำนวณ Fair Value ของหุ้นหลายตัวทีเดียว")
        bulk_input = st.text_area(
            "Tickers (คั่นด้วย comma หรือบรรทัด)",
            value="NVDA, AAPL, MSFT, GOOGL, BRK.B, KGC, NEM, GEV",
            height=100,
        )
        if st.button("💰 คำนวณ Bulk", key="bulk_btn"):
            tickers = [t.strip().upper() for t in bulk_input.replace(",", "\n").split() if t.strip()]
            if tickers:
                with st.spinner(f"กำลังคำนวณ {len(tickers)} หุ้น..."):
                    try:
                        df = cached_bulk_fv(tuple(tickers))
                    except Exception as e:
                        st.error(f"Error: {e}")
                        df = None

                if df is not None and not df.empty:
                    display = df.copy()
                    for c in ["Price", "Fair Value", "MoS %"]:
                        if c in display.columns:
                            display[c] = pd.to_numeric(display[c], errors="coerce").round(2)
                    st.dataframe(display, use_container_width=True, hide_index=True)

                    if "MoS %" in df.columns:
                        plot_df = df.dropna(subset=["MoS %"]).copy()
                        if not plot_df.empty:
                            plot_df["color"] = plot_df["MoS %"].apply(
                                lambda x: "Undervalued" if x > 10 else
                                          ("Overvalued" if x < -10 else "Fair")
                            )
                            fig = px.bar(
                                plot_df, x="Ticker", y="MoS %", color="color",
                                color_discrete_map={"Undervalued": "#16a34a",
                                                     "Fair": "#eab308",
                                                     "Overvalued": "#dc2626"},
                                title="Margin of Safety เรียงจากมากไปน้อย",
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)

                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Download CSV", csv, "bulk_fair_value.csv", "text/csv")


# ──────────────────────────────────────────────────────────────────
# PAGE 5: History
# ──────────────────────────────────────────────────────────────────
elif page == "📜 Alpha Picks History":
    st.subheader("📜 Alpha Picks History (48 picks)")
    df = pd.DataFrame(
        ALPHA_PICKS,
        columns=["Ticker", "Date", "Return %", "Sector", "Rating", "Weight %"],
    )

    c1, c2, c3 = st.columns(3)
    sector_filter = c1.multiselect("Sector", sorted(df["Sector"].unique()))
    rating_filter = c2.multiselect("Rating", sorted(df["Rating"].unique()))
    min_return = c3.slider("Min Return %", -50.0, 1600.0, -50.0)

    fdf = df.copy()
    if sector_filter: fdf = fdf[fdf["Sector"].isin(sector_filter)]
    if rating_filter: fdf = fdf[fdf["Rating"].isin(rating_filter)]
    fdf = fdf[fdf["Return %"] >= min_return]
    fdf = fdf.sort_values("Return %", ascending=False)

    st.dataframe(fdf, use_container_width=True, hide_index=True)

    fig = px.scatter(
        fdf, x="Date", y="Return %", size="Weight %",
        color="Sector", hover_name="Ticker",
        title="Performance Scatter (size = portfolio weight)",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
