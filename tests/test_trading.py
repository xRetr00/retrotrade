import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml
from pathlib import Path
from strategies.adaptive_strategy import AdaptiveStrategy
from risk_management.position_sizer import DynamicPositionSizer
from risk_management.risk_manager import RiskManager
from execution.trade_executor import TradeExecutor
from utils.performance_monitor import PerformanceMonitor

def load_config():
    """Load test configuration."""
    config_path = Path('../config/config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

@pytest.fixture
def config():
    """Load configuration for testing."""
    return load_config()

@pytest.fixture
def market_data():
    """Create sample market data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1H')
    data = pd.DataFrame(index=dates)
    
    # Generate sample price data
    np.random.seed(42)
    initial_price = 50000
    returns = np.random.normal(0, 0.002, len(dates))
    prices = initial_price * np.exp(np.cumsum(returns))
    
    data['open'] = prices
    data['high'] = prices * (1 + np.random.uniform(0, 0.01, len(dates)))
    data['low'] = prices * (1 - np.random.uniform(0, 0.01, len(dates)))
    data['close'] = prices * (1 + np.random.uniform(-0.005, 0.005, len(dates)))
    data['volume'] = np.random.uniform(100, 1000, len(dates))
    
    return data

@pytest.fixture
def strategy(config):
    """Create strategy instance for testing."""
    return AdaptiveStrategy(config)

@pytest.fixture
def position_sizer(config):
    """Create position sizer instance for testing."""
    return DynamicPositionSizer(config)

@pytest.fixture
def risk_manager(config):
    """Create risk manager instance for testing."""
    return RiskManager(config)

@pytest.fixture
def trade_executor(config):
    """Create trade executor instance for testing."""
    return TradeExecutor(config)

@pytest.fixture
def performance_monitor(config):
    """Create performance monitor instance for testing."""
    return PerformanceMonitor(config)

def test_strategy_analysis(strategy, market_data):
    """Test strategy analysis functionality."""
    # Analyze market data
    analysis = strategy.analyze_market(market_data)
    
    # Check analysis structure
    assert isinstance(analysis, dict)
    assert all(k in analysis for k in [
        'action',
        'confidence',
        'entry_price',
        'stop_loss',
        'take_profit'
    ])
    
    # Check signal validity
    assert analysis['action'] in ['BUY', 'SELL', 'HOLD']
    assert 0 <= analysis['confidence'] <= 1
    assert analysis['entry_price'] > 0
    assert analysis['stop_loss'] < analysis['entry_price'] < analysis['take_profit']

def test_position_sizing(position_sizer, market_data):
    """Test position sizing functionality."""
    portfolio_value = 100000
    confidence = 0.8
    volatility = market_data['close'].pct_change().std()
    
    # Calculate position size
    position_size = position_sizer.get_optimal_position_size(
        portfolio_value=portfolio_value,
        confidence=confidence,
        volatility=volatility
    )
    
    # Check position size validity
    assert isinstance(position_size, float)
    assert 0 < position_size <= portfolio_value
    assert position_size <= portfolio_value * position_sizer.max_position_size

def test_risk_management(risk_manager, market_data):
    """Test risk management functionality."""
    position = {
        'symbol': 'BTC/USDT',
        'side': 'long',
        'entry_price': 50000,
        'quantity': 1,
        'stop_loss': 49000,
        'take_profit': 52000
    }
    
    # Check position risk
    risk_metrics = risk_manager.analyze_position_risk(position, market_data)
    
    assert isinstance(risk_metrics, dict)
    assert all(k in risk_metrics for k in [
        'position_risk',
        'portfolio_risk',
        'max_loss',
        'risk_reward_ratio'
    ])
    
    # Test risk limits
    assert risk_metrics['position_risk'] <= risk_manager.max_position_risk
    assert risk_metrics['portfolio_risk'] <= risk_manager.max_portfolio_risk

def test_trade_execution(trade_executor):
    """Test trade execution functionality."""
    # Create test order
    order = {
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'type': 'limit',
        'quantity': 0.1,
        'price': 50000,
        'stop_loss': 49000,
        'take_profit': 52000
    }
    
    # Execute order
    result = trade_executor.execute_order(order)
    
    # Check execution result
    assert isinstance(result, dict)
    assert all(k in result for k in [
        'order_id',
        'status',
        'filled_quantity',
        'average_price',
        'commission'
    ])
    assert result['status'] in ['filled', 'partially_filled', 'failed']

def test_performance_monitoring(performance_monitor, market_data):
    """Test performance monitoring functionality."""
    # Add sample trade
    trade = {
        'timestamp': datetime.now(),
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'quantity': 0.1,
        'entry_price': 50000,
        'exit_price': 51000,
        'pnl': 100,
        'commission': 10
    }
    
    performance_monitor.update_metrics({
        'trade': trade,
        'equity': 100100,
        'return': 0.001
    })
    
    # Generate report
    report = performance_monitor.generate_report()
    
    # Check report structure
    assert isinstance(report, dict)
    assert all(k in report for k in [
        'overall_metrics',
        'pair_metrics',
        'risk_metrics',
        'trade_metrics'
    ])
    
    # Check metrics calculation
    metrics = report['overall_metrics']
    assert all(k in metrics for k in [
        'total_return',
        'sharpe_ratio',
        'calmar_ratio',
        'omega_ratio',
        'max_drawdown',
        'win_rate',
        'profit_factor'
    ])

def test_strategy_optimization(strategy, market_data):
    """Test strategy optimization functionality."""
    # Define parameter ranges
    param_ranges = {
        'rsi_period': range(10, 21, 2),
        'ma_period': range(20, 41, 5),
        'volatility_window': range(10, 31, 5)
    }
    
    # Run optimization
    results = strategy.optimize_parameters(
        market_data,
        param_ranges,
        metric='sharpe_ratio'
    )
    
    # Check optimization results
    assert isinstance(results, dict)
    assert all(k in results for k in [
        'best_params',
        'best_score',
        'all_results'
    ])
    assert all(k in results['best_params'] for k in param_ranges.keys())
    assert isinstance(results['best_score'], float)

def test_risk_adjusted_position_sizing(position_sizer, risk_manager, market_data):
    """Test risk-adjusted position sizing."""
    portfolio_value = 100000
    confidence = 0.8
    volatility = market_data['close'].pct_change().std()
    
    # Get base position size
    base_size = position_sizer.get_optimal_position_size(
        portfolio_value=portfolio_value,
        confidence=confidence,
        volatility=volatility
    )
    
    # Adjust for risk
    risk_metrics = risk_manager.analyze_market_risk(market_data)
    adjusted_size = position_sizer.adjust_for_risk(
        base_size,
        risk_metrics
    )
    
    # Check risk adjustment
    assert adjusted_size <= base_size
    assert adjusted_size > 0
    max_allowed = portfolio_value * position_sizer.max_position_size
    assert adjusted_size <= max_allowed

def test_integrated_trading_flow(
    strategy,
    position_sizer,
    risk_manager,
    trade_executor,
    performance_monitor,
    market_data
):
    """Test integrated trading flow."""
    portfolio_value = 100000
    current_price = market_data['close'].iloc[-1]
    
    # 1. Strategy Analysis
    analysis = strategy.analyze_market(market_data)
    assert isinstance(analysis, dict)
    
    if analysis['action'] != 'HOLD':
        # 2. Position Sizing
        position_size = position_sizer.get_optimal_position_size(
            portfolio_value=portfolio_value,
            confidence=analysis['confidence'],
            volatility=market_data['close'].pct_change().std()
        )
        
        # 3. Risk Check
        position = {
            'symbol': 'BTC/USDT',
            'side': 'long' if analysis['action'] == 'BUY' else 'short',
            'entry_price': current_price,
            'quantity': position_size / current_price,
            'stop_loss': analysis['stop_loss'],
            'take_profit': analysis['take_profit']
        }
        
        risk_metrics = risk_manager.analyze_position_risk(position, market_data)
        assert risk_metrics['position_risk'] <= risk_manager.max_position_risk
        
        # 4. Trade Execution
        if risk_metrics['position_risk'] <= risk_manager.max_position_risk:
            order = {
                'symbol': position['symbol'],
                'side': analysis['action'].lower(),
                'type': 'limit',
                'quantity': position['quantity'],
                'price': current_price,
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit']
            }
            
            result = trade_executor.execute_order(order)
            assert result['status'] in ['filled', 'partially_filled', 'failed']
            
            # 5. Performance Update
            if result['status'] == 'filled':
                trade = {
                    'timestamp': datetime.now(),
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': result['filled_quantity'],
                    'entry_price': result['average_price'],
                    'exit_price': None,
                    'pnl': None,
                    'commission': result['commission']
                }
                
                performance_monitor.update_metrics({
                    'trade': trade,
                    'equity': portfolio_value,
                    'return': 0
                })

def test_market_regime_detection(strategy, market_data):
    """Test market regime detection."""
    regime = strategy.detect_market_regime(market_data)
    
    # Check regime detection
    assert isinstance(regime, dict)
    assert all(k in regime for k in [
        'trend',
        'volatility',
        'liquidity'
    ])
    assert regime['trend'] in ['uptrend', 'downtrend', 'sideways']
    assert regime['volatility'] in ['low', 'medium', 'high']
    assert regime['liquidity'] in ['low', 'medium', 'high']

def test_strategy_adaptation(strategy, market_data):
    """Test strategy adaptation to market conditions."""
    # Get initial parameters
    initial_params = strategy.get_current_parameters()
    
    # Update market conditions
    regime = strategy.detect_market_regime(market_data)
    strategy.adapt_to_regime(regime)
    
    # Get adapted parameters
    adapted_params = strategy.get_current_parameters()
    
    # Verify adaptation
    assert initial_params != adapted_params
    assert all(k in adapted_params for k in initial_params.keys())
    
    # Check adaptation logic
    if regime['volatility'] == 'high':
        assert adapted_params['stop_loss_multiplier'] > initial_params['stop_loss_multiplier']
    if regime['trend'] == 'sideways':
        assert adapted_params['entry_threshold'] > initial_params['entry_threshold'] 