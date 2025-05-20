# Project Architecture

This document provides a detailed breakdown of the RetroTrade project structure, core modules, and their interactions.

## Folder Structure

```
retrotrade/         # Core trading system modules
Agents/             # RL and ML agent implementations
Models/             # Model definitions and utilities
risk_management/    # Risk management models and scripts
sentiment_analysis/ # Sentiment analysis models and scripts
data/               # Raw and processed market data
PPO_Trader/         # PPO agent implementation and configs
GRU/                # GRU agent implementation
```

## Core Modules

### retrotrade/
- **core/**: Trading engine, order management, signal processing
- **data/**: Market data processing and symbol discovery
- **exchange/**: Exchange API integration and management
- **models/**: Model orchestration, loading, prediction, and RL agent handling
- **monitoring/**: Telegram notifications, system health, and lifecycle management
- **risk/**: Risk management logic
- **strategy/**: AI and rule-based trading strategies
- **system/**: System info, resource monitoring, and usage tracking
- **trade/**: Order execution, position management, and dry-run helpers
- **trading/**: Main trading loop and orchestration
- **utils/**: Logging, settings, and UI utilities

### Agents/
- RL and ML agent implementations (PPO, GRU, GARCH, sentiment)

### Models/
- Model definitions, wrappers, and utilities

### risk_management/
- Risk models, training scripts, and saved models

### sentiment_analysis/
- Sentiment models, training scripts, and trained models

## Component Interaction Diagram

```
+-------------------+
|   Data Layer      |
+--------+----------+
         |
         v
+-------------------+
| Model Layer       |
+--------+----------+
         |
         v
+-------------------+
| Trading Engine    |
+--------+----------+
         |
         v
+-------------------+
| Risk & Monitoring |
+-------------------+
```

## Data Flow
1. Data is ingested and preprocessed
2. Models are trained or loaded (RL, sentiment, risk)
3. Trading engine receives signals and executes trades
4. Risk management and monitoring modules oversee operations

## Extending the System
- Add new agents in `Agents/`
- Implement new strategies in `retrotrade/strategy/`
- Integrate new exchanges in `retrotrade/exchange/`

For more, see module-level docstrings and comments in the codebase.
