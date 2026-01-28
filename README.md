# Volatility Sniper - Algorithmic Trading System

## Overview

**Volatility Sniper** is a mean reversion algorithmic trading strategy built for the **BatraHedge Algo-Trading Hackathon × Internship Drive** (E-Summit 2026).

The strategy identifies oversold/overbought conditions using RSI and Bollinger Bands to capture reversal opportunities in volatile markets.

## Strategy Logic

### Entry Conditions

**Long Entry:**
- RSI < 30 (oversold)
- Price < Lower Bollinger Band

**Short Entry:**
- RSI > 70 (overbought)
- Price > Upper Bollinger Band

### Exit Conditions

**Long Exit:**
- RSI > 50 OR Price > Middle Bollinger Band

**Short Exit:**
- RSI < 50 OR Price < Middle Bollinger Band

### Risk Management

- **Stop Loss:** 2× ATR from entry price
- **Position Sizing:** ATR-based (2% capital risk per trade)
- **Maximum Drawdown:** 20% (trading halts if exceeded)

## Architecture

```
algo hack/
├── core/                  # Core business logic (zero UI dependencies)
│   ├── config.py         # Configuration management
│   ├── loader.py         # Data loading and validation
│   ├── indicators.py     # RSI, Bollinger Bands, ATR calculations
│   ├── strategy.py       # Signal generation and position sizing
│   ├── backtester.py     # Event-driven simulation engine
│   ├── metrics.py        # Performance statistics
│   └── exporter.py       # Submission artifacts export (CSV/JSON/YAML/PDF)
├── ui/                   # Streamlit dashboard (separate layer)
│   ├── theme.py          # Bloomberg Terminal color constants
│   ├── style.css         # Custom CSS stylesheet
│   └── dashboard.py      # Interactive UI components
├── config/               # YAML configuration files
├── data/                 # Downloaded dataset
├── output/               # Backtest results and submission artifacts
├── app.py                # Main application entry point
└── requirements.txt      # Python dependencies
```

## Installation

```bash
pip install -r requirements.txt
```

**Dependencies:**
- pandas >= 1.5.0
- numpy >= 1.23.0
- pyyaml >= 6.0
- requests >= 2.28.0
- streamlit >= 1.28.0
- plotly >= 5.17.0
- matplotlib >= 3.7.0
- reportlab >= 4.0.0
- Pillow >= 10.0.0

## Usage

The system supports two execution modes:

### 1. CLI Mode (Command Line)

```bash
python app.py
```

This will:
1. Load data from BatraHedge URL
2. Calculate technical indicators
3. Generate trading signals
4. Run backtest simulation
5. Export results to `output/` directory

### 2. Streamlit Dashboard (Interactive UI)

```bash
streamlit run app.py
```

**Features:**
- **Bloomberg Terminal Aesthetic**: Black background, terminal green/red colors, monospace fonts
- **Interactive Parameter Controls**: Adjust RSI periods, Bollinger Bands, risk parameters in real-time
- **Live Backtesting**: Run simulations with instant visual feedback
- **Performance Metrics Cards**: Net Profit, Max Drawdown, Win Rate
- **Interactive Charts**: 
  - Candlestick price chart with Bollinger Bands overlay
  - Buy/sell signal markers
  - RSI subplot with threshold lines
- **Trade Log Table**: Detailed view of all executed trades
- **Export Functionality**: Download results as CSV/JSON/YAML

### Generating Submission Artifacts

**Via Streamlit Dashboard:**
1. Launch dashboard: `streamlit run app.py`
2. Adjust parameters in sidebar
3. Click "RUN BACKTEST"
4. Click "EXPORT RESULTS" to generate all artifacts

**Via CLI:**
```bash
python app.py
```

## Submission Artifacts

All deliverables are automatically exported to timestamped subdirectories in `output/YYYYMMDD_HHMMSS/`:

### 1. Equity Curve CSV
**File:** `equity_curve.csv`

Contains portfolio valuation over time with daily returns and drawdown calculations.

**Columns:**
- `timestamp` - Date/time of observation
- `portfolio_value` - Total portfolio value in dollars
- `daily_return` - Percentage return for the day
- `drawdown` - Current drawdown from peak equity

### 2. Trade Log CSV
**File:** `trade_log.csv`

Complete record of all trades executed during the backtest.

**Columns:**
- `trade_id` - Unique identifier
- `entry_timestamp` - Entry execution time
- `exit_timestamp` - Exit execution time
- `direction` - LONG or SHORT
- `entry_price` - Price at entry (with slippage)
- `exit_price` - Price at exit (with slippage)
- `position_size` - Number of units/shares
- `pnl` - Profit/Loss in dollars
- `pnl_percent` - Profit/Loss as percentage
- `exit_reason` - SIGNAL, STOP_LOSS, or MAX_DRAWDOWN
- `duration_hours` - Trade duration

