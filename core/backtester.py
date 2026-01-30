# backtesting engine

from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

import pandas as pd
import numpy as np

from core.strategy import calculate_position_size

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """
    Represents an open trading position.
    
    Attributes:
        direction: 1 for long, -1 for short
        entry_price: Price at position entry
        entry_time: Timestamp of entry
        position_size: Number of units/shares
        stop_loss: Stop-loss price level
        trade_id: Unique identifier for this trade
    """
    direction: int
    entry_price: float
    entry_time: pd.Timestamp
    position_size: float
    stop_loss: float
    trade_id: int


@dataclass
class Portfolio:
    """
    Portfolio state tracker.
    
    Attributes:
        cash: Available cash
        equity: Total portfolio value
        peak_equity: Historical peak for drawdown calculation
        position: Current open position (None if flat)
        trades: List of completed trades
        equity_curve: List of (timestamp, equity) tuples
    """
    cash: float
    equity: float
    peak_equity: float
    position: Optional[Position] = None
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)
    
    def update_equity(self, current_price: float, timestamp: pd.Timestamp):
        """Update portfolio equity based on current market price."""
        if self.position is None:
            self.equity = self.cash
        else:
            # Mark-to-market position value
            if self.position.direction == 1:  # Long
                position_value = self.position.position_size * current_price
            else:  # Short
                position_value = self.position.position_size * (
                    2 * self.position.entry_price - current_price
                )
            
            self.equity = self.cash + position_value
        
        # Update peak for drawdown tracking
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        # Record equity curve
        self.equity_curve.append((timestamp, self.equity))
    
    def current_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if self.peak_equity == 0:
            return 0.0
        return (self.equity - self.peak_equity) / self.peak_equity


def apply_slippage(price: float, direction: int, slippage_pct: float) -> float:
    """
    Apply slippage to execution price.
    
    Args:
        price: Base price
        direction: 1 for long entry/-1 for long exit, -1 for short entry/1 for short exit
        slippage_pct: Slippage percentage
        
    Returns:
        Adjusted price with slippage
    """
    # Buy orders (long entry, short exit) pay higher
    # Sell orders (long exit, short entry) receive lower
    if direction > 0:
        return price * (1 + slippage_pct)
    else:
        return price * (1 - slippage_pct)


def check_stop_loss(
    position: Position,
    current_high: float,
    current_low: float
) -> bool:
    """
    Check if stop-loss was triggered.
    
    Args:
        position: Current position
        current_high: Bar's high price
        current_low: Bar's low price
        
    Returns:
        True if stop-loss triggered
    """
    if position.direction == 1:  # Long position
        # Stop triggered if low breaches stop level
        return current_low <= position.stop_loss
    else:  # Short position
        # Stop triggered if high breaches stop level
        return current_high >= position.stop_loss


