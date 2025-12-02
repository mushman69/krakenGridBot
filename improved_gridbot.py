"""
 AGGRESSIVE GRIDBOT CONFIGURATION - OPTIMIZED FOR ALTCOIN CYCLE
================================================================

STRATEGY: High-risk, high-reward grid trading during altcoin season
TARGET RETURNS: 37-59% annual (XRP/BTC 45-75%, ETH/USD 25-35%)
MARKET TIMING: Early altcoin season (BTC dominance dropping)

TRADING PAIRS:
- XRP/BTC (60%): Cyclical opportunity, 1.5% grid, 20 orders/side
- ETH/USD (40%): Stable performer, 0.7% grid, 18 orders/side

OPTIMIZED MINIMUM ORDER SIZES:
- ETH/USD: 0.005 ETH minimum (conservative $11+ orders, 6-decimal volume precision)
- XRP/BTC: $10 USD minimum orders (maximizes order count & range coverage)
- Enhanced precision handling: separate volume and price precision for better accuracy

SMART FEATURES:
-  Auto-rebalancing DISABLED (let winners run)
-  Cycle-aware protection for trending assets  
-  Aggressive monitoring (20s intervals)
-  Dense grids for maximum capture
-  Trend protection logic
-  SQLite PnL Tracking & Reporting

CONFIGURATION DATE: June 2025
EXPECTED DEPLOYMENT: ~76 active orders total
"""

import os
import json
import time
import hmac
import base64
import hashlib
import asyncio
import aiohttp
import websockets
import urllib.parse
import random
import socket
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

#  AGGRESSIVE PORTFOLIO CONFIGURATION - OPTIMIZED FOR CURRENT ALTCOIN CYCLE
AUTO_REBALANCE_ENABLED = False           #  DISABLED - Let winners run during cycle
STARTUP_REBALANCE = True                 #  Global startup rebalance (overridden by per-pair settings)
REBALANCE_TOLERANCE = 25.0              #  Wide tolerance - only rebalance if >75/25 split
ORDERS_PER_SIDE = None                  # Will be calculated dynamically based on balance
GRID_SPREAD_MULTIPLIER = 0.9            #  Tighter spreads for aggressive strategy
CANCEL_ALL_ON_STARTUP = True            #  Clean slate for optimal deployment
CONTINUOUS_MONITORING = True            #  Essential for aggressive monitoring

#  CYCLE-AWARE SETTINGS - OPTIMIZED FOR ALTCOIN SEASON
ORDER_CHECK_INTERVAL = 10               # ⏱ Check every 10 seconds (increased frequency for faster replacement)
MAX_WINNER_ALLOCATION = 85.0            #  Don't rebalance until 85% in one asset
TREND_PROTECTION = True                 #  Protect trending assets from rebalancing
CURRENT_CYCLE_STAGE = 'early_altseason' #  Market timing awareness

#  DATABASE CONFIGURATION
DATABASE_FILE = os.getenv('DATABASE_FILE', "gridbot_pnl.db")  # SQLite database file (Docker-compatible)
PNL_REPORT_INTERVAL = int(os.getenv('PNL_REPORT_INTERVAL', '300'))  # Report PnL every 5 minutes (300 seconds)

#  AGGRESSIVE TRADING PAIRS - TARGET 37-59% ANNUAL RETURNS
TRADING_PAIRS = {
    "XRP/BTC": {
        'grid_interval': 2.5,           #  Optimal spacing for current volatility
        'precision': 8,                 # BTC precision (8 decimal places)
        'volume_precision': 2,          # XRP volume precision (2 decimal places)
        'min_order_size': 10.0,         # ~$10 USD minimum (dynamically calculated)
        'target_allocation': 60.0,      #  PRIMARY 60% - Capitalize on altcoin cycle
        'max_allocation': 85.0,         #  Don't rebalance until 85%
        'base_asset': 'XXBT',          # BTC is what we're accumulating
        'quote_asset': 'XXRP',         # XRP is what we're trading
        'kraken_pair': 'XXRPXXBT',     # Exact Kraken pair name
        'enabled': True,
        'max_orders_per_side': 20,     #  Dense grid for aggressive capture
        'min_orders_per_side': 4,      #  Ensure good coverage
        'cycle_pair': True,            #  Cyclical pair - protect from rebalancing
        'trend_sensitive': True,       #  High sensitivity to trends
        'startup_rebalance': False     #  No startup rebalance - let XRP run during cycle
    },
    "ETH/USD": {
        'grid_interval': 1.5,           #  Tight spacing for high-frequency trading
        'precision': 2,                 # USD price precision (2 decimal places)
        'volume_precision': 6,          # ETH volume precision (6 decimal places)
        'min_order_size': 0.005,        # Conservative minimum: 0.005 ETH (~$11+ to ensure success)
        'target_allocation': 40.0,      #  SECONDARY 40% - Stable high performer
        'min_allocation': 15.0,         #  Don't go below 15%
        'base_asset': 'ZUSD',          # USD is base currency
        'quote_asset': 'XETH',         # ETH is quote currency
        'kraken_pair': 'XETHZUSD',     # Exact Kraken pair name
        'enabled': True,
        'max_orders_per_side': 18,     #  Optimized grid density
        'min_orders_per_side': 3,      #  Minimum coverage
        'cycle_pair': False,           #  Stable pair for balance
        'trend_sensitive': False,      #  Less trend sensitive
        'auto_rebalance': False,       #  Auto rebalance DISABLED for ETH/USD
        'startup_rebalance': False,    #  Startup rebalance DISABLED for ETH/USD
        'dynamic_grid_reposition': True,  #  Enable dynamic grid repositioning
        'grid_reposition_threshold': 5.0,  #  Reposition if price moves >5% outside grid center
        'grid_reposition_cooldown': 300  #  Cooldown: 5 minutes between repositioning
    }
}

