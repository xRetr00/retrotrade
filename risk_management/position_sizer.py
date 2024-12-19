import numpy as np
import pandas as pd
from typing import Dict, Optional
import talib
from arch import arch_model

class DynamicPositionSizer:
    def __init__(self, config: Dict):
        self.config = config
        self.position_config = config['risk_controls']['dynamic_position_sizing']
        self.volatility_lookback = self.position_config['volatility_lookback']
        self.position_scale_factor = self.position_config['position_scale_factor']
        self.min_position_size = self.position_config['min_position_size']
        self.max_position_size = self.position_config['max_position_size']
    
    def calculate_volatility_adjusted_size(self, data: pd.DataFrame, 
                                        base_position_size: float,
                                        method: str = 'standard') -> float:
        """Calculate position size adjusted for volatility."""
        if method == 'standard':
            volatility = self._calculate_standard_volatility(data)
        elif method == 'garch':
            volatility = self._calculate_garch_volatility(data)
        else:
            raise ValueError(f"Unknown volatility method: {method}")
        
        # Inverse relationship with volatility
        volatility_scalar = 1 / (1 + volatility * self.position_scale_factor)
        position_size = base_position_size * volatility_scalar
        
        # Apply limits
        position_size = max(min(position_size, self.max_position_size), 
                          self.min_position_size)
        
        return position_size
    
    def _calculate_standard_volatility(self, data: pd.DataFrame) -> float:
        """Calculate standard deviation based volatility."""
        returns = data['close'].pct_change().dropna()
        volatility = returns.rolling(window=self.volatility_lookback).std().iloc[-1]
        return volatility * np.sqrt(252)  # Annualized volatility
    
    def _calculate_garch_volatility(self, data: pd.DataFrame) -> float:
        """Calculate GARCH-based volatility forecast."""
        returns = data['close'].pct_change().dropna() * 100
        model = arch_model(returns, vol='Garch', p=1, q=1)
        model_fit = model.fit(disp='off')
        forecast = model_fit.forecast(horizon=1)
        return forecast.variance.iloc[-1, 0] / 100
    
    def adjust_for_market_regime(self, position_size: float, 
                               market_regime: Dict[str, str]) -> float:
        """Adjust position size based on market regime."""
        # Volatility regime adjustment
        vol_adjustments = {
            'low_volatility': 1.2,
            'medium_volatility': 1.0,
            'high_volatility': 0.8
        }
        position_size *= vol_adjustments.get(market_regime['volatility'], 1.0)
        
        # Trend regime adjustment
        trend_adjustments = {
            'strong_uptrend': 1.2,
            'strong_downtrend': 0.8,
            'sideways': 1.0
        }
        position_size *= trend_adjustments.get(market_regime['trend'], 1.0)
        
        # Volume regime adjustment
        volume_adjustments = {
            'high_volume': 1.1,
            'normal_volume': 1.0,
            'low_volume': 0.9
        }
        position_size *= volume_adjustments.get(market_regime['volume'], 1.0)
        
        # Apply limits again
        position_size = max(min(position_size, self.max_position_size), 
                          self.min_position_size)
        
        return position_size
    
    def calculate_kelly_criterion(self, win_rate: float, 
                                avg_win: float, 
                                avg_loss: float) -> float:
        """Calculate position size using Kelly Criterion."""
        if avg_loss == 0 or win_rate >= 1 or win_rate <= 0:
            return 0
        
        kelly_fraction = (win_rate / abs(avg_loss)) - ((1 - win_rate) / abs(avg_loss))
        kelly_fraction = max(min(kelly_fraction, self.max_position_size), 0)
        
        return kelly_fraction
    
    def adjust_for_correlation(self, position_size: float, 
                             correlation_data: Dict[str, float]) -> float:
        """Adjust position size based on correlation with other positions."""
        # Reduce position size if highly correlated with existing positions
        if correlation_data:
            max_correlation = max(correlation_data.values())
            if max_correlation > 0.5:  # High correlation threshold
                reduction_factor = 1 - (max_correlation - 0.5)  # Linear reduction
                position_size *= max(reduction_factor, 0.5)  # At least 50% reduction
        
        return position_size
    
    def get_optimal_position_size(self, data: pd.DataFrame,
                                base_position_size: float,
                                market_regime: Dict[str, str],
                                correlation_data: Optional[Dict[str, float]] = None,
                                performance_metrics: Optional[Dict] = None) -> float:
        """Calculate optimal position size considering all factors."""
        # Start with volatility-adjusted size
        position_size = self.calculate_volatility_adjusted_size(
            data, base_position_size, method='garch'
        )
        
        # Adjust for market regime
        position_size = self.adjust_for_market_regime(position_size, market_regime)
        
        # Adjust for correlation if data available
        if correlation_data:
            position_size = self.adjust_for_correlation(position_size, correlation_data)
        
        # Apply Kelly Criterion if performance metrics available
        if performance_metrics and all(k in performance_metrics for k in ['win_rate', 'avg_win', 'avg_loss']):
            kelly_size = self.calculate_kelly_criterion(
                performance_metrics['win_rate'],
                performance_metrics['avg_win'],
                performance_metrics['avg_loss']
            )
            # Blend with volatility-adjusted size
            position_size = (position_size + kelly_size) / 2
        
        # Final limits check
        position_size = max(min(position_size, self.max_position_size), 
                          self.min_position_size)
        
        return position_size 