def open_position(
    portfolio: Portfolio,
    signal: int,
    price: float,
    timestamp: pd.Timestamp,
    atr: float,
    config: Dict[str, Any],
    trade_counter: int
) -> int:
    """
    Open a new position.
    
    Args:
        portfolio: Portfolio state
        signal: 1 for long, -1 for short
        price: Current price
        timestamp: Current timestamp
        atr: Current ATR value
        config: Configuration dictionary
        trade_counter: Current trade ID counter
        
    Returns:
        Updated trade counter
    """
    # Get config parameters
    slippage_pct = config.get('backtesting', {}).get('slippage_pct', 0.001)
    transaction_cost_pct = config.get('backtesting', {}).get('transaction_cost_pct', 0.0005)
    risk_per_trade = config.get('risk_management', {}).get('risk_per_trade', 0.02)
    stop_loss_pct = config.get('risk_management', {}).get('stop_loss_pct', 0.02)
    
    # Apply slippage to entry price
    entry_price = apply_slippage(price, signal, slippage_pct)
    
    # Calculate position size
    position_size = calculate_position_size(
        atr=atr,
        capital=portfolio.equity,
        risk_per_trade=risk_per_trade,
        price=entry_price
    )
    
    # Calculate position value
    position_value = position_size * entry_price
    
    # Apply transaction costs
    transaction_cost = position_value * transaction_cost_pct
    
    # Check if we have enough cash
    if position_value + transaction_cost > portfolio.cash:
        logger.warning(f"Insufficient cash for position. Required: ${position_value + transaction_cost:.2f}, Available: ${portfolio.cash:.2f}")
        return trade_counter
    
    # Calculate stop-loss level
    if signal == 1:  # Long
        stop_loss = entry_price * (1 - stop_loss_pct)
    else:  # Short
        stop_loss = entry_price * (1 + stop_loss_pct)
    
    # Create position
    portfolio.position = Position(
        direction=signal,
        entry_price=entry_price,
        entry_time=timestamp,
        position_size=position_size,
        stop_loss=stop_loss,
        trade_id=trade_counter
    )
    
    # Deduct cash
    portfolio.cash -= (position_value + transaction_cost)
    
    logger.debug(f"Opened {['SHORT', 'FLAT', 'LONG'][signal+1]} position at ${entry_price:.2f}, Size: {position_size:.2f}, Stop: ${stop_loss:.2f}")
    
    return trade_counter + 1


def close_position(
    portfolio: Portfolio,
    price: float,
    timestamp: pd.Timestamp,
    config: Dict[str, Any],
    exit_reason: str
) -> None:
    """
    Close current position and record trade.
    
    Args:
        portfolio: Portfolio state
        price: Exit price
        timestamp: Exit timestamp
        config: Configuration dictionary
        exit_reason: Reason for exit (SIGNAL, STOP_LOSS, MAX_DRAWDOWN)
    """
    if portfolio.position is None:
        return
    
    position = portfolio.position
    
    # Get config parameters
    slippage_pct = config.get('backtesting', {}).get('slippage_pct', 0.001)
    transaction_cost_pct = config.get('backtesting', {}).get('transaction_cost_pct', 0.0005)
    
    # Apply slippage to exit price (opposite direction of entry)
    exit_price = apply_slippage(price, -position.direction, slippage_pct)
    
    # Calculate P&L
    if position.direction == 1:  # Long
        pnl = position.position_size * (exit_price - position.entry_price)
    else:  # Short
        pnl = position.position_size * (position.entry_price - exit_price)
    
    # Deduct transaction costs
    position_value = position.position_size * exit_price
    transaction_cost = position_value * transaction_cost_pct
    pnl -= transaction_cost
    
    # Calculate P&L percentage
    pnl_percent = pnl / (position.position_size * position.entry_price)
    
    # Calculate duration
    duration = timestamp - position.entry_time
    duration_hours = duration.total_seconds() / 3600
    
    # Add cash back
    portfolio.cash += position_value
    
    # Record trade
    trade = {
        'trade_id': position.trade_id,
        'entry_timestamp': position.entry_time,
        'exit_timestamp': timestamp,
        'direction': 'LONG' if position.direction == 1 else 'SHORT',
        'entry_price': position.entry_price,
        'exit_price': exit_price,
        'position_size': position.position_size,
        'pnl': pnl,
        'pnl_percent': pnl_percent,
        'exit_reason': exit_reason,
        'duration_hours': duration_hours
    }
    
    portfolio.trades.append(trade)
    
    logger.debug(f"Closed {trade['direction']} position: P&L ${pnl:.2f} ({pnl_percent:.2%}), Reason: {exit_reason}")
    
    # Clear position
    portfolio.position = None


