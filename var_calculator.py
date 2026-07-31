"""
var_calculator.py
Equinox — VaR Calculator Module
Parametric | Historical Simulation | Monte Carlo
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.figure_factory as ff
from scipy import stats
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')

TRADING_DAYS = 252
BRAND_DARK   = "#060b12"
ACCENT       = "#00ffb4"


# ── Core VaR calculations ─────────────────────────────────────────────────────

def parametric_var(returns, weights, confidence, rfr):
    """Variance-Covariance (Parametric) VaR."""
    port_returns  = returns @ weights
    mu            = port_returns.mean()
    sigma         = port_returns.std()
    z             = stats.norm.ppf(1 - confidence)
    var_1d        = -(mu + z * sigma)
    cvar_1d       = -(mu - sigma * stats.norm.pdf(z) / (1 - confidence))
    sharpe        = (mu * TRADING_DAYS - rfr) / (sigma * np.sqrt(TRADING_DAYS))
    return {
        "var_1d":   var_1d,
        "var_10d":  var_1d * np.sqrt(10),
        "cvar_1d":  cvar_1d,
        "cvar_10d": cvar_1d * np.sqrt(10),
        "mu":       mu,
        "sigma":    sigma,
        "sharpe":   sharpe,
        "port_ret": port_returns,
        "method":   "Parametric (Variance-Covariance)",
    }


def historical_var(returns, weights, confidence):
    """Historical Simulation VaR — non-parametric."""
    port_returns  = returns @ weights
    var_1d        = -np.percentile(port_returns, (1 - confidence) * 100)
    tail          = port_returns[port_returns <= -var_1d]
    cvar_1d       = -tail.mean() if len(tail) > 0 else var_1d
    mu            = port_returns.mean()
    sigma         = port_returns.std()
    sharpe        = (mu * TRADING_DAYS - 0.05) / (sigma * np.sqrt(TRADING_DAYS))
    return {
        "var_1d":   var_1d,
        "var_10d":  var_1d * np.sqrt(10),
        "cvar_1d":  cvar_1d,
        "cvar_10d": cvar_1d * np.sqrt(10),
        "mu":       mu,
        "sigma":    sigma,
        "sharpe":   sharpe,
        "port_ret": port_returns,
        "method":   "Historical Simulation",
    }


def monte_carlo_var(returns, weights, confidence, n_sims, rfr):
    """Monte Carlo VaR using Cholesky decomposition."""
    mu_vec   = returns.mean().values
    cov_mat  = returns.cov().values
    L        = np.linalg.cholesky(cov_mat + np.eye(len(weights)) * 1e-10)

    np.random.seed(42)
    Z        = np.random.standard_normal((n_sims, len(weights)))
    sim_rets = Z @ L.T + mu_vec
    port_sim = sim_rets @ weights

    var_1d   = -np.percentile(port_sim, (1 - confidence) * 100)
    tail     = port_sim[port_sim <= -var_1d]
    cvar_1d  = -tail.mean() if len(tail) > 0 else var_1d

    hist_port = returns @ weights
    mu        = hist_port.mean()
    sigma     = hist_port.std()
    sharpe    = (mu * TRADING_DAYS - rfr) / (sigma * np.sqrt(TRADING_DAYS))

    return {
        "var_1d":    var_1d,
        "var_10d":   var_1d * np.sqrt(10),
        "cvar_1d":   cvar_1d,
        "cvar_10d":  cvar_1d * np.sqrt(10),
        "mu":        mu,
        "sigma":     sigma,
        "sharpe":    sharpe,
        "port_ret":  hist_port,
        "sim_rets":  port_sim,
        "method":    f"Monte Carlo ({n_sims:,} simulations)",
    }


# ── Charts ────────────────────────────────────────────────────────────────────

def plot_return_dist(result, confidence, method):
    port_ret = result["port_ret"]
    var_1d   = result["var_1d"]
    cvar_1d  = result["cvar_1d"]

    fig = go.Figure()

    # Histogram of returns
    fig.add_trace(go.Histogram(
        x=port_ret * 100,
        nbinsx=80,
        marker_color="#1e3a5f",
        marker_line_color="#2d5a8e",
        marker_line_width=0.5,
        opacity=0.85,
        name="Daily Returns",
    ))

    # VaR line
    fig.add_vline(
        x=-var_1d * 100,
        line_color="#ff4f6a", line_width=2, line_dash="dash",
        annotation_text=f"VaR {confidence*100:.0f}%: {var_1d*100:.2f}%",
        annotation_font_color="#ff4f6a",
        annotation_position="top right",
    )

    # CVaR line
    fig.add_vline(
        x=-cvar_1d * 100,
        line_color="#fbbf24", line_width=2, line_dash="dot",
        annotation_text=f"CVaR: {cvar_1d*100:.2f}%",
        annotation_font_color="#fbbf24",
        annotation_position="top left",
    )

    # Shade tail
    x_tail = np.linspace(port_ret.min() * 100, -var_1d * 100, 100)
    fig.add_trace(go.Scatter(
        x=x_tail, y=[0] * len(x_tail),
        fill="tozeroy", fillcolor="rgba(255,79,106,0.08)",
        line=dict(width=0), name="Loss Tail",
        showlegend=True,
    ))

    fig.update_layout(
        title=dict(text=f"Portfolio Return Distribution — {method}", font=dict(size=14, color="#e2e8f0")),
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color="#64748b"),
        legend=dict(bgcolor="rgba(13,21,32,0.8)", bordercolor="#1e3a5f"),
        height=380,
        bargap=0.05,
    )
    fig.update_xaxes(gridcolor="#0d1520", zerolinecolor="#1e3a5f")
    fig.update_yaxes(gridcolor="#0d1520")
    return fig


def plot_mc_simulation(sim_rets, var_1d, confidence):
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=sim_rets * 100, nbinsx=100,
        marker_color="#1e3a5f",
        marker_line_color="#2d5a8e",
        marker_line_width=0.3,
        name="Simulated Returns",
    ))
    fig.add_vline(
        x=-var_1d * 100,
        line_color="#ff4f6a", line_width=2, line_dash="dash",
        annotation_text=f"VaR {confidence*100:.0f}%: {var_1d*100:.2f}%",
        annotation_font_color="#ff4f6a",
    )
    fig.update_layout(
        title=dict(text="Monte Carlo Simulated Return Distribution", font=dict(size=14, color="#e2e8f0")),
        xaxis_title="Simulated Daily Return (%)",
        yaxis_title="Frequency",
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color="#64748b"), height=360,
    )
    fig.update_xaxes(gridcolor="#0d1520")
    fig.update_yaxes(gridcolor="#0d1520")
    return fig


def plot_cumulative(port_ret, tickers, weights, returns):
    fig = go.Figure()

    # Portfolio cumulative
    cum_port = (1 + port_ret).cumprod() - 1
    fig.add_trace(go.Scatter(
        x=cum_port.index, y=cum_port * 100,
        name="Portfolio", line=dict(color="#00ffb4", width=2.5),
    ))

    # Individual stocks
    colors = ["#60a5fa","#fbbf24","#f472b6","#a78bfa","#34d399","#fb923c"]
    for i, ticker in enumerate(tickers):
        cum_stk = (1 + returns[ticker]).cumprod() - 1
        fig.add_trace(go.Scatter(
            x=cum_stk.index, y=cum_stk * 100,
            name=ticker, line=dict(color=colors[i % len(colors)], width=1, dash="dot"),
            opacity=0.6,
        ))

    fig.update_layout(
        title=dict(text="Cumulative Returns — Portfolio vs Components", font=dict(size=14, color="#e2e8f0")),
        yaxis_title="Cumulative Return (%)",
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color="#64748b"),
        legend=dict(bgcolor="rgba(13,21,32,0.8)", bordercolor="#1e3a5f"),
        height=380,
    )
    fig.update_xaxes(gridcolor="#0d1520")
    fig.update_yaxes(gridcolor="#0d1520")
    return fig


def plot_rolling_var(port_ret, confidence, window=63):
    rolling_var = port_ret.rolling(window).apply(
        lambda x: -np.percentile(x, (1 - confidence) * 100)
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rolling_var.index, y=rolling_var * 100,
        fill="tozeroy", fillcolor="rgba(255,79,106,0.08)",
        line=dict(color="#ff4f6a", width=1.5),
        name=f"Rolling {window}d VaR ({confidence*100:.0f}%)",
    ))
    fig.update_layout(
        title=dict(text=f"Rolling {window}-Day Historical VaR", font=dict(size=14, color="#e2e8f0")),
        yaxis_title="VaR (%)",
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color="#64748b"), height=320,
    )
    fig.update_xaxes(gridcolor="#0d1520")
    fig.update_yaxes(gridcolor="#0d1520")
    return fig


def plot_correlation(corr_matrix):
    import plotly.express as px
    fig = px.imshow(
        corr_matrix, text_auto=".2f",
        color_continuous_scale="RdYlGn", zmin=-1, zmax=1,
        title="Correlation Matrix",
    )
    fig.update_layout(
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color="#64748b"), height=380,
        title_font=dict(size=14, color="#e2e8f0"),
    )
    return fig


# ── Result card HTML ──────────────────────────────────────────────────────────

def var_card(label, value, sublabel="", color="#ff4f6a"):
    return f"""
    <div style="background:#0d1520;border:1px solid rgba(255,255,255,0.07);border-radius:10px;
    padding:14px 16px;transition:border-color 0.2s;">
      <div style="font-size:9px;font-weight:600;color:#475569;text-transform:uppercase;
      letter-spacing:1.2px;margin-bottom:8px">{label}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:600;
      color:{color}">{value}</div>
      {f'<div style="font-size:10px;color:#334155;margin-top:4px">{sublabel}</div>' if sublabel else ''}
    </div>"""


# ── Main module ───────────────────────────────────────────────────────────────

def show_var_calculator():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1520,#060b12);padding:24px 28px 20px;
    border-bottom:1px solid rgba(255,255,255,0.05);">
      <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin-bottom:4px">
        📉 VaR Calculator
      </div>
      <div style="font-size:12px;color:#334155">
        Parametric &nbsp;·&nbsp; Historical Simulation &nbsp;·&nbsp; Monte Carlo &nbsp;·&nbsp;
        Value at Risk & Expected Shortfall
      </div>
    </div>
    <div style="padding:24px 28px">
    """, unsafe_allow_html=True)

    # ── Input panel ───────────────────────────────────────────────────────────
    st.markdown('<div style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px">Portfolio Configuration</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        tickers_raw = st.text_input(
            "Tickers (comma-separated)",
            value="AAPL, MSFT, GOOGL, AMZN, TSLA",
            help="Yahoo Finance format. Indian: RELIANCE.NS, TCS.NS",
            key="var_tickers",
        )
    with col2:
        weights_raw = st.text_input(
            "Weights (comma-separated, must sum to 1.0)",
            value="0.30, 0.25, 0.20, 0.15, 0.10",
            key="var_weights",
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        method = st.selectbox(
            "VaR Method",
            ["Historical Simulation", "Parametric (Variance-Covariance)", "Monte Carlo"],
            key="var_method",
        )
    with col4:
        confidence = st.selectbox(
            "Confidence Level",
            [0.99, 0.975, 0.95, 0.90],
            format_func=lambda x: f"{x*100:.1f}%",
            key="var_confidence",
        )
    with col5:
        rfr = st.number_input(
            "Risk-Free Rate (%)",
            value=5.0, min_value=0.0, max_value=20.0, step=0.25,
            key="var_rfr",
        ) / 100

    # Method-specific params
    col6, col7 = st.columns(2)
    with col6:
        if method == "Historical Simulation":
            lookback = st.selectbox(
                "Historical Lookback Period",
                ["1y", "2y", "3y", "5y"],
                index=0, key="var_lookback",
            )
        else:
            lookback = "2y"

    with col7:
        if method == "Monte Carlo":
            n_sims = st.select_slider(
                "Number of Simulations",
                options=[1000, 5000, 10000, 25000, 50000],
                value=10000, key="var_nsims",
            )
        else:
            n_sims = 10000

    portfolio_value = st.number_input(
        "Portfolio Value (optional — for dollar VaR)",
        value=100000, min_value=0, step=10000,
        key="var_portval",
        help="Enter your portfolio value to see VaR in dollar terms",
    )

    run = st.button("⚡  Calculate VaR", use_container_width=True, key="var_run")

    if not run:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#0f1f30">
          <div style="font-size:40px;margin-bottom:16px">📉</div>
          <div style="font-size:16px;color:#1e3a5f;font-weight:500">Configure your portfolio above and click Calculate VaR</div>
          <div style="font-size:12px;color:#0f1f30;margin-top:8px">Supports Parametric · Historical Simulation · Monte Carlo</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Parse inputs ──────────────────────────────────────────────────────────
    try:
        tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
        weights = np.array([float(w.strip()) for w in weights_raw.split(",") if w.strip()])
        if abs(weights.sum() - 1.0) > 0.01:
            st.error(f"Weights sum to {weights.sum():.3f} — they must sum to 1.0")
            return
        if len(tickers) != len(weights):
            st.error(f"Number of tickers ({len(tickers)}) must match weights ({len(weights)})")
            return
    except ValueError as e:
        st.error(f"Input error: {e}")
        return

    # ── Fetch data ────────────────────────────────────────────────────────────
    with st.spinner("Fetching price data..."):
        try:
            import time
            time.sleep(0.5)
            raw = yf.download(
                tickers, period=lookback,
                auto_adjust=True, progress=False,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                prices = raw["Close"][tickers].dropna()
            else:
                prices = raw[["Close"]].dropna()
                prices.columns = tickers

            if prices.empty or len(prices) < 30:
                st.error("Not enough price data returned. Check tickers or try a longer lookback.")
                return

            returns      = prices.pct_change().dropna()
            corr_matrix  = returns.corr()

        except Exception as e:
            st.error(f"Data fetch failed: {e}. Wait 30 seconds and retry.")
            return

    # ── Run VaR ───────────────────────────────────────────────────────────────
    with st.spinner(f"Running {method}..."):
        try:
            if method == "Parametric (Variance-Covariance)":
                result = parametric_var(returns, weights, confidence, rfr)
            elif method == "Historical Simulation":
                result = historical_var(returns, weights, confidence)
            else:
                result = monte_carlo_var(returns, weights, confidence, n_sims, rfr)
        except Exception as e:
            st.error(f"VaR calculation failed: {e}")
            return

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;
    text-transform:uppercase;margin-bottom:12px">
    Results — {result['method']} · {confidence*100:.0f}% Confidence
    </div>
    """, unsafe_allow_html=True)

    # VaR result cards
    dollar_var   = result["var_1d"] * portfolio_value if portfolio_value > 0 else None
    dollar_cvar  = result["cvar_1d"] * portfolio_value if portfolio_value > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(var_card(
        f"1-Day VaR ({confidence*100:.0f}%)",
        f"{result['var_1d']*100:.3f}%",
        f"${dollar_var:,.0f}" if dollar_var else "",
        "#ff4f6a"
    ), unsafe_allow_html=True)
    c2.markdown(var_card(
        f"10-Day VaR ({confidence*100:.0f}%)",
        f"{result['var_10d']*100:.3f}%",
        f"${result['var_10d']*portfolio_value:,.0f}" if portfolio_value else "",
        "#ff4f6a"
    ), unsafe_allow_html=True)
    c3.markdown(var_card(
        f"1-Day CVaR / ES",
        f"{result['cvar_1d']*100:.3f}%",
        f"${dollar_cvar:,.0f}" if dollar_cvar else "Expected Shortfall",
        "#fbbf24"
    ), unsafe_allow_html=True)
    c4.markdown(var_card(
        "Annualised Sharpe",
        f"{result['sharpe']:.3f}",
        f"RFR: {rfr*100:.2f}%",
        "#00ffb4" if result["sharpe"] > 0 else "#ff4f6a"
    ), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    ann_ret = result["mu"] * TRADING_DAYS
    ann_vol = result["sigma"] * np.sqrt(TRADING_DAYS)
    c5.markdown(var_card("Ann. Return (Hist.)", f"{ann_ret*100:.2f}%", "", "#00ffb4" if ann_ret > 0 else "#ff4f6a"), unsafe_allow_html=True)
    c6.markdown(var_card("Ann. Volatility",     f"{ann_vol*100:.2f}%", "", "#94a3b8"), unsafe_allow_html=True)
    c7.markdown(var_card("Observations",         f"{len(result['port_ret']):,}", f"~{len(result['port_ret'])//252} years", "#94a3b8"), unsafe_allow_html=True)
    c8.markdown(var_card("Portfolio Value",       f"${portfolio_value:,.0f}", "Input value", "#94a3b8"), unsafe_allow_html=True)

    # ── Interpretation box ────────────────────────────────────────────────────
    interp_color = "#ff4f6a" if result["var_1d"] > 0.03 else "#fbbf24" if result["var_1d"] > 0.015 else "#00ffb4"
    risk_label   = "HIGH RISK" if result["var_1d"] > 0.03 else "MODERATE RISK" if result["var_1d"] > 0.015 else "LOW RISK"
    st.markdown(f"""
    <div style="background:rgba(255,79,106,0.05);border:1px solid rgba(255,79,106,0.15);
    border-left:4px solid {interp_color};border-radius:10px;padding:16px 20px;margin:16px 0;">
      <div style="font-size:11px;font-weight:700;color:{interp_color};letter-spacing:1px;margin-bottom:8px">
        {risk_label}
      </div>
      <div style="font-size:13px;color:#64748b;line-height:1.7">
        At <strong style="color:#94a3b8">{confidence*100:.0f}% confidence</strong>, 
        your portfolio is not expected to lose more than 
        <strong style="color:#ff4f6a">{result['var_1d']*100:.2f}%</strong> in a single day
        {f'(<strong style="color:#ff4f6a">${dollar_var:,.0f}</strong>)' if dollar_var else ''}.
        Over a 10-day horizon this extends to 
        <strong style="color:#ff4f6a">{result['var_10d']*100:.2f}%</strong>.
        The Expected Shortfall (CVaR) — the average loss beyond VaR — is 
        <strong style="color:#fbbf24">{result['cvar_1d']*100:.2f}%</strong>, 
        giving a fuller picture of tail risk.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown('<div style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;margin:20px 0 12px">Distribution Analysis</div>', unsafe_allow_html=True)

    st.plotly_chart(
        plot_return_dist(result, confidence, result["method"]),
        use_container_width=True,
    )

    if method == "Monte Carlo" and "sim_rets" in result:
        st.plotly_chart(
            plot_mc_simulation(result["sim_rets"], result["var_1d"], confidence),
            use_container_width=True,
        )

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(plot_correlation(corr_matrix), use_container_width=True)
    with col_r:
        st.plotly_chart(
            plot_rolling_var(result["port_ret"], confidence),
            use_container_width=True,
        )

    st.plotly_chart(
        plot_cumulative(result["port_ret"], tickers, weights, returns),
        use_container_width=True,
    )

    # ── Per-asset breakdown ───────────────────────────────────────────────────
    st.markdown('<div style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;margin:20px 0 12px">Per-Asset Risk Breakdown</div>', unsafe_allow_html=True)

    asset_stats = []
    for i, ticker in enumerate(tickers):
        r      = returns[ticker]
        ind_var = -np.percentile(r, (1 - confidence) * 100)
        asset_stats.append({
            "Ticker":        ticker,
            "Weight":        f"{weights[i]*100:.1f}%",
            "Ann. Return":   f"{r.mean()*TRADING_DAYS*100:.2f}%",
            "Ann. Volatility": f"{r.std()*np.sqrt(TRADING_DAYS)*100:.2f}%",
            f"Ind. VaR ({confidence*100:.0f}%)": f"{ind_var*100:.3f}%",
            "Sharpe":        f"{(r.mean()*TRADING_DAYS - rfr) / (r.std()*np.sqrt(TRADING_DAYS)):.3f}",
        })

    st.dataframe(
        pd.DataFrame(asset_stats).set_index("Ticker"),
        use_container_width=True,
    )

    # ── Disclaimer ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:11px;color:#1e293b;margin-top:20px;padding-top:16px;
    border-top:1px solid rgba(255,255,255,0.04);line-height:1.6">
    ⚠ VaR is a statistical measure and does not guarantee maximum loss. Historical data does not 
    predict future performance. CVaR/Expected Shortfall provides a more complete view of tail risk. 
    This tool is for informational purposes only and does not constitute financial advice.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
