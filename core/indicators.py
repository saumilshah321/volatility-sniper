# technical indicators - RSI, BB, ATR

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index using exponential moving averages.
    
    Formula:
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss over period
    
    Args:
        prices: Series of closing prices
        period: Lookback period for RSI calculation (default: 14)
        
    Returns:
        Series of RSI values (0-100 scale)
        
    Raises:
        ValueError: If period < 2 or prices has insufficient data
    """
    if period < 2:
        raise ValueError(f"RSI period must be >= 2, got {period}")
    
    if len(prices) < period + 1:
        raise ValueError(f"Insufficient data for RSI calculation: need at least {period + 1} prices")
    
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0.0)
    losses = -delta.where(delta < 0, 0.0)
    
    # Calculate exponential moving average of gains and losses
    avg_gains = gains.ewm(span=period, adjust=False, min_periods=period).mean()
    avg_losses = losses.ewm(span=period, adjust=False, min_periods=period).mean()
    
    # Calculate RS (Relative Strength)
    rs = avg_gains / avg_losses
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    
    # Handle division by zero (when avg_losses = 0, RSI = 100)
    rsi = rsi.fillna(100)
    
    return rsi


def calculate_bollinger_bands(
    prices: pd.Series, 
    period: int = 20, 
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Formula:
        Middle Band = SMA(period)
        Upper Band = Middle Band + (std_dev × rolling_std)
        Lower Band = Middle Band - (std_dev × rolling_std)
    
    Args:
        prices: Series of closing prices
        period: Lookback period for moving average (default: 20)
        std_dev: Number of standard deviations (default: 2.0)
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band) Series
        
    Raises:
        ValueError: If period < 2 or prices has insufficient data
    """
    if period < 2:
        raise ValueError(f"Bollinger Bands period must be >= 2, got {period}")
    
    if len(prices) < period:
        raise ValueError(f"Insufficient data for Bollinger Bands: need at least {period} prices")
    
    # Calculate middle band (Simple Moving Average)
    middle_band = prices.rolling(window=period, min_periods=period).mean()
    
    # Calculate rolling standard deviation
    rolling_std = prices.rolling(window=period, min_periods=period).std()
    
    # Calculate upper and lower bands
    upper_band = middle_band + (std_dev * rolling_std)
    lower_band = middle_band - (std_dev * rolling_std)
    
    return upper_band, middle_band, lower_band


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Formula:
        True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        ATR = EMA(True Range, period)
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: Lookback period for ATR calculation (default: 14)
        
    Returns:
        Series of ATR values
        
    Raises:
        ValueError: If period < 1 or df has insufficient data
        KeyError: If required columns are missing
    """
    if period < 1:
        raise ValueError(f"ATR period must be >= 1, got {period}")
    
    required_columns = ['high', 'low', 'close']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise KeyError(f"Missing required columns for ATR: {missing_columns}")
    
    if len(df) < period + 1:
        raise ValueError(f"Insufficient data for ATR calculation: need at least {period + 1} rows")
    
    # Calculate the three components of True Range
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    
    # True Range is the maximum of the three components
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # ATR is the exponential moving average of True Range
    atr = true_range.ewm(span=period, adjust=False, min_periods=period).mean()
    
    return atr


def add_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Add all technical indicators to DataFrame based on configuration.
    
    Args:
        df: DataFrame with OHLCV data
        config: Configuration dictionary containing indicator parameters
        
    Returns:
        DataFrame with added indicator columns:
            - rsi_14: Relative Strength Index
            - bb_upper: Upper Bollinger Band
            - bb_middle: Middle Bollinger Band (SMA)
            - bb_lower: Lower Bollinger Band
            - atr_14: Average True Range
        
    Raises:
        KeyError: If required configuration parameters are missing
        ValueError: If data is insufficient for indicator calculation
    """
    # Create copy to avoid mutating original DataFrame
    df_enriched = df.copy()
    
    # Extract indicator parameters from config
    atr_period = config.get('indicators', {}).get('atr_period', 14)
    
    logger.info("Calculating technical indicators...")
    
    # Calculate ATR (required for position sizing)
    logger.info(f"Calculating ATR with period {atr_period}")
    df_enriched['atr_14'] = calculate_atr(df_enriched, period=atr_period)
    
    # Calculate RSI and BB only if configured
    if 'rsi_period' in config.get('indicators', {}):
        rsi_period = config['indicators']['rsi_period']
        logger.info(f"Calculating RSI with period {rsi_period}")
        df_enriched['rsi_14'] = calculate_rsi(df_enriched['close'], period=rsi_period)
    
    if 'bb_period' in config.get('indicators', {}):
        bb_period = config['indicators']['bb_period']
        bb_std_dev = config['indicators']['bb_std_dev']
        logger.info(f"Calculating Bollinger Bands with period {bb_period}, std_dev {bb_std_dev}")
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            df_enriched['close'], 
            period=bb_period, 
            std_dev=bb_std_dev
        )
        df_enriched['bb_upper'] = bb_upper
        df_enriched['bb_middle'] = bb_middle
        df_enriched['bb_lower'] = bb_lower
    
    # Calculate SMA for trend filter if configured
    sma_period = config.get('indicators', {}).get('sma_period')
    if sma_period:
        logger.info(f"Calculating SMA with period {sma_period} for trend filter")
        df_enriched['sma_200'] = df_enriched['close'].rolling(window=sma_period, min_periods=sma_period).mean()
    
    # Drop rows with NaN values from indicator warm-up period
    initial_rows = len(df_enriched)
    df_enriched = df_enriched.dropna()
    final_rows = len(df_enriched)
    
    dropped_rows = initial_rows - final_rows
    logger.info(f"Indicators calculated. Dropped {dropped_rows} warm-up rows. {final_rows} rows ready for analysis.")
    
    # Verify we still have sufficient data
    if final_rows < 50:
        logger.warning(f"Only {final_rows} rows remaining after indicator calculation. Results may be unreliable.")
    
    return df_enriched


def calculate_indicator_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate summary statistics for indicators (useful for debugging/reporting).
    
    Args:
        df: DataFrame with calculated indicators
        
    Returns:
        Dictionary with statistics for each indicator
    """
    stats = {}
    
    indicator_columns = ['rsi_14', 'bb_upper', 'bb_middle', 'bb_lower', 'atr_14']
    
    for col in indicator_columns:
        if col in df.columns:
            stats[col] = {
                'mean': df[col].mean(),
                'std': df[col].std(),
                'min': df[col].min(),
                'max': df[col].max(),
                'median': df[col].median()
            }
    
    return stats
