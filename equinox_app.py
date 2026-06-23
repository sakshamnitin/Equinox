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

# ── Initialise session state ──────────────────────────────────────────────────
if "watchlist" not in st.session_state:
    st.session_state.watchlist = [
        {"sym": "AAPL",        "name": "Apple Inc.",         "price": "$189.42",  "chg": "+1.22%",  "up": True},
        {"sym": "MSFT",        "name": "Microsoft",          "price": "$415.30",  "chg": "+0.54%",  "up": True},
        {"sym": "RELIANCE.NS", "name": "Reliance Ind.",      "price": "₹2,941",   "chg": "+0.81%",  "up": True},
        {"sym": "TSLA",        "name": "Tesla Inc.",         "price": "$248.71",  "chg": "−2.14%",  "up": False},
        {"sym": "TCS.NS",      "name": "Tata Consultancy",   "price": "₹3,812",   "chg": "−0.31%",  "up": False},
    ]
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "AAPL"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "equity"
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "ticker_input_val" not in st.session_state:
    st.session_state.ticker_input_val = ""

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    background: #080d14 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    color: #e2e8f0 !important;
}
.block-container { padding: 0 !important; max-width: 100% !important; }

/* Grid background */
.stApp::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background-image:
        linear-gradient(rgba(0,255,180,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,180,0.025) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
}

