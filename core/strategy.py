# mean reversion strategy logic

from typing import Dict, Any
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_signals(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Generate trading signals based on Volatility Sniper strategy.
    
    Strategy Logic:
        Long Entry:
            - RSI < oversold threshold (default: 30)
            - Price < Lower Bollinger Band
        
        Short Entry:
            - RSI > overbought threshold (default: 70)
            - Price > Upper Bollinger Band
        
        Long Exit:
            - RSI > 50 OR Price > Middle Bollinger Band
        
        Short Exit:
            - RSI < 50 OR Price < Middle Bollinger Band
    
    Args:
        df: DataFrame with OHLCV data and calculated indicators
        config: Configuration dictionary with strategy parameters
        
    Returns:
        DataFrame with added signal columns:
            - signal: 1 (long), -1 (short), 0 (no position)
            - exit_signal: 1 (exit long), -1 (exit short), 0 (hold)
            - signal_strength: Confidence score (0-1)
            - entry_price: Proposed entry price
            - stop_loss: Calculated stop-loss level
    
    Raises:
        KeyError: If required columns or config parameters are missing
    """
    # Create copy to avoid mutating original
    df_signals = df.copy()
    
    # Extract strategy parameters
    try:
        rsi_oversold = config['strategy']['rsi_oversold']
        rsi_overbought = config['strategy']['rsi_overbought']
    except KeyError as e:
        raise KeyError(f"Missing strategy configuration parameter: {e}")
    
    # Verify required columns
    required_columns = ['close', 'rsi_14', 'bb_upper', 'bb_middle', 'bb_lower', 'atr_14']
    missing_columns = [col for col in required_columns if col not in df_signals.columns]
    if missing_columns:
        raise KeyError(f"Missing required columns for strategy: {missing_columns}")
    
    logger.info(f"Generating signals with RSI thresholds: oversold={rsi_oversold}, overbought={rsi_overbought}")
    
    # Initialize signal columns
    df_signals['signal'] = 0
    df_signals['exit_signal'] = 0
    df_signals['signal_strength'] = 0.0
    
    # Trend filter (optional)
    use_trend_filter = config.get('strategy', {}).get('use_trend_filter', False)
    if use_trend_filter and 'sma_200' in df_signals.columns:
        trend_up = df_signals['close'] > df_signals['sma_200']
        trend_down = df_signals['close'] < df_signals['sma_200']
        logger.info("Using SMA trend filter for signal generation")
    else:
        # No filter - allow all trades
        trend_up = True
        trend_down = True
    
    # Long entry condition (with trend filter)
    long_condition = (
        (df_signals['rsi_14'] < rsi_oversold) & 
        (df_signals['close'] < df_signals['bb_lower']) &
        trend_up  # Only long if price above SMA
    ).fillna(False)
    df_signals.loc[long_condition, 'signal'] = 1
    
    # Short entry condition (with trend filter)
    short_condition = (
        (df_signals['rsi_14'] > rsi_overbought) & 
        (df_signals['close'] > df_signals['bb_upper']) &
        trend_down  # Only short if price below SMA
    ).fillna(False)
    df_signals.loc[short_condition, 'signal'] = -1
    
    # Long exit condition
    long_exit_condition = (
        (df_signals['rsi_14'] > 50) | 
        (df_signals['close'] > df_signals['bb_middle'])
    )
    df_signals.loc[long_exit_condition, 'exit_signal'] = 1
    
    # Short exit condition
    short_exit_condition = (
        (df_signals['rsi_14'] < 50) | 
        (df_signals['close'] < df_signals['bb_middle'])
    )
    df_signals.loc[short_exit_condition, 'exit_signal'] = -1
    
    # Calculate signal strength (0-1 scale based on distance from thresholds)
    # For long signals: strength based on how far below oversold threshold
    long_strength = np.where(
        long_condition,
        np.clip((rsi_oversold - df_signals['rsi_14']) / rsi_oversold, 0, 1),
        0
    )
    
    # For short signals: strength based on how far above overbought threshold
    short_strength = np.where(
        short_condition,
        np.clip((df_signals['rsi_14'] - rsi_overbought) / (100 - rsi_overbought), 0, 1),
        0
    )
    
    df_signals['signal_strength'] = long_strength + short_strength
    
    # Entry price is the close price where signal is generated
    df_signals['entry_price'] = df_signals['close']
    
    # Calculate stop loss using calculate_stop_loss function
    df_signals['stop_loss'] = df_signals.apply(
        lambda row: calculate_stop_loss(
            row['entry_price'], 
            row['signal'], 
            row['atr_14']
        ) if row['signal'] != 0 else np.nan,
        axis=1
    )
    
    # Log signal statistics
    num_long_signals = (df_signals['signal'] == 1).sum()
    num_short_signals = (df_signals['signal'] == -1).sum()
    total_signals = num_long_signals + num_short_signals
    
    logger.info(f"Generated {total_signals} total signals: {num_long_signals} long, {num_short_signals} short")
    
    return df_signals


def calculate_position_size(
    atr: float, 
    capital: float, 
    risk_per_trade: float, 
    price: float
) -> float:
    """
    Calculate position size based on ATR and capital at risk.
    
    Uses ATR-based position sizing to normalize risk across different
    volatility regimes.
    
    Formula:
        Risk Amount = Capital × Risk Per Trade
        Position Size = Risk Amount / (2 × ATR)
    
    Args:
        atr: Average True Range value
        capital: Available capital
        risk_per_trade: Percentage of capital to risk (e.g., 0.02 for 2%)
        price: Current price of asset
        
    Returns:
        Number of shares/contracts to trade
        
    Raises:
        ValueError: If parameters are invalid
    """
    if atr <= 0:
        raise ValueError(f"ATR must be positive, got {atr}")
    
    if capital <= 0:
        raise ValueError(f"Capital must be positive, got {capital}")
    
    if not (0 < risk_per_trade < 1):
        raise ValueError(f"Risk per trade must be between 0 and 1, got {risk_per_trade}")
    
    if price <= 0:
        raise ValueError(f"Price must be positive, got {price}")
    
    # Calculate risk amount
    risk_amount = capital * risk_per_trade
    
    # Position size based on 2×ATR stop distance
    position_size = risk_amount / (2 * atr)
    
    # Ensure position doesn't exceed maximum capital allocation (e.g., 95% of capital)
    max_position_value = capital * 0.95
    max_shares = max_position_value / price
    
    position_size = min(position_size, max_shares)
    
    # Round down to whole shares
    position_size = int(position_size)
    
    return position_size


def calculate_stop_loss(entry_price: float, direction: int, atr: float) -> float:
    """
    Calculate stop-loss level based on ATR.
    
    Uses 2×ATR as stop distance for both long and short positions.
    
    Args:
        entry_price: Entry price of position
        direction: 1 for long, -1 for short, 0 for no position
        atr: Average True Range value
        
    Returns:
        Stop-loss price level
        
    Raises:
        ValueError: If parameters are invalid
    """
    if entry_price <= 0:
        raise ValueError(f"Entry price must be positive, got {entry_price}")
    
    if atr <= 0:
        raise ValueError(f"ATR must be positive, got {atr}")
    
    if direction not in [-1, 0, 1]:
        raise ValueError(f"Direction must be -1, 0, or 1, got {direction}")
    
    if direction == 0:
        return np.nan
    
    # For long positions: stop below entry
    if direction == 1:
        stop_loss = entry_price - (2 * atr)
    
    # For short positions: stop above entry
    else:  # direction == -1
        stop_loss = entry_price + (2 * atr)
    
    return stop_loss


def analyze_strategy_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze signal distribution and characteristics.
    
    Useful for strategy validation and debugging.
    
    Args:
        df: DataFrame with generated signals
        
    Returns:
        Dictionary with signal statistics
    """
    stats = {
        'total_long_signals': (df['signal'] == 1).sum(),
        'total_short_signals': (df['signal'] == -1).sum(),
        'avg_signal_strength': df[df['signal'] != 0]['signal_strength'].mean(),
        'signal_frequency': (df['signal'] != 0).sum() / len(df),
        'avg_rsi_at_long_entry': df[df['signal'] == 1]['rsi_14'].mean(),
        'avg_rsi_at_short_entry': df[df['signal'] == -1]['rsi_14'].mean(),
    }
    
    return stats
