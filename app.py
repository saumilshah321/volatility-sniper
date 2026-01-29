"""
Main application entry point for Volatility Sniper trading system.

Supports two execution modes:
1. CLI Mode (default): Command-line execution with text output
2. Streamlit Mode: Interactive dashboard with Bloomberg Terminal aesthetic

Usage:
    CLI Mode:     python app.py
    Streamlit:    streamlit run app.py
"""

import sys
from pathlib import Path
import json
import logging

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import load_config, validate_config, export_config
from core.loader import load_and_prepare_data
from core.indicators import add_indicators
from core.strategy import generate_signals
from core.backtester import run_backtest
from core.metrics import calculate_all_metrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cli_mode():
    """
    Execute complete trading system workflow in CLI mode.
    
    Steps:
        1. Load configuration
        2. Load and validate dataset
        3. Calculate technical indicators
        4. Generate trading signals
        5. Run backtest simulation
        6. Calculate performance metrics
        7. Export results for submission
    """
    try:
        logger.info("=" * 80)
        logger.info("VOLATILITY SNIPER - Algorithmic Trading System")
        logger.info("=" * 80)
        
        # Step 1: Load configuration
        logger.info("\n[1/7] Loading configuration...")
        config_path = Path(__file__).parent / 'config' / 'strategy_config.yaml'
        config = load_config(str(config_path))
        validate_config(config)
        
        # Step 2: Load and prepare data
        logger.info("\n[2/7] Loading dataset from BatraHedge...")
        data_url = config['data']['source_url']
        df = load_and_prepare_data(data_url)
        logger.info(f"Loaded {len(df)} bars from {df.index.min()} to {df.index.max()}")
        
        # Step 3: Calculate technical indicators
        logger.info("\n[3/7] Calculating technical indicators...")
        df_with_indicators = add_indicators(df, config)
        logger.info(f"Indicators calculated. {len(df_with_indicators)} bars ready for analysis.")
        
        # Step 4: Generate trading signals
        logger.info("\n[4/7] Generating trading signals...")
        df_with_signals = generate_signals(df_with_indicators, config)
        num_signals = (df_with_signals['signal'] != 0).sum()
        logger.info(f"Generated {num_signals} trading signals")
        
        # Step 5: Run backtest
        logger.info("\n[5/7] Running backtest simulation...")
        trade_log, portfolio_state = run_backtest(df_with_signals, config)
        logger.info(f"Backtest complete: {len(trade_log)} trades executed")
        
        # Step 6: Calculate performance metrics
        logger.info("\n[6/7] Calculating performance metrics...")
        equity_curve = portfolio_state.get('equity_curve', [])
        metrics = calculate_all_metrics(trade_log, equity_curve, config)
        
        # Step 7: Export results
        logger.info("\n[7/7] Exporting results...")
        output_dir = Path(__file__).parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        # Export trade log
        if len(trade_log) > 0:
            trade_log_path = output_dir / 'backtest_results.csv'
            trade_log.to_csv(trade_log_path, index=False)
            logger.info(f"Trade log exported to: {trade_log_path}")
        
        # Export performance metrics
        metrics_path = output_dir / 'performance_metrics.json'
        with open(metrics_path, 'w') as f:
            # Convert numpy types to native Python types for JSON serialization
            metrics_serializable = {
                k: float(v) if isinstance(v, (int, float)) else v 
                for k, v in metrics.items()
            }
            json.dump(metrics_serializable, f, indent=2)
        logger.info(f"Performance metrics exported to: {metrics_path}")
        
        # Export configuration snapshot
        config_snapshot_path = output_dir / 'config_used.yaml'
        export_config(config, str(config_snapshot_path))
        logger.info(f"Configuration snapshot exported to: {config_snapshot_path}")
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("BACKTEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Strategy: {config['strategy']['name']}")
        logger.info(f"Total Trades: {metrics.get('total_trades', 0)}")
        logger.info(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
        logger.info(f"Total Return: {metrics.get('total_return', 0):.2%}")
        logger.info(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        logger.info(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
        logger.info(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        logger.info("=" * 80)
        
        logger.info("\n✓ All deliverables generated successfully!")
        logger.info(f"Check the 'output/' directory for submission artifacts.")
        
    except Exception as e:
        logger.error(f"\n✗ Error during execution: {e}", exc_info=True)
        sys.exit(1)


def streamlit_mode():
    """
    Launch Streamlit dashboard with Bloomberg Terminal aesthetic.
    
    This mode provides an interactive UI for parameter tuning, visualization,
    and real-time backtesting.
    """
    try:
        from ui.dashboard import main as dashboard_main
        dashboard_main()
    except ImportError as e:
        logger.error(f"Failed to import dashboard module: {e}")
        logger.error("Make sure Streamlit is installed: pip install streamlit plotly")
        sys.exit(1)


def detect_streamlit_mode() -> bool:
    """
    Detect if the script is being run via Streamlit.
    
    Returns:
        True if running in Streamlit, False otherwise
    """
    try:
        import streamlit.web.cli as stcli
        return True
    except:
        pass
    
    # Check if streamlit is in the call stack
    try:
        import streamlit as st
        # If we can import streamlit and access session_state, we're in streamlit mode
        _ = st.session_state
        return True
    except:
        return False


if __name__ == '__main__':
    # Detect execution mode
    if detect_streamlit_mode():
        # Running via streamlit command
        streamlit_mode()
    else:
        # Running directly with python
        cli_mode()
