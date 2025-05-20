# RetroTrade Codemap

This codemap provides a comprehensive overview of the RetroTrade project's structure, key modules, and their relationships. It is designed to help new contributors and users quickly understand the codebase and its organization.

---

## High-Level Architecture Diagram

```
+-------------------+        +-------------------+
|   Data Sources    |        |  External Feeds   |
+--------+----------+        +--------+----------+
         |                           |
         +-----------+   +-----------+
                     |   |
                     v   v
              +-------------------+
              | Data Preprocessing|
              +--------+----------+
                       |
                       v
              +-------------------+
              |   Model Layer     |
              | (RL, Sentiment,   |
              |  Risk Models)     |
              +--------+----------+
                       |
                       v
              +-------------------+
              | Trading Engine    |
              +--------+----------+
                       |
                       v
              +-------------------+
              | Risk Management   |
              +--------+----------+
                       |
                       v
              +-------------------+
              | Monitoring/Alerts |
              +-------------------+
```

---

## Data Flow Diagram

```
[Market Data] ---> [Preprocessing] ---> [Model Prediction] ---> [Signal Generation]
                                                        |
                                                        v
                                              [Order Execution]
                                                        |
                                                        v
                                              [Risk Management]
                                                        |
                                                        v
                                              [Monitoring/Alerts]
```

---

## Module Interaction Diagram

```
+-------------------+
| retrotrade/data   |
+--------+----------+
         |
         v
+-------------------+
| retrotrade/models |
+--------+----------+
         |
         v
+-------------------+
| retrotrade/core   |
+--------+----------+
         |
         v
+-------------------+
| retrotrade/trade  |
+--------+----------+
         |
         v
+-------------------+
| retrotrade/risk   |
+--------+----------+
         |
         v
+-------------------+
| retrotrade/monitoring |
+-------------------+
```

---

## High-Level Directory Structure

```
xRetroTrade/
│
├── Agents/                # RL and ML agent implementations (PPO, GRU, GARCH, Sentiment)
├── Models/                # Model definitions, wrappers, and utilities
├── PPO_Trader/            # PPO agent implementation, configs, checkpoints, training
├── GRU/                   # GRU agent implementation
├── risk_management/       # Risk management models, training, and saved models
├── sentiment_analysis/    # Sentiment analysis models, training, and trained models
├── retrotrade/            # Core trading system (engine, data, exchange, monitoring, etc.)
├── data/                  # Raw and processed market data
├── docs/                  # Documentation
├── requirements.txt       # Main dependencies
├── setup_talib.sh         # TA-Lib setup script
└── README.md              # Project overview
```

---

## Core Module Map

```
retrotrade/
│
├── core/           # Trading engine, order management, signal processing
├── data/           # Market data processing, symbol discovery
├── exchange/       # Exchange API integration (e.g., OKX)
├── models/         # Model orchestration, loading, prediction, RL agent handler
├── monitoring/     # Telegram notifications, system health, lifecycle
├── risk/           # Risk management logic
├── strategy/       # AI and rule-based trading strategies
├── system/         # System info, resource monitoring, usage tracking
├── trade/          # Order execution, position management, dry-run helpers
├── trading/        # Main trading loop and orchestration
└── utils/          # Logging, settings, UI utilities
```

---

## Module Relationships Diagram

```
+-------------------+
|   Data Layer      |
| (retrotrade/data) |
+--------+----------+
         |
         v
+-------------------+
| Model Layer       |
| (retrotrade/models,|
|  Agents, Models)  |
+--------+----------+
         |
         v
+-------------------+
| Trading Engine    |
| (retrotrade/core, |
|  trading, trade)  |
+--------+----------+
         |
         v
+-------------------+
| Risk & Monitoring |
| (retrotrade/risk, |
|  monitoring)      |
+-------------------+
```

---

## Key File Roles

- **retrotrade/__main__.py**: Main entry point for running the trading system
- **retrotrade/core/trading_engine.py**: Central trading logic and orchestration
- **retrotrade/exchange/**: Exchange API wrappers and management
- **retrotrade/models/rl_agent_handler.py**: RL agent loading and management
- **retrotrade/monitoring/telegram_notifier.py**: Telegram notifications
- **retrotrade/risk/risk_manager.py**: Risk management logic
- **retrotrade/strategy/ai_strategy.py**: AI-based trading strategies
- **retrotrade/trade/executor.py**: Order execution logic
- **retrotrade/utils/logger.py**: Logging utilities

---

## Data & Model Flow

1. **Data Ingestion**: Market data is loaded and processed (`retrotrade/data/`, `data/`)
2. **Model Prediction**: Models (RL, sentiment, risk) are loaded and used for signal generation (`retrotrade/models/`, `Agents/`, `Models/`)
3. **Trading Execution**: Signals are processed and orders are executed (`retrotrade/core/`, `trade/`)
4. **Risk Management**: Trades are filtered and managed for risk (`retrotrade/risk/`)
5. **Monitoring**: System status and trade alerts are sent (`retrotrade/monitoring/`)

---

## Extending RetroTrade

- Add new agents in `Agents/`
- Implement new strategies in `retrotrade/strategy/`
- Integrate new exchanges in `retrotrade/exchange/`
- Add new data sources in `retrotrade/data/`

---

For more details, see the [Architecture](Architecture.md) and [Overview](Overview.md) docs.
