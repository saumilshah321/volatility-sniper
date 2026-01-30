"""
Bloomberg Terminal-style Streamlit Dashboard.

Interactive trading dashboard with monochrome aesthetic, terminal fonts,
and high information density. Displays strategy performance metrics,
price charts with signals, and trade logs.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Tuple
import json

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent directory to path for core imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.theme import (
    BG_BLACK, BG_DARK_GREY, TERMINAL_GREEN, SIGNAL_RED,
    TEXT_WHITE, TEXT_GREY, FONT_MONO
)
from core.config import load_config, validate_config, export_config
from core.loader import load_and_prepare_data
from core.indicators import add_indicators
from core.strategy_donchian import generate_signals
from core.backtester import run_backtest
from core.metrics import calculate_all_metrics
from core.exporter import export_all


def inject_custom_css() -> None:
    """Inject custom CSS from style.css file."""
    css_path = Path(__file__).parent / 'style.css'
    
    if css_path.exists():
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    else:
        # Fallback inline CSS if file not found
        st.markdown(f"""
        <style>
        body {{ background-color: {BG_BLACK}; color: {TEXT_WHITE}; font-family: {FONT_MONO}; }}
        * {{ border-radius: 0 !important; }}
        </style>
        """, unsafe_allow_html=True)


def render_sidebar() -> Dict[str, Any]:
    """
    Render sidebar controls for strategy parameters.
    
    Returns:
        Dictionary with user-selected parameters
    """
    st.sidebar.title("⚡ VOLATILITY SNIPER")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("INDICATOR PARAMETERS")
    
    rsi_period = st.sidebar.number_input(
        "RSI Period",
        min_value=2,
        max_value=50,
        value=14,
        step=1,
        help="Period for RSI calculation"
    )
    
    bb_period = st.sidebar.number_input(
        "Bollinger Bands Period",
        min_value=5,
        max_value=100,
        value=20,
        step=1,
        help="Period for Bollinger Bands SMA"
    )
    
    bb_std_dev = st.sidebar.number_input(
        "Bollinger Bands Std Dev",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.1,
        help="Standard deviation multiplier"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("RISK MANAGEMENT")
    
    stop_loss_pct = st.sidebar.number_input(
        "Stop Loss %",
        min_value=0.1,
        max_value=10.0,
        value=2.0,
        step=0.1,
        help="Stop loss as percentage of entry price"
    )
    
    max_drawdown_pct = st.sidebar.number_input(
        "Max Drawdown %",
        min_value=5.0,
        max_value=50.0,
        value=20.0,
        step=1.0,
        help="Maximum drawdown before halting trading"
    )
    
    risk_per_trade = st.sidebar.number_input(
        "Risk Per Trade %",
        min_value=0.1,
        max_value=10.0,
        value=2.0,
        step=0.1,
        help="Percentage of capital to risk per trade"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("BACKTESTING")
    
    initial_capital = st.sidebar.number_input(
        "Initial Capital ($)",
        min_value=1000,
        max_value=10000000,
        value=100000,
        step=1000,
        help="Starting capital for backtest"
    )
    
    st.sidebar.markdown("---")
    
    run_button = st.sidebar.button("🚀 RUN BACKTEST", type="primary", use_container_width=True)
    export_button = st.sidebar.button("💾 EXPORT RESULTS", use_container_width=True)
    
    return {
        'rsi_period': rsi_period,
        'bb_period': bb_period,
        'bb_std_dev': bb_std_dev,
        'stop_loss_pct': stop_loss_pct / 100,
        'max_drawdown_pct': max_drawdown_pct / 100,
        'risk_per_trade': risk_per_trade / 100,
        'initial_capital': initial_capital,
        'run_button': run_button,
        'export_button': export_button
    }


def render_metrics_cards(metrics: Dict[str, Any]) -> None:
    """
    Render performance metrics with animated counters and premium design.
    """
    # Animated Metrics Header
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h2 style="font-size: 2rem; font-weight: 800; 
                   background: linear-gradient(135deg, #00f0ff 0%, #b24bf3 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                   text-transform: uppercase; letter-spacing: 3px;">
            📊 Performance Metrics
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        net_profit = metrics.get('final_equity', 0) - metrics.get('initial_capital', 0)
        total_return = metrics.get('total_return', 0)
        profit_color = "#00ff88" if net_profit >= 0 else "#ff3366"
        
        # Animated profit card with glow effect
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0, 240, 255, 0.05) 0%, rgba(178, 75, 243, 0.05) 100%);
                    border: 2px solid {profit_color}30;
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 40px {profit_color}20;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 4px; 
                        background: linear-gradient(90deg, transparent, {profit_color}, transparent);
                        animation: shimmer 2s infinite;"></div>
            <div style="color: #8b92b0; font-size: 0.9rem; font-weight: 700; 
                        text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;">
                💰 Net Profit
            </div>
            <div style="color: {profit_color}; font-size: 3rem; font-weight: 900; 
                        font-family: 'Courier New', monospace; text-shadow: 0 0 20px {profit_color}50;">
                ${net_profit:,.2f}
            </div>
            <div style="color: {profit_color}; font-size: 1.3rem; font-weight: 700; margin-top: 0.5rem;">
                {total_return:+.2%}
            </div>
        </div>
        <style>
        @keyframes shimmer {{
            0%, 100% {{ transform: translateX(-100%); }}
            50% {{ transform: translateX(100%); }}
        }}
        </style>
        """, unsafe_allow_html=True)
    
    with col2:
        max_dd = metrics.get('max_drawdown', 0)
        dd_duration = metrics.get('max_drawdown_duration', 0)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(255, 51, 102, 0.05) 0%, rgba(255, 170, 0, 0.05) 100%);
                    border: 2px solid #ff336630;
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 40px #ff336620;
                    transition: all 0.3s ease;">
            <div style="color: #8b92b0; font-size: 0.9rem; font-weight: 700; 
                        text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;">
                📉 Max Drawdown
            </div>
            <div style="color: #ff3366; font-size: 3rem; font-weight: 900; 
                        font-family: 'Courier New', monospace; text-shadow: 0 0 20px #ff336650;">
                {max_dd:.2%}
            </div>
            <div style="color: #8b92b0; font-size: 1rem; margin-top: 0.5rem;">
                Duration: {dd_duration} bars
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        win_rate = metrics.get('win_rate', 0)
        total_trades = metrics.get('total_trades', 0)
        win_color = "#00ff88" if win_rate >= 0.5 else "#ffaa00"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0, 255, 136, 0.05) 0%, rgba(0, 240, 255, 0.05) 100%);
                    border: 2px solid {win_color}30;
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 40px {win_color}20;
                    transition: all 0.3s ease;">
            <div style="color: #8b92b0; font-size: 0.9rem; font-weight: 700; 
                        text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;">
                🎯 Win Rate
            </div>
            <div style="color: {win_color}; font-size: 3rem; font-weight: 900; 
                        font-family: 'Courier New', monospace; text-shadow: 0 0 20px {win_color}50;">
                {win_rate:.1%}
            </div>
            <div style="color: #8b92b0; font-size: 1rem; margin-top: 0.5rem;">
                Trades: {total_trades}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Secondary metrics row with progress bars
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    
    col4, col5, col6, col7 = st.columns(4)
    
    metrics_data = [
        ("⭐ Sharpe", metrics.get('sharpe_ratio', 0), "#00f0ff", 3),
        ("💎 Profit Factor", metrics.get('profit_factor', 0), "#b24bf3", 3),
        ("✅ Avg Win", metrics.get('avg_win_pct', 0) * 100, "#00ff88", 10),
        ("❌ Avg Loss", abs(metrics.get('avg_loss_pct', 0)) * 100, "#ff3366", 10)
    ]
    
    for col, (label, value, color, max_val) in zip([col4, col5, col6, col7], metrics_data):
        with col:
            progress = min(abs(value) / max_val, 1.0) if max_val > 0 else 0
            display_val = f"{value:.2f}" if max_val <= 3 else f"{value:.1f}%"
            
            st.markdown(f"""
            <div style="background: rgba(21, 25, 50, 0.6);
                        border: 1px solid {color}30;
                        border-radius: 12px;
                        padding: 1.5rem;
                        text-align: center;">
                <div style="color: #8b92b0; font-size: 0.75rem; font-weight: 600; 
                            text-transform: uppercase; margin-bottom: 0.5rem;">
                    {label}
                </div>
                <div style="color: {color}; font-size: 1.8rem; font-weight: 800; 
                            font-family: 'Courier New', monospace;">
                    {display_val}
                </div>
                <div style="background: rgba(0, 0, 0, 0.3); height: 6px; border-radius: 3px; 
                            margin-top: 0.75rem; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, {color}, {color}80); 
                                height: 100%; width: {progress * 100}%; 
                                border-radius: 3px; transition: width 1s ease;
                                box-shadow: 0 0 10px {color}50;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_price_chart(df: pd.DataFrame, trades: pd.DataFrame) -> None:
    """
    Render interactive price chart with Bollinger Bands, signals, and RSI subplot.
    
    Args:
        df: DataFrame with OHLCV data, indicators, and signals
        trades: DataFrame with completed trades
    """
    # Create subplots: price chart + RSI
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('PRICE CHART', 'RSI-14')
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color=TERMINAL_GREEN,
            decreasing_line_color=SIGNAL_RED
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['bb_upper'],
            name='BB Upper',
            line=dict(color=TEXT_GREY, width=1, dash='dot'),
            opacity=0.5
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['bb_middle'],
            name='BB Middle',
            line=dict(color=TEXT_GREY, width=1),
            opacity=0.7
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['bb_lower'],
            name='BB Lower',
            line=dict(color=TEXT_GREY, width=1, dash='dot'),
            opacity=0.5
        ),
        row=1, col=1
    )
    
    # Buy signals (Long entry)
    long_signals = df[df['signal'] == 1]
    if len(long_signals) > 0:
        fig.add_trace(
            go.Scatter(
                x=long_signals.index,
                y=long_signals['close'],
                mode='markers',
                name='Long Entry',
                marker=dict(
                    symbol='triangle-up',
                    size=12,
                    color=TERMINAL_GREEN,
                    line=dict(color=BG_BLACK, width=1)
                )
            ),
            row=1, col=1
        )
    
    # Sell signals (Short entry)
    short_signals = df[df['signal'] == -1]
    if len(short_signals) > 0:
        fig.add_trace(
            go.Scatter(
                x=short_signals.index,
                y=short_signals['close'],
                mode='markers',
                name='Short Entry',
                marker=dict(
                    symbol='triangle-down',
                    size=12,
                    color=SIGNAL_RED,
                    line=dict(color=BG_BLACK, width=1)
                )
            ),
            row=1, col=1
        )
    
    # RSI indicator
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['rsi_14'],
            name='RSI',
            line=dict(color=TEXT_WHITE, width=2)
        ),
        row=2, col=1
    )
    
    # RSI threshold lines
    fig.add_hline(y=70, line_dash="dash", line_color=SIGNAL_RED, opacity=0.5, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color=TEXT_GREY, opacity=0.3, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=TERMINAL_GREEN, opacity=0.5, row=2, col=1)
    
    # Update layout with Bloomberg Terminal theme
    fig.update_layout(
        plot_bgcolor=BG_BLACK,
        paper_bgcolor=BG_BLACK,
        font=dict(family=FONT_MONO, color=TEXT_WHITE, size=12),
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True,
        legend=dict(
            bgcolor=BG_DARK_GREY,
            bordercolor=TEXT_GREY,
            borderwidth=1
        ),
        hovermode='x unified'
    )
    
    # Update axes
    fig.update_xaxes(
        gridcolor='#1a1a1a',
        showgrid=True,
        zeroline=False,
        color=TEXT_WHITE
    )
    
    fig.update_yaxes(
        gridcolor='#1a1a1a',
        showgrid=True,
        zeroline=False,
        color=TEXT_WHITE
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_trade_log(trades: pd.DataFrame) -> None:
    """
    Render trade log table with conditional formatting.
    
    Args:
        trades: DataFrame with completed trades
    """
    st.subheader("TRADE LOG")
    
    if len(trades) == 0:
        st.warning("No trades executed during backtest period")
        return
    
    # Format DataFrame for display
    display_df = trades.copy()
    
    # Select and reorder columns
    columns_to_display = [
        'trade_id', 'entry_timestamp', 'exit_timestamp', 'direction',
        'entry_price', 'exit_price', 'position_size', 'pnl', 'pnl_percent', 'exit_reason'
    ]
    
    display_df = display_df[columns_to_display]
    
    # Format timestamps
    display_df['entry_timestamp'] = pd.to_datetime(display_df['entry_timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    display_df['exit_timestamp'] = pd.to_datetime(display_df['exit_timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Format prices
    display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:.2f}")
    display_df['exit_price'] = display_df['exit_price'].apply(lambda x: f"${x:.2f}")
    
    # Format P&L
    display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:.2f}")
    display_df['pnl_percent'] = display_df['pnl_percent'].apply(lambda x: f"{x:.2%}")
    
    # Rename columns for display
    display_df.columns = [
        'ID', 'Entry Time', 'Exit Time', 'Direction',
        'Entry Price', 'Exit Price', 'Size', 'P&L', 'P&L %', 'Exit Reason'
    ]
    
    # Display with custom styling
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )


def export_results(
    trades: pd.DataFrame, 
    equity_curve: list,
    metrics: Dict[str, Any], 
    config: Dict[str, Any]
) -> None:
    """
    Export all submission artifacts using centralized exporter.
    
    Args:
        trades: Trade log DataFrame
        equity_curve: List of (timestamp, portfolio_value) tuples
        metrics: Performance metrics dictionary
        config: Configuration used for backtest
    """
    try:
        with st.spinner('📦 Generating submission artifacts...'):
            # Use centralized exporter
            exported_files = export_all(
                trades=trades,
                equity_curve=equity_curve,
                metrics=metrics,
                config=config,
                base_output_dir=Path(__file__).parent.parent / 'output'
            )
            
            # Display success message with all file paths
            success_msg = "✓ **All submission artifacts exported successfully!**\n\n"
            success_msg += "**Files Generated:**\n"
            for artifact_type, file_path in exported_files.items():
                success_msg += f"- **{artifact_type}**: `{file_path}`\n"
            
            st.success(success_msg)
            
            # Show directory path
            output_dir = exported_files['equity_curve'].parent
            st.info(f"📁 All files saved to: `{output_dir}`")
            
    except Exception as e:
        st.error(f"❌ Error exporting results: {e}")
        st.exception(e)


def main():
    """Main Streamlit application entry point."""
    
    # Page configuration
    st.set_page_config(
        page_title="Volatility Sniper | Bloomberg Terminal",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inject custom CSS
    inject_custom_css()
    
    # Main title
    st.markdown(f"""
    <h1 style='text-align: center; color: {TERMINAL_GREEN}; font-family: {FONT_MONO}; 
    letter-spacing: 4px; font-size: 36px; margin-bottom: 0;'>
    ⚡ VOLATILITY SNIPER
    </h1>
    <p style='text-align: center; color: {TEXT_GREY}; font-size: 14px; letter-spacing: 2px;'>
    DONCHIAN MOMENTUM BREAKOUT | TREND FOLLOWING SYSTEM
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Render sidebar and get parameters
    params = render_sidebar()
    
    # Initialize session state
    if 'backtest_complete' not in st.session_state:
        st.session_state.backtest_complete = False
    
    # Handle Run Backtest button
    if params['run_button']:
        with st.spinner('⚡ Running backtest simulation...'):
            try:
                # Load base configuration
                config_path = Path(__file__).parent.parent / 'config' / 'strategy_config.yaml'
                config = load_config(str(config_path))
                
                # Update config with sidebar parameters
                config['indicators']['rsi_period'] = params['rsi_period']
                config['indicators']['bb_period'] = params['bb_period']
                config['indicators']['bb_std_dev'] = params['bb_std_dev']
                config['risk_management']['stop_loss_pct'] = params['stop_loss_pct']
                config['risk_management']['max_drawdown_pct'] = params['max_drawdown_pct']
                config['risk_management']['risk_per_trade'] = params['risk_per_trade']
                config['backtesting']['initial_capital'] = params['initial_capital']
                
                validate_config(config)
                
                # Execute backtest workflow
                st.info("📊 Loading dataset...")
                df = load_and_prepare_data(config['data']['source_url'])
                
                st.info("📈 Calculating indicators...")
                df_with_indicators = add_indicators(df, config)
                
                st.info("🎯 Generating signals...")
                df_with_signals = generate_signals(df_with_indicators, config)
                
                st.info("⚙️ Running backtest...")
                trades, portfolio_state = run_backtest(df_with_signals, config)
                
                st.info("📊 Calculating metrics...")
                metrics = calculate_all_metrics(
                    trades,
                    portfolio_state.get('equity_curve', []),
                    config
                )
                
                # Store in session state
                st.session_state.backtest_complete = True
                st.session_state.trades = trades
                st.session_state.metrics = metrics
                st.session_state.df_with_signals = df_with_signals
                st.session_state.config = config
                st.session_state.portfolio_state = portfolio_state
                
                st.success("✓ Backtest completed successfully!")
                
            except Exception as e:
                st.error(f"❌ Error during backtest: {e}")
                st.exception(e)
    
    # Handle Export Results button
    if params['export_button']:
        if st.session_state.backtest_complete:
            export_results(
                trades=st.session_state.trades,
                equity_curve=st.session_state.portfolio_state.get('equity_curve', []),
                metrics=st.session_state.metrics,
                config=st.session_state.config
            )
        else:
            st.warning("⚠️ Please run backtest first before exporting results")
    
    # Display results if backtest completed
    if st.session_state.backtest_complete:
        st.markdown("---")
        
        # Metrics cards
        render_metrics_cards(st.session_state.metrics)
        
        st.markdown("---")
        
        # Price chart
        render_price_chart(
            st.session_state.df_with_signals,
            st.session_state.trades
        )
        
        st.markdown("---")
        
        # Trade log
        render_trade_log(st.session_state.trades)
        
        # Additional metrics in expandable section
        with st.expander("📊 DETAILED METRICS"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Sharpe Ratio", f"{st.session_state.metrics.get('sharpe_ratio', 0):.2f}")
                st.metric("Sortino Ratio", f"{st.session_state.metrics.get('sortino_ratio', 0):.2f}")
            
            with col2:
                st.metric("Profit Factor", f"{st.session_state.metrics.get('profit_factor', 0):.2f}")
                st.metric("Avg Trade Duration", f"{st.session_state.metrics.get('avg_trade_duration', 0):.1f} hrs")
            
            with col3:
                st.metric("Annualized Return", f"{st.session_state.metrics.get('annualized_return', 0):.2%}")
                st.metric("Volatility", f"{st.session_state.metrics.get('volatility', 0):.2%}")


if __name__ == '__main__':
    main()
