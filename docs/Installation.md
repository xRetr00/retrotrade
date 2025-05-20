# Installation Guide

## Prerequisites
- Python 3.8 or higher
- Git

## Steps
1. Clone the repository:
   ```pwsh
   git clone https://github.com/xRetr00/xRetroTrade
   cd xRetroTrade
   ```
2. Install main dependencies:
   ```pwsh
   pip install -r requirements.txt
   ```
3. (Optional) Install module-specific requirements:
   ```pwsh
   pip install -r Agents/PPO_Trader/requirements.txt
   pip install -r risk_management/requirements.txt
   pip install -r sentiment_analysis/requirements.txt
   ```
4. (Optional) Install TA-Lib for technical analysis:
   ```pwsh
   ./setup_talib.sh
   ```