/* ── Ticker tape ── */
.ticker-wrap {
    background: rgba(8,13,20,0.97);
    border-bottom: 1px solid rgba(0,255,180,0.12);
    padding: 10px 0; overflow: hidden;
}
.ticker-track {
    display: inline-flex; gap: 40px;
    animation: tickerScroll 35s linear infinite;
    white-space: nowrap;
}
@keyframes tickerScroll { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
.tick { display: inline-flex; align-items: center; gap: 8px; }
.tick-sym { color: #64748b; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 500; }
.tick-px  { color: #cbd5e1; font-family: 'JetBrains Mono'; font-size: 11px; }
.tick-up  { color: #00ffb4; font-family: 'JetBrains Mono'; font-size: 11px; }
.tick-dn  { color: #ff4f6a; font-family: 'JetBrains Mono'; font-size: 11px; }
.tick-sep { color: #1e293b; }

/* ── Navbar ── */
.eq-navbar {
    background: rgba(8,13,20,0.98);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 0 28px; height: 56px;
    display: flex; align-items: center; justify-content: space-between;
}
.eq-logo-icon {
    width: 30px; height: 30px;
    background: linear-gradient(135deg, #00ffb4, #0066ff);
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 800; color: #080d14;
    margin-right: 10px;
}
.eq-logo-text {
    font-size: 18px; font-weight: 700; letter-spacing: 1px;
    background: linear-gradient(135deg, #00ffb4 0%, #60a5fa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.eq-logo-wrap { display: flex; align-items: center; }
.eq-tagline { color: #334155; font-size: 11px; margin-left: 4px; }
.live-badge {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(0,255,180,0.07);
    border: 1px solid rgba(0,255,180,0.18);
    border-radius: 999px; padding: 5px 14px;
    font-size: 11px; font-weight: 600; color: #00ffb4; letter-spacing: 1px;
}
.live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #00ffb4; box-shadow: 0 0 8px #00ffb4;
    animation: livepulse 2s ease-in-out infinite;
}
@keyframes livepulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }

/* ── Tab bar ── */
.eq-tabbar {
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 0 28px;
    display: flex; gap: 0;
}
.eq-tab {
    padding: 12px 24px; font-size: 13px; font-weight: 500;
    color: #475569; cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s; letter-spacing: 0.3px;
    text-decoration: none;
}
.eq-tab.on { color: #00ffb4; border-bottom-color: #00ffb4; }

/* ── Two-panel layout ── */
.eq-layout {
    display: grid;
    grid-template-columns: 272px 1fr;
    min-height: calc(100vh - 120px);
}
.eq-sidebar {
    background: rgba(8,13,20,0.85);
    border-right: 1px solid rgba(255,255,255,0.05);
    padding: 20px 16px;
}
.eq-main { padding: 22px 28px; }

/* ── Sidebar elements ── */
.sb-label {
    font-size: 10px; font-weight: 600; color: #334155;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 10px;
}
.wl-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 10px; border-radius: 7px; cursor: pointer;
    border: 1px solid transparent;
    transition: background 0.15s; margin-bottom: 3px;
}
.wl-item:hover { background: rgba(255,255,255,0.04); }
.wl-item.sel { background: rgba(0,255,180,0.07); border-color: rgba(0,255,180,0.15); }
.wl-sym { font-size: 13px; font-weight: 600; color: #e2e8f0; }
.wl-name { font-size: 10px; color: #334155; margin-top: 1px; }
.wl-price { font-family: 'JetBrains Mono'; font-size: 12px; color: #cbd5e1; text-align: right; }
.wl-chg { font-family: 'JetBrains Mono'; font-size: 10px; text-align: right; }
.wl-up { color: #00ffb4; }
.wl-dn { color: #ff4f6a; }

/* ── Search ── */
.search-wrap {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 9px 13px;
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 14px;
}
.search-icon { color: #334155; font-size: 14px; }

/* ── Generate button (streamlit) ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono' !important;
    font-size: 13px !important;
    padding: 10px 14px !important;
    caret-color: #00ffb4 !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0,255,180,0.35) !important;
    box-shadow: 0 0 0 2px rgba(0,255,180,0.08) !important;
}
.stTextInput > div > div > input::placeholder { color: #334155 !important; }
.stButton > button {
    background: linear-gradient(135deg, rgba(0,255,180,0.12), rgba(0,102,255,0.12)) !important;
    border: 1px solid rgba(0,255,180,0.28) !important;
    border-radius: 8px !important; color: #00ffb4 !important;
    font-family: 'Space Grotesk' !important; font-size: 13px !important;
    font-weight: 600 !important; letter-spacing: 0.5px !important;
    padding: 10px 20px !important; width: 100% !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,255,180,0.22), rgba(0,102,255,0.22)) !important;
    border-color: rgba(0,255,180,0.5) !important;
}
.stDownloadButton > button {
    background: linear-gradient(135deg, rgba(0,255,180,0.08), rgba(0,102,255,0.08)) !important;
    border: 1px solid rgba(0,255,180,0.2) !important;
    border-radius: 8px !important; color: #00ffb4 !important;
    font-family: 'Space Grotesk' !important; font-weight: 600 !important;
    width: 100% !important;
}
.stSpinner > div { border-top-color: #00ffb4 !important; }
.stAlert { background: rgba(255,79,106,0.07) !important; border: 1px solid rgba(255,79,106,0.22) !important; border-radius: 8px !important; color: #ff4f6a !important; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
div[data-testid="stCaption"] { color: #334155 !important; font-size: 11px !important; }

/* Streamlit tab override — hide since we use our own tabbar */
.stTabs [data-baseweb="tab-list"] { display: none !important; }

/* ── Content area elements ── */
.stock-hdr {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 20px;
}
.stock-name { font-size: 22px; font-weight: 700; color: #f1f5f9; }
.stock-badge { font-size: 13px; color: #475569; font-weight: 400; margin-left: 8px; }
.stock-sector { font-size: 11px; color: #334155; margin-top: 4px; }
.price-main { font-family: 'JetBrains Mono'; font-size: 28px; font-weight: 600; color: #f1f5f9; text-align:right; }
.price-sub  { font-family: 'JetBrains Mono'; font-size: 12px; color: #64748b; margin-top: 3px; text-align:right; }

.verdict-banner {
    display: flex; justify-content: space-between; align-items: center;
    background: rgba(0,255,180,0.05);
    border: 1px solid rgba(0,255,180,0.15);
    border-left: 4px solid #00ffb4;
    border-radius: 10px; padding: 16px 20px;
    margin-bottom: 20px;
}
.verdict-banner.v-HOLD { background: rgba(251,191,36,0.05); border-color: rgba(251,191,36,0.15); border-left-color: #fbbf24; }
.verdict-banner.v-SELL { background: rgba(255,79,106,0.05); border-color: rgba(255,79,106,0.15); border-left-color: #ff4f6a; }
.verdict-banner.v-UNCERTAIN { background: rgba(100,116,139,0.05); border-color: rgba(100,116,139,0.15); border-left-color: #64748b; }
.vpill {
    display: inline-block; padding: 4px 16px; border-radius: 999px;
    font-size: 11px; font-weight: 700; letter-spacing: 2px;
    margin-bottom: 8px;
}
.vp-BUY  { background: rgba(0,255,180,0.12); border: 1px solid rgba(0,255,180,0.35); color: #00ffb4; }
.vp-HOLD { background: rgba(251,191,36,0.1);  border: 1px solid rgba(251,191,36,0.35); color: #fbbf24; }
.vp-SELL { background: rgba(255,79,106,0.1);  border: 1px solid rgba(255,79,106,0.35); color: #ff4f6a; }
.vp-UNCERTAIN { background: rgba(100,116,139,0.1); border: 1px solid #64748b; color: #94a3b8; }
.verdict-txt { font-size: 13px; color: #94a3b8; line-height: 1.65; max-width: 480px; }

.metrics-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
    margin-bottom: 18px;
}
.mcard {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 9px; padding: 13px 14px;
    transition: border-color 0.2s;
}
.mcard:hover { border-color: rgba(0,255,180,0.18); }
.mc-label { font-size: 9px; font-weight: 600; color: #334155; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 7px; }
.mc-val   { font-family: 'JetBrains Mono'; font-size: 16px; font-weight: 500; color: #e2e8f0; }
.mc-val.pos { color: #00ffb4; }
.mc-val.neg { color: #ff4f6a; }

.chart-area {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px; padding: 16px;
    margin-bottom: 16px; position: relative; overflow: hidden;
}
.chart-lbl { font-size: 9px; font-weight: 600; color: #334155; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 10px; }

.sec-hdr {
    font-size: 10px; font-weight: 600; color: #334155;
    text-transform: uppercase; letter-spacing: 1.5px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    padding-bottom: 8px; margin: 18px 0 12px;
}
.risk-row { display: flex; flex-wrap: wrap; gap: 7px; }
.rpill { padding: 5px 13px; border-radius: 999px; font-size: 11px; font-weight: 600; letter-spacing: 0.3px; }
.rH { background: rgba(255,79,106,0.09); border: 1px solid rgba(255,79,106,0.28); color: #ff4f6a; }
.rM { background: rgba(251,191,36,0.09); border: 1px solid rgba(251,191,36,0.28); color: #fbbf24; }
.rL { background: rgba(0,255,180,0.07);  border: 1px solid rgba(0,255,180,0.22);  color: #00ffb4; }
.pos-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
    font-size: 13px; color: #94a3b8; line-height: 1.6;
}
.pos-dot { color: #00ffb4; font-size: 14px; flex-shrink: 0; margin-top: 1px; }
.pe-box {
    background: rgba(0,102,255,0.05);
    border: 1px solid rgba(0,102,255,0.18);
    border-radius: 9px; padding: 14px 18px;
    font-size: 14px; color: #93c5fd; line-height: 1.7; font-style: italic;
}
.disc { font-size: 11px; color: #1e293b; margin-top: 20px; line-height: 1.6; }
.empty-state {
    text-align: center; padding: 80px 20px; color: #1e293b;
}
.empty-moon { font-size: 52px; margin-bottom: 18px; }
.empty-title { font-size: 17px; color: #334155; font-weight: 500; margin-bottom: 8px; }
.empty-hint  { font-size: 12px; color: #1e293b; font-family: 'JetBrains Mono'; }
</style>
""", unsafe_allow_html=True)


# ── Ticker tape ───────────────────────────────────────────────────────────────
TICKERS_TAPE = [
    ("AAPL","$189.42","+1.22%","up"), ("RELIANCE.NS","₹2,941","+0.81%","up"),
    ("MSFT","$415.30","+0.54%","up"), ("TCS.NS","₹3,812","−0.31%","dn"),
    ("TSLA","$248.71","−2.14%","dn"), ("NVDA","$875.40","+3.42%","up"),
    ("INFY.NS","₹1,642","+1.08%","up"), ("GOOGL","$175.98","+0.71%","up"),
    ("HDFC.NS","₹1,823","+0.45%","up"), ("AMZN","$192.45","+1.33%","up"),
    ("META","$527.30","+0.98%","up"), ("WIPRO.NS","₹480","−0.62%","dn"),
]

def ticker_html():
    items = ""
    for sym, px, chg, d in TICKERS_TAPE * 2:
        cls = "tick-up" if d=="up" else "tick-dn"
        arr = "▲" if d=="up" else "▼"
        items += f'<span class="tick"><span class="tick-sym">{sym}</span><span class="tick-px">{px}</span><span class="{cls}">{arr} {chg}</span></span><span class="tick-sep">·</span>'
    return f'<div class="ticker-wrap"><div class="ticker-track">{items}</div></div>'

st.markdown(ticker_html(), unsafe_allow_html=True)


# ── Navbar ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="eq-navbar">
  <div style="display:flex;align-items:center;gap:16px;">
    <div class="eq-logo-wrap">
      <div class="eq-logo-icon">E</div>
      <span class="eq-logo-text">EQUINOX</span>
    </div>
    <span class="eq-tagline">Investment Intelligence &nbsp;·&nbsp; Research · Optimise · Monitor</span>
  </div>
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="font-family:'JetBrains Mono';font-size:11px;color:#334155">{datetime.now().strftime('%d %b %Y  %H:%M')}</span>
    <div class="live-badge"><div class="live-dot"></div>LIVE</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── API key ───────────────────────────────────────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
if not api_key:
    with st.sidebar:
        st.markdown("#### 🔑 API Key")
        api_key = st.text_input("Anthropic API Key", type="password", label_visibility="collapsed")


# ── Tab state via query params / buttons ──────────────────────────────────────
tab_labels = {"equity": "📊  Equity Research", "portfolio": "📐  Portfolio Optimiser"}
active = st.session_state.active_tab

tab_html = '<div class="eq-tabbar">'
for key, label in tab_labels.items():
    cls = "eq-tab on" if key == active else "eq-tab"
    tab_html += f'<div class="{cls}" onclick="">{label}</div>'
tab_html += '</div>'
st.markdown(tab_html, unsafe_allow_html=True)

# Real tab switching via st.tabs (hidden via CSS, used for layout control)
real_tab1, real_tab2 = st.tabs(["Equity Research", "Portfolio Optimiser"])

# Tab switch buttons (minimal, below tabbar)
_tc1, _tc2, _tc3 = st.columns([1,1,8])
with _tc1:
    if st.button("Equity Research", key="sw_equity"):
        st.session_state.active_tab = "equity"
        st.rerun()
with _tc2:
    if st.button("Portfolio Optimiser", key="sw_portfolio"):
        st.session_state.active_tab = "portfolio"
        st.rerun()

st.markdown("""
<style>
/* hide the tab-switch helper buttons visually */
div[data-testid="stHorizontalBlock"]:has(button[kind="secondary"]) {
    position: absolute; opacity: 0; pointer-events: none; height: 0; overflow: hidden;
}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EQUITY RESEARCH  (sidebar + main panel)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.active_tab == "equity":

    def build_prompt(ticker, info, fin):
        return f"""You are a seasoned equity research analyst with 15 years on the sell-side.
Write like a human — direct, opinionated, occasionally dry. Zero corporate fluff.
No phrases like "it is worth noting" or "the company demonstrates".
Short punchy sentences. Say what you actually think.
Brief a smart colleague over coffee, not filing a report.
Return JSON ONLY — no preamble, no markdown fences.

COMPANY: {ticker} | {info.get('shortName','?')} | {info.get('sector','?')} | {info.get('country','?')}
DESC: {info.get('longBusinessSummary','')[:500]}

FINANCIALS:
Price:{fin.get('current_price')} PE:{fin.get('pe_ratio')} FwdPE:{fin.get('forward_pe')} EV/EBITDA:{fin.get('ev_ebitda')}
P/B:{fin.get('price_book')} P/S:{fin.get('price_sales')} D/E:{fin.get('debt_equity')} CurrentRatio:{fin.get('current_ratio')}
ROE:{fin.get('roe')} ROA:{fin.get('roa')} GrossMargin:{fin.get('gross_margin')} OpMargin:{fin.get('operating_margin')}
RevGrowth:{fin.get('revenue_growth')} EarningsGrowth:{fin.get('earnings_growth')} FCF:{fin.get('free_cash_flow')}
DivYield:{fin.get('dividend_yield')} Beta:{fin.get('beta')} 52wHi:{fin.get('week52_high')} 52wLo:{fin.get('week52_low')} 52wRet:{fin.get('return_52w')}

FRAMEWORK: DCF (FCFF, bottom-up beta, Gordon Growth terminal value, bull/base/bear 25/50/25).
Comparable multiples vs sector peers. Flag cheap/fair/expensive.

RETURN EXACTLY:
{{"verdict":"BUY"|"HOLD"|"SELL","verdict_rationale":"2-3 sentences, direct, no hedging","valuation_summary":"3-4 sentences DCF + comps + what market prices in","key_positives":["p1","p2","p3"],"risk_flags":[{{"flag":"desc","level":"HIGH"|"MEDIUM"|"LOW"}},{{"flag":"desc","level":"HIGH"|"MEDIUM"|"LOW"}},{{"flag":"desc","level":"HIGH"|"MEDIUM"|"LOW"}}],"plain_english":"1-2 sentences texting a friend, casual, no jargon"}}"""

    # ── Two-panel grid ────────────────────────────────────────────────────────
    st.markdown('<div class="eq-layout">', unsafe_allow_html=True)

    # Sidebar column
    sidebar_col, main_col = st.columns([272, 900], gap="small")

    with sidebar_col:
        st.markdown('<div class="eq-sidebar">', unsafe_allow_html=True)

        # Search box
        ticker_input = st.text_input(
            "", placeholder="⌕  Ticker — e.g. AAPL",
            label_visibility="collapsed",
            key="ticker_search"
        )

        run = st.button("⚡  Generate Report", use_container_width=True)

        # Watchlist
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-label">Watchlist</div>', unsafe_allow_html=True)

        wl_html = ""
        for item in st.session_state.watchlist:
            sel = "sel" if item["sym"] == st.session_state.selected_ticker else ""
            chg_cls = "wl-up" if item["up"] else "wl-dn"
            wl_html += f"""
            <div class="wl-item {sel}">
              <div>
                <div class="wl-sym">{item['sym']}</div>
                <div class="wl-name">{item['name']}</div>
              </div>
              <div>
                <div class="wl-price">{item['price']}</div>
                <div class="wl-chg {chg_cls}">{item['chg']}</div>
              </div>
            </div>"""
        st.markdown(wl_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with main_col:
        st.markdown('<div class="eq-main">', unsafe_allow_html=True)

        # ── Handle run ────────────────────────────────────────────────────────
        if run and ticker_input:
            ticker = ticker_input.strip().upper()

            if not api_key:
                st.error("API key missing — add it in the sidebar.")
                st.stop()

            with st.spinner(f"Pulling live data for {ticker}..."):
                try:
                    time.sleep(0.5)
                    stock = yf.Ticker(ticker)
                    info  = stock.info
                    hist  = stock.history(period="1y")
                    if not info or "shortName" not in info:
                        st.error(f"No data found for `{ticker}`. Check the symbol.")
                        st.stop()
                    financials = compute_financials(stock, info, hist)
                except Exception as e:
                    st.error(f"Data fetch failed: {e}")
                    st.stop()

            with st.spinner("Running valuation analysis..."):
                try:
                    client  = anthropic.Anthropic(api_key=api_key)
                    message = client.messages.create(
                        model="claude-sonnet-4-5", max_tokens=1800,
                        messages=[{"role":"user","content":build_prompt(ticker, info, financials)}]
                    )
                    raw      = message.content[0].text
                    raw      = raw.strip().replace("```json","").replace("```","").strip()
                    analysis = json.loads(raw)
                    st.session_state.last_result = {
                        "ticker": ticker, "info": info,
                        "financials": financials, "analysis": analysis
                    }
                    st.session_state.selected_ticker = ticker
                    # Add to watchlist if not present
                    syms = [w["sym"] for w in st.session_state.watchlist]
                    if ticker not in syms:
                        price_val = financials.get("current_price","—")
                        currency  = info.get("currency","USD")
                        sym_c     = "₹" if currency=="INR" else "$"
                        verdict   = analysis.get("verdict","?")
                        is_up     = verdict in ("BUY","HOLD")
                        st.session_state.watchlist.insert(0, {
                            "sym": ticker,
                            "name": info.get("shortName", ticker)[:20],
                            "price": f"{sym_c}{price_val}",
                            "chg": f"{financials.get('return_52w','—')}",
                            "up": is_up,
                        })
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Parse error — please retry.")
                    st.stop()
                except Exception as e:
                    st.error(f"API error: {e}")
                    st.stop()

        elif run and not ticker_input:
            st.warning("Enter a ticker symbol first.")

        # ── Render result or empty state ──────────────────────────────────────
        res = st.session_state.last_result

        if res:
            info       = res["info"]
            financials = res["financials"]
            analysis   = res["analysis"]
            ticker     = res["ticker"]

            company  = info.get("shortName", ticker)
            sector   = info.get("sector","N/A")
            industry = info.get("industry","N/A")
            currency = info.get("currency","USD")
            price    = financials.get("current_price","—")
            verdict  = analysis.get("verdict","UNCERTAIN").upper()
            ret_52w  = financials.get("return_52w","")
            ret_col  = "#00ffb4" if ret_52w and "−" not in ret_52w and "-" not in ret_52w else "#ff4f6a"

            # Stock header
            st.markdown(f"""
            <div class="stock-hdr">
              <div>
                <div class="stock-name">{company}<span class="stock-badge">{ticker} · {info.get("exchange","")}</span></div>
                <div class="stock-sector">{sector} · {industry} · {currency}</div>
              </div>
              <div>
                <div class="price-main">{currency} {price}</div>
                <div class="price-sub" style="color:{ret_col}">52W: {ret_52w}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Verdict banner
            vb_cls = f"v-{verdict}" if verdict in ("BUY","HOLD","SELL") else "v-UNCERTAIN"
            vp_cls = f"vp-{verdict}" if verdict in ("BUY","HOLD","SELL") else "vp-UNCERTAIN"
            st.markdown(f"""
            <div class="verdict-banner {vb_cls}">
              <div>
                <div class="vpill {vp_cls}">{verdict}</div>
                <div class="verdict-txt">{analysis.get('verdict_rationale','')}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Metrics grid — all 12 in 3 rows of 4
            m = financials
            def is_pos(v):
                if v in ("N/A", None): return ""
                return "pos" if not str(v).startswith("-") and "−" not in str(v) else "neg"

            all_metrics = [
                ("P/E Ratio",      m.get("pe_ratio","N/A"),       ""),
                ("EV / EBITDA",    m.get("ev_ebitda","N/A"),      ""),
                ("Debt / Equity",  m.get("debt_equity","N/A"),    ""),
                ("Current Ratio",  m.get("current_ratio","N/A"),  ""),
                ("Revenue Growth", m.get("revenue_growth","N/A"), is_pos(m.get("revenue_growth",""))),
                ("Gross Margin",   m.get("gross_margin","N/A"),   is_pos(m.get("gross_margin",""))),
                ("ROE",            m.get("roe","N/A"),             is_pos(m.get("roe",""))),
                ("Free Cash Flow", m.get("free_cash_flow","N/A"), "pos"),
                ("Dividend Yield", m.get("dividend_yield","N/A"), ""),
                ("Beta",           m.get("beta","N/A"),            ""),
                ("52W High",       m.get("week52_high","N/A"),    ""),
                ("52W Low",        m.get("week52_low","N/A"),     ""),
            ]

            grid_html = '<div class="metrics-grid">'
            for label, val, color in all_metrics:
                grid_html += f'<div class="mcard"><div class="mc-label">{label}</div><div class="mc-val {color}">{val}</div></div>'
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)

            # Sparkline chart
            st.markdown("""
            <div class="chart-area">
              <div class="chart-lbl">52-week price trend</div>
              <svg viewBox="0 0 500 72" style="width:100%;height:72px;" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#00ffb4" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="#00ffb4" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <path d="M0,65 C30,60 50,66 80,55 C110,44 130,52 160,42 C190,32 210,38 240,26 C270,14 290,30 320,22 C350,14 370,8 400,10 C430,12 460,5 500,2 L500,72 L0,72 Z" fill="url(#sg)"/>
                <path d="M0,65 C30,60 50,66 80,55 C110,44 130,52 160,42 C190,32 210,38 240,26 C270,14 290,30 320,22 C350,14 370,8 400,10 C430,12 460,5 500,2" fill="none" stroke="#00ffb4" stroke-width="1.5"/>
              </svg>
            </div>
            """, unsafe_allow_html=True)

            # Risk + Positives side by side
            col_l, col_r = st.columns(2, gap="large")

            with col_l:
                st.markdown('<div class="sec-hdr">Risk Flags</div>', unsafe_allow_html=True)
                risk_html = '<div class="risk-row">'
                for r in analysis.get("risk_flags", []):
                    lv = r.get("level","MEDIUM").upper()
                    rc = {"HIGH":"rH","MEDIUM":"rM","LOW":"rL"}.get(lv,"rM")
                    risk_html += f'<span class="rpill {rc}">[{lv}] {r["flag"]}</span>'
                risk_html += '</div>'
                st.markdown(risk_html, unsafe_allow_html=True)

            with col_r:
                st.markdown('<div class="sec-hdr">Key Positives</div>', unsafe_allow_html=True)
                for p in analysis.get("key_positives", []):
                    st.markdown(f'<div class="pos-item"><span class="pos-dot">◆</span><span>{p}</span></div>', unsafe_allow_html=True)

            # Valuation summary
            st.markdown('<div class="sec-hdr">Valuation Summary</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:13px;color:#94a3b8;line-height:1.8'>{analysis.get('valuation_summary','')}</div>", unsafe_allow_html=True)

            # Plain English
            st.markdown('<div class="sec-hdr">Plain English</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="pe-box">"{analysis.get("plain_english","")}"</div>', unsafe_allow_html=True)

            # Disclaimer
            st.markdown('<div class="disc">⚠ Data sourced from Yahoo Finance — may lag 1-2 quarters for Indian stocks. Cross-check on Screener.in. This report is for informational purposes only and does not constitute investment advice.</div>', unsafe_allow_html=True)

            # PDF download
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            with st.spinner("Preparing PDF..."):
                pdf = generate_pdf_report(
                    ticker=ticker, company=company, sector=sector,
                    currency=currency, price=str(price), financials=financials,
                    analysis=analysis, generated_at=datetime.now().strftime("%d %B %Y, %H:%M"),
                )
            st.download_button(
                "⬇  Download PDF Report", data=pdf,
                file_name=f"Equinox_{ticker}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf", use_container_width=True,
            )

        else:
            st.markdown("""
            <div class="empty-state">
              <div class="empty-moon">🌓</div>
              <div class="empty-title">Enter a ticker to generate your report</div>
              <div class="empty-hint">AAPL · MSFT · RELIANCE.NS · TCS.NS · NVDA · GOOGL</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # eq-main

    st.markdown('</div>', unsafe_allow_html=True)  # eq-layout


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO OPTIMISER
# ══════════════════════════════════════════════════════════════════════════════
else:
    from portfolio_optimiser import show_optimiser
    st.markdown("""
    <style>
    /* Re-expose streamlit elements for portfolio tab */
    div[data-testid="stMarkdownContainer"] h3 { color: #e2e8f0 !important; }
    .stDataFrame { background: rgba(255,255,255,0.02) !important; border-radius: 8px !important; }
    div[data-baseweb="select"] { background: rgba(255,255,255,0.04) !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div style="padding: 24px 28px;">', unsafe_allow_html=True)
        show_optimiser()
        st.markdown('</div>', unsafe_allow_html=True)
