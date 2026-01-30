# donchian momentum breakout strategy

from typing import Dict, Any
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_donchian_channels(df: pd.DataFrame, entry_window: int = 20, exit_window: int = 10) -> pd.DataFrame:
    """Add Donchian channel indicators to dataframe"""
    df = df.copy()
    
    # Entry channels (wider)
    df['donchian_high'] = df['high'].rolling(window=entry_window).max().shift(1)
    df['donchian_low'] = df['low'].rolling(window=entry_window).min().shift(1)
    
    # Exit channels (tighter for trailing stop)
    df['trail_exit_low'] = df['low'].rolling(window=exit_window).min().shift(1)
    df['trail_exit_high'] = df['high'].rolling(window=exit_window).max().shift(1)
    
    return df


def generate_signals(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Generate Donchian breakout signals"""
    df_signals = df.copy()
    
    # Get parameters
    entry_window = config.get('strategy', {}).get('entry_window', 20)
    exit_window = config.get('strategy', {}).get('exit_window', 10)
    
    logger.info(f"Generating Donchian signals: entry={entry_window}, exit={exit_window}")
    
    # Calculate channels
    df_signals = calculate_donchian_channels(df_signals, entry_window, exit_window)
    
    # Initialize
    df_signals['signal'] = 0
    df_signals['position'] = 0
    
    # Vectorized entry signals
    long_breakout = df_signals['close'] > df_signals['donchian_high']
    short_breakout = df_signals['close'] < df_signals['donchian_low']
    
    df_signals.loc[long_breakout, 'signal'] = 1
    df_signals.loc[short_breakout, 'signal'] = -1
    
    # Position management with trailing stops
    position = 0
    positions = []
    
    for idx, row in df_signals.iterrows():
        # Entry logic
        if row['signal'] == 1:
            position = 1
        elif row['signal'] == -1:
            position = -1
        
        # Exit logic (trailing stop)
        elif position == 1 and row['close'] < row['trail_exit_low']:
            position = 0
        elif position == -1 and row['close'] > row['trail_exit_high']:
            position = 0
        
        positions.append(position)
    
    df_signals['position'] = positions
    
    # Convert position to signal format for backtester
    df_signals['signal'] = df_signals['position'].diff().fillna(df_signals['position'])
    
    num_long = (df_signals['signal'] == 1).sum()
    num_short = (df_signals['signal'] == -1).sum()
    logger.info(f"Generated {num_long} long and {num_short} short signals")
    
    return df_signals


def calculate_position_size(atr: float, capital: float, risk_per_trade: float, price: float) -> float:
    """ATR-based position sizing"""
    if atr <= 0 or capital <= 0 or price <= 0:
        return 0
    
    risk_amount = capital * risk_per_trade
    position_size = risk_amount / (2.5 * atr)
    
    max_shares = (capital * 0.95) / price
    position_size = min(position_size, max_shares)
    
    return int(position_size)


def calculate_stop_loss(entry_price: float, direction: int, atr: float = None) -> float:
    """Fixed 0.5% stop loss"""
    if entry_price <= 0 or direction == 0:
        return np.nan
    
    stop_pct = 0.005  # 0.5%
    
    if direction == 1:  # Long
        return entry_price * (1 - stop_pct)
    else:  # Short
        return entry_price * (1 + stop_pct)
