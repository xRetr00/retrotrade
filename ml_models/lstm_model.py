import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import yaml
from .base_model import BaseMLModel

class LSTMModel(BaseMLModel):
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the LSTM model."""
        super().__init__(config_path)
        
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self._build_model()
    
    def _build_model(self):
        """Build the LSTM model architecture."""
        self.model = Sequential([
            LSTM(units=50, return_sequences=True, input_shape=(60, 13)),  # 13 features
            Dropout(0.2),
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            LSTM(units=50),
            Dropout(0.2),
            Dense(units=1)
        ])
        
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mean_squared_error'
        )
        
        self.logger.info("LSTM model built successfully")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
             X_val: np.ndarray, y_val: np.ndarray):
        """Train the LSTM model."""
        try:
            ml_config = self.config['ml_settings']
            
            history = self.model.fit(
                X_train, y_train,
                epochs=ml_config['epochs'],
                batch_size=ml_config['batch_size'],
                validation_data=(X_val, y_val),
                verbose=1
            )
            
            self.logger.info("Model training completed successfully")
            return history
        
        except Exception as e:
            self.logger.error(f"Error during training: {str(e)}")
            raise
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        """Evaluate the model performance."""
        try:
            # Make predictions
            y_pred = self.model.predict(X_test)
            
            # Calculate metrics
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            metrics = {
                'mse': float(mse),
                'rmse': float(rmse),
                'mae': float(mae),
                'r2': float(r2)
            }
            
            self.logger.info(f"Model evaluation metrics: {metrics}")
            return metrics
        
        except Exception as e:
            self.logger.error(f"Error during evaluation: {str(e)}")
            raise
    
    def predict_next_price(self, data: np.ndarray) -> float:
        """Predict the next price point."""
        try:
            # Ensure data is properly shaped
            if len(data.shape) == 2:
                data = np.expand_dims(data, axis=0)
            
            # Make prediction
            prediction = self.model.predict(data)
            
            # Inverse transform the prediction
            prediction_original_scale = self.scaler.inverse_transform(
                np.array([[0] * 3 + [prediction[0][0]] + [0] * 9])
            )[0][3]
            
            return float(prediction_original_scale)
        
        except Exception as e:
            self.logger.error(f"Error during prediction: {str(e)}")
            raise
    
    def load_model(self, model_path: str):
        """Load the LSTM model and scaler."""
        try:
            # Load the scaler
            super().load_model(model_path)
            
            # Load the Keras model
            self.model = tf.keras.models.load_model(f"{model_path}/model")
            self.logger.info(f"LSTM model loaded from {model_path}")
        
        except Exception as e:
            self.logger.error(f"Error loading LSTM model: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    model = LSTMModel()
    print("Model initialized successfully") 