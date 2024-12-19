from fastapi import FastAPI, HTTPException, WebSocket, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import yaml
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import asyncio
from pathlib import Path
import jwt
from passlib.context import CryptContext
import time
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import ipaddress

sys.path.append('..')
from utils.logger import TradingLogger
from utils.performance_monitor import PerformanceMonitor
from utils.security import SecurityManager

# Initialize components
app = FastAPI(title="Trading Bot API", version="1.0.0")
logger = TradingLogger()
monitor = PerformanceMonitor()
security_manager = SecurityManager()

# Security settings
SECRET_KEY = "your-secret-key"  # Should be loaded from environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Rate limiting
class RateLimiter:
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.tokens = {}
    
    async def is_allowed(self, token: str) -> bool:
        now = time.time()
        if token not in self.tokens:
            self.tokens[token] = {"calls": 1, "reset": now + self.period}
            return True
        
        token_info = self.tokens[token]
        if now > token_info["reset"]:
            token_info["calls"] = 1
            token_info["reset"] = now + self.period
            return True
        
        if token_info["calls"] >= self.calls:
            return False
        
        token_info["calls"] += 1
        return True

rate_limiter = RateLimiter(calls=100, period=60)  # 100 calls per minute

# Load whitelist
def load_whitelist():
    try:
        with open('../config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            return config.get('security', {}).get('ip_whitelist', {}).get('allowed_ips', [])
    except Exception:
        return []

WHITELIST = load_whitelist()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure based on your needs
)

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class ConfigUpdate(BaseModel):
    section: str
    data: dict

class TradeSignal(BaseModel):
    symbol: str
    action: str  # buy, sell
    amount: float
    price: Optional[float] = None

# WebSocket connections
active_connections: List[WebSocket] = []

# Security functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_user(username: str) -> Optional[UserInDB]:
    # Implement user lookup from database
    # This is a dummy implementation
    if username == "admin":
        return UserInDB(
            username=username,
            hashed_password=get_password_hash("admin"),
            disabled=False
        )
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user

# IP Whitelist middleware
@app.middleware("http")
async def validate_ip(request: Request, call_next):
    if WHITELIST:
        client_ip = request.client.host
        if not any(ipaddress.ip_address(client_ip) in ipaddress.ip_network(wl)
                  for wl in WHITELIST):
            return JSONResponse(
                status_code=403,
                content={"detail": "IP address not allowed"}
            )
    return await call_next(request)

# Rate limiting middleware
@app.middleware("http")
async def rate_limiting(request: Request, call_next):
    token = request.headers.get("Authorization")
    if token and not await rate_limiter.is_allowed(token):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )
    return await call_next(request)

# Authentication endpoint
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# WebSocket connection manager
async def broadcast_message(message: dict):
    """Broadcast message to all connected clients."""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
    except:
        active_connections.remove(websocket)

# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "online", "timestamp": datetime.now().isoformat()}

@app.get("/config")
async def get_config(current_user: User = Depends(get_current_user)):
    """Get current configuration."""
    try:
        with open('../config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            # Decrypt sensitive information
            config = security_manager.decrypt_config(config)
        return config
    except Exception as e:
        logger.log_error("Error reading configuration", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
async def update_config(update: ConfigUpdate, current_user: User = Depends(get_current_user)):
    """Update configuration."""
    try:
        with open('../config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        
        # Update configuration
        section_parts = update.section.split('.')
        current = config
        for part in section_parts[:-1]:
            current = current[part]
        current[section_parts[-1]] = update.data
        
        # Encrypt sensitive information
        secure_config = security_manager.secure_config(config)
        
        # Save updated configuration
        with open('../config/config.yaml', 'w') as file:
            yaml.dump(secure_config, file)
        
        logger.log_system(f"Configuration updated: {update.section}")
        return {"status": "success"}
    except Exception as e:
        logger.log_error("Error updating configuration", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance")
async def get_performance():
    """Get performance metrics."""
    try:
        metrics = monitor.get_metrics()
        return metrics
    except Exception as e:
        logger.log_error("Error getting performance metrics", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades")
async def get_trades(limit: int = 100):
    """Get recent trades."""
    try:
        trades = monitor.trades_history[-limit:]
        return trades
    except Exception as e:
        logger.log_error("Error getting trades", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trades")
async def execute_trade(trade: TradeSignal, background_tasks: BackgroundTasks):
    """Execute manual trade."""
    try:
        # Here you would integrate with your trading execution module
        trade_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": trade.symbol,
            "action": trade.action,
            "amount": trade.amount,
            "price": trade.price
        }
        
        logger.log_trade(trade_data)
        background_tasks.add_task(broadcast_message, {
            "type": "trade",
            "data": trade_data
        })
        
        return {"status": "success", "trade": trade_data}
    except Exception as e:
        logger.log_error("Error executing trade", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{log_type}")
async def get_logs(log_type: str, lines: int = 100):
    """Get recent log entries."""
    try:
        logs = logger.get_recent_logs(log_type, lines)
        return {"logs": logs}
    except Exception as e:
        logger.log_error("Error getting logs", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/start")
async def start_bot():
    """Start the trading bot."""
    try:
        # Here you would integrate with your main bot control
        logger.log_system("Trading bot started")
        await broadcast_message({"type": "status", "data": "started"})
        return {"status": "success"}
    except Exception as e:
        logger.log_error("Error starting bot", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot."""
    try:
        # Here you would integrate with your main bot control
        logger.log_system("Trading bot stopped")
        await broadcast_message({"type": "status", "data": "stopped"})
        return {"status": "success"}
    except Exception as e:
        logger.log_error("Error stopping bot", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """Get bot status and system information."""
    try:
        # Get various status information
        status = {
            "bot_status": "running",  # You would get this from your bot
            "uptime": "12:34:56",  # Calculate actual uptime
            "active_trades": len(monitor.trades_history),
            "system_time": datetime.now().isoformat(),
            "performance_summary": monitor.get_metrics()
        }
        return status
    except Exception as e:
        logger.log_error("Error getting status", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 