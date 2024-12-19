import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.optimizers import Adam
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .market_regime import MarketRegimeDetector
from .base_model import BaseMLModel
import talib

class TransformerModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, output_size: int):
        super().__init__()
        self.transformer_layer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=input_size, nhead=4),
            num_layers=num_layers
        )
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        x = self.transformer_layer(x)
        x = self.fc(x[:, -1, :])  # Take the last sequence output
        return x

class EnsembleModel(BaseMLModel):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.lookback_period = config['ml_settings']['lookback_period']
        self.feature_size = config['ml_settings']['feature_size']
        self.regime_detector = MarketRegimeDetector(config)
        self.scaler = StandardScaler()
        
        # Initialize models
        self.lstm_model = self._build_lstm_model()
        self.transformer_model = TransformerModel(
            input_size=self.feature_size,
            hidden_size=64,
            num_layers=3,
            output_size=3  # Predict: direction, volatility, optimal_position_size
        )
        
        # Initialize sentiment analyzer
        self.tokenizer = AutoTokenizer.from_pretrained('finbert-sentiment')
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained('finbert-sentiment')
        
        # Model weights for ensemble
        self.model_weights = {
            'lstm': 0.3,
            'transformer': 0.3,
            'sentiment': 0.2,
            'regime': 0.2
        }
    
    def _build_lstm_model(self) -> Sequential:
        """Build LSTM model architecture."""
        model = Sequential([
            Bidirectional(LSTM(128, return_sequences=True), 
                         input_shape=(self.lookback_period, self.feature_size)),
            Dropout(0.2),
            Bidirectional(LSTM(64, return_sequences=True)),
            Dropout(0.2),
            Bidirectional(LSTM(32)),
            Dense(16, activation='relu'),
            Dense(3, activation='tanh')  # Predict: direction, volatility, optimal_position_size
        ])
        model.compile(optimizer=Adam(learning_rate=0.001),
                     loss='mse',
                     metrics=['mae'])
        return model
    
    def preprocess_data(self, data: pd.DataFrame) -> np.ndarray:
        """Extract and preprocess features from market data."""
        features = []
        
        # Price-based features
        features.extend([
            data['close'].pct_change(),
            data['high'].pct_change(),
            data['low'].pct_change(),
            data['volume'].pct_change(),
        ])
        
        # Technical indicators
        features.extend([
            talib.RSI(data['close']),
            talib.MACD(data['close'])[0],
            talib.ATR(data['high'], data['low'], data['close']),
            talib.BBANDS(data['close'])[0],
        ])
        
        # Volatility features
        returns = data['close'].pct_change()
        features.extend([
            returns.rolling(window=20).std(),
            returns.rolling(window=20).skew(),
            returns.rolling(window=20).kurt(),
        ])
        
        # Market microstructure features
        features.extend([
            (data['high'] - data['low']) / data['close'],  # Normalized range
            data['volume'] * data['close'],  # Dollar volume
        ])
        
        feature_matrix = np.column_stack(features)
        return self.scaler.fit_transform(feature_matrix)
    
    def prepare_sequences(self, features: np.ndarray) -> np.ndarray:
        """Prepare sequences for LSTM input."""
        sequences = []
        for i in range(len(features) - self.lookback_period):
            sequences.append(features[i:i+self.lookback_period])
        return np.array(sequences)
    
    def train_models(self, train_data: pd.DataFrame, 
                    sentiment_data: Optional[List[str]] = None):
        """Train all models in the ensemble."""
        # Prepare market data
        features = self.preprocess_data(train_data)
        sequences = self.prepare_sequences(features)
        
        # Prepare targets
        future_returns = train_data['close'].pct_change().shift(-1).iloc[self.lookback_period:]
        volatility = train_data['close'].pct_change().rolling(window=20).std().shift(-1).iloc[self.lookback_period:]
        position_sizes = self._calculate_optimal_positions(train_data).iloc[self.lookback_period:]
        
        targets = np.column_stack([
            np.sign(future_returns),
            volatility,
            position_sizes
        ])
        
        # Train LSTM
        self.lstm_model.fit(sequences, targets, 
                          epochs=self.config['ml_settings']['epochs'],
                          batch_size=self.config['ml_settings']['batch_size'],
                          validation_split=0.2)
        
        # Train Transformer
        sequences_torch = torch.FloatTensor(sequences)
        targets_torch = torch.FloatTensor(targets)
        self._train_transformer(sequences_torch, targets_torch)
        
        # Train regime detector
        self.regime_detector.fit_regime_model(train_data)
    
    def _train_transformer(self, sequences: torch.Tensor, 
                         targets: torch.Tensor, 
                         epochs: int = 100):
        """Train the Transformer model."""
        optimizer = torch.optim.Adam(self.transformer_model.parameters())
        criterion = nn.MSELoss()
        
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.transformer_model(sequences)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
    
    def predict(self, market_data: pd.DataFrame, 
                sentiment_data: Optional[List[str]] = None) -> Dict[str, float]:
        """Generate ensemble predictions."""
        # Prepare market data
        features = self.preprocess_data(market_data)
        sequence = self.prepare_sequences(features)[-1:]  # Get last sequence
        
        # LSTM prediction
        lstm_pred = self.lstm_model.predict(sequence)[0]
        
        # Transformer prediction
        sequence_torch = torch.FloatTensor(sequence)
        transformer_pred = self.transformer_model(sequence_torch).detach().numpy()[0]
        
        # Sentiment prediction
        if sentiment_data:
            sentiment_scores = self._analyze_sentiment(sentiment_data)
        else:
            sentiment_scores = np.zeros(3)
        
        # Regime prediction
        regime_state = self.regime_detector.predict_regime_state(market_data)
        regime_probs = self.regime_detector.get_regime_probabilities(market_data)
        
        # Combine predictions
        ensemble_pred = (
            lstm_pred * self.model_weights['lstm'] +
            transformer_pred * self.model_weights['transformer'] +
            sentiment_scores * self.model_weights['sentiment'] +
            regime_probs * self.model_weights['regime']
        )
        
        return {
            'direction': ensemble_pred[0],
            'volatility': ensemble_pred[1],
            'position_size': ensemble_pred[2],
            'confidence': self._calculate_prediction_confidence(
                lstm_pred, transformer_pred, sentiment_scores, regime_probs
            ),
            'regime_state': regime_state
        }
    
    def _analyze_sentiment(self, texts: List[str]) -> np.ndarray:
        """Analyze sentiment from text data."""
        sentiments = []
        for text in texts:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            outputs = self.sentiment_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            sentiments.append(probs.detach().numpy()[0])
        
        return np.mean(sentiments, axis=0)
    
    def _calculate_prediction_confidence(self, lstm_pred: np.ndarray,
                                      transformer_pred: np.ndarray,
                                      sentiment_scores: np.ndarray,
                                      regime_probs: np.ndarray) -> float:
        """Calculate confidence score for ensemble prediction."""
        # Calculate agreement between models
        predictions = [lstm_pred, transformer_pred, sentiment_scores, regime_probs]
        agreements = []
        
        for i in range(len(predictions)):
            for j in range(i + 1, len(predictions)):
                correlation = np.corrcoef(predictions[i], predictions[j])[0, 1]
                agreements.append(abs(correlation))
        
        # Average agreement weighted by model weights
        confidence = np.mean(agreements) * (
            np.max(regime_probs) * self.model_weights['regime'] +
            np.max(sentiment_scores) * self.model_weights['sentiment']
        )
        
        return min(max(confidence, 0), 1)  # Normalize to [0, 1]
    
    def _calculate_optimal_positions(self, data: pd.DataFrame) -> pd.Series:
        """Calculate historically optimal position sizes."""
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=20).std()
        sharpe = returns.rolling(window=20).mean() / volatility
        
        # Scale position sizes based on Sharpe ratio
        position_sizes = (sharpe - sharpe.min()) / (sharpe.max() - sharpe.min())
        return position_sizes.clip(0, 1)
    
    def update_model_weights(self, performance_metrics: Dict[str, float]):
        """Dynamically update model weights based on performance."""
        total_weight = sum(performance_metrics.values())
        if total_weight > 0:
            self.model_weights = {
                model: metric / total_weight
                for model, metric in performance_metrics.items()
            }
    
    def save_models(self, path: str):
        """Save all models and weights."""
        self.lstm_model.save(f"{path}/lstm_model")
        torch.save(self.transformer_model.state_dict(), f"{path}/transformer_model.pt")
        np.save(f"{path}/model_weights.npy", self.model_weights)
    
    def load_models(self, path: str):
        """Load all models and weights."""
        self.lstm_model = tf.keras.models.load_model(f"{path}/lstm_model")
        self.transformer_model.load_state_dict(torch.load(f"{path}/transformer_model.pt"))
        self.model_weights = np.load(f"{path}/model_weights.npy", allow_pickle=True).item() 