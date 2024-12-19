import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from utils.performance_monitor import PerformanceMonitor
from utils.logger import OperationalLogger
from strategies.adaptive_strategy import AdaptiveStrategy
from risk_management.position_sizer import DynamicPositionSizer

class Portfolio:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.trades_history = []
        self.equity_curve = [initial_capital]
        self.returns = []
    
    def update(self, current_prices: Dict[str, float]) -> None:
        """Update portfolio value based on current prices."""
        portfolio_value = self.current_capital
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                market_value = position['quantity'] * current_prices[symbol]
                portfolio_value += market_value - position['cost_basis']
        
        self.equity_curve.append(portfolio_value)
        if len(self.equity_curve) > 1:
            self.returns.append(
                (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
            )
    
    def execute_trade(self, trade: Dict) -> Dict:
        """Execute a trade and update portfolio."""
        symbol = trade['symbol']
        side = trade['side']
        quantity = trade['quantity']
        price = trade['price']
        timestamp = trade['timestamp']
        
        # Calculate trade cost
        cost = quantity * price
        commission = cost * trade.get('commission', 0.001)  # Default 0.1% commission
        total_cost = cost + commission
        
        # Update positions
        if side == 'buy':
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'quantity': quantity,
                    'cost_basis': total_cost
                }
            else:
                self.positions[symbol]['quantity'] += quantity
                self.positions[symbol]['cost_basis'] += total_cost
        else:  # sell
            if symbol in self.positions:
                self.positions[symbol]['quantity'] -= quantity
                realized_pnl = (price - self.positions[symbol]['cost_basis'] / 
                              self.positions[symbol]['quantity']) * quantity
                
                if self.positions[symbol]['quantity'] <= 0:
                    del self.positions[symbol]
                
                trade['realized_pnl'] = realized_pnl - commission
        
        # Update capital
        self.current_capital -= total_cost if side == 'buy' else -total_cost
        
        # Record trade
        trade_record = {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'cost': total_cost,
            'portfolio_value': self.equity_curve[-1]
        }
        self.trades_history.append(trade_record)
        
        return trade_record

class BacktestEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = OperationalLogger(config)
        self.strategy = AdaptiveStrategy(config)
        self.position_sizer = DynamicPositionSizer(config)
        self.performance_monitor = PerformanceMonitor(config)
        
        # Backtesting parameters
        self.params = config['backtesting']
        self.commission = self.params.get('commission', 0.001)
        self.slippage = self.params.get('slippage', 0.0005)
        
        # Initialize data storage
        self.market_data = {}
        self.sentiment_data = {}
        self.results = None
    
    def load_data(self, 
                 market_data: Dict[str, pd.DataFrame],
                 sentiment_data: Optional[Dict[str, pd.DataFrame]] = None) -> None:
        """Load market and sentiment data for backtesting."""
        self.market_data = market_data
        self.sentiment_data = sentiment_data or {}
        
        # Validate data
        self._validate_data()
    
    def _validate_data(self) -> None:
        """Validate loaded data for consistency."""
        # Check if all required symbols are present
        required_symbols = self.config['trading']['trading_pairs']
        missing_symbols = [s for s in required_symbols if s not in self.market_data]
        
        if missing_symbols:
            raise ValueError(f"Missing market data for symbols: {missing_symbols}")
        
        # Check data quality
        for symbol, data in self.market_data.items():
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [c for c in required_columns if c not in data.columns]
            
            if missing_columns:
                raise ValueError(f"Missing columns for {symbol}: {missing_columns}")
            
            # Check for NaN values
            if data.isnull().any().any():
                self.logger.log_warning(
                    'data_quality_warning',
                    message=f"NaN values found in {symbol} data"
                )
    
    def run_backtest(self, 
                    start_date: str,
                    end_date: str,
                    initial_capital: float = 100000) -> Dict:
        """Run backtest simulation."""
        try:
            # Initialize portfolio
            portfolio = Portfolio(initial_capital)
            trades = []
            signals = []
            
            # Convert dates to datetime
            start_dt = pd.Timestamp(start_date)
            end_dt = pd.Timestamp(end_date)
            
            # Get common timestamp range
            timestamps = self._get_common_timestamps(start_dt, end_dt)
            
            # Main simulation loop
            for timestamp in timestamps:
                # Get current market data
                current_data = self._get_market_snapshot(timestamp)
                
                # Get sentiment data if available
                sentiment = self._get_sentiment_data(timestamp)
                
                # Update portfolio value
                portfolio.update(current_data['close'])
                
                # Generate trading signals
                for symbol in self.market_data.keys():
                    signal = self.strategy.analyze_market(
                        self._get_symbol_history(symbol, timestamp),
                        sentiment.get(symbol, None)
                    )
                    
                    if signal['action'] != 'HOLD':
                        # Calculate position size
                        position_size = self.position_sizer.get_optimal_position_size(
                            symbol,
                            portfolio.current_capital,
                            signal['confidence'],
                            current_data['volatility'].get(symbol, 0)
                        )
                        
                        # Execute trade
                        trade = self._execute_trade(
                            symbol=symbol,
                            side='buy' if signal['action'] == 'BUY' else 'sell',
                            quantity=position_size,
                            price=current_data['close'][symbol],
                            timestamp=timestamp,
                            portfolio=portfolio
                        )
                        
                        trades.append(trade)
                        signals.append({
                            'timestamp': timestamp,
                            'symbol': symbol,
                            'signal': signal,
                            'trade': trade
                        })
            
            # Calculate results
            self.results = self._calculate_results(portfolio, trades, signals)
            
            return self.results
            
        except Exception as e:
            self.logger.log_error(
                'backtest_error',
                error=str(e),
                context={
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': initial_capital
                }
            )
            raise
    
    def _get_common_timestamps(self, start_dt: pd.Timestamp, 
                             end_dt: pd.Timestamp) -> List[pd.Timestamp]:
        """Get common timestamps across all data sources."""
        timestamps = None
        
        for data in self.market_data.values():
            data_timestamps = data.index[(data.index >= start_dt) & 
                                      (data.index <= end_dt)]
            
            if timestamps is None:
                timestamps = set(data_timestamps)
            else:
                timestamps = timestamps.intersection(data_timestamps)
        
        return sorted(list(timestamps))
    
    def _get_market_snapshot(self, timestamp: pd.Timestamp) -> Dict:
        """Get market data snapshot at given timestamp."""
        snapshot = {
            'close': {},
            'volume': {},
            'volatility': {}
        }
        
        for symbol, data in self.market_data.items():
            if timestamp in data.index:
                snapshot['close'][symbol] = data.loc[timestamp, 'close']
                snapshot['volume'][symbol] = data.loc[timestamp, 'volume']
                
                # Calculate rolling volatility
                volatility_window = self.params.get('volatility_window', 20)
                returns = data['close'].pct_change()
                volatility = returns.rolling(window=volatility_window).std().loc[timestamp]
                snapshot['volatility'][symbol] = volatility
        
        return snapshot
    
    def _get_sentiment_data(self, timestamp: pd.Timestamp) -> Dict:
        """Get sentiment data at given timestamp."""
        sentiment = {}
        
        for symbol, data in self.sentiment_data.items():
            if timestamp in data.index:
                sentiment[symbol] = data.loc[timestamp]
        
        return sentiment
    
    def _get_symbol_history(self, symbol: str, 
                          current_timestamp: pd.Timestamp) -> pd.DataFrame:
        """Get historical data for symbol up to current timestamp."""
        return self.market_data[symbol][self.market_data[symbol].index <= current_timestamp]
    
    def _execute_trade(self, symbol: str, side: str, quantity: float,
                      price: float, timestamp: pd.Timestamp,
                      portfolio: Portfolio) -> Dict:
        """Execute trade with slippage and commission."""
        # Apply slippage
        executed_price = price * (1 + self.slippage) if side == 'buy' else price * (1 - self.slippage)
        
        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': executed_price,
            'commission': self.commission,
            'slippage': self.slippage
        }
        
        return portfolio.execute_trade(trade)
    
    def _calculate_results(self, portfolio: Portfolio,
                         trades: List[Dict],
                         signals: List[Dict]) -> Dict:
        """Calculate comprehensive backtest results."""
        returns = pd.Series(portfolio.returns)
        equity_curve = pd.Series(portfolio.equity_curve)
        
        results = {
            'summary': {
                'initial_capital': portfolio.initial_capital,
                'final_capital': portfolio.equity_curve[-1],
                'total_return': (portfolio.equity_curve[-1] / portfolio.initial_capital - 1),
                'total_trades': len(trades),
                'win_rate': len([t for t in trades if t.get('realized_pnl', 0) > 0]) / len(trades),
                'avg_trade_return': np.mean([t.get('realized_pnl', 0) for t in trades]),
                'max_drawdown': self._calculate_max_drawdown(equity_curve),
                'sharpe_ratio': self._calculate_sharpe_ratio(returns),
                'sortino_ratio': self._calculate_sortino_ratio(returns),
                'calmar_ratio': self._calculate_calmar_ratio(returns, equity_curve)
            },
            'trades': trades,
            'signals': signals,
            'equity_curve': portfolio.equity_curve,
            'returns': portfolio.returns,
            'positions': portfolio.positions
        }
        
        # Add monthly analysis
        results['monthly_analysis'] = self._calculate_monthly_analysis(equity_curve)
        
        # Add symbol-specific analysis
        results['symbol_analysis'] = self._calculate_symbol_analysis(trades)
        
        return results
    
    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown."""
        rolling_max = equity_curve.expanding().max()
        drawdowns = equity_curve / rolling_max - 1
        return float(drawdowns.min())
    
    def _calculate_sharpe_ratio(self, returns: pd.Series,
                              risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate/252
        return float(np.sqrt(252) * excess_returns.mean() / returns.std())
    
    def _calculate_sortino_ratio(self, returns: pd.Series,
                               risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate/252
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')
        
        return float(np.sqrt(252) * excess_returns.mean() / downside_returns.std())
    
    def _calculate_calmar_ratio(self, returns: pd.Series,
                              equity_curve: pd.Series) -> float:
        """Calculate Calmar ratio."""
        if len(returns) < 252:  # Need at least 1 year of data
            return 0.0
        
        annual_return = returns.mean() * 252
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        if max_drawdown == 0:
            return float('inf')
        
        return float(annual_return / abs(max_drawdown))
    
    def _calculate_monthly_analysis(self, equity_curve: pd.Series) -> pd.DataFrame:
        """Calculate monthly performance metrics."""
        monthly_returns = pd.Series(index=equity_curve.index)
        monthly_returns[1:] = equity_curve[1:].values / equity_curve[:-1].values - 1
        
        return monthly_returns.resample('M').agg([
            ('return', 'sum'),
            ('volatility', 'std'),
            ('sharpe', lambda x: np.sqrt(12) * x.mean() / x.std() if len(x) > 1 else 0)
        ])
    
    def _calculate_symbol_analysis(self, trades: List[Dict]) -> Dict:
        """Calculate performance metrics per symbol."""
        symbol_analysis = {}
        
        for symbol in self.market_data.keys():
            symbol_trades = [t for t in trades if t['symbol'] == symbol]
            
            if not symbol_trades:
                continue
            
            pnls = [t.get('realized_pnl', 0) for t in symbol_trades]
            
            symbol_analysis[symbol] = {
                'total_trades': len(symbol_trades),
                'win_rate': len([p for p in pnls if p > 0]) / len(pnls),
                'avg_pnl': np.mean(pnls),
                'total_pnl': sum(pnls),
                'best_trade': max(pnls),
                'worst_trade': min(pnls),
                'avg_holding_time': self._calculate_avg_holding_time(symbol_trades)
            }
        
        return symbol_analysis
    
    def _calculate_avg_holding_time(self, trades: List[Dict]) -> float:
        """Calculate average holding time for trades."""
        holding_times = []
        
        for i in range(0, len(trades) - 1, 2):  # Assuming entry/exit pairs
            if i + 1 < len(trades):
                entry_time = pd.Timestamp(trades[i]['timestamp'])
                exit_time = pd.Timestamp(trades[i + 1]['timestamp'])
                holding_time = (exit_time - entry_time).total_seconds() / 3600  # in hours
                holding_times.append(holding_time)
        
        return np.mean(holding_times) if holding_times else 0
    
    def plot_results(self) -> None:
        """Generate comprehensive visualization of backtest results."""
        if not self.results:
            raise ValueError("No backtest results available. Run backtest first.")
        
        plt.style.use('seaborn')
        fig = plt.figure(figsize=(15, 10))
        
        # Plot equity curve
        ax1 = plt.subplot(2, 2, 1)
        equity_curve = pd.Series(self.results['equity_curve'])
        equity_curve.plot(title='Equity Curve', ax=ax1)
        ax1.set_ylabel('Portfolio Value')
        ax1.grid(True)
        
        # Plot drawdown
        ax2 = plt.subplot(2, 2, 2)
        rolling_max = equity_curve.expanding().max()
        drawdown = equity_curve / rolling_max - 1
        drawdown.plot(title='Drawdown', ax=ax2)
        ax2.set_ylabel('Drawdown')
        ax2.grid(True)
        
        # Plot returns distribution
        ax3 = plt.subplot(2, 2, 3)
        returns = pd.Series(self.results['returns'])
        sns.histplot(returns, kde=True, ax=ax3)
        ax3.set_title('Returns Distribution')
        ax3.set_xlabel('Return')
        ax3.grid(True)
        
        # Plot symbol performance comparison
        ax4 = plt.subplot(2, 2, 4)
        symbol_returns = pd.Series({
            symbol: analysis['total_pnl']
            for symbol, analysis in self.results['symbol_analysis'].items()
        })
        symbol_returns.plot(kind='bar', title='Symbol Performance', ax=ax4)
        ax4.set_ylabel('Total PnL')
        ax4.grid(True)
        
        plt.tight_layout()
        plt.show()
    
    def generate_report(self, output_format: str = 'markdown') -> str:
        """Generate detailed backtest report."""
        if not self.results:
            raise ValueError("No backtest results available. Run backtest first.")
        
        if output_format == 'markdown':
            return self._generate_markdown_report()
        elif output_format == 'html':
            return self._generate_html_report()
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown format report."""
        summary = self.results['summary']
        
        report = f"""
# Backtest Results

## Summary
- Initial Capital: ${summary['initial_capital']:,.2f}
- Final Capital: ${summary['final_capital']:,.2f}
- Total Return: {summary['total_return']:.2%}
- Total Trades: {summary['total_trades']}
- Win Rate: {summary['win_rate']:.2%}
- Average Trade Return: ${summary['avg_trade_return']:,.2f}
- Maximum Drawdown: {summary['max_drawdown']:.2%}
- Sharpe Ratio: {summary['sharpe_ratio']:.2f}
- Sortino Ratio: {summary['sortino_ratio']:.2f}
- Calmar Ratio: {summary['calmar_ratio']:.2f}

## Symbol Analysis
"""
        
        for symbol, analysis in self.results['symbol_analysis'].items():
            report += f"""
### {symbol}
- Total Trades: {analysis['total_trades']}
- Win Rate: {analysis['win_rate']:.2%}
- Average PnL: ${analysis['avg_pnl']:,.2f}
- Total PnL: ${analysis['total_pnl']:,.2f}
- Best Trade: ${analysis['best_trade']:,.2f}
- Worst Trade: ${analysis['worst_trade']:,.2f}
- Average Holding Time: {analysis['avg_holding_time']:.1f} hours
"""
        
        return report 