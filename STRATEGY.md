# Volatility Sniper Strategy

## Strategy Overview

**Type**: Mean Reversion  
**Market**: Futures (FINNIFTY)  
**Timeframe**: 1-minute bars  
**Capital**: ₹100,000

## Core Logic

### Entry Conditions

**Long Entry** (Oversold Bounce):
- RSI < 25 (extreme oversold)
- Price below Lower Bollinger Band
- Price above 200-bar SMA (trend filter)

**Short Entry** (Overbought Reversal):
- RSI > 75 (extreme overbought)
- Price above Upper Bollinger Band
- Price below 200-bar SMA (trend filter)

### Exit Conditions

**Take Profit**:
- Long: Price crosses above Middle Bollinger Band
- Short: Price crosses below Middle Bollinger Band

**Stop Loss**:
- Fixed at 2.5× ATR from entry price
- Protects against large losses

**Max Drawdown Circuit Breaker**:
- Trading halts if portfolio loses >15% from peak
- Prevents catastrophic losses

## Risk Management

### Position Sizing
- Risk per trade: 1.5% of capital
- Position size = (Capital × Risk%) / (2.5 × ATR)
- Maximum 90% capital allocation per trade

### Stop Loss
- Dynamic: 2.5× ATR distance
- Adapts to market volatility
- Tighter stops in low volatility, wider in high volatility

### Drawdown Protection
- Maximum allowed drawdown: 15%
- Automatic trading halt if breached
- Requires manual review to resume

## Technical Indicators

### RSI (Relative Strength Index)
- Period: 14 bars
- Oversold threshold: 25 (stricter than typical 30)
- Overbought threshold: 75 (stricter than typical 70)
- Identifies extreme price movements

### Bollinger Bands
- Period: 20 bars
- Standard Deviation: 2.0
- Upper/Lower bands mark price extremes
- Middle band used for exits

### ATR (Average True Range)
- Period: 14 bars
- Measures volatility
- Used for position sizing and stop-loss placement

### SMA (Simple Moving Average)
- Period: 200 bars
- Trend filter to avoid counter-trend trades
- Long only in uptrends, short only in downtrends

## Execution Details

### Slippage
- 0.1% per trade
- Simulates realistic market impact

### Transaction Costs
- 0.05% per trade
- Includes brokerage, taxes, fees

### Trade Management
- One position at a time
- No pyramiding or averaging down
- Clean entry/exit signals

## Performance Targets

### Expected Metrics
- Win Rate: 40-50%
- Profit Factor: >1.5
- Sharpe Ratio: >1.0
- Max Drawdown: <15%
- Annual Return: 15-25%

## Strategy Rationale

### Why Mean Reversion?
- Futures markets often overreact to short-term news
- Price tends to return to average after extreme moves
- Bollinger Bands + RSI capture these extremes effectively

### Why Trend Filter?
- Prevents trading against strong trends
- Improves win rate significantly
- Reduces drawdowns during trending markets

### Why Tight Risk Controls?
- Futures have high leverage
- Small price moves = large P&L impact
- Preservation of capital is priority #1

## Assumptions & Limitations

### Assumptions
- Market is liquid (FINNIFTY futures)
- Execution at displayed prices
- No slippage beyond 0.1%
- Sufficient margin available

### Limitations
- Does not account for gaps (futures can gap)
- No position sizing based on margin requirements
- Assumes 24/5 market access
- Backtested on historical data only

## Improvements Made

### Version 2.0 Updates (Current)
1. **Stricter entry conditions**: RSI 25/75 instead of 30/70
2. **Trend filter added**: 200-bar SMA prevents counter-trend trades
3. **Wider stop loss**: 2.5× ATR instead of 2× ATR
4. **Lower risk per trade**: 1.5% instead of 2%
5. **Tighter drawdown limit**: 15% instead of 20%

These changes reduce trade frequency but improve quality, targeting better risk-adjusted returns.

---

**Strategy Developer**: Volatility Sniper Team  
**Last Updated**: January 30, 2026  
**Version**: 2.0
