"""
portfolio_optimiser.py
Equinox — Portfolio Optimiser Module
Converted from Colab by Saksham Minde
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from scipy.optimize import minimize
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')


# ── Constants ─────────────────────────────────────────────────────────────────
TRADING_DAYS = 252
BRAND_DARK   = "#0f1923"
BRAND_MID    = "#1a2d45"
ACCENT       = "#00ffcc"


# ── Core maths ────────────────────────────────────────────────────────────────
def portfolio_performance(weights, expected_returns, cov_matrix, rfr):
    ret    = np.dot(weights, expected_returns)
    vol    = np.sqrt(weights @ cov_matrix.values @ weights)
    sharpe = (ret - rfr) / vol if vol > 0 else 0
    return ret, vol, sharpe


def run_optimisation(expected_returns, cov_matrix, rfr, num_portfolios=3000):
    n   = len(expected_returns)
    w0  = np.array([1.0 / n] * n)
    bounds      = tuple((0.0, 1.0) for _ in range(n))
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

    def neg_sharpe(w):
        r, v, _ = portfolio_performance(w, expected_returns, cov_matrix, rfr)
        return -(r - rfr) / v if v > 0 else 0

    def port_vol(w):
        return portfolio_performance(w, expected_returns, cov_matrix, rfr)[1]

    def port_ret(w):
        return portfolio_performance(w, expected_returns, cov_matrix, rfr)[0]

    # Max Sharpe
    res_ms = minimize(neg_sharpe, w0, method='SLSQP',
                      bounds=bounds, constraints=constraints,
                      options={'maxiter': 1000, 'ftol': 1e-9})
    w_ms = res_ms.x
    r_ms, v_ms, s_ms = portfolio_performance(w_ms, expected_returns, cov_matrix, rfr)

    # Min Variance
    res_mv = minimize(port_vol, w0, method='SLSQP',
                      bounds=bounds, constraints=constraints,
                      options={'maxiter': 1000, 'ftol': 1e-9})
    w_mv = res_mv.x
    r_mv, v_mv, s_mv = portfolio_performance(w_mv, expected_returns, cov_matrix, rfr)

    # Efficient Frontier
    target_rets = np.linspace(
        expected_returns.min() * 0.8,
        expected_returns.max() * 1.1, 150
    )
    ef_vols, ef_rets = [], []
    for target in target_rets:
        cons = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w, t=target: port_ret(w) - t}
        ]
        res = minimize(port_vol, w0, method='SLSQP',
                       bounds=bounds, constraints=cons,
                       options={'maxiter': 500, 'ftol': 1e-9})
        if res.success:
            ef_vols.append(res.fun)
            ef_rets.append(target)

    # Monte Carlo
    np.random.seed(42)
    sim_rets, sim_vols, sim_sharpes, sim_weights = [], [], [], []
    for _ in range(num_portfolios):
        w = np.random.dirichlet(np.ones(n))
        r, v, s = portfolio_performance(w, expected_returns, cov_matrix, rfr)
        sim_rets.append(r); sim_vols.append(v)
        sim_sharpes.append(s); sim_weights.append(w)

    return {
        'w_ms': w_ms, 'r_ms': r_ms, 'v_ms': v_ms, 's_ms': s_ms,
        'w_mv': w_mv, 'r_mv': r_mv, 'v_mv': v_mv, 's_mv': s_mv,
        'ef_vols': np.array(ef_vols), 'ef_rets': np.array(ef_rets),
        'sim_rets': np.array(sim_rets), 'sim_vols': np.array(sim_vols),
        'sim_sharpes': np.array(sim_sharpes), 'sim_weights': np.array(sim_weights),
    }


# ── Charts ────────────────────────────────────────────────────────────────────
def plot_efficient_frontier(tickers, weights, expected_returns, volatility,
                             port_ret, port_vol, port_sharpe, opt, rfr):
    fig = go.Figure()

    # Monte Carlo scatter
    fig.add_trace(go.Scatter(
        x=opt['sim_vols'] * 100, y=opt['sim_rets'] * 100,
        mode='markers',
        marker=dict(size=3, color=opt['sim_sharpes'],
                    colorscale='Plasma', opacity=0.4,
                    colorbar=dict(title='Sharpe', thickness=12)),
        name='Simulated Portfolios', hovertemplate='Vol: %{x:.1f}%<br>Ret: %{y:.1f}%'
    ))

    # Efficient Frontier
    fig.add_trace(go.Scatter(
        x=opt['ef_vols'] * 100, y=opt['ef_rets'] * 100,
        mode='lines', line=dict(color='#00ffcc', width=3),
        name='Efficient Frontier'
    ))

    # CML
    cml_x = np.linspace(0, opt['ef_vols'].max() * 100 * 1.1, 200)
    cml_y = rfr * 100 + opt['s_ms'] * cml_x
    fig.add_trace(go.Scatter(
        x=cml_x, y=cml_y, mode='lines',
        line=dict(color='#ffdd57', width=1.8, dash='dash'),
        name='Capital Market Line'
    ))

    # Max Sharpe
    fig.add_trace(go.Scatter(
        x=[opt['v_ms'] * 100], y=[opt['r_ms'] * 100],
        mode='markers', marker=dict(symbol='star', size=18, color='#ffdd57',
                                     line=dict(color='black', width=1)),
        name=f"Max Sharpe ({opt['s_ms']:.2f})",
        hovertemplate=f"Max Sharpe<br>Return: {opt['r_ms']*100:.1f}%<br>Vol: {opt['v_ms']*100:.1f}%"
    ))

    # Min Variance
    fig.add_trace(go.Scatter(
        x=[opt['v_mv'] * 100], y=[opt['r_mv'] * 100],
        mode='markers', marker=dict(symbol='diamond', size=14, color='#ff6b9d',
                                     line=dict(color='black', width=1)),
        name=f"Min Variance (σ={opt['v_mv']*100:.1f}%)",
        hovertemplate=f"Min Variance<br>Return: {opt['r_mv']*100:.1f}%<br>Vol: {opt['v_mv']*100:.1f}%"
    ))

    # Your Portfolio
    fig.add_trace(go.Scatter(
        x=[port_vol * 100], y=[port_ret * 100],
        mode='markers', marker=dict(symbol='circle', size=16, color='#ff4444',
                                     line=dict(color='white', width=2)),
        name=f"Your Portfolio (SR={port_sharpe:.2f})",
        hovertemplate=f"Your Portfolio<br>Return: {port_ret*100:.1f}%<br>Vol: {port_vol*100:.1f}%"
    ))

    # Individual stocks
    colors = px.colors.qualitative.Set2
    for i, ticker in enumerate(tickers):
        fig.add_trace(go.Scatter(
            x=[volatility[ticker] * 100], y=[expected_returns[ticker] * 100],
            mode='markers+text',
            marker=dict(symbol='triangle-up', size=12,
                        color=colors[i % len(colors)],
                        line=dict(color='white', width=1)),
            text=[ticker], textposition='top right',
            textfont=dict(size=10, color=colors[i % len(colors)]),
            name=ticker,
            hovertemplate=f"{ticker}<br>Return: {expected_returns[ticker]*100:.1f}%<br>Vol: {volatility[ticker]*100:.1f}%"
        ))

    fig.update_layout(
        title=dict(text='Markowitz Efficient Frontier', font=dict(size=18)),
        xaxis_title='Annualised Volatility (%)',
        yaxis_title='Annualised Expected Return (%)',
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color='#ccccee'),
        legend=dict(bgcolor='rgba(26,45,69,0.8)', bordercolor='#444466'),
        height=550,
    )
    return fig


def plot_weights(tickers, weights_dict_list):
    """weights_dict_list: list of (label, weights_array, color)"""
    fig = go.Figure()
    colors = px.colors.qualitative.Set2

    for label, w, _ in weights_dict_list:
        fig.add_trace(go.Bar(
            name=label, x=tickers, y=w * 100,
            text=[f"{v:.1f}%" for v in w * 100],
            textposition='outside',
            marker_color=[colors[i % len(colors)] for i in range(len(tickers))]
        ))

    fig.update_layout(
        barmode='group',
        title='Portfolio Weight Comparison',
        yaxis_title='Weight (%)',
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color='#ccccee'),
        height=400,
    )
    return fig


def plot_rolling(log_returns, weights, rfr):
    port_daily = log_returns @ weights
    window = 63

    rolling_ret    = port_daily.rolling(window).mean() * TRADING_DAYS
    rolling_vol    = port_daily.rolling(window).std()  * np.sqrt(TRADING_DAYS)
    rolling_sharpe = (rolling_ret - rfr) / rolling_vol

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rolling_ret.index, y=rolling_ret * 100,
                              name='Rolling Return (%)', line=dict(color='#00ffcc')))
    fig.add_trace(go.Scatter(x=rolling_vol.index, y=rolling_vol * 100,
                              name='Rolling Volatility (%)', line=dict(color='#ff6b9d'),
                              yaxis='y2'))
    fig.update_layout(
        title=f'Rolling {window}-Day Portfolio Statistics',
        yaxis=dict(title='Return / Vol (%)', color='#ccccee'),
        yaxis2=dict(title='Volatility (%)', overlaying='y', side='right', color='#ff6b9d'),
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color='#ccccee'), height=380,
    )
    return fig


def plot_correlation(corr_matrix):
    fig = px.imshow(
        corr_matrix, text_auto='.2f', color_continuous_scale='RdYlGn',
        zmin=-1, zmax=1, title='Correlation Matrix'
    )
    fig.update_layout(
        plot_bgcolor=BRAND_DARK, paper_bgcolor=BRAND_DARK,
        font=dict(color='#ccccee'), height=380,
    )
    return fig


# ── Main Streamlit page ───────────────────────────────────────────────────────
def show_optimiser():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f1923,#1a2d45);padding:2rem;
    border-radius:12px;margin-bottom:1.5rem;text-align:center;">
      <h2 style="color:#f0e6d3;margin:0;">📐 Portfolio Optimiser</h2>
      <p style="color:#8fa8c8;margin:.4rem 0 0;">Markowitz MPT · Monte Carlo · SLSQP Optimisation</p>
    </div>
    """, unsafe_allow_html=True)

    # ── User inputs ───────────────────────────────────────────────────────────
    st.markdown("### Define Your Portfolio")

    col1, col2 = st.columns(2)
    with col1:
        tickers_raw = st.text_input(
            "Stock Tickers (comma-separated)",
            value="AAPL, MSFT, GOOGL, AMZN, TSLA",
            help="Use Yahoo Finance format. Indian stocks: RELIANCE.NS, TCS.NS"
        )
    with col2:
        weights_raw = st.text_input(
            "Current Weights (comma-separated, must sum to 1)",
            value="0.30, 0.25, 0.20, 0.15, 0.10"
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        start_date = st.date_input("Start Date", value=date(2020, 1, 1))
    with col4:
        end_date = st.date_input("End Date", value=date(2024, 12, 31))
    with col5:
        rfr = st.number_input("Risk-Free Rate (%)", value=5.0, step=0.25) / 100

    num_portfolios = st.slider("Monte Carlo Simulations", 1000, 10000, 3000, 500)

    run = st.button("Run Optimisation", use_container_width=True)

    if not run:
        return

    # ── Parse inputs ──────────────────────────────────────────────────────────
    try:
        tickers = [t.strip().upper() for t in tickers_raw.split(',')]
        weights = np.array([float(w.strip()) for w in weights_raw.split(',')])
        assert abs(sum(weights) - 1.0) < 1e-4, "Weights must sum to 1.0"
        assert len(tickers) == len(weights), "Number of tickers must match weights"
    except Exception as e:
        st.error(f"Input error: {e}")
        return

    # ── Fetch data ────────────────────────────────────────────────────────────
    with st.spinner("Fetching price data from Yahoo Finance..."):
        try:
            raw = yf.download(tickers, start=str(start_date), end=str(end_date),
                              auto_adjust=True, progress=False)
            if isinstance(raw.columns, pd.MultiIndex):
                prices = raw['Close'][tickers].dropna()
            else:
                prices = raw[['Close']].dropna()
                prices.columns = tickers

            if prices.empty:
                st.error("No data returned. Check your tickers.")
                return

            log_returns = np.log(prices / prices.shift(1)).dropna()
            expected_returns = log_returns.mean() * TRADING_DAYS
            volatility       = log_returns.std()  * np.sqrt(TRADING_DAYS)
            cov_matrix       = log_returns.cov()  * TRADING_DAYS
            corr_matrix      = log_returns.corr()

        except Exception as e:
            st.error(f"Data fetch failed: {e}")
            return

    # ── Run optimisation ──────────────────────────────────────────────────────
    with st.spinner(f"Running Monte Carlo ({num_portfolios:,} simulations) + SLSQP optimisation..."):
        port_ret, port_vol, port_sharpe = portfolio_performance(
            weights, expected_returns, cov_matrix, rfr)
        opt = run_optimisation(expected_returns, cov_matrix, rfr, num_portfolios)

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Current Portfolio Metrics")

    m1, m2, m3 = st.columns(3)
    m1.metric("Expected Return (Ann.)", f"{port_ret*100:.2f}%")
    m2.metric("Volatility (Ann.)",      f"{port_vol*100:.2f}%")
    m3.metric("Sharpe Ratio",           f"{port_sharpe:.4f}")

    # ── Comparison table ──────────────────────────────────────────────────────
    st.markdown("### Portfolio Comparison")

    def fmt_weights(w):
        return {t: f"{v*100:.1f}%" for t, v in zip(tickers, w)}

    comparison = pd.DataFrame([
        {'Portfolio': 'Your Current Portfolio',
         'Return': f"{port_ret*100:.2f}%", 'Volatility': f"{port_vol*100:.2f}%",
         'Sharpe': f"{port_sharpe:.4f}", **fmt_weights(weights)},
        {'Portfolio': '★ Max Sharpe Portfolio',
         'Return': f"{opt['r_ms']*100:.2f}%", 'Volatility': f"{opt['v_ms']*100:.2f}%",
         'Sharpe': f"{opt['s_ms']:.4f}", **fmt_weights(opt['w_ms'])},
        {'Portfolio': '◆ Min Variance Portfolio',
         'Return': f"{opt['r_mv']*100:.2f}%", 'Volatility': f"{opt['v_mv']*100:.2f}%",
         'Sharpe': f"{opt['s_mv']:.4f}", **fmt_weights(opt['w_mv'])},
    ]).set_index('Portfolio')

    st.dataframe(comparison, use_container_width=True)

    # ── Deviation insight ─────────────────────────────────────────────────────
    ef_df = pd.DataFrame({'vol': opt['ef_vols'], 'ret': opt['ef_rets']})
    if not ef_df.empty:
        closest = (ef_df['vol'] - port_vol).abs().idxmin()
        ef_ret_at_vol = ef_df.loc[closest, 'ret']
        deviation = ef_ret_at_vol - port_ret

        if deviation < -0.01:
            st.warning(f"⚠️ At your risk level ({port_vol*100:.1f}% vol), the Efficient Frontier offers "
                       f"{ef_ret_at_vol*100:.1f}% return. Rebalancing could improve returns by ~{abs(deviation)*100:.1f}%.")
        else:
            st.success(f"✅ Your portfolio is close to or above the Efficient Frontier. Well positioned!")

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown("### Efficient Frontier")
    st.plotly_chart(
        plot_efficient_frontier(tickers, weights, expected_returns, volatility,
                                 port_ret, port_vol, port_sharpe, opt, rfr),
        use_container_width=True
    )

    st.markdown("### Weight Allocation Comparison")
    st.plotly_chart(
        plot_weights(tickers, [
            ('Your Portfolio',       weights,       '#ff4444'),
            ('Max Sharpe Portfolio', opt['w_ms'],   '#ffdd57'),
            ('Min Variance',         opt['w_mv'],   '#ff6b9d'),
        ]),
        use_container_width=True
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Correlation Matrix")
        st.plotly_chart(plot_correlation(corr_matrix), use_container_width=True)
    with col_b:
        st.markdown("### Individual Stock Statistics")
        stats = pd.DataFrame({
            'Expected Return': expected_returns.map('{:.2%}'.format),
            'Volatility':      volatility.map('{:.2%}'.format),
            'Sharpe Ratio':    ((expected_returns - rfr) / volatility).map('{:.3f}'.format)
        })
        st.dataframe(stats, use_container_width=True)

    st.markdown("### Rolling Portfolio Statistics")
    st.plotly_chart(plot_rolling(log_returns, weights, rfr), use_container_width=True)

    st.markdown("---")
    st.caption("⚠️ Past performance does not guarantee future returns. This is not investment advice.")
