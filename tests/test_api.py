import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json
import yaml
from pathlib import Path
from web_interface.api import app

client = TestClient(app)

def load_config():
    """Load test configuration."""
    config_path = Path('../config/config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    config = load_config()
    return {
        "Authorization": f"Bearer {config['api']['test_token']}"
    }

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_auth_required(auth_headers):
    """Test authentication requirement."""
    # Without auth headers
    response = client.get("/api/v1/trades")
    assert response.status_code == 401
    
    # With auth headers
    response = client.get("/api/v1/trades", headers=auth_headers)
    assert response.status_code == 200

def test_get_trades(auth_headers):
    """Test trades endpoint."""
    response = client.get("/api/v1/trades", headers=auth_headers)
    assert response.status_code == 200
    trades = response.json()
    assert isinstance(trades, list)
    
    # Test with filters
    params = {
        'symbol': 'BTC/USDT',
        'start_date': (datetime.now() - timedelta(days=7)).isoformat(),
        'end_date': datetime.now().isoformat()
    }
    response = client.get("/api/v1/trades", params=params, headers=auth_headers)
    assert response.status_code == 200
    filtered_trades = response.json()
    assert isinstance(filtered_trades, list)
    
    # Verify filtered trades
    for trade in filtered_trades:
        assert trade['symbol'] == 'BTC/USDT'
        assert params['start_date'] <= trade['timestamp'] <= params['end_date']

def test_get_performance_metrics(auth_headers):
    """Test performance metrics endpoint."""
    response = client.get("/api/v1/metrics", headers=auth_headers)
    assert response.status_code == 200
    metrics = response.json()
    assert isinstance(metrics, dict)
    
    # Check required metrics
    required_metrics = [
        'sharpe_ratio',
        'max_drawdown',
        'win_rate',
        'profit_factor'
    ]
    for metric in required_metrics:
        assert metric in metrics

def test_get_market_data(auth_headers):
    """Test market data endpoint."""
    params = {
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'limit': 100
    }
    response = client.get("/api/v1/market-data", params=params, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= params['limit']
    
    # Verify data structure
    for candle in data:
        assert all(k in candle for k in ['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def test_get_alerts(auth_headers):
    """Test alerts endpoint."""
    response = client.get("/api/v1/alerts", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
    
    # Test alert creation
    test_alert = {
        'type': 'PRICE_ALERT',
        'message': 'Test alert',
        'metadata': {'price': 50000, 'symbol': 'BTC/USDT'}
    }
    response = client.post(
        "/api/v1/alerts",
        json=test_alert,
        headers=auth_headers
    )
    assert response.status_code == 201
    created_alert = response.json()
    assert created_alert['type'] == test_alert['type']
    assert created_alert['message'] == test_alert['message']

def test_get_strategies(auth_headers):
    """Test strategies endpoint."""
    response = client.get("/api/v1/strategies", headers=auth_headers)
    assert response.status_code == 200
    strategies = response.json()
    assert isinstance(strategies, list)
    
    # Test strategy creation
    test_strategy = {
        'name': 'test_strategy',
        'parameters': {
            'timeframe': '1h',
            'indicators': ['RSI', 'MACD'],
            'entry_conditions': [
                {'indicator': 'RSI', 'condition': '<', 'value': 30}
            ],
            'exit_conditions': [
                {'indicator': 'RSI', 'condition': '>', 'value': 70}
            ]
        },
        'status': 'active'
    }
    response = client.post(
        "/api/v1/strategies",
        json=test_strategy,
        headers=auth_headers
    )
    assert response.status_code == 201
    created_strategy = response.json()
    assert created_strategy['name'] == test_strategy['name']
    assert created_strategy['status'] == test_strategy['status']

def test_websocket_connection():
    """Test WebSocket connection."""
    with client.websocket_connect("/ws") as websocket:
        # Subscribe to trades channel
        websocket.send_json({
            "action": "subscribe",
            "channel": "trades"
        })
        response = websocket.receive_json()
        assert response["status"] == "subscribed"
        
        # Test message reception
        message = websocket.receive_json()
        assert "type" in message
        assert "data" in message

def test_error_handling(auth_headers):
    """Test error handling."""
    # Test invalid endpoint
    response = client.get("/api/v1/invalid", headers=auth_headers)
    assert response.status_code == 404
    
    # Test invalid parameters
    response = client.get(
        "/api/v1/market-data",
        params={'invalid': 'parameter'},
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Test invalid JSON
    response = client.post(
        "/api/v1/strategies",
        data="invalid json",
        headers=auth_headers
    )
    assert response.status_code == 422

def test_rate_limiting(auth_headers):
    """Test rate limiting."""
    # Make multiple requests quickly
    for _ in range(10):
        response = client.get("/api/v1/trades", headers=auth_headers)
    
    # Next request should be rate limited
    response = client.get("/api/v1/trades", headers=auth_headers)
    assert response.status_code == 429
    assert "Retry-After" in response.headers

def test_metrics_aggregation(auth_headers):
    """Test metrics aggregation endpoint."""
    params = {
        'start_date': (datetime.now() - timedelta(days=30)).isoformat(),
        'end_date': datetime.now().isoformat(),
        'timeframe': '1d'
    }
    response = client.get(
        "/api/v1/metrics/aggregate",
        params=params,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Verify aggregated data structure
    for entry in data:
        assert all(k in entry for k in ['timestamp', 'metrics'])
        assert all(k in entry['metrics'] for k in [
            'sharpe_ratio',
            'max_drawdown',
            'win_rate',
            'profit_factor'
        ])

def test_config_endpoints(auth_headers):
    """Test configuration endpoints."""
    # Get configuration
    response = client.get("/api/v1/config", headers=auth_headers)
    assert response.status_code == 200
    config = response.json()
    assert isinstance(config, dict)
    
    # Update configuration
    test_config = {
        'risk_limit': 0.03,
        'max_position_size': 0.15
    }
    response = client.put(
        "/api/v1/config",
        json=test_config,
        headers=auth_headers
    )
    assert response.status_code == 200
    updated_config = response.json()
    assert updated_config['risk_limit'] == test_config['risk_limit']
    assert updated_config['max_position_size'] == test_config['max_position_size']

def test_backtest_endpoint(auth_headers):
    """Test backtest endpoint."""
    backtest_params = {
        'strategy': 'test_strategy',
        'symbol': 'BTC/USDT',
        'start_date': (datetime.now() - timedelta(days=30)).isoformat(),
        'end_date': datetime.now().isoformat(),
        'initial_capital': 100000
    }
    response = client.post(
        "/api/v1/backtest",
        json=backtest_params,
        headers=auth_headers
    )
    assert response.status_code == 200
    results = response.json()
    
    # Verify backtest results structure
    assert all(k in results for k in [
        'summary',
        'trades',
        'equity_curve',
        'metrics'
    ])
    assert all(k in results['summary'] for k in [
        'total_return',
        'sharpe_ratio',
        'max_drawdown',
        'win_rate'
    ]) 