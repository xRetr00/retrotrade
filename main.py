import yaml
import logging
import schedule
import time
from datetime import datetime
import pandas as pd
from typing import Dict, List
import traceback
import os

from data_collection.data_collector import DataCollector
from ml_models.lstm_model import LSTMModel
from execution.trade_executor import TradeExecutor
from reports.telegram_reporter import TelegramReporter, send_telegram_message

class TradingBot:
    def __init__(self, config_path: str = 'config/config.yaml'):
        """Initialize the trading bot."""
        self.config_path = os.path.abspath(config_path)
        with open(self.config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TradingBot')
        
        # Initialize components
        self.data_collector = DataCollector(self.config_path)
        self.model = LSTMModel(self.config_path)
        self.executor = TradeExecutor(self.config_path)
        self.reporter = TelegramReporter(self.config_path)
        
        # Trading state
        self.is_trading = False
        self.performance_data = []

    def start(self):
        """Start the trading bot."""
        try:
            self.is_trading = True
            self.logger.info('Trading bot started')
            send_telegram_message(self.reporter, 'message', message='🤖 Trading Bot Started 🤖')
            
            # Schedule tasks
            schedule.every(1).hours.do(self.update_data)
            schedule.every(5).minutes.do(self.check_signals)
            schedule.every(1).minutes.do(self.monitor_positions)
            schedule.every().day.at('00:00').do(self.generate_daily_report)
            
            # Main loop
            while self.is_trading:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            self.handle_error('Bot startup error', e)

    def stop(self):
        """Stop the trading bot."""
        try:
            self.is_trading = False
            self.logger.info('Trading bot stopped')
            
            # Close all open positions
            open_positions = self.executor.get_open_positions()
            for symbol in open_positions:
                self.executor.close_position(symbol)
            
            send_telegram_message(self.reporter, 'message', message='🔴 Trading Bot Stopped 🔴')
        except Exception as e:
            self.handle_error('Bot shutdown error', e)

    def update_data(self):
        """Update market data."""
        try:
            self.logger.info('Updating market data')
            self.data_collector.update_all_pairs()
        except Exception as e:
            self.handle_error('Data update error', e)

    def check_signals(self):
        """Check for trading signals."""
        try:
            trading_pairs = self.config['trading']['trading_pairs']
            
            for symbol in trading_pairs:
                # Get latest data
                df = self.data_collector.fetch_ohlcv(symbol, '1h')
                X, _ = self.model.prepare_data(df)
                
                if len(X) > 0:
                    # Get prediction
                    predicted_price = self.model.predict_next_price(X[-1:])
                    current_price = df['close'].iloc[-1]
                    
                    # Calculate signal
                    price_change = (predicted_price - current_price) / current_price
                    confidence = abs(price_change)
                    
                    if confidence >= 0.01:  # 1% minimum confidence threshold
                        signal_type = 'LONG' if price_change > 0 else 'SHORT'
                        
                        # Send signal alert
                        send_telegram_message(
                            self.reporter,
                            'trade_signal',
                            symbol=symbol,
                            signal_type=signal_type,
                            predicted_price=predicted_price,
                            confidence=confidence
                        )
                        
                        # Execute trade
                        if self.executor.can_open_position(symbol):
                            order = self.executor.execute_trade_signal(symbol, signal_type, predicted_price)
                            
                            if order:
                                send_telegram_message(
                                    self.reporter,
                                    'trade_execution',
                                    symbol=symbol,
                                    order_type=order['type'],
                                    price=order['price'],
                                    amount=order['amount'],
                                    side=order['side']
                                )
        except Exception as e:
            self.handle_error('Signal check error', e)

    def monitor_positions(self):
        """Monitor open positions."""
        try:
            open_positions = self.executor.get_open_positions()
            
            for symbol, position in open_positions.items():
                # Get current price
                current_price = self.executor.exchange.fetch_ticker(symbol)['last']
                
                # Calculate P&L
                if position['type'].lower() == 'long':
                    pnl = (current_price - position['entry_price']) * position['position_size']
                else:
                    pnl = (position['entry_price'] - current_price) * position['position_size']
                
                pnl_percentage = pnl / (position['entry_price'] * position['position_size'])
                
                # Send position update
                send_telegram_message(
                    self.reporter,
                    'position_update',
                    symbol=symbol,
                    position_type=position['type'],
                    entry_price=position['entry_price'],
                    current_price=current_price,
                    pnl=pnl,
                    pnl_percentage=pnl_percentage
                )
                
                # Check for exit signals
                exit_signal = self.executor.risk_manager.check_position_exits(symbol, current_price)
                
                if exit_signal:
                    order = self.executor.close_position(symbol)
                    if order:
                        send_telegram_message(
                            self.reporter,
                            'position_closed',
                            symbol=symbol,
                            position_type=position['type'],
                            entry_price=position['entry_price'],
                            exit_price=current_price,
                            pnl=pnl,
                            pnl_percentage=pnl_percentage,
                            reason=exit_signal
                        )
                
                # Store performance data
                self.performance_data.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'position_type': position['type'],
                    'entry_price': position['entry_price'],
                    'current_price': current_price,
                    'pnl': pnl,
                    'pnl_percentage': pnl_percentage
                })
        except Exception as e:
            self.handle_error('Position monitoring error', e)

    def generate_daily_report(self):
        """Generate daily performance report."""
        try:
            if not self.performance_data:
                return
            
            # Convert performance data to DataFrame
            df = pd.DataFrame(self.performance_data)
            df.set_index('timestamp', inplace=True)
            
            # Calculate metrics
            daily_pnl = df.groupby(df.index.date)['pnl'].sum()
            total_trades = len(df)
            winning_trades = len(df[df['pnl'] > 0])
            
            trades_summary = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_profit': df['pnl'].sum(),
                'avg_profit_per_trade': df['pnl'].mean(),
                'largest_win': df['pnl'].max(),
                'largest_loss': df['pnl'].min(),
                'sharpe_ratio': daily_pnl.mean() / daily_pnl.std() if len(daily_pnl) > 1 else 0,
                'max_drawdown': (df['pnl'].min() / df['pnl'].max()) if df['pnl'].max() != 0 else 0
            }
            
            # Send report
            send_telegram_message(
                self.reporter,
                'performance_report',
                performance_data=df,
                trades_summary=trades_summary
            )
            
            # Clear performance data
            self.performance_data = []
        except Exception as e:
            self.handle_error('Report generation error', e)

    def handle_error(self, error_type: str, error: Exception):
        """Handle and report errors."""
        self.logger.error(f'{error_type}: {str(error)}')
        stack_trace = traceback.format_exc()
        
        send_telegram_message(
            self.reporter,
            'error_alert',
            error_message=str(error),
            error_type=error_type,
            stack_trace=stack_trace
        )

if __name__ == '__main__':
    bot = TradingBot()
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.stop() 