### 3. Performance Metrics JSON
**File:** `performance_metrics.json`

Comprehensive performance statistics in structured format.

**Metrics Include:**
- **Returns:** total_return, annualized_return, volatility
- **Risk:** max_drawdown, max_drawdown_duration, sharpe_ratio, sortino_ratio
- **Trades:** total_trades, winning_trades, losing_trades, win_rate, profit_factor
- **Statistics:** avg_win, avg_loss, avg_trade_duration

### 4. Configuration Snapshot YAML
**File:** `config_snapshot.yaml`

Complete configuration used for the backtest ensuring reproducibility.

**Includes:**
- Data source URL
- All indicator parameters (RSI, BB, ATR periods)
- Strategy thresholds (oversold/overbought levels)
- Risk management rules (stop-loss, position sizing, max drawdown)
- Backtesting settings (initial capital, slippage, costs)
- Export metadata (timestamp, strategy name)

### 5. Strategy Documentation PDF
**File:** `strategy_documentation.pdf`

**Professional 8-page PDF covering:**

1. **Strategy Overview** - Hypothesis, market conditions, performance summary
2. **Technical Indicators** - RSI, Bollinger Bands, ATR descriptions with calculations
3. **Entry/Exit Logic** - Detailed conditions with rationale and workflow
4. **Risk Management** - Stop-loss methodology, position sizing, drawdown controls
5. **Backtesting Results** - Performance metrics table, equity curve chart
6. **Drawdown Analysis** - Drawdown chart over time
7. **Assumptions & Limitations** - Transaction costs, execution model, known limitations
8. **Observations** - What worked, weaknesses, improvements, parameter sensitivity

**Charts Included:**
- Equity curve (green line on black background)
- Drawdown visualization (red fill)

### Output Directory Structure

```
output/
└── 20260130_170500/          # Timestamp-based subdirectory
    ├── equity_curve.csv
    ├── trade_log.csv
    ├── performance_metrics.json
    ├── config_snapshot.yaml
    └── strategy_documentation.pdf
```

### Troubleshooting Export Issues

**"No trades executed":**
- Verify dataset has sufficient data
- Check if RSI/BB parameters are too restrictive
- Review signal generation logic

**"PDF generation failed":**
- Ensure matplotlib, reportlab, Pillow are installed
- Check no file permissions issues in output directory
- Verify sufficient disk space

**"Missing equity curve":**
- Run backtest first before exporting
- Check backtester returns portfolio_state with equity_curve


## Technical Indicators

### RSI (Relative Strength Index)
- Period: 14
- Oversold: < 30
- Overbought: > 70

### Bollinger Bands
- Period: 20
- Standard Deviation: 2.0
- Used for mean reversion signals

### ATR (Average True Range)
- Period: 14
- Used for position sizing and stop-loss placement

## Performance Metrics

The system calculates comprehensive metrics including:

**Returns:**
- Total Return
- Annualized Return
- Volatility

**Risk:**
- Maximum Drawdown
- Sharpe Ratio
- Sortino Ratio

**Trade Statistics:**
- Win Rate
- Profit Factor
- Average Trade Duration
- Average Win/Loss

## Configuration

All parameters are configurable via `config/strategy_config.yaml`:

```yaml
strategy:
  rsi_oversold: 30
  rsi_overbought: 70

risk_management:
  stop_loss_pct: 0.02
  max_drawdown_pct: 0.20
  risk_per_trade: 0.02

backtesting:
  initial_capital: 100000
  slippage_pct: 0.001
  transaction_cost_pct: 0.0005
```

## Design Principles

1. **Clean Architecture** - Strict separation between core logic and UI
2. **Vectorized Operations** - All calculations use pandas/numpy (no loops)
3. **Event-Driven Backtesting** - Bar-by-bar processing for realistic simulation
4. **Configuration-Driven** - All parameters externalized to YAML
5. **Professional Standards** - Type hints, docstrings, comprehensive error handling

## Dataset

Data source: `http://13.201.224.23:8001/` (BatraHedge provided dataset)

The system automatically:
- Downloads the dataset
- Validates OHLCV schema
- Cleans data (handles missing values, outliers)
- Ensures chronological ordering

## Backtesting Features

- **Realistic Execution:** Includes slippage and transaction costs
- **Risk Controls:** Stop-loss on every trade, maximum drawdown limit
- **Position Management:** No overlapping positions, ATR-based sizing
- **Complete Logging:** Every trade recorded with entry/exit/P&L details

## Team

Created for E-Summit 2026 Algo-Trading Hackathon

---

**Last Updated:** January 30, 2026
