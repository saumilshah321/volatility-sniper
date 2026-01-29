"""
Configuration management module for the trading system.

Handles loading, validation, and exporting of YAML configuration files.
All strategy parameters, risk management rules, and backtesting settings
are managed through this module.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


def load_config(path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        path: Path to YAML configuration file
        
    Returns:
        Dictionary containing configuration parameters
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    config_path = Path(path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Successfully loaded configuration from {path}")
        return config
    
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML configuration: {e}")
        raise


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate configuration structure and parameter values.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ConfigurationError: If validation fails with detailed error message
    """
    required_sections = ['data', 'indicators', 'strategy', 'risk_management', 'backtesting']
    
    # Check required top-level sections
    for section in required_sections:
        if section not in config:
            raise ConfigurationError(f"Missing required configuration section: {section}")
    
    # Validate data section
    if 'source_url' not in config['data']:
        raise ConfigurationError("Missing 'source_url' in data section")
    
    # Validate indicator parameters
    indicators = config['indicators']
    required_indicators = ['rsi_period', 'bb_period', 'bb_std_dev', 'atr_period']
    for param in required_indicators:
        if param not in indicators:
            raise ConfigurationError(f"Missing indicator parameter: {param}")
        if not isinstance(indicators[param], (int, float)):
            raise ConfigurationError(f"Invalid type for {param}: expected numeric")
        if indicators[param] <= 0:
            raise ConfigurationError(f"Invalid value for {param}: must be positive")
    
    # Validate strategy parameters
    strategy = config['strategy']
    if 'name' not in strategy:
        raise ConfigurationError("Missing strategy name")
    if 'rsi_oversold' not in strategy or 'rsi_overbought' not in strategy:
        raise ConfigurationError("Missing RSI threshold parameters")
    
    if not (0 < strategy['rsi_oversold'] < strategy['rsi_overbought'] < 100):
        raise ConfigurationError("Invalid RSI thresholds: must satisfy 0 < oversold < overbought < 100")
    
    # Validate risk management parameters
    risk = config['risk_management']
    required_risk_params = ['stop_loss_pct', 'max_drawdown_pct', 'risk_per_trade']
    for param in required_risk_params:
        if param not in risk:
            raise ConfigurationError(f"Missing risk management parameter: {param}")
        if not isinstance(risk[param], (int, float)):
            raise ConfigurationError(f"Invalid type for {param}: expected numeric")
        if not (0 < risk[param] < 1):
            raise ConfigurationError(f"Invalid value for {param}: must be between 0 and 1")
    
    # Validate backtesting parameters
    backtest = config['backtesting']
    required_backtest_params = ['initial_capital', 'slippage_pct', 'transaction_cost_pct']
    for param in required_backtest_params:
        if param not in backtest:
            raise ConfigurationError(f"Missing backtesting parameter: {param}")
        if not isinstance(backtest[param], (int, float)):
            raise ConfigurationError(f"Invalid type for {param}: expected numeric")
        if backtest[param] < 0:
            raise ConfigurationError(f"Invalid value for {param}: must be non-negative")
    
    if backtest['initial_capital'] <= 0:
        raise ConfigurationError("Initial capital must be positive")
    
    logger.info("Configuration validation passed")
    return True


def export_config(config: Dict[str, Any], path: str) -> None:
    """
    Export configuration to YAML file for submission artifacts.
    
    Args:
        config: Configuration dictionary to export
        path: Output path for YAML file
        
    Raises:
        IOError: If file write fails
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration exported to {path}")
    
    except IOError as e:
        logger.error(f"Failed to export configuration: {e}")
        raise


def get_default_config() -> Dict[str, Any]:
    """
    Return default configuration for testing purposes.
    
    Returns:
        Dictionary with default configuration values
    """
    return {
        'data': {
            'source_url': 'http://13.201.224.23:8001/'
        },
        'indicators': {
            'rsi_period': 14,
            'bb_period': 20,
            'bb_std_dev': 2.0,
            'atr_period': 14
        },
        'strategy': {
            'name': 'Volatility Sniper',
            'rsi_oversold': 30,
            'rsi_overbought': 70
        },
        'risk_management': {
            'stop_loss_pct': 0.02,
            'max_drawdown_pct': 0.20,
            'risk_per_trade': 0.02
        },
        'backtesting': {
            'initial_capital': 100000,
            'slippage_pct': 0.001,
            'transaction_cost_pct': 0.0005
        }
    }
