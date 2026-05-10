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
        ["📊 Dashboard", "🔍 Analyze หุ้นเดี่ยว", "📋 Screen Universe",
         "🎯 Next Picks", "📜 Alpha Picks History"],
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
