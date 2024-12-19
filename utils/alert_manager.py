import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import telegram
from .logger import OperationalLogger

class AlertManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = OperationalLogger(config)
        
        # Initialize Telegram bot if enabled
        self.telegram_bot = None
        if self.config['notifications']['telegram']['enabled']:
            self.telegram_bot = telegram.Bot(
                token=self.config['notifications']['telegram']['bot_token']
            )
            self.telegram_chat_id = self.config['notifications']['telegram']['chat_id']
        
        # Alert cooldown settings
        self.cooldown_periods = {
            'WARNING': timedelta(minutes=30),
            'CRITICAL': timedelta(minutes=5),
            'INFO': timedelta(hours=1)
        }
        
        # Track last alert times
        self.last_alerts = {}
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.alert_logger = logging.getLogger('AlertManager')
    
    async def send_alert(self, title: str, message: str, 
                        level: str = "INFO", 
                        metadata: Optional[Dict] = None) -> None:
        """Send alert through configured channels."""
        try:
            # Check cooldown
            if not self._check_cooldown(title, level):
                return
            
            # Format alert message
            formatted_message = self._format_alert_message(title, message, level, metadata)
            
            # Log alert
            self._log_alert(formatted_message, level)
            
            # Send through configured channels
            await self._send_through_channels(formatted_message, level)
            
            # Update last alert time
            self.last_alerts[title] = datetime.now()
            
        except Exception as e:
            self.logger.log_error(
                'alert_send_error',
                error=str(e),
                context={'title': title, 'message': message, 'level': level}
            )
    
    def _check_cooldown(self, alert_key: str, level: str) -> bool:
        """Check if enough time has passed since the last alert."""
        if alert_key in self.last_alerts:
            time_since_last = datetime.now() - self.last_alerts[alert_key]
            return time_since_last > self.cooldown_periods[level]
        return True
    
    def _format_alert_message(self, title: str, message: str, 
                            level: str, metadata: Optional[Dict] = None) -> str:
        """Format alert message with consistent structure."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"""
🚨 {level} ALERT
📌 {title}
⏰ {timestamp}

{message}
"""
        
        if metadata:
            formatted_message += "\nAdditional Information:"
            for key, value in metadata.items():
                formatted_message += f"\n• {key}: {value}"
        
        return formatted_message
    
    def _log_alert(self, message: str, level: str) -> None:
        """Log alert to file system."""
        if level == "CRITICAL":
            self.alert_logger.critical(message)
        elif level == "WARNING":
            self.alert_logger.warning(message)
        else:
            self.alert_logger.info(message)
    
    async def _send_through_channels(self, message: str, level: str) -> None:
        """Send alert through all configured channels."""
        # Send through Telegram if enabled
        if self.telegram_bot and self._should_send_telegram(level):
            await self._send_telegram(message)
        
        # Add more channels here (e.g., email, Slack, Discord)
    
    async def _send_telegram(self, message: str) -> None:
        """Send alert through Telegram."""
        try:
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.log_error(
                'telegram_send_error',
                error=str(e),
                context={'message': message}
            )
    
    def _should_send_telegram(self, level: str) -> bool:
        """Check if alert should be sent to Telegram based on level."""
        telegram_levels = self.config['notifications']['telegram']['alert_levels']
        return level in telegram_levels
    
    def send_volatility_alert(self, symbol: str, 
                            current_volatility: float, 
                            threshold: float) -> None:
        """Send volatility-specific alert."""
        title = f"High Volatility Alert - {symbol}"
        message = f"""
High volatility detected for {symbol}
Current Volatility: {current_volatility:.2%}
Threshold: {threshold:.2%}
"""
        metadata = {
            'symbol': symbol,
            'volatility': f"{current_volatility:.2%}",
            'threshold': f"{threshold:.2%}",
            'timestamp': datetime.now().isoformat()
        }
        
        asyncio.create_task(
            self.send_alert(
                title=title,
                message=message,
                level="WARNING",
                metadata=metadata
            )
        )
    
    def send_performance_alert(self, metric: str, 
                             current_value: float, 
                             threshold: float) -> None:
        """Send performance-specific alert."""
        title = f"Performance Alert - {metric}"
        message = f"""
Performance metric below threshold:
Metric: {metric}
Current Value: {current_value:.2f}
Threshold: {threshold:.2f}
"""
        metadata = {
            'metric': metric,
            'current_value': f"{current_value:.2f}",
            'threshold': f"{threshold:.2f}",
            'timestamp': datetime.now().isoformat()
        }
        
        asyncio.create_task(
            self.send_alert(
                title=title,
                message=message,
                level="WARNING",
                metadata=metadata
            )
        )
    
    def send_system_alert(self, component: str, 
                         status: str, 
                         details: Optional[str] = None) -> None:
        """Send system-related alert."""
        title = f"System Alert - {component}"
        message = f"""
System component status change:
Component: {component}
Status: {status}
"""
        if details:
            message += f"Details: {details}"
        
        metadata = {
            'component': component,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        asyncio.create_task(
            self.send_alert(
                title=title,
                message=message,
                level="CRITICAL" if status == "ERROR" else "WARNING",
                metadata=metadata
            )
        )
    
    def send_trade_alert(self, trade_type: str, 
                        symbol: str, 
                        details: Dict) -> None:
        """Send trade-related alert."""
        title = f"Trade Alert - {trade_type}"
        message = f"""
New trade executed:
Type: {trade_type}
Symbol: {symbol}
Entry Price: {details.get('entry_price')}
Position Size: {details.get('position_size')}
"""
        
        asyncio.create_task(
            self.send_alert(
                title=title,
                message=message,
                level="INFO",
                metadata=details
            )
        ) 