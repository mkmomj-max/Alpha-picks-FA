# 📈 Alpha Picks FA

DIY Quant Stock Screener — เลียนแบบและพัฒนาต่อจาก **Seeking Alpha Alpha Picks**
ใช้ Python + Streamlit + yfinance · ฟรี · ไม่ต้อง API key

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- 📊 **Dashboard** — สถิติ Alpha Picks history (48 picks, win rate 87.5%)
- 🔍 **Analyze** — วิเคราะห์หุ้นรายตัว พร้อม radar chart + price chart
- 📋 **Screener** — scan universe ทั้งหมด ranking ด้วย 5 factors
- 🎯 **Next Picks** — แนะนำหุ้นที่ profile ใกล้เคียงกับ Alpha Picks winners
- 📜 **History** — interactive table + scatter plot ของ picks เก่าทั้งหมด

## 🚀 Quick Start

### 1. Clone และติดตั้ง

```bash
git clone https://github.com/<your-username>/alpha-picks-fa.git
cd alpha-picks-fa
pip install -r requirements.txt
```

### 2. รัน web app (มีปุ่มกด — แนะนำ)

```bash
streamlit run app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501` แล้วใช้ปุ่มได้เลย ไม่ต้องพิมพ์คำสั่ง

### 3. หรือใช้ CLI (สำหรับ automation)

```bash
python run.py history                   # สถิติ Alpha Picks
python run.py analyze CRDO              # วิเคราะห์ตัวเดียว
python run.py screen --top 20           # screen universe
python run.py next-picks --top 15       # หา picks ใหม่
```

## 🧠 Methodology

| Factor | Weight | Inputs |
|--------|--------|--------|
| Valuation | 20% | P/E, P/S, EV/EBITDA, PEG |
| Growth | 25% | Revenue & EPS YoY |
| Profitability | 20% | Gross/Op/Net margin, ROE, ROA |
| Momentum | 20% | 3M / 6M / 12M return |
| EPS Revisions | 15% | Analyst recommendations + price target upside |
| Quality (bonus) | 15% | D/E, current ratio, FCF yield |

ทุก factor → winsorize → z-score → percentile rank (0-100) → composite weighted average

## 📁 Project Structure

```
alpha-picks-fa/
├── app.py                    # Streamlit web UI (มีปุ่มกด)
├── run.py                    # CLI runner
├── config.py                 # weights, filters, themes
├── data_fetcher.py           # yfinance wrapper
├── factors.py                # 6 factor calculations
├── scorer.py                 # composite scoring + filters
├── next_picks.py             # similarity engine
├── alpha_picks_history.py    # 48 historical picks
├── screener.py               # orchestrator
├── universe.txt              # 100+ ticker scan list
└── universe_small.txt        # 50 tickers (faster testing)
```

## 🎯 Improvements over Alpha Picks

- ✅ โปร่งใส 100% — เห็นทุก factor + ปรับ weight ได้
- ✅ มี Quality factor (Piotroski-style)
- ✅ Sector cap + position size rules
- ✅ Stop-loss rules (ที่ Alpha Picks ไม่มี)
- ✅ ฟรี ไม่ต้องจ่าย $499/ปี

## ⚠️ Disclaimer

โค้ดนี้สร้างเพื่อการศึกษา **ไม่ใช่คำแนะนำการลงทุน** การลงทุนมีความเสี่ยง โปรดทำการบ้านเอง

## 📜 License

MIT
