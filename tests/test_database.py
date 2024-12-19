import pytest
import psycopg2
import yaml
from pathlib import Path
from datetime import datetime, timedelta

def load_config():
    """Load test configuration."""
    config_path = Path('../config/config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

@pytest.fixture
def db_connection():
    """Create database connection for testing."""
    config = load_config()
    conn = psycopg2.connect(
        host=config['database']['host'],
        port=config['database']['port'],
        user=config['database']['user'],
        password=config['database']['password'],
        database=config['database']['name']
    )
    yield conn
    conn.close()

def test_database_connection(db_connection):
    """Test database connection."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    assert result[0] == 1

def test_tables_exist(db_connection):
    """Test if all required tables exist."""
    required_tables = [
        'trades',
        'performance_metrics',
        'alerts',
        'config',
        'strategies',
        'market_data'
    ]
    
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    for table in required_tables:
        assert table in existing_tables

def test_config_data(db_connection):
    """Test if configuration data is properly inserted."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM config")
    count = cursor.fetchone()[0]
    assert count > 0
    
    # Check specific config entries
    cursor.execute("""
        SELECT value 
        FROM config 
        WHERE key = 'risk_limit'
    """)
    risk_limit = float(cursor.fetchone()[0])
    assert 0 < risk_limit < 1

def test_insert_trade(db_connection):
    """Test trade insertion."""
    cursor = db_connection.cursor()
    
    # Insert test trade
    test_trade = {
        'timestamp': datetime.now(),
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'price': 50000.0,
        'quantity': 0.1,
        'pnl': None,
        'commission': 0.001,
        'strategy': 'test_strategy'
    }
    
    cursor.execute("""
        INSERT INTO trades (
            timestamp, symbol, side, price, 
            quantity, pnl, commission, strategy
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id
    """, (
        test_trade['timestamp'],
        test_trade['symbol'],
        test_trade['side'],
        test_trade['price'],
        test_trade['quantity'],
        test_trade['pnl'],
        test_trade['commission'],
        test_trade['strategy']
    ))
    
    db_connection.commit()
    trade_id = cursor.fetchone()[0]
    
    # Verify insertion
    cursor.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
    inserted_trade = cursor.fetchone()
    assert inserted_trade is not None

def test_insert_performance_metric(db_connection):
    """Test performance metric insertion."""
    cursor = db_connection.cursor()
    
    # Insert test metric
    test_metric = {
        'timestamp': datetime.now(),
        'metric_name': 'sharpe_ratio',
        'value': 1.5,
        'symbol': 'BTC/USDT',
        'timeframe': '1h'
    }
    
    cursor.execute("""
        INSERT INTO performance_metrics (
            timestamp, metric_name, value, 
            symbol, timeframe
        ) VALUES (
            %s, %s, %s, %s, %s
        ) RETURNING id
    """, (
        test_metric['timestamp'],
        test_metric['metric_name'],
        test_metric['value'],
        test_metric['symbol'],
        test_metric['timeframe']
    ))
    
    db_connection.commit()
    metric_id = cursor.fetchone()[0]
    
    # Verify insertion
    cursor.execute(
        "SELECT * FROM performance_metrics WHERE id = %s",
        (metric_id,)
    )
    inserted_metric = cursor.fetchone()
    assert inserted_metric is not None

def test_insert_market_data(db_connection):
    """Test market data insertion."""
    cursor = db_connection.cursor()
    
    # Insert test market data
    test_data = {
        'timestamp': datetime.now(),
        'symbol': 'BTC/USDT',
        'open': 50000.0,
        'high': 51000.0,
        'low': 49000.0,
        'close': 50500.0,
        'volume': 100.0
    }
    
    cursor.execute("""
        INSERT INTO market_data (
            timestamp, symbol, open, high, 
            low, close, volume
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id
    """, (
        test_data['timestamp'],
        test_data['symbol'],
        test_data['open'],
        test_data['high'],
        test_data['low'],
        test_data['close'],
        test_data['volume']
    ))
    
    db_connection.commit()
    data_id = cursor.fetchone()[0]
    
    # Verify insertion
    cursor.execute("SELECT * FROM market_data WHERE id = %s", (data_id,))
    inserted_data = cursor.fetchone()
    assert inserted_data is not None

def test_insert_alert(db_connection):
    """Test alert insertion."""
    cursor = db_connection.cursor()
    
    # Insert test alert
    test_alert = {
        'timestamp': datetime.now(),
        'type': 'PRICE_ALERT',
        'message': 'BTC price above 50000',
        'status': 'NEW',
        'metadata': {'price': 50000, 'symbol': 'BTC/USDT'}
    }
    
    cursor.execute("""
        INSERT INTO alerts (
            timestamp, type, message, 
            status, metadata
        ) VALUES (
            %s, %s, %s, %s, %s::jsonb
        ) RETURNING id
    """, (
        test_alert['timestamp'],
        test_alert['type'],
        test_alert['message'],
        test_alert['status'],
        yaml.dump(test_alert['metadata'])
    ))
    
    db_connection.commit()
    alert_id = cursor.fetchone()[0]
    
    # Verify insertion
    cursor.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,))
    inserted_alert = cursor.fetchone()
    assert inserted_alert is not None

def test_database_indexes(db_connection):
    """Test if all required indexes exist."""
    cursor = db_connection.cursor()
    
    # Get all indexes
    cursor.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public'
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    
    # Check required indexes
    required_indexes = [
        'idx_trades_timestamp',
        'idx_trades_symbol',
        'idx_metrics_timestamp',
        'idx_metrics_name',
        'idx_market_data_timestamp',
        'idx_market_data_symbol'
    ]
    
    for index in required_indexes:
        assert index in indexes

def test_database_constraints(db_connection):
    """Test database constraints."""
    cursor = db_connection.cursor()
    
    # Test unique constraint on config keys
    with pytest.raises(psycopg2.IntegrityError):
        cursor.execute("""
            INSERT INTO config (key, value) 
            VALUES ('risk_limit', '0.02')
        """)
        db_connection.commit()
    db_connection.rollback()
    
    # Test unique constraint on strategy names
    with pytest.raises(psycopg2.IntegrityError):
        cursor.execute("""
            INSERT INTO strategies (name, parameters, status) 
            VALUES ('default_strategy', '{}', 'active')
        """)
        db_connection.commit()
    db_connection.rollback()
    
    # Test unique constraint on market data
    with pytest.raises(psycopg2.IntegrityError):
        timestamp = datetime.now()
        cursor.execute("""
            INSERT INTO market_data (
                timestamp, symbol, open, high, 
                low, close, volume
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (timestamp, 'BTC/USDT', 1.0, 1.0, 1.0, 1.0, 1.0))
        cursor.execute("""
            INSERT INTO market_data (
                timestamp, symbol, open, high, 
                low, close, volume
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (timestamp, 'BTC/USDT', 2.0, 2.0, 2.0, 2.0, 2.0))
        db_connection.commit()
    db_connection.rollback() 