import streamlit as st
import yfinance as yf
import anthropic
import json
import time
import random
from datetime import datetime
from report_generator import generate_pdf_report
from financial_engine import compute_financials

st.set_page_config(
    page_title="Equinox — Investment Intelligence",
    page_icon="🌓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

/* Ticker tape */
.ticker-wrap {
    background: rgba(8,13,20,0.97);
    border-bottom: 1px solid rgba(0,255,180,0.12);
    padding: 10px 0;
    overflow: hidden;
    position: relative;
}
.ticker-track {
    display: inline-flex; gap: 40px;
    animation: tickerScroll 35s linear infinite;
    white-space: nowrap;
}
@keyframes tickerScroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
.tick { display: inline-flex; align-items: center; gap: 8px; }
.tick-sym { color: #64748b; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 500; }
.tick-px  { color: #cbd5e1; font-family: 'JetBrains Mono'; font-size: 11px; }
.tick-up  { color: #00ffb4; font-family: 'JetBrains Mono'; font-size: 11px; }
.tick-dn  { color: #ff4f6a; font-family: 'JetBrains Mono'; font-size: 11px; }
.tick-sep { color: #1e293b; }

/* Top navbar */
.eq-navbar {
    background: rgba(8,13,20,0.98);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 14px 28px;
    display: flex; align-items: center; justify-content: space-between;
}
.eq-logo {
    font-family: 'Space Grotesk'; font-size: 22px; font-weight: 700;
    background: linear-gradient(135deg, #00ffb4 0%, #60a5fa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 1px;
}
.eq-tagline { color: #475569; font-size: 12px; margin-top: 2px; }
.live-badge {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(0,255,180,0.08);
    border: 1px solid rgba(0,255,180,0.2);
    border-radius: 999px; padding: 5px 14px;
    font-size: 11px; font-weight: 600; color: #00ffb4; letter-spacing: 1px;
}
.live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #00ffb4; box-shadow: 0 0 8px #00ffb4;
    animation: livepulse 2s ease-in-out infinite;
}
@keyframes livepulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }

/* Module tabs */
.eq-tabs {
    display: flex; gap: 0;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 0 28px;
}
.eq-tab {
    padding: 12px 24px; font-size: 13px; font-weight: 500;
    color: #475569; cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s; letter-spacing: 0.3px;
}
.eq-tab.on { color: #00ffb4; border-bottom-color: #00ffb4; }

/* Input area */
.input-zone {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
}

/* Metric cards */
.mcard {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 16px;
    transition: border-color 0.2s;
}
.mcard:hover { border-color: rgba(0,255,180,0.2); }
.mcard-label {
    font-size: 10px; font-weight: 600; color: #475569;
    text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px;
}
.mcard-value {
    font-family: 'JetBrains Mono'; font-size: 18px; font-weight: 500; color: #e2e8f0;
}
.mcard-value.pos { color: #00ffb4; }
.mcard-value.neg { color: #ff4f6a; }

/* Verdict */
.verdict-wrap {
    border-radius: 12px; padding: 18px 22px;
    margin: 20px 0;
    border-left: 4px solid;
}
.v-BUY  { background: rgba(0,255,180,0.06); border-color: #00ffb4; }
.v-HOLD { background: rgba(251,191,36,0.06); border-color: #fbbf24; }
.v-SELL { background: rgba(255,79,106,0.06); border-color: #ff4f6a; }
.v-UNCERTAIN { background: rgba(100,116,139,0.06); border-color: #64748b; }

.verdict-pill {
    display: inline-block;
    padding: 4px 18px; border-radius: 999px;
    font-size: 12px; font-weight: 700; letter-spacing: 2px;
    margin-bottom: 10px;
}
.vp-BUY  { background: rgba(0,255,180,0.15); border: 1px solid rgba(0,255,180,0.4); color: #00ffb4; }
.vp-HOLD { background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.4); color: #fbbf24; }
.vp-SELL { background: rgba(255,79,106,0.12); border: 1px solid rgba(255,79,106,0.4); color: #ff4f6a; }
.vp-UNCERTAIN { background: rgba(100,116,139,0.1); border: 1px solid #64748b; color: #94a3b8; }

.verdict-rationale { font-size: 14px; color: #cbd5e1; line-height: 1.7; }

/* Risk pills */
.risk-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.rpill {
    padding: 5px 14px; border-radius: 999px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.5px;
}
.rH { background: rgba(255,79,106,0.1); border: 1px solid rgba(255,79,106,0.3); color: #ff4f6a; }
.rM { background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); color: #fbbf24; }
.rL { background: rgba(0,255,180,0.08); border: 1px solid rgba(0,255,180,0.25); color: #00ffb4; }

/* Section headers */
.sec-hdr {
    font-size: 11px; font-weight: 600; color: #475569;
    text-transform: uppercase; letter-spacing: 1.5px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding-bottom: 8px; margin: 20px 0 14px;
}

/* Positives */
.pos-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 13px; color: #94a3b8; line-height: 1.6;
}
.pos-dot { color: #00ffb4; font-size: 16px; flex-shrink: 0; }

/* Plain English box */
.pe-box {
    background: rgba(0,102,255,0.06);
    border: 1px solid rgba(0,102,255,0.2);
    border-radius: 10px; padding: 16px 20px;
    font-size: 14px; color: #93c5fd; line-height: 1.7;
    font-style: italic; margin: 16px 0;
}

/* Disclaimer */
.disc { font-size: 11px; color: #334155; margin-top: 20px; line-height: 1.6; }

/* Stock header */
.stock-hdr {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 20px 0 16px; border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 20px;
}
.stock-name { font-size: 24px; font-weight: 700; color: #f1f5f9; }
.stock-ticker { font-size: 14px; color: #475569; font-weight: 400; margin-left: 8px; }
.stock-sector { font-size: 12px; color: #475569; margin-top: 4px; }
.price-block { text-align: right; }
.price-main { font-family: 'JetBrains Mono'; font-size: 30px; font-weight: 600; color: #f1f5f9; }
.price-sub { font-family: 'JetBrains Mono'; font-size: 12px; color: #64748b; margin-top: 3px; }

/* Download btn */
.dl-btn {
    background: linear-gradient(135deg, rgba(0,255,180,0.1), rgba(0,102,255,0.1));
    border: 1px solid rgba(0,255,180,0.25);
    border-radius: 8px; color: #00ffb4;
    padding: 10px 24px; font-size: 13px; font-weight: 600;
    cursor: pointer; width: 100%; margin-top: 16px;
    font-family: 'Space Grotesk';
}

/* Streamlit overrides */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono' !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0,255,180,0.4) !important;
    box-shadow: 0 0 0 2px rgba(0,255,180,0.1) !important;
}
.stButton > button {
    background: linear-gradient(135deg, rgba(0,255,180,0.12), rgba(0,102,255,0.12)) !important;
    border: 1px solid rgba(0,255,180,0.3) !important;
    border-radius: 8px !important;
    color: #00ffb4 !important;
    font-family: 'Space Grotesk' !important;
    font-size: 13px !important; font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    padding: 10px 24px !important; width: 100% !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,255,180,0.22), rgba(0,102,255,0.22)) !important;
    border-color: rgba(0,255,180,0.5) !important;
}
.stDownloadButton > button {
    background: linear-gradient(135deg, rgba(0,255,180,0.1), rgba(0,102,255,0.1)) !important;
    border: 1px solid rgba(0,255,180,0.25) !important;
    border-radius: 8px !important; color: #00ffb4 !important;
    font-family: 'Space Grotesk' !important; font-weight: 600 !important;
    width: 100% !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.02) !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    gap: 0 !important; padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #475569 !important;
    font-family: 'Space Grotesk' !important; font-size: 13px !important;
    font-weight: 500 !important; padding: 14px 28px !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #00ffb4 !important;
    border-bottom: 2px solid #00ffb4 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stSpinner > div { border-top-color: #00ffb4 !important; }
.stAlert { background: rgba(255,79,106,0.08) !important; border: 1px solid rgba(255,79,106,0.25) !important; border-radius: 8px !important; color: #ff4f6a !important; }
div[data-testid="stCaption"] { color: #334155 !important; font-size: 11px !important; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Ticker tape ───────────────────────────────────────────────────────────────
TICKERS = [
    ("AAPL","$189.42","+1.22%","up"), ("RELIANCE.NS","₹2,941","+0.81%","up"),
    ("MSFT","$415.30","+0.54%","up"), ("TCS.NS","₹3,812","-0.31%","dn"),
    ("TSLA","$248.71","-2.14%","dn"), ("NVDA","$875.40","+3.42%","up"),
    ("INFY.NS","₹1,642","+1.08%","up"), ("GOOGL","$175.98","+0.71%","up"),
    ("HDFC.NS","₹1,823","+0.45%","up"), ("AMZN","$192.45","+1.33%","up"),
    ("META","$527.30","+0.98%","up"), ("WIPRO.NS","₹480","-0.62%","dn"),
]

def ticker_html():
    items = ""
    for sym, px, chg, d in TICKERS * 2:
        cls = "tick-up" if d=="up" else "tick-dn"
        arr = "▲" if d=="up" else "▼"
        items += f'<span class="tick"><span class="tick-sym">{sym}</span><span class="tick-px">{px}</span><span class="{cls}">{arr} {chg}</span></span><span class="tick-sep">|</span>'
    return f'<div class="ticker-wrap"><div class="ticker-track">{items}</div></div>'

st.markdown(ticker_html(), unsafe_allow_html=True)

# ── Navbar ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="eq-navbar">
  <div>
    <div class="eq-logo">🌓 EQUINOX</div>
    <div class="eq-tagline">Investment Intelligence Platform &nbsp;·&nbsp; Research · Optimise · Monitor Risk</div>
  </div>
  <div class="live-badge"><div class="live-dot"></div>LIVE DATA</div>
</div>
""", unsafe_allow_html=True)

# ── API key ───────────────────────────────────────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
if not api_key:
    with st.sidebar:
        api_key = st.text_input("Anthropic API Key", type="password")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊  Equity Research", "📐  Portfolio Optimiser"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EQUITY RESEARCH
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

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

    # Input row
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        ticker_input = st.text_input("", placeholder="Enter ticker — e.g. AAPL · RELIANCE.NS · TCS.NS · MSFT",
                                      label_visibility="collapsed")
    with c2:
        run = st.button("⚡  Generate Report", use_container_width=True)
    with c3:
        st.markdown(f"<div style='padding:10px 0;font-size:11px;color:#475569;font-family:JetBrains Mono'>{datetime.now().strftime('%d %b %Y %H:%M')}</div>", unsafe_allow_html=True)

    st.markdown("<div style='font-size:11px;color:#334155;margin-bottom:16px'>Supports NSE (.NS) · BSE (.BO) · NYSE · NASDAQ · LSE · Frankfurt · Yahoo Finance data</div>", unsafe_allow_html=True)

    if run and ticker_input:
        ticker = ticker_input.strip().upper()

        if not api_key:
            st.markdown('<div class="stAlert">API key missing — add it in the sidebar.</div>', unsafe_allow_html=True)
            st.stop()

        with st.spinner(f"Pulling live data for {ticker}..."):
            try:
                time.sleep(0.8)
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
        ret_52w  = financials.get("return_52w","")

        # Stock header
        ret_color = "#00ffb4" if ret_52w and "-" not in ret_52w else "#ff4f6a"
        st.markdown(f"""
        <div class="stock-hdr">
          <div>
            <div class="stock-name">{company}<span class="stock-ticker">{ticker}</span></div>
            <div class="stock-sector">{sector} · {industry} · {currency}</div>
          </div>
          <div class="price-block">
            <div class="price-main">{currency} {price}</div>
            <div class="price-sub" style="color:{ret_color}">52W: {ret_52w}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Metrics row 1
        m = financials
        def mcard(label, val, color=""):
            cls = f'mcard-value {color}' if color else 'mcard-value'
            return f'<div class="mcard"><div class="mcard-label">{label}</div><div class="{cls}">{val}</div></div>'

        def is_pos(v):
            if v == "N/A": return ""
            return "pos" if not str(v).startswith("-") else "neg"

        col_grid = st.columns(4)
        metrics1 = [
            ("P/E Ratio",      m.get("pe_ratio","N/A"),      ""),
            ("EV / EBITDA",    m.get("ev_ebitda","N/A"),     ""),
            ("Debt / Equity",  m.get("debt_equity","N/A"),   ""),
            ("Current Ratio",  m.get("current_ratio","N/A"), ""),
        ]
        for i,(label,val,_) in enumerate(metrics1):
            col_grid[i].markdown(mcard(label,val), unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        col_grid2 = st.columns(4)
        metrics2 = [
            ("Revenue Growth",  m.get("revenue_growth","N/A"),  is_pos(m.get("revenue_growth",""))),
            ("Gross Margin",    m.get("gross_margin","N/A"),     is_pos(m.get("gross_margin",""))),
            ("ROE",             m.get("roe","N/A"),              is_pos(m.get("roe",""))),
            ("Free Cash Flow",  m.get("free_cash_flow","N/A"),  "pos"),
        ]
        for i,(label,val,color) in enumerate(metrics2):
            col_grid2[i].markdown(mcard(label,val,color), unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        col_grid3 = st.columns(4)
        metrics3 = [
            ("Dividend Yield",   m.get("dividend_yield","N/A"), ""),
            ("Beta",             m.get("beta","N/A"),           ""),
            ("52W High",         m.get("week52_high","N/A"),    ""),
            ("52W Low",          m.get("week52_low","N/A"),     ""),
        ]
        for i,(label,val,color) in enumerate(metrics3):
            col_grid3[i].markdown(mcard(label,val,color), unsafe_allow_html=True)

        # Verdict
        vclass = f"v-{verdict}" if verdict in ("BUY","HOLD","SELL") else "v-UNCERTAIN"
        pclass = f"vp-{verdict}" if verdict in ("BUY","HOLD","SELL") else "vp-UNCERTAIN"
        st.markdown(f"""
        <div class="verdict-wrap {vclass}">
          <div class="verdict-pill {pclass}">{verdict}</div>
          <div class="verdict-rationale">{analysis.get('verdict_rationale','')}</div>
        </div>
        """, unsafe_allow_html=True)

        # Valuation summary
        st.markdown('<div class="sec-hdr">Valuation Summary</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:13px;color:#94a3b8;line-height:1.8'>{analysis.get('valuation_summary','')}</div>", unsafe_allow_html=True)

        # Two columns — risks + positives
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="sec-hdr">Risk Flags</div>', unsafe_allow_html=True)
            risk_html = '<div class="risk-row">'
            for r in analysis.get("risk_flags",[]):
                lv = r.get("level","MEDIUM").upper()
                rc = {"HIGH":"rH","MEDIUM":"rM","LOW":"rL"}.get(lv,"rM")
                risk_html += f'<span class="rpill {rc}">[{lv}] {r["flag"]}</span>'
            risk_html += '</div>'
            st.markdown(risk_html, unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="sec-hdr">Key Positives</div>', unsafe_allow_html=True)
            for p in analysis.get("key_positives",[]):
                st.markdown(f'<div class="pos-item"><span class="pos-dot">◆</span><span>{p}</span></div>', unsafe_allow_html=True)

        # Plain English
        st.markdown('<div class="sec-hdr">Plain English</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pe-box">"{analysis.get("plain_english","")}"</div>', unsafe_allow_html=True)

        # Disclaimer + download
        st.markdown('<div class="disc">⚠ Data sourced from Yahoo Finance — may lag 1-2 quarters for Indian stocks. Cross-check on Screener.in. This report is for informational purposes only and does not constitute investment advice. Past performance does not guarantee future returns.</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        with st.spinner("Generating PDF..."):
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

    elif run and not ticker_input:
        st.warning("Enter a ticker symbol first.")

    if not run:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#1e293b;">
          <div style="font-size:48px;margin-bottom:16px">🌓</div>
          <div style="font-size:18px;color:#334155;font-weight:500">Enter a ticker above to generate your report</div>
          <div style="font-size:12px;color:#1e293b;margin-top:8px">AAPL · MSFT · RELIANCE.NS · TCS.NS · NVDA · GOOGL · INFY.NS</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO OPTIMISER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    from portfolio_optimiser import show_optimiser
    show_optimiser()
