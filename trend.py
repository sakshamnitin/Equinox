"""
trend.py
Equinox — "Trend" Module: Macro News + Market Pulse

Aggregates headlines by category via RSS (no API key needed) and shows a
live snapshot of key macro instruments (oil, gold, FX, rates, indices)
via yfinance, which Equinox already depends on.

Usage in your app:
    from trend import show_trend
    show_trend()

Add to requirements.txt:
    feedparser
"""

import streamlit as st
import feedparser
import yfinance as yf
from datetime import datetime

BRAND_DARK = "#0f1923"
ACCENT     = "#00ffcc"

# ── Market Pulse: live macro snapshot via yfinance ─────────────────────────────
# Tuples: (display label, yfinance ticker, display format)
MARKET_PULSE = [
    ("Brent Crude",     "BZ=F",     "${:.2f}"),
    ("WTI Crude",       "CL=F",     "${:.2f}"),
    ("Gold",            "GC=F",     "${:.2f}"),
    ("Silver",          "SI=F",     "${:.2f}"),
    ("US 10Y Yield",    "^TNX",     "{:.2f}%"),
    ("USD/INR",         "INR=X",    "₹{:.2f}"),
    ("Dollar Index",    "DX-Y.NYB", "{:.2f}"),
    ("Nifty 50",        "^NSEI",    "{:.0f}"),
    ("Sensex",          "^BSESN",   "{:.0f}"),
    ("S&P 500",         "^GSPC",    "{:.0f}"),
]

# ── News categories: curated RSS feeds (verify periodically — feeds do go stale) ──
CATEGORY_FEEDS = {
    "Commodities (Oil & Gold)": [
        "https://oilprice.com/rss/main",
        "https://www.investing.com/rss/news_11.rss",           # commodities news
    ],
    "Rates, FX & Macro": [
        "https://www.investing.com/rss/news_25.rss",           # economic indicators
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    ],
    "IPO & M&A": [
        "https://www.moneycontrol.com/rss/business.xml",
        "https://economictimes.indiatimes.com/markets/ipos/fpos/rssfeeds/58189741.cms",
    ],
    "Technology (AI & Electronics)": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.investing.com/rss/news_95.rss",           # tech news
    ],
    "Manufacturing": [
        "https://www.moneycontrol.com/rss/economy.xml",
    ],
    "Geopolitical": [
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_pulse():
    """Fetch last price + % change for each Market Pulse instrument."""
    results = []
    for label, ticker, fmt in MARKET_PULSE:
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if hist.empty or len(hist) < 2:
                continue
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            pct_change = (last - prev) / prev * 100
            results.append({
                "label": label, "value": fmt.format(last),
                "pct_change": pct_change,
            })
        except Exception:
            continue  # skip instrument silently, don't break the whole panel
    return results


@st.cache_data(ttl=900, show_spinner=False)
def fetch_category_news(category: str, limit: int = 6):
    """Fetch and merge headlines from all RSS feeds under a category."""
    urls = CATEGORY_FEEDS.get(category, [])
    items = []
    failed_feeds = 0

    for url in urls:
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                failed_feeds += 1
                continue
            for entry in parsed.entries[:limit]:
                items.append({
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", "#"),
                    "published": entry.get("published", ""),
                    "source": parsed.feed.get("title", url),
                })
        except Exception:
            failed_feeds += 1
            continue

    items = items[: limit * max(len(urls), 1)]
    return items, failed_feeds


def _render_news_list(category: str):
    items, failed_feeds = fetch_category_news(category)

    if failed_feeds and not items:
        st.warning(f"Couldn't reach news sources for {category} right now. Try refreshing shortly.")
        return

    if not items:
        st.info("No headlines available right now.")
        return

    for item in items:
        st.markdown(
            f"""
            <div style="background:{BRAND_DARK};border-left:3px solid {ACCENT};
            padding:0.7rem 1rem;border-radius:6px;margin-bottom:0.5rem;">
              <a href="{item['link']}" target="_blank"
                 style="color:#f0e6d3;text-decoration:none;font-weight:600;">
                 {item['title']}
              </a>
              <div style="color:#8fa8c8;font-size:0.8rem;margin-top:0.3rem;">
                {item['source']}{' · ' + item['published'] if item['published'] else ''}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_trend():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f1923,#1a2d45);padding:2rem;
    border-radius:12px;margin-bottom:1.5rem;text-align:center;">
      <h2 style="color:#f0e6d3;margin:0;">📊 Trend</h2>
      <p style="color:#8fa8c8;margin:.4rem 0 0;">Macro Markets · Commodities · IPO & M&A · Geopolitical</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Market Pulse ──────────────────────────────────────────────────────────
    st.markdown("### Market Pulse")
    pulse = fetch_market_pulse()
    if pulse:
        cols = st.columns(len(pulse))
        for col, item in zip(cols, pulse):
            col.metric(item["label"], item["value"], f"{item['pct_change']:+.2f}%")
    else:
        st.info("Market data temporarily unavailable.")

    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')} (cached ~15 min)")
    st.markdown("---")

    # ── News by category ──────────────────────────────────────────────────────
    st.markdown("### Headlines by Category")
    tabs = st.tabs(list(CATEGORY_FEEDS.keys()))
    for tab, category in zip(tabs, CATEGORY_FEEDS.keys()):
        with tab:
            _render_news_list(category)

    st.markdown("---")
    st.caption("News aggregated from third-party sources via RSS. Equinox does not verify or endorse linked content.")
