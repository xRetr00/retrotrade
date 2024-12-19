import ccxt
import yaml
import logging
from typing import Dict, Optional
from datetime import datetime
import sys
sys.path.append('..')
from risk_management.risk_manager import RiskManager

class TradeExecutor:
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the TradeExecutor with configuration."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Setup exchange
        exchange_config = self.config['exchange']
        self.exchange = getattr(ccxt, exchange_config['name'])({
            'apiKey': exchange_config['api_key'],
            'secret': exchange_config['api_secret'],
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        if exchange_config['testnet']:
            self.exchange.set_sandbox_mode(True)
        
        # Initialize risk manager
        self.risk_manager = RiskManager(config_path)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TradeExecutor')
    
    def get_account_balance(self) -> float:
        """Get the current account balance."""
        try:
            balance = self.exchange.fetch_balance()
            total_balance = balance['total']['USDT']
            self.logger.info(f"Current account balance: {total_balance} USDT")
            return total_balance
        
        except Exception as e:
            self.logger.error(f"Error fetching account balance: {str(e)}")
            raise
    
    def place_order(self, symbol: str, side: str, amount: float, 
                   price: Optional[float] = None, order_type: str = 'market') -> dict:
        """Place an order on the exchange."""
        try:
            order_params = {
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount
            }
            
            if order_type == 'limit' and price is not None:
                order_params['price'] = price
            
            order = self.exchange.create_order(**order_params)
            self.logger.info(f"Order placed: {order}")
            return order
        
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            raise
    
    def execute_trade_signal(self, symbol: str, signal_type: str, 
                           predicted_price: float) -> Optional[dict]:
        """Execute a trade based on the signal."""
        try:
            # Check if we can open a position
            if not self.risk_manager.can_open_position(symbol):
                return None
            
            # Get current market price
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Get account balance
            account_balance = self.get_account_balance()
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                symbol, current_price, account_balance
            )
            
            # Calculate stop loss and take profit
            stop_loss = self.risk_manager.calculate_stop_loss(
                symbol, current_price, signal_type
            )
            take_profit = self.risk_manager.calculate_take_profit(
                symbol, current_price, signal_type
            )
            
            # Place the main order
            order = self.place_order(
                symbol=symbol,
                side='buy' if signal_type.lower() == 'long' else 'sell',
                amount=position_size
            )
            
            if order['status'] == 'closed':
                # Place stop loss order
                self.place_order(
                    symbol=symbol,
                    side='sell' if signal_type.lower() == 'long' else 'buy',
                    amount=position_size,
                    price=stop_loss,
                    order_type='stop'
                )
                
                # Place take profit order
                self.place_order(
                    symbol=symbol,
                    side='sell' if signal_type.lower() == 'long' else 'buy',
                    amount=position_size,
                    price=take_profit,
                    order_type='limit'
                )
                
                # Track the position
                self.risk_manager.track_position(
                    symbol=symbol,
                    position_type=signal_type,
                    entry_price=current_price,
                    position_size=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                return order
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error executing trade signal: {str(e)}")
            raise
    
    def close_position(self, symbol: str) -> Optional[dict]:
        """Close an open position."""
        try:
            if symbol not in self.risk_manager.open_positions:
                return None
            
            position = self.risk_manager.open_positions[symbol]
            
            # Place closing order
            order = self.place_order(
                symbol=symbol,
                side='sell' if position['type'].lower() == 'long' else 'buy',
                amount=position['position_size']
            )
            
            if order['status'] == 'closed':
                # Remove position tracking
                self.risk_manager.close_position(symbol)
                return order
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")
            raise
    
    def check_and_update_positions(self):
        """Check and update all open positions."""
        try:
            for symbol in list(self.risk_manager.open_positions.keys()):
                # Get current price
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Check if position should be closed
                exit_signal = self.risk_manager.check_position_exits(symbol, current_price)
                
                if exit_signal:
                    self.logger.info(f"Closing position for {symbol} due to {exit_signal}")
                    self.close_position(symbol)
        
        except Exception as e:
            self.logger.error(f"Error updating positions: {str(e)}")
            raise
    
    def get_open_positions(self) -> Dict[str, dict]:
        """Get all open positions."""
        return self.risk_manager.open_positions

if __name__ == "__main__":
    # Example usage
    executor = TradeExecutor()
    print("Trade executor initialized successfully") 