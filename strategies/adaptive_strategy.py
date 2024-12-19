import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from ..ml_models.ensemble_model import DeepEnsembleModel
from ..ml_models.market_regime import MarketRegimeDetector
from ..risk_management.position_sizer import DynamicPositionSizer
import talib

class AdaptiveStrategy:
    def __init__(self, config: Dict):
        self.config = config
        self.ensemble_model = DeepEnsembleModel(config)
        self.position_sizer = DynamicPositionSizer(config)
        self.regime_detector = MarketRegimeDetector(config)
        
        # Strategy parameters
        self.min_confidence = config['strategy']['confidence_threshold']
        self.position_holding_time = {}
        self.active_positions = {}
        
        # Performance tracking
        self.performance_metrics = {
            'trades': [],
            'returns': [],
            'drawdowns': [],
            'sharpe_ratio': 0,
            'win_rate': 0
        }
        
        # Adaptive parameters
        self.adaptive_params = {
            'stop_loss': config['risk_management']['stop_loss_percentage'],
            'take_profit': config['risk_management']['take_profit_percentage'],
            'entry_threshold': 0.7,
            'exit_threshold': -0.3,
            'holding_period': 24  # hours
        }
    
    def analyze_market(self, market_data: pd.DataFrame, 
                      sentiment_data: Optional[List[str]] = None) -> Dict:
        """Analyze market conditions and generate trading signals."""
        # Get ensemble model predictions
        predictions = self.ensemble_model.predict(market_data, sentiment_data)
        
        # Detect market regime
        regime = self.regime_detector.detect_market_regime(market_data)
        
        # Calculate optimal position size
        position_size = self.position_sizer.get_optimal_position_size(
            market_data,
            predictions['position_size'],
            regime,
            self._get_correlation_data(market_data),
            self.performance_metrics
        )
        
        # Adjust strategy parameters based on regime
        self._adjust_parameters(regime, market_data)
        
        return {
            'signal': self._generate_signal(predictions, regime),
            'position_size': position_size,
            'confidence': predictions['confidence'],
            'regime': regime,
            'parameters': self.adaptive_params
        }
    
    def _generate_signal(self, predictions: Dict, regime: Dict) -> str:
        """Generate trading signal based on predictions and regime."""
        direction = predictions['direction']
        confidence = predictions['confidence']
        
        # Adjust thresholds based on regime
        if regime['volatility'] == 'high_volatility':
            self.min_confidence *= 1.2  # Require higher confidence in volatile markets
        elif regime['volatility'] == 'low_volatility':
            self.min_confidence *= 0.8
        
        if confidence < self.min_confidence:
            return "NEUTRAL"
        
        if direction > self.adaptive_params['entry_threshold']:
            return "BUY"
        elif direction < self.adaptive_params['exit_threshold']:
            return "SELL"
        
        return "NEUTRAL"
    
    def _adjust_parameters(self, regime: Dict, market_data: pd.DataFrame):
        """Dynamically adjust strategy parameters based on market conditions."""
        volatility = market_data['close'].pct_change().std() * np.sqrt(252)
        
        # Adjust stop loss and take profit based on volatility
        if regime['volatility'] == 'high_volatility':
            self.adaptive_params['stop_loss'] *= 1.2
            self.adaptive_params['take_profit'] *= 1.2
            self.adaptive_params['holding_period'] *= 0.8
        elif regime['volatility'] == 'low_volatility':
            self.adaptive_params['stop_loss'] *= 0.8
            self.adaptive_params['take_profit'] *= 0.8
            self.adaptive_params['holding_period'] *= 1.2
        
        # Adjust entry/exit thresholds based on trend
        if regime['trend'] == 'strong_uptrend':
            self.adaptive_params['entry_threshold'] *= 0.9  # More aggressive entries
            self.adaptive_params['exit_threshold'] *= 1.1  # More conservative exits
        elif regime['trend'] == 'strong_downtrend':
            self.adaptive_params['entry_threshold'] *= 1.1  # More conservative entries
            self.adaptive_params['exit_threshold'] *= 0.9  # More aggressive exits
        
        # Adjust based on performance
        if self.performance_metrics['win_rate'] < 0.4:
            self.adaptive_params['entry_threshold'] *= 1.1  # More conservative
            self.min_confidence *= 1.1
        elif self.performance_metrics['win_rate'] > 0.6:
            self.adaptive_params['entry_threshold'] *= 0.9  # More aggressive
            self.min_confidence *= 0.9
    
    def _get_correlation_data(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate correlation between trading pairs."""
        correlations = {}
        for pair in self.active_positions:
            if pair in market_data.columns:
                corr = market_data[pair].corr(market_data['close'])
                correlations[pair] = corr
        return correlations
    
    def update_performance_metrics(self, trade_result: Dict):
        """Update strategy performance metrics."""
        self.performance_metrics['trades'].append(trade_result)
        self.performance_metrics['returns'].append(trade_result['return'])
        
        # Calculate metrics
        returns = np.array(self.performance_metrics['returns'])
        self.performance_metrics['sharpe_ratio'] = self._calculate_sharpe_ratio(returns)
        self.performance_metrics['win_rate'] = np.mean(returns > 0)
        
        # Update model weights based on performance
        self.ensemble_model.update_model_weights({
            'lstm': self.performance_metrics['sharpe_ratio'],
            'transformer': self.performance_metrics['win_rate'],
            'sentiment': self.performance_metrics['win_rate'],
            'regime': self.performance_metrics['sharpe_ratio']
        })
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio of returns."""
        if len(returns) < 2:
            return 0
        return np.mean(returns) / (np.std(returns) + 1e-6) * np.sqrt(252)
    
    def should_exit_position(self, position: Dict, current_price: float, 
                           market_data: pd.DataFrame) -> Tuple[bool, str]:
        """Determine if position should be closed."""
        # Calculate returns
        entry_price = position['entry_price']
        returns = (current_price - entry_price) / entry_price
        
        # Check stop loss and take profit
        if returns <= -self.adaptive_params['stop_loss']:
            return True, "stop_loss"
        if returns >= self.adaptive_params['take_profit']:
            return True, "take_profit"
        
        # Check holding time
        holding_time = position['holding_time']
        if holding_time >= self.adaptive_params['holding_period']:
            return True, "holding_period"
        
        # Check trend reversal
        predictions = self.ensemble_model.predict(market_data)
        if (position['side'] == 'BUY' and 
            predictions['direction'] < self.adaptive_params['exit_threshold']):
            return True, "trend_reversal"
        if (position['side'] == 'SELL' and 
            predictions['direction'] > self.adaptive_params['entry_threshold']):
            return True, "trend_reversal"
        
        return False, ""
    
    def train(self, historical_data: pd.DataFrame, 
              sentiment_data: Optional[List[str]] = None):
        """Train all models in the strategy."""
        self.ensemble_model.train_models(historical_data, sentiment_data)
    
    def save_state(self, path: str):
        """Save strategy state and models."""
        self.ensemble_model.save_models(f"{path}/models")
        np.save(f"{path}/adaptive_params.npy", self.adaptive_params)
        np.save(f"{path}/performance_metrics.npy", self.performance_metrics)
    
    def load_state(self, path: str):
        """Load strategy state and models."""
        self.ensemble_model.load_models(f"{path}/models")
        self.adaptive_params = np.load(f"{path}/adaptive_params.npy", 
                                     allow_pickle=True).item()
        self.performance_metrics = np.load(f"{path}/performance_metrics.npy", 
                                         allow_pickle=True).item() 