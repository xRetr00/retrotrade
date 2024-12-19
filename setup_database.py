import psycopg2
import yaml
import logging
from typing import Dict, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self, config_path: str = 'config/config.yaml'):
        """Initialize database setup with configuration."""
        self.config = self._load_config(config_path)
        self.conn = None
        self.cursor = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise
    
    def connect(self) -> None:
        """Connect to PostgreSQL server."""
        try:
            # Connect to default database to create new database
            self.conn = psycopg2.connect(
                host=self.config['database']['host'],
                port=self.config['database']['port'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                database='postgres'
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            logger.info("Connected to PostgreSQL server")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def create_database(self) -> None:
        """Create the RetroTrade database."""
        try:
            logger.info("Creating database...")
            
            # Check if database exists
            self.cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.config['database']['name'],)
            )
            
            if not self.cursor.fetchone():
                # Create database
                self.cursor.execute(
                    f"CREATE DATABASE {self.config['database']['name']}"
                )
                logger.info(f"Database '{self.config['database']['name']}' created successfully")
            else:
                logger.info(f"Database '{self.config['database']['name']}' already exists")
            
            # Close connection to postgres database
            self.conn.close()
            
            # Connect to the new database
            self.conn = psycopg2.connect(
                host=self.config['database']['host'],
                port=self.config['database']['port'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                database=self.config['database']['name']
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            
        except Exception as e:
            logger.error(f"Failed to create database: {str(e)}")
            raise
    
    def create_tables(self) -> None:
        """Create all required tables."""
        try:
            logger.info("Creating tables...")
            
            # Create trades table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(4) NOT NULL,
                    price DECIMAL NOT NULL,
                    quantity DECIMAL NOT NULL,
                    pnl DECIMAL,
                    commission DECIMAL,
                    strategy VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: trades")
            
            # Create performance metrics table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    metric_name VARCHAR(50) NOT NULL,
                    value DECIMAL NOT NULL,
                    symbol VARCHAR(20),
                    timeframe VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: performance_metrics")
            
            # Create alerts table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(10) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: alerts")
            
            # Create config table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(50) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: config")
            
            # Create strategies table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    parameters JSONB NOT NULL,
                    status VARCHAR(10) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Created table: strategies")
            
            # Create market_data table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    open DECIMAL NOT NULL,
                    high DECIMAL NOT NULL,
                    low DECIMAL NOT NULL,
                    close DECIMAL NOT NULL,
                    volume DECIMAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, symbol)
                )
            """)
            logger.info("Created table: market_data")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise
    
    def insert_initial_data(self) -> None:
        """Insert initial configuration and data."""
        try:
            logger.info("Inserting default configuration...")
            
            # Insert default configuration
            default_config = [
                ('risk_limit', '0.02', 'Maximum risk per trade'),
                ('max_position_size', '0.1', 'Maximum position size as fraction of portfolio'),
                ('default_timeframe', '1h', 'Default trading timeframe'),
                ('stop_loss_multiplier', '2.0', 'Stop loss multiplier for ATR'),
                ('take_profit_multiplier', '3.0', 'Take profit multiplier for ATR'),
                ('max_open_trades', '3', 'Maximum number of concurrent open trades'),
                ('min_volume_usd', '1000000', 'Minimum 24h volume in USD for trading pair')
            ]
            
            self.cursor.executemany(
                """
                INSERT INTO config (key, value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value,
                    description = EXCLUDED.description,
                    updated_at = CURRENT_TIMESTAMP
                """,
                default_config
            )
            
            # Insert default strategy
            default_strategy = {
                'name': 'default_strategy',
                'parameters': {
                    'timeframe': '1h',
                    'indicators': ['RSI', 'MACD', 'BB'],
                    'entry_conditions': [
                        {'indicator': 'RSI', 'condition': '<', 'value': 30},
                        {'indicator': 'MACD', 'condition': 'cross_above', 'value': 0}
                    ],
                    'exit_conditions': [
                        {'indicator': 'RSI', 'condition': '>', 'value': 70},
                        {'indicator': 'BB', 'condition': 'touch_upper', 'value': None}
                    ],
                    'risk_parameters': {
                        'stop_loss': 0.02,
                        'take_profit': 0.04,
                        'max_position_size': 0.1
                    }
                },
                'status': 'active'
            }
            
            self.cursor.execute(
                """
                INSERT INTO strategies (name, parameters, status)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT (name) DO UPDATE
                SET parameters = EXCLUDED.parameters,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    default_strategy['name'],
                    yaml.dump(default_strategy['parameters']),
                    default_strategy['status']
                )
            )
            
            logger.info("Initial data inserted successfully")
            
        except Exception as e:
            logger.error(f"Failed to insert initial data: {str(e)}")
            raise
    
    def create_indexes(self) -> None:
        """Create database indexes for better performance."""
        try:
            logger.info("Creating indexes...")
            
            # Trades table indexes
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
            """)
            
            # Performance metrics indexes
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_metrics_name ON performance_metrics(metric_name);
            """)
            
            # Market data indexes
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);
                CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);
            """)
            
            logger.info("Indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise
    
    def setup(self) -> None:
        """Run complete database setup."""
        try:
            self.connect()
            self.create_database()
            self.create_tables()
            self.insert_initial_data()
            self.create_indexes()
            logger.info("Database setup completed successfully")
        except Exception as e:
            logger.error(f"Database setup failed: {str(e)}")
            raise
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    setup = DatabaseSetup()
    setup.setup() 