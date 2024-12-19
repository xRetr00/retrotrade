import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, List, Optional
import joblib
import os
import logging
from datetime import datetime

class BaseMLModel:
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the base ML model with configuration."""
        self.scaler = MinMaxScaler()
        self.model = None
        self.config_path = config_path
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('BaseMLModel')
        
        # Create models directory if it doesn't exist
        os.makedirs('../models', exist_ok=True)
    
    def prepare_data(self, df: pd.DataFrame, sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training or prediction."""
        # Calculate technical indicators
        df = self._add_technical_indicators(df)
        
        # Scale the features
        scaled_data = self.scaler.fit_transform(df)
        
        X, y = [], []
        for i in range(sequence_length, len(scaled_data)):
            X.append(scaled_data[i-sequence_length:i])
            y.append(scaled_data[i, 3])  # Predict close price
        
        return np.array(X), np.array(y)
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the dataframe."""
        # Simple Moving Averages
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        
        # Relative Strength Index (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        df['BB_upper'] = df['BB_middle'] + 2 * df['close'].rolling(window=20).std()
        df['BB_lower'] = df['BB_middle'] - 2 * df['close'].rolling(window=20).std()
        
        # Drop NaN values
        df.dropna(inplace=True)
        return df
    
    def save_model(self, model_name: str):
        """Save the model and scaler."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"../models/{model_name}_{timestamp}"
        os.makedirs(model_path, exist_ok=True)
        
        # Save the model
        if hasattr(self.model, 'save'):
            self.model.save(f"{model_path}/model")
        else:
            joblib.dump(self.model, f"{model_path}/model.joblib")
        
        # Save the scaler
        joblib.dump(self.scaler, f"{model_path}/scaler.joblib")
        self.logger.info(f"Model saved to {model_path}")
    
    def load_model(self, model_path: str):
        """Load the model and scaler."""
        try:
            # Load the scaler
            self.scaler = joblib.load(f"{model_path}/scaler.joblib")
            
            # Load the model
            if os.path.exists(f"{model_path}/model.joblib"):
                self.model = joblib.load(f"{model_path}/model.joblib")
            else:
                # Implement specific model loading logic in child classes
                raise NotImplementedError("Model loading must be implemented in child class")
            
            self.logger.info(f"Model loaded from {model_path}")
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            raise
    
    def predict(self, data: np.ndarray) -> np.ndarray:
        """Make predictions using the model."""
        if self.model is None:
            raise ValueError("Model not loaded or trained")
        return self.model.predict(data)
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        """Evaluate the model performance."""
        raise NotImplementedError("Evaluate method must be implemented in child class") 