# Load environment variables - try multiple paths for Docker compatibility
env_paths = [
    "kraken.env",  # Current directory
    "/app/kraken.env",  # Docker container path
    os.path.join(os.path.dirname(__file__), "kraken.env"),  # Same directory as script
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
        env_loaded = True
        # Logger not yet defined here, so use print for Docker deployments
        if os.getenv('DOCKER_DEPLOYMENT'):
            print(f"[INFO] ✅ Loaded environment from: {env_path}")
        break

# Also load from environment variables directly (useful for Docker)
# Docker Compose can pass env vars directly, so this is a fallback
if not env_loaded:
    # Try to load from any .env file in current directory
    load_dotenv(override=True)

last_nonce = 0
def get_nonce():
    global last_nonce
    
    # Docker-aware nonce generation with enhanced conflict prevention
    current_time = time.time()
    
    # Check if we're in a Docker environment
    is_docker = (os.getenv('DOCKER_DEPLOYMENT') or 
                 os.path.exists('/.dockerenv') or 
                 os.getenv('HOSTNAME', '').startswith(('gridbot', 'container')))
    
    if is_docker:
        # Enhanced Docker nonce generation with container-specific seeding
        try:
            # Get container-specific identifier
            hostname = socket.gethostname()
            container_id = os.getenv('HOSTNAME', hostname)
            
            # Create container-specific seed from hostname/container ID
            container_seed = int(hashlib.md5(container_id.encode()).hexdigest()[:8], 16)
            
            # Use nanosecond precision with container-specific offset
            nonce_base = int(current_time * 1000000000)  # Nanoseconds
            
            # Large random component for Docker (10K-99K range)
            docker_random = random.randint(10000, 99999)
            
            # Add container-specific seed and environment variables if available
            env_seed = int(os.getenv('NONCE_SEED', '0'))
            
            nonce = nonce_base + container_seed + docker_random + env_seed
            
            # Extra large jump for Docker if nonce conflict
            if nonce <= last_nonce:
                nonce = last_nonce + random.randint(50000, 200000)
            
            if os.getenv('DEBUG_NONCE'):
                print(f"Docker nonce: {nonce}, container: {container_id}, seed: {container_seed}")
                
        except Exception as e:
            # Fallback for Docker if container detection fails
            print(f"Docker nonce generation fallback: {e}")
            nonce_base = int(current_time * 1000000000)
            nonce = nonce_base + random.randint(100000, 999999)
            if nonce <= last_nonce:
                nonce = last_nonce + random.randint(100000, 500000)
    else:
        # Standard nonce generation for non-Docker environments
        try:
            nonce_base = int(current_time * 1000000000)  # Nanoseconds
        except:
            nonce_base = int(current_time * 1000000)     # Microseconds fallback
        
        # Smaller random component for non-Docker
        random_component = random.randint(1000, 99999)
        nonce = nonce_base + random_component
        
        # Standard jump for conflicts
        if nonce <= last_nonce:
            nonce = last_nonce + random.randint(10000, 100000)
    
    last_nonce = nonce
    
    # Enhanced debug logging
    if os.getenv('DEBUG_NONCE'):
        env_type = "Docker" if is_docker else "Local"
        print(f"{env_type} nonce generated: {nonce}, time: {current_time}")
    
    return str(nonce)

class Logger:
    ERROR = '\033[91m'    
    WARNING = '\033[93m' 
    INFO = '\033[96m'     
    SUCCESS = '\033[92m' 
    ENHANCED = '\033[95m'
    PNL = '\033[93m'      # Yellow for PnL reporting
    RESET = '\033[0m'    
    _log_file = None
    _log_dir = None
    
    @staticmethod
    def init_file_logging(log_dir="logs"):
        """Initialize file logging"""
        try:
            Logger._log_dir = log_dir
            # Create log directory if it doesn't exist
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Create log file with timestamp
            log_filename = f"gridbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_path = os.path.join(log_dir, log_filename)
            
            # Also create a "latest.log" symlink/file for easy access
            Logger._log_file = open(log_path, 'a', encoding='utf-8')
            
            # Write to latest.log as well (for Docker compatibility)
            latest_log_path = os.path.join(log_dir, "latest.log")
            try:
                # Try to open in append mode
                latest_file = open(latest_log_path, 'a', encoding='utf-8')
                latest_file.close()
            except:
                pass
            
            Logger.info(f"📝 File logging enabled: {log_path}")
            return True
        except Exception as e:
            print(f"⚠️ Failed to initialize file logging: {e}")
            return False
    
    @staticmethod
    def _write_to_file(level: str, msg: str):
        """Write log message to file"""
        if Logger._log_file:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Remove ANSI color codes for file logging
                clean_msg = msg
                for code in [Logger.ERROR, Logger.WARNING, Logger.INFO, Logger.SUCCESS, Logger.ENHANCED, Logger.PNL, Logger.RESET]:
                    clean_msg = clean_msg.replace(code, '')
                
                log_entry = f"[{timestamp}][{level}] {clean_msg}\n"
                Logger._log_file.write(log_entry)
                Logger._log_file.flush()  # Ensure it's written immediately
                
                # Also write to latest.log
                if Logger._log_dir:
                    latest_log_path = os.path.join(Logger._log_dir, "latest.log")
                    try:
                        with open(latest_log_path, 'a', encoding='utf-8') as f:
                            f.write(log_entry)
                    except:
                        pass
            except Exception as e:
                # Don't fail if file logging fails
                pass
    
    @staticmethod
    def error(msg: str):
        CURRENT_TIME = time.strftime('%H:%M:%S')
        formatted_msg = f"{Logger.ERROR}[{CURRENT_TIME}][ERROR] {msg}{Logger.RESET}"
        print(formatted_msg)
        Logger._write_to_file("ERROR", msg)
        
    @staticmethod
    def warning(msg: str):
        CURRENT_TIME = time.strftime('%H:%M:%S')
        formatted_msg = f"{Logger.WARNING}[{CURRENT_TIME}][WARNING] {msg}{Logger.RESET}"
        print(formatted_msg)
        Logger._write_to_file("WARNING", msg)
        
    @staticmethod
    def info(msg: str):
        CURRENT_TIME = time.strftime('%H:%M:%S')
        formatted_msg = f"{Logger.INFO}[{CURRENT_TIME}][INFO] {msg}{Logger.RESET}"
        print(formatted_msg)
        Logger._write_to_file("INFO", msg)
        
    @staticmethod
    def success(msg: str):
        CURRENT_TIME = time.strftime('%H:%M:%S')
        formatted_msg = f"{Logger.SUCCESS}[{CURRENT_TIME}][SUCCESS] {msg}{Logger.RESET}"
        print(formatted_msg)
        Logger._write_to_file("SUCCESS", msg)
        
    @staticmethod
    def enhanced(msg: str):
        CURRENT_TIME = time.strftime('%H:%M:%S')
        formatted_msg = f"{Logger.ENHANCED}[{CURRENT_TIME}][ENHANCED] {msg}{Logger.RESET}"
        print(formatted_msg)
        Logger._write_to_file("ENHANCED", msg)
        
    @staticmethod
    def pnl(msg: str):
        CURRENT_TIME = time.strftime('%H:%M:%S')
        formatted_msg = f"{Logger.PNL}[{CURRENT_TIME}][PNL] {msg}{Logger.RESET}"
        print(formatted_msg)
        Logger._write_to_file("PNL", msg)

class PnLTracker:
    """SQLite-based PnL tracking system for the grid bot"""
    
    def __init__(self, db_file=None):
        self.db_file = db_file or DATABASE_FILE  # Use environment variable or default
        self.init_database()
        self.session_start_time = datetime.now()
        self.last_pnl_report = 0
        
    def init_database(self):
        """Initialize the SQLite database and create tables"""
        try:
            # Ensure directory exists with proper error handling
            db_dir = os.path.dirname(self.db_file)
            if db_dir:
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    # Set permissions if on Unix-like system
                    if hasattr(os, 'chmod'):
                        try:
                            os.chmod(db_dir, 0o755)
                        except:
                            pass  # Ignore permission errors if we can't set them
                except PermissionError as pe:
                    Logger.error(f"Permission denied creating database directory: {db_dir}")
                    Logger.error(f"Error: {str(pe)}")
                    raise
                except Exception as e:
                    Logger.warning(f"Could not create database directory {db_dir}: {str(e)}")
            
            # Try to connect to database
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
            except sqlite3.OperationalError as e:
                error_msg = str(e)
                if "unable to open database file" in error_msg.lower():
                    Logger.error(f"❌ Cannot open database file: {self.db_file}")
                    Logger.error(f"   Directory exists: {os.path.exists(db_dir) if db_dir else 'N/A'}")
                    Logger.error(f"   Directory writable: {os.access(db_dir, os.W_OK) if db_dir and os.path.exists(db_dir) else 'N/A'}")
                    Logger.error(f"   Full error: {error_msg}")
                    # Try to create in current directory as fallback
                    fallback_db = os.path.basename(self.db_file)
                    Logger.warning(f"⚠️ Attempting fallback to: {fallback_db}")
                    self.db_file = fallback_db
                    conn = sqlite3.connect(self.db_file)
                    cursor = conn.cursor()
                else:
                    raise
            
            # Create orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    pair TEXT,
                    side TEXT,
                    order_type TEXT,
                    volume REAL,
                    price REAL,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level INTEGER,
                    usd_value REAL
                )
            ''')
            
            # Create executions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    execution_id TEXT UNIQUE,
                    pair TEXT,
                    side TEXT,
                    volume REAL,
                    price REAL,
                    fee REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    usd_value REAL,
                    pnl_contribution REAL
                )
            ''')
            
            # Create portfolio snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    pair TEXT,
                    base_asset TEXT,
                    quote_asset TEXT,
                    base_balance REAL,
                    quote_balance REAL,
                    current_price REAL,
                    total_value_usd REAL,
                    allocation_percentage REAL
                )
            ''')
            
            # Create PnL summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pnl_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    pair TEXT,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    total_pnl REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    session_duration_hours REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            Logger.success("✅ PnL database initialized successfully")
            
        except Exception as e:
            Logger.error(f"Failed to initialize database: {str(e)}")
    
    def record_order_placed(self, order_id, pair, side, order_type, volume, price, level=None):
        """Record when an order is placed"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Calculate USD value approximation
            usd_value = self.estimate_usd_value(pair, volume, price)
            
            cursor.execute('''
                INSERT OR REPLACE INTO orders 
                (order_id, pair, side, order_type, volume, price, status, level, usd_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, pair, side, order_type, volume, price, 'open', level, usd_value))
            
            conn.commit()
            conn.close()
            
            Logger.info(f"📝 Order recorded: {pair} {side.upper()} {volume:.6f} @ {price:.6f}")
            
        except Exception as e:
            Logger.error(f"Failed to record order: {str(e)}")
    
    def record_order_execution(self, order_id, execution_id, pair, side, volume, price, fee=0):
        """Record when an order is executed"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Update order status
            cursor.execute('''
                UPDATE orders SET status = 'executed' WHERE order_id = ?
            ''', (order_id,))
            
            # Calculate USD value and PnL contribution
            usd_value = self.estimate_usd_value(pair, volume, price)
            pnl_contribution = self.calculate_pnl_contribution(pair, side, volume, price)
            
            # Record execution
            cursor.execute('''
                INSERT OR REPLACE INTO executions 
                (order_id, execution_id, pair, side, volume, price, fee, usd_value, pnl_contribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, execution_id, pair, side, volume, price, fee, usd_value, pnl_contribution))
            
            conn.commit()
            conn.close()
            
            Logger.success(f"✅ Execution recorded: {pair} {side.upper()} {volume:.6f} @ {price:.6f} (PnL: ${pnl_contribution:.2f})")
            
        except Exception as e:
            Logger.error(f"Failed to record execution: {str(e)}")
    
    def estimate_usd_value(self, pair, volume, price):
        """Estimate USD value of a trade"""
        if pair == "ETH/USD":
            return volume * price
        elif pair == "XRP/BTC":
            # Approximate BTC to USD conversion
            btc_usd_rate = 100000.0  # Rough estimate
            btc_value = volume * price
            return btc_value * btc_usd_rate
        else:
            return volume * price  # Default fallback
    
    def calculate_pnl_contribution(self, pair, side, volume, price):
        """Calculate PnL contribution of an execution"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get recent opposite side executions for this pair
            opposite_side = 'sell' if side == 'buy' else 'buy'
            
            cursor.execute('''
                SELECT price, volume FROM executions 
                WHERE pair = ? AND side = ? 
                ORDER BY timestamp DESC LIMIT 10
            ''', (pair, opposite_side))
            
            recent_trades = cursor.fetchall()
            conn.close()
            
            if recent_trades:
                # Simple PnL calculation based on price differences
                avg_opposite_price = sum(trade[0] for trade in recent_trades) / len(recent_trades)
                
                if side == 'buy':
                    # Bought at current price, compare to recent sells
                    price_diff = avg_opposite_price - price
                else:
                    # Sold at current price, compare to recent buys
                    price_diff = price - avg_opposite_price
                
                usd_value = self.estimate_usd_value(pair, volume, abs(price_diff))
                return usd_value if price_diff > 0 else -usd_value
            
            return 0.0
            
        except Exception as e:
            Logger.error(f"Failed to calculate PnL contribution: {str(e)}")
            return 0.0
    
    def generate_pnl_report(self):
        """Generate and display comprehensive PnL report"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            Logger.pnl("=" * 60)
            Logger.pnl("📊 GRIDBOT PnL REPORT")
            Logger.pnl("=" * 60)
            
            # Session info
            session_duration = datetime.now() - self.session_start_time
            Logger.pnl(f"📅 Session Duration: {session_duration}")
            Logger.pnl(f"🕐 Started: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Overall statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_executions,
                    SUM(usd_value) as total_volume,
                    SUM(pnl_contribution) as total_pnl,
                    AVG(pnl_contribution) as avg_pnl_per_trade
                FROM executions
            ''')
            
            overall_stats = cursor.fetchone()
            if overall_stats and overall_stats[0] > 0:
                total_executions, total_volume, total_pnl, avg_pnl = overall_stats
                Logger.pnl(f"📈 Total Executions: {total_executions}")
                Logger.pnl(f"💰 Total Volume: ${total_volume:.2f}")
                Logger.pnl(f"💵 Total PnL: ${total_pnl:.2f}")
                Logger.pnl(f"📊 Avg PnL/Trade: ${avg_pnl:.2f}")
            else:
                Logger.pnl("📭 No executions recorded yet")
                
            Logger.pnl("-" * 40)
            
            conn.close()
            
        except Exception as e:
            Logger.error(f"Failed to generate PnL report: {str(e)}")
    
    def get_quick_pnl_stats(self):
        """Get quick PnL statistics for console updates"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get session totals
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_executions,
                    SUM(pnl_contribution) as total_pnl,
                    SUM(usd_value) as total_volume
                FROM executions
            ''')
            
            stats = cursor.fetchone()
            conn.close()
            
            if stats and stats[0] > 0:
                executions, total_pnl, total_volume = stats
                session_duration = datetime.now() - self.session_start_time
                session_hours = session_duration.total_seconds() / 3600
                hourly_pnl = total_pnl / session_hours if session_hours > 0 else 0
                
                return {
                    'executions': executions,
                    'total_pnl': total_pnl,
                    'total_volume': total_volume,
                    'hourly_pnl': hourly_pnl,
                    'session_hours': session_hours
                }
            
            return None
            
        except Exception as e:
            Logger.error(f"Failed to get quick PnL stats: {str(e)}")
            return None
    
    def should_report_pnl(self):
        """Check if it's time for a PnL report"""
        current_time = time.time()
        if current_time - self.last_pnl_report >= PNL_REPORT_INTERVAL:
            self.last_pnl_report = current_time
            return True
        return False

class ImprovedGridBot:
    def __init__(self):
        self.api_key = os.getenv('KRAKEN_API_KEY')
        self.api_secret = os.getenv('KRAKEN_API_SECRET')
        self.rest_url = "https://api.kraken.com"
        self.balances = {}
        self.current_prices = {}
        
        # Initialize PnL tracker
        self.pnl_tracker = PnLTracker()
        
        # Track grid center prices and last reposition times for dynamic repositioning
        self.grid_center_prices = {}  # Track where each grid is centered
        self.last_reposition_time = {}  # Track when we last repositioned each pair
        
        # Track expected order counts to detect filled orders
        self.expected_order_counts = {}  # Track expected buy/sell counts per pair
        
        # Get enabled trading pairs
        self.enabled_pairs = {pair: config for pair, config in TRADING_PAIRS.items() 
                             if config.get('enabled', True)}
        
        if not self.api_key or not self.api_secret:
            raise ValueError("❌ Missing API credentials!\nMake sure KRAKEN_API_KEY and KRAKEN_API_SECRET are set")
        
        Logger.enhanced("🚀 ENHANCED MULTI-PAIR GRIDBOT WITH PnL TRACKING 🚀")
        Logger.info(f"📈 Trading pairs enabled: {len(self.enabled_pairs)}")
        for pair, config in self.enabled_pairs.items():
            grid_interval = config.get('grid_interval', 3.0)
            target_allocation = config.get('target_allocation', 'N/A')
            Logger.info(f"  {pair}: {grid_interval}% spacing, {target_allocation}% allocation")
        Logger.info(f"📊 PnL Tracking: ENABLED (reporting every {PNL_REPORT_INTERVAL//60} minutes)")

    def get_kraken_signature(self, urlpath, data):
        post_data = urllib.parse.urlencode(data)
        encoded = (data['nonce'] + post_data).encode('utf-8')
        message = urlpath.encode('utf-8') + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    async def api_call_with_retry(self, method, path, data=None, max_retries=3):
        """Make API call with retry logic"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = 2 + (attempt * 2)
                    Logger.info(f"⏳ Waiting {delay} seconds before attempt {attempt + 1}...")
                    await asyncio.sleep(delay)
                
                url = self.rest_url + path
                nonce = get_nonce()
                
                if data is None:
                    data = {}
                data['nonce'] = nonce
                
                headers = {
                    "API-Key": self.api_key,
                    "API-Sign": self.get_kraken_signature(path, data),
                }
                
                async with aiohttp.ClientSession() as session:
                    if method.upper() == 'GET':
                        async with session.get(url, headers=headers, params=data) as response:
                            result = await response.json()
                    else:  # POST
                        async with session.post(url, headers=headers, data=data) as response:
                            result = await response.json()
                
                # Check for errors
                if 'error' in result and result['error']:
                    error_msg = str(result['error'])
                    
                    if 'nonce' in error_msg.lower() and attempt < max_retries - 1:
                        Logger.warning(f"⚠️ Nonce error on attempt {attempt + 1}, retrying...")
                        continue
                    else:
                        Logger.error(f"❌ API error: {result['error']}")
                        return None
                
                return result.get("result", {})
                
            except Exception as e:
                if attempt < max_retries - 1:
                    Logger.warning(f"⚠️ API call failed (attempt {attempt + 1}): {str(e)}")
                    await asyncio.sleep(2 + attempt)
                    continue
                else:
                    Logger.error(f"❌ API call failed after {max_retries} attempts: {str(e)}")
                    return None
        
        return None

    async def get_account_balance(self):
        """Get current account balances"""
        try:
            Logger.info("💰 Fetching current balances...")
            result = await self.api_call_with_retry('POST', '/0/private/Balance')
            
            if result is None:
                Logger.error("❌ Failed to get account balance")
                return False
            
            self.balances = result
            
            # Display current balances
            Logger.info("💰 Current balances:")
            for asset, balance in self.balances.items():
                balance_float = float(balance)
                if balance_float > 0:
                    Logger.info(f"  {asset}: {balance_float:.6f}")
            
            return True
            
        except Exception as e:
            Logger.error(f"❌ Error getting balance: {str(e)}")
            return False

    async def get_current_prices(self):
        """Get current market prices for all enabled trading pairs"""
        try:
            Logger.info("📈 Fetching current prices...")
            path = "/0/public/Ticker"
            url = self.rest_url + path
            
            # Use the exact Kraken pair names from configuration
            kraken_pairs = []
            pair_mapping = {}
            
            for pair, config in self.enabled_pairs.items():
                kraken_pair = config.get('kraken_pair', pair.replace("/", ""))
                kraken_pairs.append(kraken_pair)
                pair_mapping[kraken_pair] = pair
                Logger.info(f"  Mapping {pair} -> {kraken_pair}")
            
            params = {'pair': ','.join(kraken_pairs)}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        Logger.error(f"❌ Price request failed: HTTP {response.status}")
                        return False
                    
                    result = await response.json()
                    if 'error' in result and result['error']:
                        Logger.error(f"❌ Price error: {result['error']}")
                        return False
                    
                    ticker_data = result.get("result", {})
                    
                    for kraken_pair, data in ticker_data.items():
                        if 'c' in data:  # 'c' is the last trade price
                            price = float(data['c'][0])
                            display_pair = pair_mapping.get(kraken_pair, kraken_pair)
                            self.current_prices[display_pair] = price
                            Logger.success(f"✅ {display_pair}: {price:.7f}")
                    
                    Logger.success(f"✅ Retrieved prices for {len(self.current_prices)} pairs")
                    return True
                    
        except Exception as e:
            Logger.error(f"❌ Error getting prices: {str(e)}")
            return False

    async def cancel_all_orders(self):
        """Cancel all existing orders"""
        try:
            Logger.enhanced("🧹 CANCELING ALL EXISTING ORDERS...")
            result = await self.api_call_with_retry('POST', '/0/private/CancelAll')
            
            if result is None:
                Logger.error("❌ Failed to cancel orders")
                return False
            
            canceled_count = result.get("count", 0)
            Logger.success(f"✅ Canceled {canceled_count} existing orders")
            return True
            
        except Exception as e:
            Logger.error(f"❌ Error canceling orders: {str(e)}")
            return False

    def round_price(self, price, precision):
        """Round price to specified precision"""
        return round(price, precision)
    
    def round_volume(self, volume, precision):
        """Round volume to specified precision"""
        return round(volume, precision)

    async def place_limit_order(self, pair, side, volume, price, config):
        """Place a limit order for a trading pair"""
        try:
            kraken_pair = config.get('kraken_pair')
            precision = config.get('precision', 8)
            volume_precision = config.get('volume_precision', 8)
            
            # Round price and volume to proper precision
            rounded_price = self.round_price(price, precision)
            rounded_volume = self.round_volume(volume, volume_precision)
            
            # Validate minimum order size
            min_order_size = config.get('min_order_size', 0.001)
            if pair == "ETH/USD":
                # For ETH/USD, min_order_size is in ETH
                if rounded_volume < min_order_size:
                    Logger.warning(f"⚠️ Order too small for {pair}: {rounded_volume} < {min_order_size}")
                    return None
            else:
                # For other pairs, min_order_size is typically in USD value
                order_value = rounded_volume * rounded_price
                if order_value < min_order_size:
                    Logger.warning(f"⚠️ Order value too small for {pair}: ${order_value:.2f} < ${min_order_size:.2f}")
                    return None
            
            data = {
                'pair': kraken_pair,
                'type': side,
                'ordertype': 'limit',
                'price': str(rounded_price),
                'volume': str(rounded_volume)
            }
            
            result = await self.api_call_with_retry('POST', '/0/private/AddOrder', data)
            
            if result is None:
                Logger.error(f"❌ Failed to place {side} order for {pair} - API call returned None")
                Logger.error(f"   Details: pair={kraken_pair}, price={rounded_price}, volume={rounded_volume}")
                return None
            
            # Check for API errors in result
            if 'error' in result and result['error']:
                error_msg = str(result['error'])
                Logger.error(f"❌ API error placing {side} order for {pair}: {error_msg}")
                Logger.error(f"   Details: pair={kraken_pair}, price={rounded_price}, volume={rounded_volume}")
                return None
            
            txid_list = result.get('txid', [])
            if not txid_list:
                Logger.error(f"❌ No transaction ID returned for {pair} {side} order")
                Logger.error(f"   API response: {result}")
                Logger.error(f"   Details: pair={kraken_pair}, price={rounded_price}, volume={rounded_volume}")
                return None
            
            order_id = txid_list[0]
            Logger.success(f"✅ Placed {side.upper()} order for {pair}: {rounded_volume:.{volume_precision}f} @ {rounded_price:.{precision}f} (ID: {order_id})")
            
            # Record order in database
            self.pnl_tracker.record_order_placed(order_id, pair, side, 'limit', rounded_volume, rounded_price)
            
            return order_id
            
        except Exception as e:
            Logger.error(f"❌ Exception placing {side} order for {pair}: {str(e)}")
            Logger.error(f"   Details: pair={pair}, side={side}, price={price}, volume={volume}")
            import traceback
            Logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    async def get_open_orders(self):
        """Get all open orders"""
        try:
            result = await self.api_call_with_retry('POST', '/0/private/OpenOrders')
            
            if result is None:
                return {}
            
            return result.get('open', {})
            
        except Exception as e:
            Logger.error(f"❌ Error getting open orders: {str(e)}")
            return {}

    async def get_trades_history(self, pair_config):
        """Get recent trades history to detect filled orders"""
        try:
            kraken_pair = pair_config.get('kraken_pair')
            data = {'pair': kraken_pair}
            
            result = await self.api_call_with_retry('POST', '/0/private/TradesHistory', data)
            
            if result is None:
                return {}
            
            return result.get('trades', {})
            
        except Exception as e:
            Logger.error(f"❌ Error getting trades history: {str(e)}")
            return {}

    def calculate_order_volume(self, pair, side, config, current_price, orders_count):
        """Calculate order volume based on available balance and number of orders"""
        try:
            base_asset = config.get('base_asset')
            quote_asset = config.get('quote_asset')
            
            # Get available balances
            base_balance = float(self.balances.get(base_asset, 0))
            quote_balance = float(self.balances.get(quote_asset, 0))
            
            if pair == "ETH/USD":
                # For ETH/USD: base is ZUSD, quote is XETH
                if side == 'buy':
                    # Buy orders: need USD, buying ETH
                    available_usd = base_balance * 0.95  # Use 95% of USD
                    if available_usd < 10:  # Minimum $10
                        return None
                    # Distribute USD across buy orders
                    usd_per_order = available_usd / orders_count
                    volume = usd_per_order / current_price  # ETH volume
                else:  # sell
                    # Sell orders: need ETH, selling for USD
                    available_eth = quote_balance * 0.95  # Use 95% of ETH
                    if available_eth < 0.005:  # Minimum 0.005 ETH
                        Logger.warning(f"⚠️ Insufficient ETH balance for sell order: {available_eth:.6f} < 0.005 (quote_balance: {quote_balance:.6f})")
                        return None
                    # Distribute ETH across sell orders
                    volume = available_eth / orders_count
                    Logger.info(f"📊 Calculated sell volume for {pair}: {volume:.6f} ETH (from {available_eth:.6f} available, {orders_count} orders)")
            else:
                # For XRP/BTC: base is XXBT, quote is XXRP
                if side == 'buy':
                    # Buy orders: need BTC, buying XRP
                    available_btc = base_balance * 0.95
                    if available_btc < 0.0001:  # Minimum BTC
                        return None
                    btc_per_order = available_btc / orders_count
                    volume = btc_per_order / current_price  # XRP volume
                else:  # sell
                    # Sell orders: need XRP, selling for BTC
                    available_xrp = quote_balance * 0.95
                    if available_xrp < 10:  # Minimum XRP
                        Logger.warning(f"⚠️ Insufficient XRP balance for sell order: {available_xrp:.2f} < 10 (quote_balance: {quote_balance:.2f})")
                        return None
                    volume = available_xrp / orders_count
                    Logger.info(f"📊 Calculated sell volume for {pair}: {volume:.2f} XRP (from {available_xrp:.2f} available, {orders_count} orders)")
            
            return volume
            
        except Exception as e:
            Logger.error(f"❌ Error calculating order volume for {pair}: {str(e)}")
            return None

    async def create_grid_orders(self, pair, config):
        """Create initial grid of buy and sell orders for a trading pair"""
        try:
            if pair not in self.current_prices:
                Logger.error(f"❌ No current price available for {pair}")
                return False
            
            current_price = self.current_prices[pair]
            grid_interval = config.get('grid_interval', 1.5)
            max_orders_per_side = config.get('max_orders_per_side', 10)
            min_orders_per_side = config.get('min_orders_per_side', 3)
            
            Logger.enhanced(f"📊 Creating grid for {pair} at price {current_price:.6f}")
            
            # Calculate orders per side based on available balance
            base_asset = config.get('base_asset')
            quote_asset = config.get('quote_asset')
            
            if pair == "ETH/USD":
                base_balance = float(self.balances.get(base_asset, 0))  # USD
                quote_balance = float(self.balances.get(quote_asset, 0))  # ETH
                
                # Calculate orders per side
                usd_available = base_balance * 0.95
                eth_available = quote_balance * 0.95
                
                # Buy orders: based on USD available
                buy_orders_count = min(max_orders_per_side, max(min_orders_per_side, int(usd_available / (current_price * 0.005))))
                # Sell orders: based on ETH available
                sell_orders_count = min(max_orders_per_side, max(min_orders_per_side, int(eth_available / 0.005)))
            else:
                # XRP/BTC logic
                base_balance = float(self.balances.get(base_asset, 0))  # BTC
                quote_balance = float(self.balances.get(quote_asset, 0))  # XRP
                
                buy_orders_count = min(max_orders_per_side, max(min_orders_per_side, int(base_balance / 0.0001)))
                sell_orders_count = min(max_orders_per_side, max(min_orders_per_side, int(quote_balance / 10)))
            
            orders_placed = 0
            
            # Create buy orders (below current price)
            if buy_orders_count > 0:
                volume = self.calculate_order_volume(pair, 'buy', config, current_price, buy_orders_count)
                if volume is None:
                    Logger.warning(f"⚠️ Cannot calculate buy order volume for {pair}")
                else:
                    for i in range(1, buy_orders_count + 1):
                        price_offset = (grid_interval / 100.0) * i
                        buy_price = current_price * (1 - price_offset)
                        
                        order_id = await self.place_limit_order(pair, 'buy', volume, buy_price, config)
                        if order_id:
                            orders_placed += 1
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.1)
            
            # Create sell orders (above current price)
            if sell_orders_count > 0:
                volume = self.calculate_order_volume(pair, 'sell', config, current_price, sell_orders_count)
                if volume is None:
                    Logger.warning(f"⚠️ Cannot calculate sell order volume for {pair}")
                else:
                    for i in range(1, sell_orders_count + 1):
                        price_offset = (grid_interval / 100.0) * i
                        sell_price = current_price * (1 + price_offset)
                        
                        order_id = await self.place_limit_order(pair, 'sell', volume, sell_price, config)
                        if order_id:
                            orders_placed += 1
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.1)
            
            Logger.success(f"✅ Created {orders_placed} grid orders for {pair}")
            
            # Track grid center price for dynamic repositioning
            self.grid_center_prices[pair] = current_price
            
            # Track expected order counts
            self.expected_order_counts[pair] = {
                'buy': buy_orders_count if buy_orders_count > 0 else 0,
                'sell': sell_orders_count if sell_orders_count > 0 else 0
            }
            
            return True
            
        except Exception as e:
            Logger.error(f"❌ Error creating grid orders for {pair}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def check_grid_reposition_needed(self, pair, config):
        """Check if grid needs to be repositioned based on price movement"""
        try:
            # Only check if dynamic repositioning is enabled
            if not config.get('dynamic_grid_reposition', False):
                return False
            
            if pair not in self.current_prices or pair not in self.grid_center_prices:
                return False
            
            current_price = self.current_prices[pair]
            grid_center = self.grid_center_prices[pair]
            grid_interval = config.get('grid_interval', 1.5)
            max_orders_per_side = config.get('max_orders_per_side', 18)
            threshold = config.get('grid_reposition_threshold', 5.0)  # Default 5%
            cooldown = config.get('grid_reposition_cooldown', 300)  # Default 5 minutes
            
            # Check cooldown period
            if pair in self.last_reposition_time:
                time_since_reposition = time.time() - self.last_reposition_time[pair]
                if time_since_reposition < cooldown:
                    return False
            
            # Calculate grid range (how far the grid extends from center)
            grid_range_percent = (grid_interval / 100.0) * max_orders_per_side
            
            # Calculate how far current price is from grid center
            price_deviation = abs((current_price - grid_center) / grid_center) * 100
            
            # Check if price is outside grid range by more than threshold
            if price_deviation > (grid_range_percent + threshold):
                Logger.warning(f"📊 {pair}: Price moved {price_deviation:.2f}% from grid center ({grid_center:.2f} -> {current_price:.2f})")
                Logger.info(f"   Grid range: ±{grid_range_percent:.2f}%, Threshold: {threshold}%")
                return True
            
            return False
            
        except Exception as e:
            Logger.error(f"❌ Error checking grid reposition for {pair}: {str(e)}")
            return False

    async def reposition_grid(self, pair, config):
        """Reposition grid around current price"""
        try:
            Logger.enhanced(f"🔄 Repositioning grid for {pair} around current price...")
            
            # Cancel all existing orders for this pair
            kraken_pair = config.get('kraken_pair')
            result = await self.api_call_with_retry('POST', '/0/private/CancelAll', {'pair': kraken_pair})
            
            if result:
                canceled = result.get('count', 0)
                Logger.info(f"   Canceled {canceled} existing orders")
            
            # Wait a moment for cancellations to process
            await asyncio.sleep(1)
            
            # Refresh balances and prices
            await self.get_account_balance()
            await self.get_current_prices()
            
            # Create new grid around current price
            success = await self.create_grid_orders(pair, config)
            
            if success:
                self.last_reposition_time[pair] = time.time()
                # Expected counts will be updated by create_grid_orders
                Logger.success(f"✅ Grid repositioned for {pair}")
                return True
            else:
                Logger.error(f"❌ Failed to reposition grid for {pair}")
                return False
                
        except Exception as e:
            Logger.error(f"❌ Error repositioning grid for {pair}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def monitor_and_replace_orders(self):
        """Monitor open orders and replace filled ones"""
        try:
            open_orders = await self.get_open_orders()
            
            # Track orders by pair
            orders_by_pair = {}
            for order_id, order_data in open_orders.items():
                pair_name = None
                # Find which pair this order belongs to
                desc = order_data.get('descr', {})
                order_pair = desc.get('pair', '')
                
                for pair, config in self.enabled_pairs.items():
                    if config.get('kraken_pair') == order_pair:
                        pair_name = pair
                        break
                
                if pair_name:
                    if pair_name not in orders_by_pair:
                        orders_by_pair[pair_name] = {'buy': 0, 'sell': 0}
                    
                    order_type = desc.get('type', '')
                    if order_type == 'buy':
                        orders_by_pair[pair_name]['buy'] += 1
                    elif order_type == 'sell':
                        orders_by_pair[pair_name]['sell'] += 1
            
            # Initialize expected counts from current orders if not set (handles bot restart)
            for pair in self.enabled_pairs.keys():
                if pair not in self.expected_order_counts:
                    pair_orders = orders_by_pair.get(pair, {'buy': 0, 'sell': 0})
                    self.expected_order_counts[pair] = {
                        'buy': pair_orders['buy'],
                        'sell': pair_orders['sell']
                    }
                    Logger.info(f"📊 {pair}: Initialized expected counts from current orders: {pair_orders['buy']} buy, {pair_orders['sell']} sell")
            
            # Check each pair and replace missing orders
            for pair, config in self.enabled_pairs.items():
                if pair not in self.current_prices:
                    continue
                
                # First, check if grid needs repositioning (before checking individual orders)
                if await self.check_grid_reposition_needed(pair, config):
                    await self.reposition_grid(pair, config)
                    continue  # Skip individual order replacement this cycle
                
                current_price = self.current_prices[pair]
                max_orders_per_side = config.get('max_orders_per_side', 10)
                min_orders_per_side = config.get('min_orders_per_side', 3)
                
                pair_orders = orders_by_pair.get(pair, {'buy': 0, 'sell': 0})
                buy_count = pair_orders['buy']
                sell_count = pair_orders['sell']
                
                # Get expected counts (if we have them)
                expected = self.expected_order_counts.get(pair, {'buy': 0, 'sell': 0})
                expected_buy = expected.get('buy', 0)
                expected_sell = expected.get('sell', 0)
                
                # Detect filled orders: if we have fewer orders than expected, orders were filled
                # When a sell order fills, we should place a new buy order
                # When a buy order fills, we should place a new sell order
                
                # Check if sell orders were filled (we have fewer than expected)
                if sell_count < expected_sell:
                    filled_sells = expected_sell - sell_count
                    Logger.info(f"📊 {pair}: {filled_sells} sell order(s) filled! Placing {filled_sells} new buy order(s)...")
                    
                    # Refresh balances to get updated base currency from the sale
                    # (USD for ETH/USD, BTC for XRP/BTC)
                    await self.get_account_balance()
                    
                    # Place replacement buy orders for each filled sell order
                    grid_interval = config.get('grid_interval', 1.5)
                    orders_placed = 0
                    for i in range(filled_sells):
                        volume = self.calculate_order_volume(pair, 'buy', config, current_price, 1)
                        if volume:
                            # Place buy order at appropriate grid level below current price
                            price_offset = (grid_interval / 100.0) * (buy_count + i + 1)
                            buy_price = current_price * (1 - price_offset)
                            order_id = await self.place_limit_order(pair, 'buy', volume, buy_price, config)
                            if order_id:
                                orders_placed += 1
                                await asyncio.sleep(0.2)  # Small delay between orders
                    
                    if orders_placed > 0:
                        # Update expected counts after placing all replacement orders
                        expected_buy = buy_count + orders_placed
                        expected_sell = sell_count  # Update to actual count
                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                        Logger.success(f"✅ Placed {orders_placed} new buy order(s) after sell fill(s)")
                    else:
                        Logger.warning(f"⚠️ Failed to place replacement buy orders for {pair}")
                
                # Check if buy orders were filled (we have fewer than expected)
                if buy_count < expected_buy:
                    filled_buys = expected_buy - buy_count
                    Logger.info(f"📊 {pair}: {filled_buys} buy order(s) filled! Placing {filled_buys} new sell order(s)...")
                    
                    # Refresh balances to get updated quote currency from the purchase
                    # (ETH for ETH/USD, XRP for XRP/BTC)
                    await self.get_account_balance()
                    
                    # Place replacement sell orders for each filled buy order
                    grid_interval = config.get('grid_interval', 1.5)
                    orders_placed = 0
                    for i in range(filled_buys):
                        volume = self.calculate_order_volume(pair, 'sell', config, current_price, 1)
                        if volume:
                            # Place sell order at appropriate grid level above current price
                            price_offset = (grid_interval / 100.0) * (sell_count + i + 1)
                            sell_price = current_price * (1 + price_offset)
                            order_id = await self.place_limit_order(pair, 'sell', volume, sell_price, config)
                            if order_id:
                                orders_placed += 1
                                await asyncio.sleep(0.2)  # Small delay between orders
                    
                    if orders_placed > 0:
                        # Update expected counts after placing all replacement orders
                        expected_sell = sell_count + orders_placed
                        expected_buy = buy_count  # Update to actual count
                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                        Logger.success(f"✅ Placed {orders_placed} new sell order(s) after buy fill(s)")
                    else:
                        Logger.warning(f"⚠️ Failed to place replacement sell orders for {pair}")
                
                # Also check if we need to add orders to maintain minimum grid
                # Check if we need to add buy orders
                if buy_count < min_orders_per_side:
                    needed = min_orders_per_side - buy_count
                    Logger.info(f"📊 {pair}: Need {needed} more buy orders (current: {buy_count})")
                    
                    volume = self.calculate_order_volume(pair, 'buy', config, current_price, needed)
                    if volume:
                        orders_placed = 0
                        for i in range(needed):
                            # Find a price below current that doesn't have an order
                            grid_interval = config.get('grid_interval', 1.5)
                            price_offset = (grid_interval / 100.0) * (buy_count + i + 1)
                            buy_price = current_price * (1 - price_offset)
                            
                            order_id = await self.place_limit_order(pair, 'buy', volume, buy_price, config)
                            if order_id:
                                orders_placed += 1
                            await asyncio.sleep(0.1)
                        
                        if orders_placed > 0:
                            # Update expected counts
                            expected_buy = buy_count + orders_placed
                            self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                    else:
                        Logger.warning(f"⚠️ Cannot calculate buy order volume for {pair}")
                elif buy_count < max_orders_per_side:
                    # Check if we can add more buy orders (we have capacity and balance)
                    base_asset = config.get('base_asset')
                    base_balance = float(self.balances.get(base_asset, 0))
                    
                    # For XRP/BTC: check BTC balance; for ETH/USD: check USD balance
                    if pair == "ETH/USD":
                        if base_balance > current_price * 0.005 * (max_orders_per_side - buy_count):
                            # We have enough balance to add more orders
                            can_add = min(max_orders_per_side - buy_count, int(base_balance / (current_price * 0.005)))
                            if can_add > 0:
                                Logger.info(f"📊 {pair}: Can add {can_add} more buy orders (current: {buy_count}, max: {max_orders_per_side})")
                                volume = self.calculate_order_volume(pair, 'buy', config, current_price, can_add)
                                if volume:
                                    orders_placed = 0
                                    for i in range(can_add):
                                        grid_interval = config.get('grid_interval', 1.5)
                                        price_offset = (grid_interval / 100.0) * (buy_count + i + 1)
                                        buy_price = current_price * (1 - price_offset)
                                        order_id = await self.place_limit_order(pair, 'buy', volume, buy_price, config)
                                        if order_id:
                                            orders_placed += 1
                                        await asyncio.sleep(0.1)
                                    
                                    if orders_placed > 0:
                                        expected_buy = buy_count + orders_placed
                                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                    else:  # XRP/BTC
                        if base_balance > 0.0001 * (max_orders_per_side - buy_count):
                            can_add = min(max_orders_per_side - buy_count, int(base_balance / 0.0001))
                            if can_add > 0:
                                Logger.info(f"📊 {pair}: Can add {can_add} more buy orders (current: {buy_count}, max: {max_orders_per_side})")
                                volume = self.calculate_order_volume(pair, 'buy', config, current_price, can_add)
                                if volume:
                                    orders_placed = 0
                                    for i in range(can_add):
                                        grid_interval = config.get('grid_interval', 1.5)
                                        price_offset = (grid_interval / 100.0) * (buy_count + i + 1)
                                        buy_price = current_price * (1 - price_offset)
                                        order_id = await self.place_limit_order(pair, 'buy', volume, buy_price, config)
                                        if order_id:
                                            orders_placed += 1
                                        await asyncio.sleep(0.1)
                                    
                                    if orders_placed > 0:
                                        expected_buy = buy_count + orders_placed
                                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                
                # Check if we need to add sell orders
                if sell_count < min_orders_per_side:
                    needed = min_orders_per_side - sell_count
                    Logger.info(f"📊 {pair}: Need {needed} more sell orders (current: {sell_count})")
                    
                    volume = self.calculate_order_volume(pair, 'sell', config, current_price, needed)
                    if volume:
                        orders_placed = 0
                        for i in range(needed):
                            # Find a price above current that doesn't have an order
                            grid_interval = config.get('grid_interval', 1.5)
                            price_offset = (grid_interval / 100.0) * (sell_count + i + 1)
                            sell_price = current_price * (1 + price_offset)
                            
                            order_id = await self.place_limit_order(pair, 'sell', volume, sell_price, config)
                            if order_id:
                                orders_placed += 1
                            await asyncio.sleep(0.1)
                        
                        if orders_placed > 0:
                            # Update expected counts
                            expected_sell = sell_count + orders_placed
                            self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                    else:
                        Logger.warning(f"⚠️ Cannot calculate sell order volume for {pair}")
                elif sell_count < max_orders_per_side:
                    # Check if we can add more sell orders (we have capacity and balance)
                    quote_asset = config.get('quote_asset')
                    quote_balance = float(self.balances.get(quote_asset, 0))
                    
                    # For XRP/BTC: check XRP balance; for ETH/USD: check ETH balance
                    if pair == "ETH/USD":
                        if quote_balance > 0.005 * (max_orders_per_side - sell_count):
                            can_add = min(max_orders_per_side - sell_count, int(quote_balance / 0.005))
                            if can_add > 0:
                                Logger.info(f"📊 {pair}: Can add {can_add} more sell orders (current: {sell_count}, max: {max_orders_per_side})")
                                volume = self.calculate_order_volume(pair, 'sell', config, current_price, can_add)
                                if volume:
                                    orders_placed = 0
                                    for i in range(can_add):
                                        grid_interval = config.get('grid_interval', 1.5)
                                        price_offset = (grid_interval / 100.0) * (sell_count + i + 1)
                                        sell_price = current_price * (1 + price_offset)
                                        order_id = await self.place_limit_order(pair, 'sell', volume, sell_price, config)
                                        if order_id:
                                            orders_placed += 1
                                        await asyncio.sleep(0.1)
                                    
                                    if orders_placed > 0:
                                        expected_sell = sell_count + orders_placed
                                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
                    else:  # XRP/BTC
                        if quote_balance > 10 * (max_orders_per_side - sell_count):
                            can_add = min(max_orders_per_side - sell_count, int(quote_balance / 10))
                            if can_add > 0:
                                Logger.info(f"📊 {pair}: Can add {can_add} more sell orders (current: {sell_count}, max: {max_orders_per_side})")
                                volume = self.calculate_order_volume(pair, 'sell', config, current_price, can_add)
                                if volume:
                                    orders_placed = 0
                                    for i in range(can_add):
                                        grid_interval = config.get('grid_interval', 1.5)
                                        price_offset = (grid_interval / 100.0) * (sell_count + i + 1)
                                        sell_price = current_price * (1 + price_offset)
                                        order_id = await self.place_limit_order(pair, 'sell', volume, sell_price, config)
                                        if order_id:
                                            orders_placed += 1
                                        await asyncio.sleep(0.1)
                                    
                                    if orders_placed > 0:
                                        expected_sell = sell_count + orders_placed
                                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': expected_sell}
            
            return True
            
        except Exception as e:
            Logger.error(f"❌ Error monitoring orders: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def start_trading(self):
        """Main trading function"""
        try:
            Logger.enhanced("🎯 STARTING GRIDBOT TRADING SESSION")
            
            # Initialize
            if not await self.get_account_balance():
                return False
            
            if not await self.get_current_prices():
                return False
            
            if CANCEL_ALL_ON_STARTUP:
                await self.cancel_all_orders()
            
            # Create initial grid orders for each enabled pair
            Logger.enhanced("📊 Creating initial grid orders...")
            for pair, config in self.enabled_pairs.items():
                if config.get('enabled', True):
                    await self.create_grid_orders(pair, config)
                    await asyncio.sleep(1)  # Small delay between pairs
            
            Logger.success("🎉 GridBot initialized successfully!")
            Logger.info("📊 PnL tracking active - check logs for execution reports")
            Logger.info(f"⏱️ Monitoring orders every {ORDER_CHECK_INTERVAL} seconds")
            
            # Main trading loop
            while True:
                try:
                    # Refresh balances and prices periodically
                    await self.get_account_balance()
                    await self.get_current_prices()
                    
                    # Monitor and replace filled orders
                    await self.monitor_and_replace_orders()
                    
                    # Generate periodic PnL reports
                    if self.pnl_tracker.should_report_pnl():
                        Logger.enhanced("📊 GENERATING PnL REPORT...")
                        self.pnl_tracker.generate_pnl_report()
                    
                    await asyncio.sleep(ORDER_CHECK_INTERVAL)
                    
                except KeyboardInterrupt:
                    Logger.info("🛑 Shutdown requested")
                    break
                except Exception as e:
                    Logger.error(f"❌ Error in main loop: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(30)
            
        except Exception as e:
            Logger.error(f"❌ Critical error in trading: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main entry point"""
    try:
        # Initialize file logging
        log_dir = os.getenv('LOG_DIR', 'logs')
        Logger.init_file_logging(log_dir)
        
        # Check time synchronization
        Logger.enhanced("🕐 Checking container time synchronization...")
        container_time = datetime.now()
        Logger.info(f"📅 Container time: {container_time.strftime('%a %b %d %H:%M:%S UTC %Y')}")
        Logger.info(f"🌍 UTC time: {datetime.utcnow().strftime('%a %b %d %H:%M:%S UTC %Y')}")
        
        # Adding startup delay to prevent nonce conflicts
        startup_delay = random.randint(5, 12)
        Logger.enhanced(f"⏳ Adding {startup_delay}s startup delay to prevent nonce conflicts...")
        await asyncio.sleep(startup_delay)
        
        # Check API credentials
        api_key = os.getenv('KRAKEN_API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET')
        
        if not api_key or not api_secret:
            Logger.error("❌ Missing API credentials!")
            Logger.error("Make sure KRAKEN_API_KEY and KRAKEN_API_SECRET are set")
            
            # Debug: Check if env file exists
            env_paths = ["kraken.env", "/app/kraken.env", os.path.join(os.path.dirname(__file__), "kraken.env")]
            Logger.info("Checking for environment file...")
            for env_path in env_paths:
                exists = os.path.exists(env_path)
                Logger.info(f"  {env_path}: {'✅ exists' if exists else '❌ not found'}")
                if exists:
                    try:
                        with open(env_path, 'r') as f:
                            content = f.read()
                            has_key = 'KRAKEN_API_KEY' in content
                            has_secret = 'KRAKEN_API_SECRET' in content
                            Logger.info(f"    Contains KRAKEN_API_KEY: {'✅' if has_key else '❌'}")
                            Logger.info(f"    Contains KRAKEN_API_SECRET: {'✅' if has_secret else '❌'}")
                    except Exception as e:
                        Logger.error(f"    Error reading file: {e}")
            
            return
        
        Logger.success("✅ API credentials configured")
        
        # Start bot
        bot = ImprovedGridBot()
        await bot.start_trading()
        
    except Exception as e:
        Logger.error(f"❌ Failed to start GridBot: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
