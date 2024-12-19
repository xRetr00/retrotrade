import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import talib

class MarketRegimeDetector:
    def __init__(self, config: Dict):
        self.config = config
        self.lookback_period = config['market_analysis']['regime_detection']['lookback_period']
        self.scaler = StandardScaler()
        self.gmm = GaussianMixture(n_components=3, random_state=42)
        
    def detect_volatility_regime(self, prices: pd.Series) -> str:
        """Detect volatility regime using rolling volatility."""
        volatility = prices.pct_change().rolling(window=20).std() * np.sqrt(252)
        current_vol = volatility.iloc[-1]
        
        # Define volatility thresholds
        low_threshold = np.percentile(volatility, 33)
        high_threshold = np.percentile(volatility, 66)
        
        if current_vol <= low_threshold:
            return "low_volatility"
        elif current_vol >= high_threshold:
            return "high_volatility"
        else:
            return "medium_volatility"
    
    def detect_trend_regime(self, prices: pd.Series) -> str:
        """Detect trend regime using multiple indicators."""
        # Calculate technical indicators
        sma_20 = talib.SMA(prices, timeperiod=20)
        sma_50 = talib.SMA(prices, timeperiod=50)
        sma_200 = talib.SMA(prices, timeperiod=200)
        
        current_price = prices.iloc[-1]
        
        # Define trend conditions
        strong_uptrend = (current_price > sma_20.iloc[-1] > sma_50.iloc[-1] > sma_200.iloc[-1])
        strong_downtrend = (current_price < sma_20.iloc[-1] < sma_50.iloc[-1] < sma_200.iloc[-1])
        
        if strong_uptrend:
            return "strong_uptrend"
        elif strong_downtrend:
            return "strong_downtrend"
        else:
            return "sideways"
    
    def detect_volume_regime(self, volume: pd.Series) -> str:
        """Detect volume regime using relative volume."""
        avg_volume = volume.rolling(window=20).mean()
        current_rel_volume = volume.iloc[-1] / avg_volume.iloc[-1]
        
        if current_rel_volume >= 2.0:
            return "high_volume"
        elif current_rel_volume <= 0.5:
            return "low_volume"
        else:
            return "normal_volume"
    
    def detect_market_regime(self, data: pd.DataFrame) -> Dict[str, str]:
        """Detect overall market regime using multiple methods."""
        regimes = {
            "volatility": self.detect_volatility_regime(data['close']),
            "trend": self.detect_trend_regime(data['close']),
            "volume": self.detect_volume_regime(data['volume'])
        }
        
        return regimes
    
    def get_regime_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features for regime detection."""
        features = []
        
        # Price-based features
        returns = data['close'].pct_change()
        features.extend([
            returns.mean(),
            returns.std(),
            returns.skew(),
            returns.kurtosis()
        ])
        
        # Volume-based features
        volume_change = data['volume'].pct_change()
        features.extend([
            volume_change.mean(),
            volume_change.std()
        ])
        
        # Technical indicators
        rsi = talib.RSI(data['close'])
        features.append(rsi.iloc[-1])
        
        return np.array(features).reshape(1, -1)
    
    def fit_regime_model(self, historical_data: pd.DataFrame):
        """Fit the regime detection model using historical data."""
        features_list = []
        for i in range(len(historical_data) - self.lookback_period):
            window = historical_data.iloc[i:i+self.lookback_period]
            features = self.get_regime_features(window)
            features_list.append(features.flatten())
        
        X = np.array(features_list)
        X_scaled = self.scaler.fit_transform(X)
        self.gmm.fit(X_scaled)
    
    def predict_regime_state(self, data: pd.DataFrame) -> int:
        """Predict the current regime state."""
        features = self.get_regime_features(data)
        features_scaled = self.scaler.transform(features)
        regime = self.gmm.predict(features_scaled)[0]
        return regime
    
    def get_regime_probabilities(self, data: pd.DataFrame) -> np.ndarray:
        """Get probabilities of each regime state."""
        features = self.get_regime_features(data)
        features_scaled = self.scaler.transform(features)
        probabilities = self.gmm.predict_proba(features_scaled)[0]
        return probabilities 