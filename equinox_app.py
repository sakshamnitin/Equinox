import streamlit as st

st.set_page_config(
    page_title="Equinox – Investment Intelligence Platform",
    page_icon="🌓",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

.top-nav {
    background: linear-gradient(135deg, #0f1923 0%, #1a2d45 100%);
    padding: 1.2rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.top-nav h1 { color: #f0e6d3; font-size: 1.8rem; margin: 0; }
.top-nav p  { color: #8fa8c8; margin: 0; font-size: 0.85rem; }

.metric-card {
    background: #f8f9fb; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
}
.metric-card .label { font-size: 0.72rem; color: #718096; text-transform: uppercase; letter-spacing: .06em; }
.metric-card .value { font-size: 1.5rem; font-weight: 600; color: #1a202c; }

.verdict-box { border-left: 4px solid; padding: 1rem 1.4rem; border-radius: 0 10px 10px 0; margin: 1.2rem 0; }
.verdict-BUY       { border-color: #38a169; background: #f0fff4; color: #22543d; }
.verdict-HOLD      { border-color: #d69e2e; background: #fffff0; color: #744210; }
.verdict-SELL      { border-color: #e53e3e; background: #fff5f5; color: #742a2a; }
.verdict-UNCERTAIN { border-color: #718096; background: #f7fafc; color: #2d3748; }

.risk-pill { display:inline-block; padding:3px 10px; border-radius:999px; font-size:0.78rem; font-weight:500; margin:3px 4px 3px 0; }
.risk-HIGH   { background:#fed7d7; color:#9b2c2c; }
.risk-MEDIUM { background:#fefcbf; color:#7b6226; }
.risk-LOW    { background:#c6f6d5; color:#22543d; }

.stButton>button {
    background: linear-gradient(135deg, #1a2d45 0%, #2c5282 100%);
    color: white; border: none; border-radius: 8px; padding: .65rem 2rem;
    font-size: 1rem; font-weight: 500; width: 100%;
}
.stButton>button:hover { opacity: .88; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-nav">
  <div>
    <h1>🌓 Equinox</h1>
    <p>Investment Intelligence Platform &nbsp;·&nbsp; Research · Optimise · Monitor Risk</p>
  </div>
  <div style="color:#8fa8c8;font-size:0.8rem;text-align:right;">
    Built by Saksham Minde<br>Not investment advice
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌓 Equinox")
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or st.text_input(
        "Anthropic API Key", type="password", help="Required for Research module only"
    )
    st.markdown("---")
    st.markdown("**Modules**")
    st.markdown("📊 Research — Equity reports")
    st.markdown("📐 Optimiser — Portfolio allocation")
    st.markdown("---")
    st.caption("Data: Yahoo Finance · Not investment advice")

# ── Navigation tabs ───────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Equity Research", "📐 Portfolio Optimiser"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EQUITY RESEARCH
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    import yfinance as yf
    import anthropic
    import json
    from datetime import datetime
    from report_generator import generate_pdf_report
    from financial_engine import compute_financials

    def build_analysis_prompt(ticker, info, fin):
        return f"""You are a seasoned equity research analyst with 15 years on the sell-side.
You write like a human — direct, opinionated, occasionally dry. No corporate fluff,
no AI-sounding phrases like "it is worth noting" or "the company demonstrates".
Use short punchy sentences. Say what you actually think.
Write like you're briefing a smart colleague over coffee, not filing a report.
Return a JSON object ONLY — no preamble, no markdown.

COMPANY DATA:
Ticker: {ticker}
Name: {info.get('shortName', 'Unknown')}
Sector: {info.get('sector', 'N/A')}
Industry: {info.get('industry', 'N/A')}
Country: {info.get('country', 'N/A')}
Market Cap: {info.get('marketCap', 'N/A')}
Description: {info.get('longBusinessSummary', '')[:600]}

KEY FINANCIALS:
Current Price: {fin.get('current_price')}
P/E Ratio: {fin.get('pe_ratio')}
Forward P/E: {fin.get('forward_pe')}
EV/EBITDA: {fin.get('ev_ebitda')}
Debt/Equity: {fin.get('debt_equity')}
ROE: {fin.get('roe')} | ROA: {fin.get('roa')}
Gross Margin: {fin.get('gross_margin')} | Operating Margin: {fin.get('operating_margin')}
Revenue Growth: {fin.get('revenue_growth')} | Earnings Growth: {fin.get('earnings_growth')}
Free Cash Flow: {fin.get('free_cash_flow')}
Dividend Yield: {fin.get('dividend_yield')}
Beta: {fin.get('beta')} | 52W Return: {fin.get('return_52w')}

VALUATION FRAMEWORK:
- DCF: FCFF-based. WACC via bottom-up beta. Terminal value via Gordon Growth Model.
  Bull/base/bear scenarios weighted 25/50/25.
- Comparables: sector P/E and EV/EBITDA vs peers.

OUTPUT — return EXACTLY this JSON:
{{
  "verdict": "BUY" | "HOLD" | "SELL",
  "verdict_rationale": "2-3 sentences. Direct, opinionated, no hedging.",
  "valuation_summary": "3-4 sentences on DCF, relative valuation, what market is pricing in.",
  "key_positives": ["point 1", "point 2", "point 3"],
  "risk_flags": [
    {{"flag": "description", "level": "HIGH" | "MEDIUM" | "LOW"}},
    {{"flag": "description", "level": "HIGH" | "MEDIUM" | "LOW"}},
    {{"flag": "description", "level": "HIGH" | "MEDIUM" | "LOW"}}
  ],
  "plain_english": "1-2 sentences like you're texting a friend. Casual, honest, no jargon."
}}"""

    col1, col2 = st.columns([3, 1])
    with col1:
        ticker_input = st.text_input("Enter stock ticker",
            placeholder="e.g. AAPL · RELIANCE.NS · TCS.NS · MSFT",
            label_visibility="collapsed")
    with col2:
        run = st.button("Generate Report", use_container_width=True)

    st.caption("Supports NSE (.NS), BSE (.BO), and all major US tickers. · Data: Yahoo Finance (may lag 1-2 quarters for Indian stocks)")

    if run and ticker_input:
        ticker = ticker_input.strip().upper()
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar.")
            st.stop()

        with st.spinner(f"Pulling live data for {ticker}..."):
            try:
                stock = yf.Ticker(ticker)
                info  = stock.info
                hist  = stock.history(period="1y")
                if not info or "shortName" not in info:
                    st.error(f"Could not find data for `{ticker}`.")
                    st.stop()
                financials = compute_financials(stock, info, hist)
            except Exception as e:
                st.error(f"Data fetch failed: {e}")
                st.stop()

        with st.spinner("Running AI valuation analysis..."):
            try:
                client  = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-sonnet-4-5", max_tokens=1800,
                    messages=[{"role": "user", "content": build_analysis_prompt(ticker, info, financials)}]
                )
                raw      = message.content[0].text
                raw      = raw.strip().replace("```json", "").replace("```", "").strip()
                analysis = json.loads(raw)
            except json.JSONDecodeError:
                st.error("AI response parse error. Please retry.")
                st.stop()
            except Exception as e:
                st.error(f"Claude API error: {e}")
                st.stop()

        company  = info.get("shortName", ticker)
        sector   = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        currency = info.get("currency", "USD")
        price    = financials.get("current_price", "N/A")
        verdict  = analysis.get("verdict", "UNCERTAIN").upper()

        st.markdown(f"## {company} `{ticker}`")
        st.markdown(f"**{sector}** · {industry} · {currency}")
        st.markdown("---")

        def metric_card(col, label, val):
            col.markdown(f'<div class="metric-card"><div class="label">{label}</div><div class="value">{val}</div></div>', unsafe_allow_html=True)

        m1,m2,m3,m4 = st.columns(4)
        metric_card(m1,"Current Price", f"{currency} {price}")
        metric_card(m2,"P/E Ratio",     financials.get("pe_ratio","N/A"))
        metric_card(m3,"EV/EBITDA",     financials.get("ev_ebitda","N/A"))
        metric_card(m4,"Debt/Equity",   financials.get("debt_equity","N/A"))
        st.markdown("<br>", unsafe_allow_html=True)
        m5,m6,m7,m8 = st.columns(4)
        metric_card(m5,"Revenue Growth",financials.get("revenue_growth","N/A"))
        metric_card(m6,"Gross Margin",  financials.get("gross_margin","N/A"))
        metric_card(m7,"ROE",           financials.get("roe","N/A"))
        metric_card(m8,"52W Return",    financials.get("return_52w","N/A"))

        st.markdown("### Valuation Summary")
        st.markdown(analysis.get("valuation_summary",""))

        vc = f"verdict-{verdict}" if verdict in ("BUY","HOLD","SELL") else "verdict-UNCERTAIN"
        vi = {"BUY":"🟢","HOLD":"🟡","SELL":"🔴"}.get(verdict,"⚪")
        st.markdown(f'<div class="verdict-box {vc}"><strong>{vi} Verdict: {verdict}</strong><br>{analysis.get("verdict_rationale","")}</div>', unsafe_allow_html=True)

        st.markdown("### Risk Flags")
        rh = ""
        for r in analysis.get("risk_flags",[]):
            lv = r.get("level","MEDIUM").upper()
            rh += f'<span class="risk-pill risk-{lv}">{lv}</span> {r["flag"]}<br>'
        st.markdown(rh, unsafe_allow_html=True)

        st.markdown("### Key Positives")
        for p in analysis.get("key_positives",[]): st.markdown(f"✅ {p}")

        st.markdown("### Plain English Takeaway")
        st.info(analysis.get("plain_english",""))

        st.markdown("---")
        st.caption("⚠️ For informational purposes only. Not investment advice. Cross-check Indian stocks on Screener.in.")

        st.markdown("### Download Report")
        with st.spinner("Generating PDF..."):
            pdf_bytes = generate_pdf_report(
                ticker=ticker, company=company, sector=sector,
                currency=currency, price=str(price), financials=financials,
                analysis=analysis, generated_at=datetime.now().strftime("%d %B %Y, %H:%M"),
            )
        st.download_button("⬇️  Download PDF Report", data=pdf_bytes,
            file_name=f"Equinox_{ticker}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf")

    elif run and not ticker_input:
        st.warning("Please enter a ticker symbol.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO OPTIMISER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    from portfolio_optimiser import show_optimiser
    show_optimiser()
