# RetroTrade - Advanced Cryptocurrency Trading Bot

RetroTrade is an advanced cryptocurrency trading bot that uses ensemble machine learning models, adaptive strategies, and sophisticated risk management to automate trading decisions.

## Features

- 🤖 Ensemble ML models (LSTM, Transformer, Sentiment Analysis)
- 📈 Adaptive trading strategies with market regime detection
- 🛡️ Dynamic position sizing and risk management
- 📊 Real-time performance monitoring
- 🔒 Enterprise-grade security
- 🌐 Modern web interface with TypeScript
- 📱 Real-time notifications
- 🔄 Automated model retraining

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (recommended)

### Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/xRetr00/retrotrade.git
   cd retrotrade
   ```

2. **Make scripts executable**
   ```bash
   chmod +x deploy.sh backup.sh restore.sh
   ```

3. **Run deployment**
   ```bash
   ./deploy.sh
   ```

4. **Access the application**
   - Frontend: http://localhost
   - Grafana: http://localhost:3000

### Manual Installation

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   cd web_interface/frontend
   npm install
   cd ../..
   ```

3. **Configure the application**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config.yaml with your settings
   ```

4. **Initialize database**
   ```bash
   python setup_database.py
   ```

5. **Start services**
   ```bash
   # Start Redis
   redis-server &
   
   # Start API server
   cd web_interface
   uvicorn api:app --host 0.0.0.0 --port 8000 &
   
   # Start frontend
   cd frontend
   npm start
   ```

## Configuration

### Essential Settings

```yaml
# config.yaml
exchange:
  name: "binance"
  testnet: true  # Set to false for real trading
  api_key: ""    # Your API key
  api_secret: "" # Your API secret

trading:
  base_currencies:
    - "USDT"
  trading_pairs:
    - "BTC/USDT"
    - "ETH/USDT"

risk_management:
  max_position_size: 0.1
  stop_loss_percentage: 0.02
  take_profit_percentage: 0.04
```

## Security

1. **API Security**
   - Use read-only API keys when possible
   - Enable IP whitelisting
   - Implement 2FA
   - Regular key rotation

2. **Data Protection**
   - Database encryption
   - Automated backups
   - Secure configuration storage

## Backup & Recovery

### Create Backup
```bash
./backup.sh
```

### Restore from Backup
```bash
./restore.sh backups/20230815_120000.tar.gz
```

## Monitoring

### Metrics Available
- Performance metrics (Sharpe ratio, win rate, etc.)
- System health metrics
- Trading metrics
- Risk metrics

### Monitoring Tools
- Grafana dashboards
- Prometheus metrics
- Real-time alerts
- Performance reports

## Architecture

### Components
1. **Trading Engine**
   - Order execution
   - Position management
   - Risk control

2. **ML Models**
   - LSTM price prediction
   - Sentiment analysis
   - Market regime detection
   - Ensemble predictions

3. **Risk Manager**
   - Position sizing
   - Stop-loss management
   - Exposure control
   - Correlation analysis

4. **Data Pipeline**
   - Market data collection
   - Feature engineering
   - Real-time processing

## Production Deployment

### System Requirements
- CPU: 4+ cores recommended
- RAM: 8GB minimum, 16GB recommended
- Storage: 50GB+ SSD recommended
- OS: Ubuntu 20.04+ or similar Linux distribution

### Scaling Options
1. **Horizontal Scaling**
   - Load balancer configuration
   - Database replication
   - Session management

2. **Vertical Scaling**
   - Resource optimization
   - Database tuning
   - Caching implementation

## Troubleshooting

### Common Issues

1. **Database Connection**
   ```bash
   # Check database status
   sudo systemctl status postgresql
   
   # Check logs
   sudo tail -f /var/log/postgresql/postgresql-13-main.log
   ```

2. **API Server**
   ```bash
   # Check API logs
   docker-compose logs backend
   
   # Restart service
   docker-compose restart backend
   ```

3. **Frontend Issues**
   ```bash
   # Check logs
   docker-compose logs frontend
   
   # Rebuild
   docker-compose up -d --build frontend
   ```

## Support

- Documentation: Check the `docs` directory
- Issues: Submit on GitHub

## License

This project is licensed under the MIT License - see the LICENSE file for details. 