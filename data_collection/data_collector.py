import ccxt
import pandas as pd
import yaml
from datetime import datetime, timedelta
import os
import logging
from typing import List, Dict, Optional

class DataCollector:
    def __init__(self, config_path: str = 'config/config.yaml'):
        """Initialize the DataCollector with configuration."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Setup exchange
        exchange_config = self.config['exchange']
        credentials = self.config['credentials']['exchange']
        
        self.exchange = getattr(ccxt, exchange_config['name'])({
            'apiKey': credentials['api_key'],
            'secret': credentials['api_secret'],
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        if exchange_config.get('testnet', False):
            self.exchange.set_sandbox_mode(True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('DataCollector')
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, since: Optional[str] = None, limit: int = 1000) -> pd.DataFrame:
        """Fetch OHLCV data for a given symbol and timeframe."""
        try:
            if since is None:
                since = self.config['data_collection']['historical_data_start']
            
            since_ts = int(datetime.strptime(since, '%Y-%m-%d').timestamp() * 1000)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ts, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {str(e)}")
            raise
    
    def save_data(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Save the data to a CSV file."""
        filename = f"data/{symbol.replace('/', '_')}_{timeframe}.csv"
        df.to_csv(filename)
        self.logger.info(f"Data saved to {filename}")
    
    def update_all_pairs(self):
        """Update data for all configured trading pairs and timeframes."""
        trading_pairs = self.config['trading']['trading_pairs']
        timeframes = self.config['trading']['timeframes']
        
        # Collect all pairs from different markets
        all_pairs = []
        for market_type in ['spot', 'futures', 'margin']:
            if market_type in trading_pairs:
                all_pairs.extend(trading_pairs[market_type])
        
        for pair in all_pairs:
            for timeframe in timeframes:
                try:
                    self.logger.info(f"Fetching data for {pair} on {timeframe} timeframe")
                    df = self.fetch_ohlcv(pair, timeframe)
                    self.save_data(df, pair, timeframe)
                except Exception as e:
                    self.logger.error(f"Error updating {pair} {timeframe}: {str(e)}")
    
    def get_latest_price(self, symbol: str) -> float:
        """Get the latest price for a symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"Error fetching latest price: {str(e)}")
            raise

if __name__ == "__main__":
    collector = DataCollector()
    collector.update_all_pairs() 