def run_backtest(
    df: pd.DataFrame,
    config: Dict[str, Any]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Run event-driven backtest simulation.
    
    Args:
        df: DataFrame with OHLCV data, indicators, and signals
        config: Configuration dictionary
        
    Returns:
        Tuple of (trade_log DataFrame, portfolio_state dictionary)
    """
    logger.info("Starting backtest simulation...")
    
    # Initialize portfolio
    initial_capital = config.get('backtesting', {}).get('initial_capital', 100000)
    portfolio = Portfolio(
        cash=initial_capital,
        equity=initial_capital,
        peak_equity=initial_capital
    )
    
    # Get risk parameters
    max_drawdown_pct = config.get('risk_management', {}).get('max_drawdown_pct', 0.20)
    
    # Trade counter
    trade_counter = 1
    
    # Trading halted flag
    trading_halted = False
    
    # Event-driven simulation: process bar-by-bar
    for idx, row in df.iterrows():
        timestamp = idx
        open_price = row['open']
        high_price = row['high']
        low_price = row['low']
        close_price = row['close']
        signal = row.get('signal', 0)
        atr = row.get('atr_14', 0)
        
        # Update equity at open
        portfolio.update_equity(open_price, timestamp)
        
        # Check for max drawdown breach
        current_dd = portfolio.current_drawdown()
        if current_dd <= -max_drawdown_pct and not trading_halted:
            logger.warning(f"Maximum drawdown breached: {current_dd:.2%}. Halting trading.")
            trading_halted = True
            
            # Close any open position
            if portfolio.position is not None:
                close_position(
                    portfolio=portfolio,
                    price=close_price,
                    timestamp=timestamp,
                    config=config,
                    exit_reason='MAX_DRAWDOWN'
                )
        
        # Skip trading if halted
        if trading_halted:
            continue
        
        # Check stop-loss if position is open
        if portfolio.position is not None:
            if check_stop_loss(portfolio.position, high_price, low_price):
                # Use stop-loss price as exit
                stop_price = portfolio.position.stop_loss
                close_position(
                    portfolio=portfolio,
                    price=stop_price,
                    timestamp=timestamp,
                    config=config,
                    exit_reason='STOP_LOSS'
                )
        
        # Process signals (only if no position and not halted)
        if portfolio.position is None and not trading_halted:
            if signal in [1, -1]:  # Entry signal
                # Check we have valid ATR
                if pd.notna(atr) and atr > 0:
                    trade_counter = open_position(
                        portfolio=portfolio,
                        signal=int(signal),
                        price=close_price,
                        timestamp=timestamp,
                        atr=atr,
                        config=config,
                        trade_counter=trade_counter
                    )
        
        # Check for exit signal if position is open
        elif portfolio.position is not None:
            # Exit if we get an opposite signal or neutral signal
            if signal != portfolio.position.direction:
                close_position(
                    portfolio=portfolio,
                    price=close_price,
                    timestamp=timestamp,
                    config=config,
                    exit_reason='SIGNAL'
                )
        
        # Update equity at close
        portfolio.update_equity(close_price, timestamp)
    
    # Close any remaining open position at end
    if portfolio.position is not None:
        last_row = df.iloc[-1]
        close_position(
            portfolio=portfolio,
            price=last_row['close'],
            timestamp=df.index[-1],
            config=config,
            exit_reason='END_OF_DATA'
        )
    
    # Convert trades to DataFrame
    if len(portfolio.trades) > 0:
        trade_log = pd.DataFrame(portfolio.trades)
    else:
        # Empty trade log with proper schema
        trade_log = pd.DataFrame(columns=[
            'trade_id', 'entry_timestamp', 'exit_timestamp', 'direction',
            'entry_price', 'exit_price', 'position_size', 'pnl',
            'pnl_percent', 'exit_reason', 'duration_hours'
        ])
    
    # Portfolio state summary
    portfolio_state = {
        'initial_capital': initial_capital,
        'final_equity': portfolio.equity,
        'final_cash': portfolio.cash,
        'equity_curve': portfolio.equity_curve,
        'peak_equity': portfolio.peak_equity,
        'trading_halted': trading_halted
    }
    
    logger.info(f"Backtest complete: {len(trade_log)} trades executed")
    logger.info(f"Final equity: ${portfolio.equity:,.2f} (Return: {(portfolio.equity/initial_capital - 1):.2%})")
    
    return trade_log, portfolio_state
