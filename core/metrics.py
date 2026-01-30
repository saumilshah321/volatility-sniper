# performance metrics calculation

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_returns_metrics(
    trades: pd.DataFrame, 
    equity_curve: pd.Series,
    initial_capital: float
) -> Dict[str, float]:
    """
    Calculate return-based performance metrics.
    
    Args:
        trades: DataFrame of completed trades
        equity_curve: Series of equity values over time
        initial_capital: Starting capital
        
    Returns:
        Dictionary with return metrics
    """
    if len(equity_curve) == 0:
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0
        }
    
    final_equity = equity_curve.iloc[-1]
    
    # Total return
    total_return = (final_equity - initial_capital) / initial_capital
    
    # Calculate daily returns
    daily_returns = equity_curve.pct_change().dropna()
    
    # Annualized return
    trading_days = len(equity_curve)
    if trading_days > 0:
        annualized_return = total_return * (252 / trading_days)
    else:
        annualized_return = 0.0
    
    # Annualized volatility
    if len(daily_returns) > 1:
        volatility = daily_returns.std() * np.sqrt(252)
    else:
        volatility = 0.0
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility
    }


def calculate_risk_metrics(
    equity_curve: pd.Series, 
    returns: pd.Series
) -> Dict[str, float]:
    """
    Calculate risk-based performance metrics.
    
    Args:
        equity_curve: Series of equity values over time
        returns: Series of period returns
        
    Returns:
        Dictionary with risk metrics
    """
    if len(equity_curve) == 0:
        return {
            'max_drawdown': 0.0,
            'max_drawdown_duration': 0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0
        }
    
    # Maximum Drawdown
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Drawdown Duration (in days/bars)
    is_drawdown = equity_curve < running_max
    if is_drawdown.any():
        # Find longest consecutive drawdown period
        drawdown_periods = is_drawdown.astype(int).groupby(
            (is_drawdown != is_drawdown.shift()).cumsum()
        ).sum()
        max_drawdown_duration = drawdown_periods.max()
    else:
        max_drawdown_duration = 0
    
    # Sharpe Ratio (assuming risk-free rate = 0)
    if len(returns) > 1 and returns.std() > 0:
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0
    
    # Sortino Ratio (using downside deviation)
    negative_returns = returns[returns < 0]
    if len(negative_returns) > 1:
        downside_deviation = negative_returns.std()
        if downside_deviation > 0:
            sortino_ratio = (returns.mean() / downside_deviation) * np.sqrt(252)
        else:
            sortino_ratio = 0.0
    else:
        sortino_ratio = 0.0
    
    return {
        'max_drawdown': abs(max_drawdown),
        'max_drawdown_duration': int(max_drawdown_duration),
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio
    }


def calculate_trade_metrics(trades: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate trade-level performance metrics.
    
    Args:
        trades: DataFrame of completed trades
        
    Returns:
        Dictionary with trade statistics
    """
    if len(trades) == 0:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_trade_duration': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
    
    total_trades = len(trades)
    
    # Separate winning and losing trades
    winning_trades = trades[trades['pnl'] > 0]
    losing_trades = trades[trades['pnl'] < 0]
    
    num_winning = len(winning_trades)
    num_losing = len(losing_trades)
    
    # Win rate
    win_rate = num_winning / total_trades if total_trades > 0 else 0.0
    
    # Profit factor
    gross_profit = winning_trades['pnl'].sum() if num_winning > 0 else 0.0
    gross_loss = abs(losing_trades['pnl'].sum()) if num_losing > 0 else 0.0
    
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float('inf') if gross_profit > 0 else 0.0
    
    # Average trade duration
    if 'duration_hours' in trades.columns:
        avg_duration = trades['duration_hours'].mean()
    else:
        avg_duration = 0.0
    
    # Average win/loss
    avg_win = winning_trades['pnl'].mean() if num_winning > 0 else 0.0
    avg_loss = losing_trades['pnl'].mean() if num_losing > 0 else 0.0
    
    return {
        'total_trades': total_trades,
        'winning_trades': num_winning,
        'losing_trades': num_losing,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_trade_duration': avg_duration,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }


def calculate_all_metrics(
    trades: pd.DataFrame,
    equity_curve: List[Tuple],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate all performance metrics.
    
    Args:
        trades: DataFrame of completed trades
        equity_curve: List of (timestamp, equity) tuples
        config: Configuration dictionary
        
    Returns:
        Comprehensive dictionary with all metrics
    """
    logger.info("Calculating performance metrics...")
    
    # Convert equity curve to Series
    if equity_curve:
        timestamps, values = zip(*equity_curve)
        equity_series = pd.Series(values, index=timestamps)
        returns_series = equity_series.pct_change().dropna()
    else:
        equity_series = pd.Series([])
        returns_series = pd.Series([])
    
    initial_capital = config['backtesting']['initial_capital']
    
    # Calculate metric groups
    returns_metrics = calculate_returns_metrics(trades, equity_series, initial_capital)
    risk_metrics = calculate_risk_metrics(equity_series, returns_series)
    trade_metrics = calculate_trade_metrics(trades)
    
    # Combine all metrics
    all_metrics = {
        **returns_metrics,
        **risk_metrics,
        **trade_metrics,
        'initial_capital': initial_capital,
        'final_equity': equity_series.iloc[-1] if len(equity_series) > 0 else initial_capital,
        'strategy_name': config['strategy']['name']
    }
    
    # Add date range
    if len(equity_series) > 0:
        all_metrics['start_date'] = str(equity_series.index[0])
        all_metrics['end_date'] = str(equity_series.index[-1])
    
    logger.info(f"Metrics calculated: {trade_metrics['total_trades']} trades, "
                f"{returns_metrics['total_return']:.2%} return, "
                f"{trade_metrics['win_rate']:.2%} win rate")
    
    return all_metrics
