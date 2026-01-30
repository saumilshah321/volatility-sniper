# data loading and validation

from typing import Optional
import pandas as pd
import requests
import logging
import time
from io import StringIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when data loading or validation fails."""
    pass


def load_dataset(url: str, max_retries: int = 3) -> pd.DataFrame:
    # load dataset from URL with retries
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to fetch data from {url} (attempt {attempt + 1}/{max_retries})")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV data
            df = pd.read_csv(StringIO(response.text))
            
            # Parse timestamp and set as index
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.index.name = 'timestamp'
            else:
                # If no timestamp column, assume first column is datetime
                df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                df.set_index(df.columns[0], inplace=True)
                df.index.name = 'timestamp'
            
            logger.info(f"Successfully loaded {len(df)} rows of data")
            return df
        
        except requests.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise DataLoadError(f"Failed to fetch data after {max_retries} attempts: {e}")
        
        except Exception as e:
            raise DataLoadError(f"Unexpected error loading data: {e}")
    
    raise DataLoadError("Failed to load data")


def validate_schema(df: pd.DataFrame) -> bool:
    # validate OHLCV schema
    # Check required columns (case-insensitive)
    df_columns_lower = [col.lower() for col in df.columns]
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    missing_columns = []
    for col in required_columns:
        if col not in df_columns_lower:
            missing_columns.append(col)
    
    if missing_columns:
        raise DataLoadError(f"Missing required columns: {missing_columns}")
    
    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()
    
    # Verify datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataLoadError("Index must be DatetimeIndex")
    
    # Check data types
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise DataLoadError(f"Column '{col}' must be numeric, got {df[col].dtype}")
    
    # Validate OHLC relationships
    invalid_ohlc = (
        (df['high'] < df['open']) | 
        (df['high'] < df['close']) | 
        (df['low'] > df['open']) | 
        (df['low'] > df['close']) |
        (df['high'] < df['low'])
    )
    
    if invalid_ohlc.any():
        num_invalid = invalid_ohlc.sum()
        logger.warning(f"Found {num_invalid} rows with invalid OHLC relationships")
        # Log first few invalid rows for debugging
        logger.warning(f"Sample invalid rows:\n{df[invalid_ohlc].head()}")
    
    # Check minimum data points
    min_required_rows = 100
    if len(df) < min_required_rows:
        raise DataLoadError(f"Insufficient data: {len(df)} rows, minimum {min_required_rows} required")
    
    logger.info("Schema validation passed")
    return True


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # clean data and handle missing values
    df = df.copy()
    
    # Log initial state
    initial_rows = len(df)
    logger.info(f"Cleaning data: {initial_rows} rows")
    
    # Check for missing values
    missing_counts = df.isnull().sum()
    if missing_counts.any():
        logger.warning(f"Missing values detected:\n{missing_counts[missing_counts > 0]}")
        
        # Forward fill price data
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].ffill()
        
        # Fill any remaining NaNs at the start
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].bfill()
        
        # Fill volume with 0 if missing
        df['volume'] = df['volume'].fillna(0)
    
    # Remove duplicate timestamps
    duplicates = df.index.duplicated()
    if duplicates.any():
        num_duplicates = duplicates.sum()
        logger.warning(f"Removing {num_duplicates} duplicate timestamps")
        df = df[~duplicates]
    
    # Sort by timestamp to ensure chronological order
    df = df.sort_index()
    
    # Detect and handle outliers using IQR method
    for col in ['open', 'high', 'low', 'close']:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR
        
        outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
        if outliers.any():
            num_outliers = outliers.sum()
            logger.warning(f"Detected {num_outliers} outliers in '{col}' column")
            
            # Replace outliers with interpolated values
            df.loc[outliers, col] = None
            df[col] = df[col].interpolate(method='linear', limit_direction='both')
    
    final_rows = len(df)
    logger.info(f"Data cleaning complete: {final_rows} rows (removed {initial_rows - final_rows})")
    
    return df


def load_and_prepare_data(url: str) -> pd.DataFrame:
    # load, validate and clean data
    df = load_dataset(url)
    validate_schema(df)
    df = clean_data(df)
    
    logger.info(f"Data preparation complete: {len(df)} rows from {df.index.min()} to {df.index.max()}")
    
    return df
