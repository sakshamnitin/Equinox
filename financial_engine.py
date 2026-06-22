"""
financial_engine.py
Pulls and normalises key financial metrics from yfinance.
"""

import math


def fmt_pct(val):
    """For values already in decimal form e.g. 0.047 → 4.7%"""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val * 100:.1f}%"


def fmt_pct_raw(val):
    """For values already in percentage form e.g. 47.0 → 47.0%"""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val:.1f}%"


def fmt_x(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val:.1f}x"


def fmt_num(val, decimals=2):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "N/A"
    return f"{val:.{decimals}f}"


def fmt_large(val):
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except (TypeError, ValueError):
        return "N/A"
    if abs(val) >= 1e12:
        return f"{val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"{val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"{val/1e6:.2f}M"
    return f"{val:.0f}"


def compute_financials(stock, info: dict, hist) -> dict:
    def g(key, default=None):
        v = info.get(key, default)
        if v in (None, "N/A", "", "Infinity"):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # 52-week return
    try:
        if len(hist) > 0:
            ret_52w = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]
        else:
            ret_52w = None
    except Exception:
        ret_52w = None

    # D/E from yfinance is already in ratio form (e.g. 0.45 means 45%)
    # but some tickers return it as a whole number — normalise anything > 20 by /100
    de_raw = g("debtToEquity")
    if de_raw is not None and de_raw > 20:
        de_raw = de_raw / 100
    de = fmt_num(de_raw)

    return {
        "current_price":    fmt_num(g("currentPrice") or g("regularMarketPrice") or g("previousClose")),

        # Multiples — already in ratio form from yfinance
        "pe_ratio":         fmt_x(g("trailingPE")),
        "forward_pe":       fmt_x(g("forwardPE")),
        "peg_ratio":        fmt_x(g("pegRatio")),
        "ev_ebitda":        fmt_x(g("enterpriseToEbitda")),
        "price_book":       fmt_x(g("priceToBook")),
        "price_sales":      fmt_x(g("priceToSalesTrailing12Months")),

        # Leverage — ratio, not percentage
        "debt_equity":      de,
        "current_ratio":    fmt_num(g("currentRatio")),

        # Returns — yfinance returns these as decimals (0.47 = 47%), multiply by 100
        "roe":              fmt_pct(g("returnOnEquity")),
        "roa":              fmt_pct(g("returnOnAssets")),

        # Margins — yfinance returns as decimals (0.47 = 47%)
        "gross_margin":     fmt_pct(g("grossMargins")),
        "operating_margin": fmt_pct(g("operatingMargins")),
        "profit_margin":    fmt_pct(g("profitMargins")),

        # Growth — yfinance returns as decimals
        "revenue_growth":   fmt_pct(g("revenueGrowth")),
        "earnings_growth":  fmt_pct(g("earningsGrowth")),

        # Dividend yield — yfinance returns as decimal (0.0047 = 0.47%)
        "dividend_yield":   fmt_pct(g("dividendYield")),

        # 52W return — calculated from price history as decimal
        "return_52w":       fmt_pct(ret_52w),

        # Other
        "free_cash_flow":   fmt_large(g("freeCashflow")),
        "beta":             fmt_num(g("beta")),
        "week52_high":      fmt_num(g("fiftyTwoWeekHigh")),
        "week52_low":       fmt_num(g("fiftyTwoWeekLow")),
        "market_cap":       fmt_large(g("marketCap")),
        "enterprise_value": fmt_large(g("enterpriseValue")),
    }
