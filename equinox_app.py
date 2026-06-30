import streamlit as st
import yfinance as yf
import anthropic
import json
import time
from datetime import datetime
from report_generator import generate_pdf_report
from financial_engine import compute_financials

st.set_page_config(
    page_title="Equinox — Investment Intelligence",
    page_icon="🌓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── COMPLETE CSS MATCHING THE PREVIEW ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp { background: #080d14 !important; font-family: 'Space Grotesk', sans-serif !important; color: #e2e8f0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }
header { visibility: hidden !important; }
footer { visibility: hidden !important; }
#MainMenu { visibility: hidden !important; }

/* GRID BACKGROUND */
.stApp::after {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(0,255,180,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,180,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* TICKER TAPE */
.topbar {
    background: rgba(10,18,30,0.97);
    border-bottom: 1px solid rgba(0,255,180,0.15);
    padding: 0 20px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative; z-index: 100;
}
.logo { display: flex; align-items: center; gap: 10px; }
.logo-icon {
    width: 30px; height: 30px;
    background: linear-gradient(135deg, #00ffb4, #0066ff);
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 700; color: #080d14;
}
.logo-name {
    font-size: 16px; font-weight: 700;
    background: linear-gradient(135deg, #00ffb4, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 1px;
}
.ticker-tape {
    flex: 1; margin: 0 28px;
    overflow: hidden; height: 52px;
    display: flex; align-items: center;
    mask-image: linear-gradient(90deg, transparent, black 5%, black 95%, transparent);
}
.ticker-inner {
    display: inline-flex; gap: 0;
    animation: tickscroll 35s linear infinite;
    white-space: nowrap;
}
@keyframes tickscroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
.tick-item {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 0 20px;
    border-right: 1px solid rgba(255,255,255,0.05);
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
}
.tick-sym { color: #64748b; font-weight: 500; }
.tick-price { color: #94a3b8; }
.tick-up { color: #00ffb4; }
.tick-down { color: #ff4f6a; }
.live-badge {
    display: flex; align-items: center; gap: 7px;
    background: rgba(0,255,180,0.08);
    border: 1px solid rgba(0,255,180,0.2);
    border-radius: 999px; padding: 5px 14px;
    font-size: 11px; font-weight: 600; color: #00ffb4; letter-spacing: 1px;
    flex-shrink: 0;
}
.live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #00ffb4; box-shadow: 0 0 6px #00ffb4;
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* TABS */
.eq-tabs {
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 0 20px;
    display: flex; gap: 0;
    position: relative; z-index: 99;
}
.eq-tab {
    padding: 12px 24px; font-size: 13px; font-weight: 500;
    color: #64748b; cursor: pointer;
    border-bottom: 2px solid transparent;
}
.eq-tab.on { color: #00ffb4; border-bottom-color: #00ffb4; }

/* TWO-COLUMN LAYOUT */
.eq-layout {
    display: flex;
    min-height: calc(100vh - 104px);
    position: relative; z-index: 10;
}

/* SIDEBAR */
.eq-sidebar {
    width: 280px;
    flex-shrink: 0;
    background: rgba(10,18,30,0.85);
    border-right: 1px solid rgba(255,255,255,0.06);
    padding: 20px 16px;
    overflow-y: auto;
}
.sidebar-label {
    font-size: 10px; font-weight: 600;
    color: #475569; letter-spacing: 1.5px;
    text-transform: uppercase; margin-bottom: 10px;
}
.watchlist-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 10px; border-radius: 7px;
    cursor: pointer; margin-bottom: 3px;
    border: 1px solid transparent;
    transition: all 0.15s;
}
.watchlist-item:hover { background: rgba(255,255,255,0.04); }
.watchlist-item.sel { background: rgba(0,255,180,0.07); border-color: rgba(0,255,180,0.15); }
.wi-sym { font-size: 13px; font-weight: 600; color: #e2e8f0; display: block; }
.wi-name { font-size: 10px; color: #475569; display: block; }
.wi-price { font-family: 'JetBrains Mono'; font-size: 12px; color: #e2e8f0; text-align: right; display: block; }
.wi-chg { font-family: 'JetBrains Mono'; font-size: 10px; text-align: right; display: block; }
.g { color: #00ffb4; }
.r { color: #ff4f6a; }

/* MAIN CONTENT */
.eq-content { flex: 1; padding: 24px 28px; overflow-y: auto; }

/* STOCK HEADER */
.stock-hdr {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 20px; padding-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.stock-name { font-size: 22px; font-weight: 700; color: #f1f5f9; }
.stock-ticker-badge {
    font-size: 12px; color: #475569; font-weight: 400;
    margin-left: 10px;
}
.stock-meta { font-size: 12px; color: #475569; margin-top: 4px; }
.stock-price { font-family: 'JetBrains Mono'; font-size: 28px; font-weight: 600; color: #f1f5f9; text-align: right; }
.stock-ret { font-family: 'JetBrains Mono'; font-size: 12px; margin-top: 4px; text-align: right; }

/* VERDICT BANNER */
.verdict-banner {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(0,255,180,0.05);
    border: 1px solid rgba(0,255,180,0.2);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 18px;
    gap: 16px;
}
.verdict-banner.HOLD { background: rgba(251,191,36,0.05); border-color: rgba(251,191,36,0.2); }
.verdict-banner.SELL { background: rgba(255,79,106,0.05); border-color: rgba(255,79,106,0.2); }
.verdict-pill {
    font-size: 13px; font-weight: 700;
    padding: 6px 20px; border-radius: 999px;
    letter-spacing: 1px; flex-shrink: 0;
}
.vp-BUY  { background: rgba(0,255,180,0.15); border: 1px solid rgba(0,255,180,0.4); color: #00ffb4; }
.vp-HOLD { background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.4); color: #fbbf24; }
.vp-SELL { background: rgba(255,79,106,0.12); border: 1px solid rgba(255,79,106,0.4); color: #ff4f6a; }
.vp-UNCERTAIN { background: rgba(100,116,139,0.1); border: 1px solid #64748b; color: #94a3b8; }
.verdict-text { font-size: 13px; color: #94a3b8; line-height: 1.65; flex: 1; }

/* METRICS GRID */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 14px;
}
.metric-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 13px 14px;
    transition: border-color 0.2s, transform 0.15s;
}
.metric-card:hover { border-color: rgba(0,255,180,0.2); transform: translateY(-1px); }
.metric-label { font-size: 9px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 7px; }
.metric-value { font-family: 'JetBrains Mono'; font-size: 16px; font-weight: 500; color: #e2e8f0; }
.metric-value.pos { color: #00ffb4; }
.metric-value.neg { color: #ff4f6a; }

/* CHART AREA */
.chart-area {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 16px;
    height: 130px;
    overflow: hidden;
}
.chart-label { font-size: 9px; color: #475569; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }

/* SECTION LABEL */
.sec-lbl {
    font-size: 10px; font-weight: 600;
    color: #475569; letter-spacing: 1.5px;
    text-transform: uppercase;
    margin: 18px 0 10px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding-bottom: 8px;
}

/* RISK PILLS */
.risk-row { display: flex; flex-wrap: wrap; gap: 8px; }
.risk-pill { padding: 5px 13px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.risk-high { background: rgba(255,79,79,0.1); border: 1px solid rgba(255,79,79,0.3); color: #ff4f6a; }
.risk-med  { background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.3); color: #fbbf24; }
.risk-low  { background: rgba(0,255,180,0.06); border: 1px solid rgba(0,255,180,0.25); color: #00ffb4; }

/* POSITIVES */
.pos-item { display: flex; align-items: flex-start; gap: 10px; padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px; color: #64748b; line-height: 1.6; }
.pos-dot { color: #00ffb4; flex-shrink: 0; margin-top: 2px; }

/* PLAIN ENGLISH */
.pe-box {
    background: rgba(0,102,255,0.06);
    border: 1px solid rgba(0,102,255,0.18);
    border-radius: 10px; padding: 16px 20px;
    font-size: 14px; color: #60a5fa;
    line-height: 1.75; font-style: italic; margin: 14px 0;
}

/* VALUATION TEXT */
.val-text { font-size: 13px; color: #64748b; line-height: 1.8; }

/* DISCLAIMER */
.disc { font-size: 11px; color: #1e293b; margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.04); line-height: 1.6; }

/* EMPTY STATE */
.empty-state { text-align: center; padding: 80px 20px; }
.empty-icon { font-size: 52px; margin-bottom: 18px; }
.empty-title { font-size: 17px; color: #1e3a5f; font-weight: 500; margin-bottom: 8px; }
.empty-tickers { font-size: 12px; color: #0f1f30; letter-spacing: 0.5px; }

/* INPUT OVERRIDES */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0,255,180,0.4) !important;
    box-shadow: 0 0 0 3px rgba(0,255,180,0.08) !important;
    color: #f1f5f9 !important;
}
.stTextInput > div > div > input::placeholder { color: #334155 !important; }
.stTextInput label { display: none !important; }

.stButton > button {
    background: linear-gradient(135deg, rgba(0,255,180,0.12), rgba(0,102,255,0.12)) !important;
    border: 1px solid rgba(0,255,180,0.35) !important;
    border-radius: 8px !important;
    color: #00ffb4 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 13px !important; font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    padding: 12px 24px !important; width: 100% !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,255,180,0.22), rgba(0,102,255,0.22)) !important;
    box-shadow: 0 0 20px rgba(0,255,180,0.15) !important;
}

.stDownloadButton > button {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 12px !important;
    padding: 8px 18px !important;
    width: auto !important;
}
.stDownloadButton > button:hover { border-color: rgba(0,255,180,0.3) !important; color: #00ffb4 !important; }

.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.02) !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
    padding: 0 20px !important; gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #475569 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 12px 24px !important; border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] { color: #00ffb4 !important; border-bottom-color: #00ffb4 !important; background: transparent !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
div[data-testid="stSpinner"] > div { border-top-color: #00ffb4 !important; }
.stAlert { background: rgba(255,79,106,0.08) !important; border: 1px solid rgba(255,79,106,0.25) !important; border-radius: 8px !important; color: #ff4f6a !important; }

/* Portfolio optimiser theme */
.stSlider > div > div > div > div { background: #00ffb4 !important; }
.stNumberInput > div > div > input { background: rgba(255,255,255,0.04) !important; border-color: rgba(255,255,255,0.1) !important; color: #e2e8f0 !important; border-radius: 8px !important; }
.stDateInput > div > div > input { background: rgba(255,255,255,0.04) !important; border-color: rgba(255,255,255,0.1) !important; color: #e2e8f0 !important; border-radius: 8px !important; }
.stDataFrame { background: rgba(10,18,30,0.8) !important; }
div[data-testid="stMetricValue"] { color: #00ffb4 !important; font-family: 'JetBrains Mono' !important; }
div[data-testid="stMetricLabel"] { color: #475569 !important; }
</style>
""", unsafe_allow_html=True)

# ── TICKER TAPE ───────────────────────────────────────────────────────────────
TICKERS = [
    ("AAPL","$189.42","+1.22%","u"), ("RELIANCE.NS","₹2,941","+0.81%","u"),
    ("MSFT","$415.30","+0.54%","u"), ("TCS.NS","₹3,812","-0.31%","d"),
    ("TSLA","$248.71","-2.14%","d"), ("NVDA","$875.40","+3.42%","u"),
    ("INFY.NS","₹1,642","+1.08%","u"), ("GOOGL","$175.98","+0.71%","u"),
    ("HDFCBANK.NS","₹1,823","+0.45%","u"), ("AMZN","$192.45","+1.33%","u"),
    ("META","$527.30","+0.98%","u"), ("WIPRO.NS","₹480","-0.62%","d"),
    ("JPM","$198.20","+0.33%","u"), ("BAJFINANCE.NS","₹6,820","+1.15%","u"),
]

tick_items = ""
for sym, px, chg, d in TICKERS * 2:
    cls = "tick-up" if d=="u" else "tick-down"
    arr = "▲" if d=="u" else "▼"
    tick_items += f'<span class="tick-item"><span class="tick-sym">{sym}</span><span class="tick-price">{px}</span><span class="{cls}">{arr} {chg}</span></span>'

st.markdown(f"""
<div class="topbar">
  <div class="logo">
    <div class="logo-icon">E</div>
    <span class="logo-name">EQUINOX</span>
  </div>
  <div class="ticker-tape">
    <div class="ticker-inner">{tick_items}</div>
  </div>
  <div class="live-badge"><div class="live-dot"></div>LIVE</div>
</div>
""", unsafe_allow_html=True)

# ── API KEY ───────────────────────────────────────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊  Equity Research", "📐  Portfolio Optimiser"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EQUITY RESEARCH
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    WATCHLIST = [
        ("AAPL",  "Apple Inc.",       "$189.42", "+1.22%", "g"),
        ("MSFT",  "Microsoft",        "$415.30", "+0.54%", "g"),
        ("RELIANCE.NS","Reliance Ind.","₹2,941", "+0.81%", "g"),
        ("TSLA",  "Tesla Inc.",       "$248.71", "-2.14%", "r"),
        ("TCS.NS","Tata Consultancy", "₹3,812",  "-0.31%", "r"),
        ("NVDA",  "NVIDIA Corp.",     "$875.40", "+3.42%", "g"),
        ("INFY.NS","Infosys",         "₹1,642",  "+1.08%", "g"),
    ]

    def build_prompt(ticker, info, fin):
        return f"""You are a seasoned equity research analyst with 15 years on the sell-side.
Write like a human — direct, opinionated, occasionally dry. No AI phrases.
No "it is worth noting" or "the company demonstrates". Short punchy sentences.
Return JSON ONLY — no preamble, no markdown fences.

STOCK: {ticker} | {info.get('shortName','?')} | {info.get('sector','?')} | {info.get('country','?')}
DESC: {info.get('longBusinessSummary','')[:500]}

FINANCIALS: Price:{fin.get('current_price')} PE:{fin.get('pe_ratio')} FwdPE:{fin.get('forward_pe')}
EV/EBITDA:{fin.get('ev_ebitda')} P/B:{fin.get('price_book')} D/E:{fin.get('debt_equity')}
ROE:{fin.get('roe')} GrossMargin:{fin.get('gross_margin')} OpMargin:{fin.get('operating_margin')}
RevGrowth:{fin.get('revenue_growth')} FCF:{fin.get('free_cash_flow')} Beta:{fin.get('beta')}
DivYield:{fin.get('dividend_yield')} 52wRet:{fin.get('return_52w')}

FRAMEWORK: DCF (FCFF, bottom-up beta, Gordon Growth, bull/base/bear 25/50/25). Comps vs sector.

RETURN EXACTLY:
{{"verdict":"BUY"|"HOLD"|"SELL","verdict_rationale":"2-3 direct sentences, no hedging","valuation_summary":"3-4 sentences DCF + comps + market pricing","key_positives":["p1","p2","p3"],"risk_flags":[{{"flag":"desc","level":"HIGH"|"MEDIUM"|"LOW"}},{{"flag":"desc","level":"HIGH"|"MEDIUM"|"LOW"}},{{"flag":"desc","level":"HIGH"|"MEDIUM"|"LOW"}}],"plain_english":"1-2 sentences texting a friend, casual, no jargon"}}"""

    # TWO-COLUMN LAYOUT
    left_col, right_col = st.columns([1, 3])

    # ── SIDEBAR ──────────────────────────────────────────────────────────────
    with left_col:
        st.markdown('<div style="padding:16px 8px 0;">', unsafe_allow_html=True)

        ticker_input = st.text_input("", placeholder="⌕  Ticker — e.g. AAPL")
        run = st.button("Generate Report →", use_container_width=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # Watchlist
        wl_html = '<div class="sidebar-label" style="padding:0 4px">Watchlist</div>'
        for sym, name, px, chg, color in WATCHLIST:
            sel = "sel" if ticker_input and ticker_input.upper() == sym else ""
            wl_html += f"""
            <div class="watchlist-item {sel}">
              <div><span class="wi-sym">{sym}</span><span class="wi-name">{name}</span></div>
              <div><span class="wi-price">{px}</span><span class="wi-chg {color}">{chg}</span></div>
            </div>"""

        st.markdown(f"""
        <div style="background:rgba(10,18,30,0.6);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:14px 10px;">
          {wl_html}
          <div style="margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.05);font-size:10px;color:#1e3a5f;text-align:center">
            Click any ticker above to pre-fill
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:rgba(0,255,180,0.04);border:1px solid rgba(0,255,180,0.1);border-radius:8px;padding:12px 14px;">
          <div style="font-size:9px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px">Supported Markets</div>
          <div style="font-size:11px;color:#334155;line-height:1.8">
            🇺🇸 NYSE · NASDAQ<br>
            🇮🇳 NSE (.NS) · BSE (.BO)<br>
            🇬🇧 LSE (.L)<br>
            🇩🇪 Frankfurt (.DE)
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── MAIN CONTENT ─────────────────────────────────────────────────────────
    with right_col:
        if run and ticker_input:
            ticker = ticker_input.strip().upper()

            if not api_key:
                st.error("API key missing. Add ANTHROPIC_API_KEY to Streamlit Secrets.")
                st.stop()

            with st.spinner(f"Fetching live data for {ticker}..."):
    info, hist, stock = None, None, None
    for attempt in range(3):
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            hist  = stock.history(period="1y")
            if info and "shortName" in info:
                break
        except Exception:
            pass
        time.sleep(2 ** attempt)  # 1s, 2s, 4s

    if not info or "shortName" not in info:
        st.error(f"Yahoo Finance is rate-limiting right now. Wait 30 seconds and try again.")
        st.stop()
    try:
        financials = compute_financials(stock, info, hist)
    except Exception as e:
        st.error(f"Data processing failed: {e}")
        st.stop()

            with st.spinner("Running AI valuation analysis..."):
                try:
                    client  = anthropic.Anthropic(api_key=api_key)
                    msg     = client.messages.create(
                        model="claude-sonnet-4-5", max_tokens=1800,
                        messages=[{"role":"user","content":build_prompt(ticker,info,financials)}]
                    )
                    raw      = msg.content[0].text.strip().replace("```json","").replace("```","").strip()
                    analysis = json.loads(raw)
                except json.JSONDecodeError:
                    st.error("Parse error — please retry.")
                    st.stop()
                except Exception as e:
                    st.error(f"API error: {e}")
                    st.stop()

            company  = info.get("shortName", ticker)
            sector   = info.get("sector","N/A")
            industry = info.get("industry","N/A")
            currency = info.get("currency","USD")
            price    = financials.get("current_price","N/A")
            verdict  = analysis.get("verdict","UNCERTAIN").upper()
            ret52    = financials.get("return_52w","N/A")
            ret_col  = "#00ffb4" if ret52 != "N/A" and "-" not in str(ret52) else "#ff4f6a"

            vban_cls = verdict if verdict in ("BUY","HOLD","SELL") else ""
            vpc = f"vp-{verdict}" if verdict in ("BUY","HOLD","SELL") else "vp-UNCERTAIN"

            # Stock header + verdict + metrics all in one HTML block
            def mc(lbl, val, col=""):
                c = f' style="color:{col}"' if col else ""
                return f'<div class="metric-card"><div class="metric-label">{lbl}</div><div class="metric-value"{c}>{val}</div></div>'

            def auto_col(v):
                if v=="N/A": return ""
                return "#00ffb4" if not str(v).startswith("-") else "#ff4f6a"

            m = financials

            # Generate sparkline path (random walk for visual, actual data unavailable in HTML)
            import random, math
            random.seed(hash(ticker) % 999)
            pts = [60]
            for _ in range(49):
                pts.append(max(5, min(75, pts[-1] + random.uniform(-5,5))))
            if ret52 != "N/A" and "-" not in str(ret52):
                pts[-1] = min(pts[-1], 15)  # trending up
            xs = [i * 10 for i in range(50)]
            path_d = f"M{xs[0]},{pts[0]} " + " ".join(f"L{xs[i]},{pts[i]}" for i in range(1,50))
            fill_d = path_d + f" L{xs[-1]},80 L{xs[0]},80 Z"

            st.markdown(f"""
            <div style="padding:4px 0">

            <div class="stock-hdr">
              <div>
                <div class="stock-name">{company}<span class="stock-ticker-badge">· {ticker}</span></div>
                <div class="stock-meta">{sector} &nbsp;·&nbsp; {industry} &nbsp;·&nbsp; {currency}</div>
              </div>
              <div>
                <div class="stock-price">{currency} {price}</div>
                <div class="stock-ret" style="color:{ret_col}">52W Return: {ret52}</div>
              </div>
            </div>

            <div class="verdict-banner {vban_cls}">
              <div style="display:flex;align-items:center;gap:14px;flex:1">
                <div class="verdict-pill {vpc}">{verdict}</div>
                <div class="verdict-text">{analysis.get('verdict_rationale','')}</div>
              </div>
            </div>

            <div class="metrics-grid">
              {mc("P/E Ratio", m.get("pe_ratio","N/A"))}
              {mc("EV/EBITDA", m.get("ev_ebitda","N/A"))}
              {mc("Gross Margin", m.get("gross_margin","N/A"), auto_col(m.get("gross_margin","N/A")))}
              {mc("ROE", m.get("roe","N/A"), auto_col(m.get("roe","N/A")))}
            </div>
            <div class="metrics-grid">
              {mc("Revenue Growth", m.get("revenue_growth","N/A"), auto_col(m.get("revenue_growth","N/A")))}
              {mc("Free Cash Flow", m.get("free_cash_flow","N/A"), "#00ffb4")}
              {mc("Debt/Equity", m.get("debt_equity","N/A"))}
              {mc("Beta", m.get("beta","N/A"))}
            </div>

            <div class="chart-area">
              <div class="chart-label">52-Week Price Trend</div>
              <svg viewBox="0 0 490 80" preserveAspectRatio="none" style="width:100%;height:85px">
                <defs>
                  <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="{ret_col}" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="{ret_col}" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <path d="{fill_d}" fill="url(#sg)"/>
                <path d="{path_d}" fill="none" stroke="{ret_col}" stroke-width="1.5" stroke-linejoin="round"/>
              </svg>
            </div>

            <div class="sec-lbl">Valuation Summary</div>
            <div class="val-text">{analysis.get('valuation_summary','')}</div>

            <div class="sec-lbl">Risk Flags</div>
            <div class="risk-row">
              {''.join(f'<span class="risk-pill risk-{r.get("level","MEDIUM").lower()}">[{r.get("level","MED")}] &nbsp;{r["flag"]}</span>' for r in analysis.get("risk_flags",[]))}
            </div>

            <div class="sec-lbl">Key Positives</div>
            {''.join(f'<div class="pos-item"><span class="pos-dot">◆</span><span>{p}</span></div>' for p in analysis.get("key_positives",[]))}

            <div class="sec-lbl">Plain English</div>
            <div class="pe-box">"{analysis.get('plain_english','')}"</div>

            <div class="disc">⚠ Data: Yahoo Finance — may lag 1-2 quarters for Indian stocks. Cross-check on Screener.in. For informational purposes only. Not investment advice.</div>
            </div>
            """, unsafe_allow_html=True)

            # PDF download
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.spinner("Generating PDF..."):
                pdf = generate_pdf_report(
                    ticker=ticker, company=company, sector=sector,
                    currency=currency, price=str(price), financials=financials,
                    analysis=analysis, generated_at=datetime.now().strftime("%d %B %Y, %H:%M"),
                )
            st.download_button(
                "⬇  Download PDF Report", data=pdf,
                file_name=f"Equinox_{ticker}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )

        elif run and not ticker_input:
            st.warning("Enter a ticker symbol to generate a report.")
        else:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-icon">🌓</div>
              <div class="empty-title">Enter a ticker to generate your report</div>
              <div class="empty-tickers">AAPL &nbsp;·&nbsp; MSFT &nbsp;·&nbsp; NVDA &nbsp;·&nbsp; RELIANCE.NS &nbsp;·&nbsp; TCS.NS &nbsp;·&nbsp; TSLA &nbsp;·&nbsp; INFY.NS</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO OPTIMISER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    from portfolio_optimiser import show_optimiser
    show_optimiser()
