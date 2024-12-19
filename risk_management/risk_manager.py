import yaml
import logging
from typing import Dict, Optional
import numpy as np

class RiskManager:
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the RiskManager with configuration."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.risk_config = self.config['risk_management']
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('RiskManager')
        
        # Track open positions
        self.open_positions: Dict[str, dict] = {}
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              account_balance: float, risk_per_trade: Optional[float] = None) -> float:
        """Calculate the position size based on risk parameters."""
        try:
            if risk_per_trade is None:
                risk_per_trade = self.risk_config['max_position_size']
            
            # Calculate maximum position size based on account balance
            max_position_value = account_balance * risk_per_trade
            
            # Calculate position size in base currency
            position_size = max_position_value / entry_price
            
            self.logger.info(f"Calculated position size for {symbol}: {position_size}")
            return position_size
        
        except Exception as e:
            self.logger.error(f"Error calculating position size: {str(e)}")
            raise
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                          position_type: str) -> float:
        """Calculate stop loss price based on risk parameters."""
        try:
            stop_loss_percentage = self.risk_config['stop_loss_percentage']
            
            if position_type.lower() == 'long':
                stop_loss = entry_price * (1 - stop_loss_percentage)
            else:  # short position
                stop_loss = entry_price * (1 + stop_loss_percentage)
            
            self.logger.info(f"Calculated stop loss for {symbol}: {stop_loss}")
            return stop_loss
        
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {str(e)}")
            raise
    
    def calculate_take_profit(self, symbol: str, entry_price: float, 
                            position_type: str) -> float:
        """Calculate take profit price based on risk parameters."""
        try:
            take_profit_percentage = self.risk_config['take_profit_percentage']
            
            if position_type.lower() == 'long':
                take_profit = entry_price * (1 + take_profit_percentage)
            else:  # short position
                take_profit = entry_price * (1 - take_profit_percentage)
            
            self.logger.info(f"Calculated take profit for {symbol}: {take_profit}")
            return take_profit
        
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {str(e)}")
            raise
    
    def can_open_position(self, symbol: str) -> bool:
        """Check if a new position can be opened based on risk rules."""
        try:
            # Check maximum number of open positions
            if len(self.open_positions) >= self.risk_config['max_open_trades']:
                self.logger.warning("Maximum number of open positions reached")
                return False
            
            # Check if position already exists for this symbol
            if symbol in self.open_positions:
                self.logger.warning(f"Position already exists for {symbol}")
                return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error checking position opening: {str(e)}")
            raise
    
    def track_position(self, symbol: str, position_type: str, entry_price: float, 
                      position_size: float, stop_loss: float, take_profit: float):
        """Track a new position."""
        try:
            self.open_positions[symbol] = {
                'type': position_type,
                'entry_price': entry_price,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            self.logger.info(f"Tracking new position for {symbol}")
        
        except Exception as e:
            self.logger.error(f"Error tracking position: {str(e)}")
            raise
    
    def close_position(self, symbol: str):
        """Close a tracked position."""
        try:
            if symbol in self.open_positions:
                del self.open_positions[symbol]
                self.logger.info(f"Closed position for {symbol}")
            else:
                self.logger.warning(f"No position found for {symbol}")
        
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")
            raise
    
    def check_position_exits(self, symbol: str, current_price: float) -> Optional[str]:
        """Check if position should be closed based on stop loss or take profit."""
        try:
            if symbol not in self.open_positions:
                return None
            
            position = self.open_positions[symbol]
            
            if position['type'].lower() == 'long':
                if current_price <= position['stop_loss']:
                    return 'stop_loss'
                elif current_price >= position['take_profit']:
                    return 'take_profit'
            else:  # short position
                if current_price >= position['stop_loss']:
                    return 'stop_loss'
                elif current_price <= position['take_profit']:
                    return 'take_profit'
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error checking position exits: {str(e)}")
            raise
    
    def get_position_risk_metrics(self, symbol: str) -> Optional[dict]:
        """Get risk metrics for an open position."""
        try:
            if symbol not in self.open_positions:
                return None
            
            position = self.open_positions[symbol]
            
            risk_amount = abs(position['entry_price'] - position['stop_loss']) * position['position_size']
            reward_amount = abs(position['take_profit'] - position['entry_price']) * position['position_size']
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            
            return {
                'risk_amount': risk_amount,
                'reward_amount': reward_amount,
                'risk_reward_ratio': risk_reward_ratio
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating position risk metrics: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    risk_manager = RiskManager()
    print("Risk manager initialized successfully") 