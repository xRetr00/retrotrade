import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from .logger import OperationalLogger
from .alert_manager import AlertManager

class PerformanceMonitor:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = OperationalLogger(config)
        self.alert_manager = AlertManager(config)
        
        # Initialize metrics storage
        self.metrics_history = {
            'returns': [],
            'trades': [],
            'equity_curve': [],
            'drawdowns': [],
            'pair_metrics': {}
        }
        
        # Performance thresholds
        self.thresholds = config['monitoring']['thresholds']
        
        # Update frequencies
        self.update_frequencies = {
            'metrics': timedelta(hours=1),
            'pair_analysis': timedelta(hours=1),
            'risk_metrics': timedelta(minutes=5)
        }
        
        # Last update timestamps
        self.last_updates = {
            'metrics': datetime.min,
            'pair_analysis': datetime.min,
            'risk_metrics': datetime.min
        }
    
    def update_metrics(self, new_data: Dict) -> None:
        """Update performance metrics with new data."""
        current_time = datetime.now()
        
        # Update basic metrics
        self.metrics_history['returns'].append(new_data['return'])
        self.metrics_history['trades'].append(new_data['trade'])
        self.metrics_history['equity_curve'].append(new_data['equity'])
        
        # Calculate drawdown
        equity_series = pd.Series(self.metrics_history['equity_curve'])
        drawdown = self._calculate_drawdown(equity_series)
        self.metrics_history['drawdowns'].append(drawdown)
        
        # Check if it's time to update comprehensive metrics
        if current_time - self.last_updates['metrics'] > self.update_frequencies['metrics']:
            self._update_comprehensive_metrics()
            self.last_updates['metrics'] = current_time
        
        # Check if it's time to update pair analysis
        if current_time - self.last_updates['pair_analysis'] > self.update_frequencies['pair_analysis']:
            self._update_pair_analysis()
            self.last_updates['pair_analysis'] = current_time
        
        # Check if it's time to update risk metrics
        if current_time - self.last_updates['risk_metrics'] > self.update_frequencies['risk_metrics']:
            self._update_risk_metrics()
            self.last_updates['risk_metrics'] = current_time
    
    def _calculate_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate current drawdown."""
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        return drawdown.iloc[-1]
    
    def calculate_sharpe_ratio(self, returns: np.array, 
                             risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        excess_returns = returns - risk_free_rate/252
        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
    
    def calculate_calmar_ratio(self, returns: np.array, 
                             period: int = 252) -> float:
        """Calculate Calmar ratio."""
        if len(returns) < period:
            return 0.0
        
        cumulative_returns = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.abs(drawdowns.min())
        
        if max_drawdown == 0:
            return 0.0
        
        annual_return = np.mean(returns) * 252
        return annual_return / max_drawdown
    
    def calculate_omega_ratio(self, returns: np.array, 
                            threshold: float = 0) -> float:
        """Calculate Omega ratio."""
        gains = returns[returns > threshold].sum()
        losses = np.abs(returns[returns < threshold].sum())
        return gains / losses if losses != 0 else np.inf
    
    def _update_comprehensive_metrics(self) -> None:
        """Update comprehensive performance metrics."""
        returns = np.array(self.metrics_history['returns'])
        
        metrics = {
            'sharpe_ratio': self.calculate_sharpe_ratio(returns),
            'calmar_ratio': self.calculate_calmar_ratio(returns),
            'omega_ratio': self.calculate_omega_ratio(returns),
            'max_drawdown': np.min(self.metrics_history['drawdowns']),
            'win_rate': self._calculate_win_rate(),
            'profit_factor': self._calculate_profit_factor(),
            'recovery_factor': self._calculate_recovery_factor(),
            'risk_adjusted_return': self._calculate_risk_adjusted_return()
        }
        
        # Log metrics
        self.logger.log_operation('metrics_update', metrics)
        
        # Check for threshold breaches
        self._check_metric_thresholds(metrics)
    
    def _update_pair_analysis(self) -> None:
        """Update pair-specific performance analysis."""
        for pair in self.config['trading']['trading_pairs']:
            pair_trades = [t for t in self.metrics_history['trades'] 
                         if t['symbol'] == pair]
            
            if len(pair_trades) < self.config['monitoring']['pair_analysis']['min_trades']:
                continue
            
            pair_metrics = {
                'total_trades': len(pair_trades),
                'win_rate': len([t for t in pair_trades if t['pnl'] > 0]) / len(pair_trades),
                'avg_profit': np.mean([t['pnl'] for t in pair_trades]),
                'max_drawdown': self._calculate_pair_drawdown(pair_trades),
                'profit_factor': self._calculate_pair_profit_factor(pair_trades)
            }
            
            self.metrics_history['pair_metrics'][pair] = pair_metrics
            
            # Check for pair-specific issues
            self._check_pair_performance(pair, pair_metrics)
    
    def _update_risk_metrics(self) -> None:
        """Update risk metrics and check for issues."""
        returns = np.array(self.metrics_history['returns'])
        
        risk_metrics = {
            'current_drawdown': self.metrics_history['drawdowns'][-1],
            'volatility': np.std(returns) * np.sqrt(252),
            'var_95': self._calculate_var(returns, 0.95),
            'cvar_95': self._calculate_cvar(returns, 0.95),
            'beta': self._calculate_beta(returns)
        }
        
        # Check for risk threshold breaches
        self._check_risk_thresholds(risk_metrics)
    
    def _check_metric_thresholds(self, metrics: Dict) -> None:
        """Check if any metrics breach their thresholds."""
        for metric, value in metrics.items():
            if metric in self.thresholds:
                threshold = self.thresholds[metric]
                if value < threshold['warning']:
                    self.alert_manager.send_alert(
                        title=f"Performance Warning: {metric}",
                        message=f"{metric} ({value:.2f}) below warning threshold ({threshold['warning']:.2f})",
                        level="WARNING"
                    )
    
    def _check_pair_performance(self, pair: str, metrics: Dict) -> None:
        """Check pair-specific performance issues."""
        thresholds = self.config['monitoring']['pair_analysis']['thresholds']
        
        if metrics['win_rate'] < thresholds['min_win_rate']:
            self.alert_manager.send_alert(
                title=f"Pair Performance Warning: {pair}",
                message=f"Win rate ({metrics['win_rate']:.2%}) below threshold ({thresholds['min_win_rate']:.2%})",
                level="WARNING"
            )
    
    def generate_report(self) -> Dict:
        """Generate comprehensive performance report."""
        returns = np.array(self.metrics_history['returns'])
        
        report = {
            'overall_metrics': {
                'total_return': (1 + returns).prod() - 1,
                'sharpe_ratio': self.calculate_sharpe_ratio(returns),
                'calmar_ratio': self.calculate_calmar_ratio(returns),
                'omega_ratio': self.calculate_omega_ratio(returns),
                'max_drawdown': np.min(self.metrics_history['drawdowns']),
                'win_rate': self._calculate_win_rate(),
                'profit_factor': self._calculate_profit_factor()
            },
            'pair_metrics': self.metrics_history['pair_metrics'],
            'risk_metrics': {
                'current_drawdown': self.metrics_history['drawdowns'][-1],
                'volatility': np.std(returns) * np.sqrt(252),
                'var_95': self._calculate_var(returns, 0.95),
                'cvar_95': self._calculate_cvar(returns, 0.95)
            },
            'trade_metrics': {
                'total_trades': len(self.metrics_history['trades']),
                'avg_trade_duration': self._calculate_avg_trade_duration(),
                'best_trade': self._get_best_trade(),
                'worst_trade': self._get_worst_trade()
            }
        }
        
        return report
    
    def plot_performance(self) -> None:
        """Generate performance visualization."""
        plt.figure(figsize=(15, 10))
        
        # Equity curve
        plt.subplot(2, 2, 1)
        plt.plot(self.metrics_history['equity_curve'])
        plt.title('Equity Curve')
        
        # Drawdown
        plt.subplot(2, 2, 2)
        plt.plot(self.metrics_history['drawdowns'])
        plt.title('Drawdown')
        
        # Returns distribution
        plt.subplot(2, 2, 3)
        plt.hist(self.metrics_history['returns'], bins=50)
        plt.title('Returns Distribution')
        
        # Pair performance comparison
        plt.subplot(2, 2, 4)
        pair_returns = pd.DataFrame(self.metrics_history['pair_metrics']).T['avg_profit']
        pair_returns.plot(kind='bar')
        plt.title('Pair Performance Comparison')
        
        plt.tight_layout()
        plt.show()
    
    def _calculate_var(self, returns: np.array, confidence: float = 0.95) -> float:
        """Calculate Value at Risk."""
        return np.percentile(returns, (1 - confidence) * 100)
    
    def _calculate_cvar(self, returns: np.array, confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        var = self._calculate_var(returns, confidence)
        return np.mean(returns[returns <= var])
    
    def _calculate_beta(self, returns: np.array) -> float:
        """Calculate beta against market returns."""
        market_returns = self._get_market_returns()  # Implement this based on your market data
        if len(market_returns) != len(returns):
            return 0.0
        
        covariance = np.cov(returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        return covariance / market_variance if market_variance != 0 else 0
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trades."""
        if not self.metrics_history['trades']:
            return 0.0
        winning_trades = len([t for t in self.metrics_history['trades'] if t['pnl'] > 0])
        return winning_trades / len(self.metrics_history['trades'])
    
    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor."""
        profits = sum(t['pnl'] for t in self.metrics_history['trades'] if t['pnl'] > 0)
        losses = abs(sum(t['pnl'] for t in self.metrics_history['trades'] if t['pnl'] < 0))
        return profits / losses if losses != 0 else float('inf')
    
    def _calculate_recovery_factor(self) -> float:
        """Calculate recovery factor."""
        if not self.metrics_history['trades']:
            return 0.0
        total_return = sum(t['pnl'] for t in self.metrics_history['trades'])
        max_drawdown = abs(min(self.metrics_history['drawdowns']))
        return total_return / max_drawdown if max_drawdown != 0 else float('inf')
    
    def _calculate_risk_adjusted_return(self) -> float:
        """Calculate risk-adjusted return."""
        returns = np.array(self.metrics_history['returns'])
        if len(returns) < 2:
            return 0.0
        return np.mean(returns) / np.std(returns) * np.sqrt(252) 