import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
import json
import yaml
from pathlib import Path

class TradingLogger:
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the trading logger."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Create logs directory
        self.logs_dir = Path('../logs')
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize loggers
        self.setup_trading_logger()
        self.setup_performance_logger()
        self.setup_error_logger()
        
        self.trading_logger = logging.getLogger('trading')
        self.performance_logger = logging.getLogger('performance')
        self.error_logger = logging.getLogger('error')
    
    def setup_trading_logger(self):
        """Setup the main trading logger."""
        logger = logging.getLogger('trading')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.logs_dir / 'trading.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    def setup_performance_logger(self):
        """Setup the performance logger."""
        logger = logging.getLogger('performance')
        logger.setLevel(logging.INFO)
        
        # JSON handler for performance metrics
        file_handler = logging.handlers.RotatingFileHandler(
            self.logs_dir / 'performance.json',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                if isinstance(record.msg, (dict, list)):
                    return json.dumps(record.msg)
                return record.msg
        
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)
    
    def setup_error_logger(self):
        """Setup the error logger."""
        logger = logging.getLogger('error')
        logger.setLevel(logging.ERROR)
        
        # File handler for errors
        file_handler = logging.handlers.TimedRotatingFileHandler(
            self.logs_dir / 'errors.log',
            when='midnight',
            interval=1,
            backupCount=30
        )
        file_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s\n'
            'Exception: %(exc_info)s\n'
        )
        file_handler.setFormatter(formatter)
        
        # Email handler for critical errors
        if self.config.get('email'):
            email_handler = logging.handlers.SMTPHandler(
                mailhost=self.config['email']['smtp_server'],
                fromaddr=self.config['email']['from_address'],
                toaddrs=self.config['email']['to_addresses'],
                subject='Trading Bot Error Alert'
            )
            email_handler.setLevel(logging.CRITICAL)
            email_handler.setFormatter(formatter)
            logger.addHandler(email_handler)
        
        logger.addHandler(file_handler)
    
    def log_trade(self, trade_data: dict):
        """Log trade information."""
        self.trading_logger.info(f"Trade executed: {json.dumps(trade_data, indent=2)}")
    
    def log_performance(self, metrics: dict):
        """Log performance metrics."""
        self.performance_logger.info(metrics)
    
    def log_error(self, error_msg: str, exc_info: Optional[Exception] = None):
        """Log error information."""
        self.error_logger.error(error_msg, exc_info=exc_info)
    
    def log_strategy(self, strategy_data: dict):
        """Log strategy information."""
        self.trading_logger.info(f"Strategy signal: {json.dumps(strategy_data, indent=2)}")
    
    def log_system(self, msg: str, level: str = 'info'):
        """Log system information."""
        logger = self.trading_logger
        level_map = {
            'debug': logger.debug,
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }
        level_map.get(level.lower(), logger.info)(msg)
    
    def get_recent_logs(self, log_type: str = 'trading', n_lines: int = 100) -> list:
        """Get recent log entries."""
        log_file = self.logs_dir / f'{log_type}.log'
        if not log_file.exists():
            return []
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return lines[-n_lines:]
    
    def clear_logs(self, log_type: str = None):
        """Clear log files."""
        if log_type:
            log_file = self.logs_dir / f'{log_type}.log'
            if log_file.exists():
                log_file.unlink()
        else:
            for log_file in self.logs_dir.glob('*.log'):
                log_file.unlink()

if __name__ == "__main__":
    # Example usage
    logger = TradingLogger()
    
    # Log different types of information
    logger.log_trade({
        'symbol': 'BTC/USDT',
        'type': 'long',
        'entry_price': 50000,
        'amount': 0.1
    })
    
    logger.log_performance({
        'total_pnl': 1000,
        'win_rate': 0.65,
        'sharpe_ratio': 1.8
    })
    
    try:
        raise ValueError("Example error")
    except Exception as e:
        logger.log_error("An error occurred", exc_info=e)
    
    logger.log_system("Trading bot started", "info") 