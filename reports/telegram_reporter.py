import yaml
import logging
from telegram import Bot
from telegram.error import TelegramError
import asyncio
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
from typing import Optional, List, Dict
import sys
sys.path.append('..')

class TelegramReporter:
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the TelegramReporter with configuration."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        telegram_config = self.config['telegram']
        self.bot = Bot(token=telegram_config['bot_token'])
        self.chat_id = telegram_config['chat_id']
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TelegramReporter')
    
    async def send_message(self, message: str):
        """Send a text message via Telegram."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            self.logger.info("Message sent successfully")
        
        except TelegramError as e:
            self.logger.error(f"Error sending message: {str(e)}")
            raise
    
    async def send_trade_signal(self, symbol: str, signal_type: str, 
                              predicted_price: float, confidence: float):
        """Send a trade signal alert."""
        message = (
            f"🚨 <b>Trade Signal Alert</b> 🚨\n\n"
            f"Symbol: {symbol}\n"
            f"Signal: {'🟢 LONG' if signal_type.lower() == 'long' else '🔴 SHORT'}\n"
            f"Predicted Price: {predicted_price:.2f}\n"
            f"Confidence: {confidence:.2%}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await self.send_message(message)
    
    async def send_trade_execution(self, symbol: str, order_type: str, 
                                 price: float, amount: float, side: str):
        """Send a trade execution notification."""
        message = (
            f"✅ <b>Trade Executed</b> ✅\n\n"
            f"Symbol: {symbol}\n"
            f"Type: {order_type.upper()}\n"
            f"Side: {'🟢 BUY' if side.lower() == 'buy' else '🔴 SELL'}\n"
            f"Price: {price:.2f}\n"
            f"Amount: {amount:.8f}\n"
            f"Total: {(price * amount):.2f} USDT\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await self.send_message(message)
    
    async def send_position_update(self, symbol: str, position_type: str, 
                                 entry_price: float, current_price: float, 
                                 pnl: float, pnl_percentage: float):
        """Send a position update notification."""
        message = (
            f"📊 <b>Position Update</b> 📊\n\n"
            f"Symbol: {symbol}\n"
            f"Type: {'🟢 LONG' if position_type.lower() == 'long' else '🔴 SHORT'}\n"
            f"Entry Price: {entry_price:.2f}\n"
            f"Current Price: {current_price:.2f}\n"
            f"P&L: {pnl:.2f} USDT ({pnl_percentage:+.2%})\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await self.send_message(message)
    
    async def send_position_closed(self, symbol: str, position_type: str, 
                                 entry_price: float, exit_price: float, 
                                 pnl: float, pnl_percentage: float, 
                                 reason: str):
        """Send a position closed notification."""
        message = (
            f"🎯 <b>Position Closed</b> 🎯\n\n"
            f"Symbol: {symbol}\n"
            f"Type: {'🟢 LONG' if position_type.lower() == 'long' else '🔴 SHORT'}\n"
            f"Entry Price: {entry_price:.2f}\n"
            f"Exit Price: {exit_price:.2f}\n"
            f"P&L: {pnl:.2f} USDT ({pnl_percentage:+.2%})\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await self.send_message(message)
    
    def _create_performance_chart(self, performance_data: pd.DataFrame) -> io.BytesIO:
        """Create a performance chart."""
        plt.figure(figsize=(10, 6))
        plt.plot(performance_data.index, performance_data['balance'], 'b-')
        plt.title('Account Balance Over Time')
        plt.xlabel('Date')
        plt.ylabel('Balance (USDT)')
        plt.grid(True)
        
        # Save plot to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
    
    async def send_performance_report(self, performance_data: pd.DataFrame, 
                                    trades_summary: Dict[str, float]):
        """Send a performance report with chart."""
        try:
            # Create and send chart
            chart_buf = self._create_performance_chart(performance_data)
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=chart_buf
            )
            
            # Send performance metrics
            message = (
                f"📈 <b>Performance Report</b> 📈\n\n"
                f"Period: {performance_data.index[0].strftime('%Y-%m-%d')} to "
                f"{performance_data.index[-1].strftime('%Y-%m-%d')}\n\n"
                f"Total Trades: {trades_summary['total_trades']}\n"
                f"Winning Trades: {trades_summary['winning_trades']}\n"
                f"Win Rate: {trades_summary['win_rate']:.2%}\n"
                f"Total Profit: {trades_summary['total_profit']:.2f} USDT\n"
                f"Average Profit per Trade: {trades_summary['avg_profit_per_trade']:.2f} USDT\n"
                f"Largest Win: {trades_summary['largest_win']:.2f} USDT\n"
                f"Largest Loss: {trades_summary['largest_loss']:.2f} USDT\n"
                f"Sharpe Ratio: {trades_summary['sharpe_ratio']:.2f}\n"
                f"Max Drawdown: {trades_summary['max_drawdown']:.2%}"
            )
            await self.send_message(message)
        
        except Exception as e:
            self.logger.error(f"Error sending performance report: {str(e)}")
            raise
    
    async def send_error_alert(self, error_message: str, error_type: str, 
                             stack_trace: Optional[str] = None):
        """Send an error alert."""
        message = (
            f"⚠️ <b>Error Alert</b> ⚠️\n\n"
            f"Type: {error_type}\n"
            f"Message: {error_message}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if stack_trace:
            message += f"\n\nStack Trace:\n<pre>{stack_trace}</pre>"
        
        await self.send_message(message)

def send_telegram_message(reporter: TelegramReporter, message_type: str, **kwargs):
    """Helper function to send messages asynchronously."""
    async def _send():
        if message_type == 'trade_signal':
            await reporter.send_trade_signal(**kwargs)
        elif message_type == 'trade_execution':
            await reporter.send_trade_execution(**kwargs)
        elif message_type == 'position_update':
            await reporter.send_position_update(**kwargs)
        elif message_type == 'position_closed':
            await reporter.send_position_closed(**kwargs)
        elif message_type == 'performance_report':
            await reporter.send_performance_report(**kwargs)
        elif message_type == 'error_alert':
            await reporter.send_error_alert(**kwargs)
        else:
            await reporter.send_message(kwargs.get('message', ''))
    
    asyncio.run(_send())

if __name__ == "__main__":
    # Example usage
    reporter = TelegramReporter()
    send_telegram_message(
        reporter,
        'trade_signal',
        symbol='BTC/USDT',
        signal_type='LONG',
        predicted_price=50000.0,
        confidence=0.85
    ) 