import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import talib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging
import os

class StrategyGenerator:
    def __init__(self):
        """Initialize the strategy generator."""
        self.logger = logging.getLogger('StrategyGenerator')
        self.scaler = StandardScaler()
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        # Create models directory if it doesn't exist
        os.makedirs('../models/strategies', exist_ok=True)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        # Price action indicators
        df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
        df['SMA_50'] = talib.SMA(df['close'], timeperiod=50)
        df['SMA_200'] = talib.SMA(df['close'], timeperiod=200)
        
        # Momentum indicators
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(
            df['close'], fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # Volatility indicators
        df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        df['BBANDS_Upper'], df['BBANDS_Middle'], df['BBANDS_Lower'] = talib.BBANDS(
            df['close'], timeperiod=20
        )
        
        # Volume indicators
        df['OBV'] = talib.OBV(df['close'], df['volume'])
        df['ADX'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        
        # Additional indicators
        df['STOCH_K'], df['STOCH_D'] = talib.STOCH(
            df['high'], df['low'], df['close']
        )
        df['CCI'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)
        df['MFI'] = talib.MFI(
            df['high'], df['low'], df['close'], df['volume'], timeperiod=14
        )
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on indicators."""
        signals = pd.DataFrame(index=df.index)
        
        # Trend signals
        signals['trend_signal'] = np.where(
            (df['SMA_20'] > df['SMA_50']) & (df['SMA_50'] > df['SMA_200']),
            1,  # Bullish trend
            np.where(
                (df['SMA_20'] < df['SMA_50']) & (df['SMA_50'] < df['SMA_200']),
                -1,  # Bearish trend
                0  # Neutral
            )
        )
        
        # Momentum signals
        signals['momentum_signal'] = np.where(
            (df['RSI'] > 70) | (df['MACD'] < df['MACD_Signal']),
            -1,  # Overbought
            np.where(
                (df['RSI'] < 30) | (df['MACD'] > df['MACD_Signal']),
                1,  # Oversold
                0  # Neutral
            )
        )
        
        # Volatility signals
        signals['volatility_signal'] = np.where(
            (df['close'] > df['BBANDS_Upper']) & (df['ATR'] > df['ATR'].mean()),
            -1,  # High volatility, potential reversal
            np.where(
                (df['close'] < df['BBANDS_Lower']) & (df['ATR'] > df['ATR'].mean()),
                1,  # High volatility, potential reversal
                0  # Normal volatility
            )
        )
        
        # Volume signals
        signals['volume_signal'] = np.where(
            (df['OBV'].diff() > 0) & (df['ADX'] > 25),
            1,  # Strong volume confirming trend
            np.where(
                (df['OBV'].diff() < 0) & (df['ADX'] > 25),
                -1,  # Strong volume confirming trend
                0  # Weak volume
            )
        )
        
        # Additional signals
        signals['stoch_signal'] = np.where(
            (df['STOCH_K'] < 20) & (df['STOCH_K'] > df['STOCH_D']),
            1,  # Bullish stochastic
            np.where(
                (df['STOCH_K'] > 80) & (df['STOCH_K'] < df['STOCH_D']),
                -1,  # Bearish stochastic
                0  # Neutral
            )
        )
        
        signals['mfi_signal'] = np.where(
            (df['MFI'] < 20),
            1,  # Bullish money flow
            np.where(
                (df['MFI'] > 80),
                -1,  # Bearish money flow
                0  # Neutral
            )
        )
        
        return signals
    
    def prepare_features(self, df: pd.DataFrame, signals: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for machine learning."""
        # Combine indicators and signals
        features = pd.DataFrame(index=df.index)
        
        # Technical indicators
        features['rsi'] = df['RSI']
        features['macd'] = df['MACD']
        features['atr'] = df['ATR']
        features['adx'] = df['ADX']
        features['cci'] = df['CCI']
        features['mfi'] = df['MFI']
        
        # Price ratios
        features['price_sma20'] = df['close'] / df['SMA_20']
        features['price_sma50'] = df['close'] / df['SMA_50']
        features['price_sma200'] = df['close'] / df['SMA_200']
        
        # Signals
        features['trend_signal'] = signals['trend_signal']
        features['momentum_signal'] = signals['momentum_signal']
        features['volatility_signal'] = signals['volatility_signal']
        features['volume_signal'] = signals['volume_signal']
        features['stoch_signal'] = signals['stoch_signal']
        features['mfi_signal'] = signals['mfi_signal']
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Create labels (1 for positive returns, 0 for negative)
        labels = np.where(df['returns'].shift(-1) > 0, 1, 0)
        
        # Drop NaN values
        features = features.dropna()
        labels = labels[features.index]
        
        return features.values, labels
    
    def train_strategy(self, df: pd.DataFrame) -> None:
        """Train the strategy model."""
        try:
            # Calculate indicators
            df_indicators = self.calculate_indicators(df)
            
            # Generate signals
            signals = self.generate_signals(df_indicators)
            
            # Prepare features and labels
            X, y = self.prepare_features(df_indicators, signals)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            
            # Save model and scaler
            joblib.dump(self.model, '../models/strategies/strategy_model.joblib')
            joblib.dump(self.scaler, '../models/strategies/strategy_scaler.joblib')
            
            self.logger.info("Strategy model trained and saved successfully")
        
        except Exception as e:
            self.logger.error(f"Error training strategy model: {str(e)}")
            raise
    
    def predict_signal(self, df: pd.DataFrame) -> Tuple[int, float]:
        """Predict trading signal and confidence."""
        try:
            # Calculate indicators
            df_indicators = self.calculate_indicators(df)
            
            # Generate signals
            signals = self.generate_signals(df_indicators)
            
            # Prepare features
            features, _ = self.prepare_features(df_indicators, signals)
            
            # Scale features
            X_scaled = self.scaler.transform(features[-1:])
            
            # Get prediction and probability
            prediction = self.model.predict(X_scaled)[0]
            confidence = self.model.predict_proba(X_scaled)[0][prediction]
            
            # Convert to signal (-1 for short, 1 for long)
            signal = 1 if prediction == 1 else -1
            
            return signal, confidence
        
        except Exception as e:
            self.logger.error(f"Error predicting signal: {str(e)}")
            raise
    
    def load_model(self) -> None:
        """Load the trained strategy model."""
        try:
            self.model = joblib.load('../models/strategies/strategy_model.joblib')
            self.scaler = joblib.load('../models/strategies/strategy_scaler.joblib')
            self.logger.info("Strategy model loaded successfully")
        
        except Exception as e:
            self.logger.error(f"Error loading strategy model: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    generator = StrategyGenerator()
    print("Strategy generator initialized successfully") 