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

VERSION: 2025-12-04 - FIXED ORDER REPLACEMENT LOGIC
- Fixed expected counts tracking (no longer auto-syncs to mask missing orders)
- Improved order matching with case-insensitive fallbacks
- Refreshes actual order counts after placing replacements
- Better error logging for failed order placements
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
_nonce_file = None

def _load_persistent_nonce():
    """Load last nonce from file to survive container restarts"""
    global last_nonce
    try:
        nonce_file = os.path.join(os.getenv('DATA_DIR', '/app/data'), '.last_nonce')
        if os.path.exists(nonce_file):
            with open(nonce_file, 'r') as f:
                saved_nonce = int(f.read().strip())
                # Only use if it's recent (within last hour) to avoid huge jumps
                if saved_nonce > 0:
                    last_nonce = saved_nonce
    except:
        pass

def _save_persistent_nonce(nonce):
    """Save last nonce to file"""
    try:
        nonce_file = os.path.join(os.getenv('DATA_DIR', '/app/data'), '.last_nonce')
        os.makedirs(os.path.dirname(nonce_file), exist_ok=True)
        with open(nonce_file, 'w') as f:
            f.write(str(nonce))
    except:
        pass

def get_nonce():
    global last_nonce
    
    # Load persistent nonce on first call
    if last_nonce == 0:
        _load_persistent_nonce()
    
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
            
            # Large random component for Docker (50K-200K range for better spacing)
            docker_random = random.randint(50000, 200000)
            
            # Add container-specific seed and environment variables if available
            env_seed = int(os.getenv('NONCE_SEED', '0'))
            
            nonce = nonce_base + container_seed + docker_random + env_seed
            
            # Extra large jump for Docker if nonce conflict (ensure minimum 1M gap)
            if nonce <= last_nonce:
                nonce = last_nonce + random.randint(1000000, 5000000)
            
            if os.getenv('DEBUG_NONCE'):
                print(f"Docker nonce: {nonce}, container: {container_id}, seed: {container_seed}, last: {last_nonce}")
                
        except Exception as e:
            # Fallback for Docker if container detection fails
            print(f"Docker nonce generation fallback: {e}")
            nonce_base = int(current_time * 1000000000)
            nonce = nonce_base + random.randint(100000, 999999)
            if nonce <= last_nonce:
                nonce = last_nonce + random.randint(1000000, 5000000)
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
    _save_persistent_nonce(nonce)
    
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
        self.btc_usd_price = None  # For converting XRP/BTC order values to USD
        
        # Initialize PnL tracker
        self.pnl_tracker = PnLTracker()
        
        # Track grid center prices and last reposition times for dynamic repositioning
        self.grid_center_prices = {}  # Track where each grid is centered
        self.last_reposition_time = {}  # Track when we last repositioned each pair
        
        # Track expected order counts to detect filled orders
        self.expected_order_counts = {}  # Track expected buy/sell counts per pair
        self.expected_counts_file = os.path.join(os.getenv('DATA_DIR', '.'), '.expected_order_counts.json')
        self._load_expected_counts()  # Load from file if exists
        
        # Get enabled trading pairs
        self.enabled_pairs = {pair: config for pair, config in TRADING_PAIRS.items() 
                             if config.get('enabled', True)}
        
        if not self.api_key or not self.api_secret:
            raise ValueError("❌ Missing API credentials!\nMake sure KRAKEN_API_KEY and KRAKEN_API_SECRET are set")
        
        Logger.enhanced("🚀 ENHANCED MULTI-PAIR GRIDBOT WITH PnL TRACKING 🚀")
        Logger.info(f"📈 Trading pairs enabled: {len(self.enabled_pairs)}")
        if self.expected_order_counts:
            Logger.info(f"📊 Loaded expected order counts from previous session: {self.expected_order_counts}")
        for pair, config in self.enabled_pairs.items():
            grid_interval = config.get('grid_interval', 3.0)
            target_allocation = config.get('target_allocation', 'N/A')
            Logger.info(f"  {pair}: {grid_interval}% spacing, {target_allocation}% allocation")
        Logger.info(f"📊 PnL Tracking: ENABLED (reporting every {PNL_REPORT_INTERVAL//60} minutes)")

    def _load_expected_counts(self):
        """Load expected order counts from file (survives restarts)"""
        try:
            if os.path.exists(self.expected_counts_file):
                with open(self.expected_counts_file, 'r') as f:
                    data = json.load(f)
                    self.expected_order_counts = data
                    Logger.info(f"📂 Loaded expected order counts from {self.expected_counts_file}")
        except Exception as e:
            Logger.warning(f"⚠️ Could not load expected order counts: {e}")
            self.expected_order_counts = {}
    
    def _save_expected_counts(self):
        """Save expected order counts to file (survives restarts)"""
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(self.expected_counts_file)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            with open(self.expected_counts_file, 'w') as f:
                json.dump(self.expected_order_counts, f)
            Logger.info(f"💾 Saved expected order counts: {self.expected_order_counts}")
        except Exception as e:
            Logger.warning(f"⚠️ Could not save expected order counts: {e}")

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
                        # Increase delay for nonce errors and force a larger nonce jump
                        delay = 3 + (attempt * 3)
                        Logger.info(f"Waiting {delay} seconds before attempt {attempt + 1}...")
                        await asyncio.sleep(delay)
                        # Force a large nonce jump by updating last_nonce
                        global last_nonce
                        last_nonce = int(time.time() * 1000000000) + random.randint(1000000, 5000000)
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
        """Get current account balances and calculate available balances (subtracting locked funds)"""
        try:
            Logger.info("💰 Fetching current balances...")
            result = await self.api_call_with_retry('POST', '/0/private/Balance')
            
            if result is None:
                Logger.error("❌ Failed to get account balance")
                return False
            
            # Store total balances
            self.balances = result
            
            # Get open orders to calculate locked funds
            open_orders = await self.get_open_orders()
            
            # Calculate locked funds per asset
            locked_funds = {}
            Logger.info(f"🔍 Analyzing {len(open_orders)} open orders for locked funds...")
            for order_id, order_data in open_orders.items():
                desc = order_data.get('descr', {})
                order_type = desc.get('type', '')
                vol = float(order_data.get('vol', 0))
                pair_str = desc.get('pair', '')
                pair_str_upper = pair_str.upper()
                
                if order_type == 'buy':
                    # Buy orders lock the base currency (USD for ETH/USD, BTC for XRP/BTC)
                    if 'ETH' in pair_str_upper and 'USD' in pair_str_upper:
                        # ETH/USD buy order: locks USD
                        price = float(desc.get('price', 0))
                        locked_usd = vol * price
                        locked_funds['ZUSD'] = locked_funds.get('ZUSD', 0) + locked_usd
                        Logger.info(f"  🔒 Locked {locked_usd:.2f} USD from ETH/USD buy: {vol:.6f} ETH @ ${price:.2f} (pair: {pair_str})")
                    elif 'XRP' in pair_str_upper and ('BTC' in pair_str_upper or 'XBT' in pair_str_upper):
                        # XRP/BTC buy order: locks BTC (Kraken returns XRPXBT, not XRPBTC)
                        price = float(desc.get('price', 0))
                        locked_btc = vol * price
                        locked_funds['XXBT'] = locked_funds.get('XXBT', 0) + locked_btc
                        Logger.info(f"  🔒 Locked {locked_btc:.8f} BTC from XRP/BTC buy: {vol:.2f} XRP @ {price:.8f} BTC (pair: {pair_str})")
                elif order_type == 'sell':
                    # Sell orders lock the quote currency (ETH for ETH/USD, XRP for XRP/BTC)
                    if 'ETH' in pair_str_upper and 'USD' in pair_str_upper:
                        # ETH/USD sell order: locks ETH
                        locked_funds['XETH'] = locked_funds.get('XETH', 0) + vol
                        Logger.info(f"  🔒 Locked {vol:.6f} ETH from ETH/USD sell (pair: {pair_str})")
                    elif 'XRP' in pair_str_upper and ('BTC' in pair_str_upper or 'XBT' in pair_str_upper):
                        # XRP/BTC sell order: locks XRP (Kraken returns XRPXBT, not XRPBTC)
                        locked_funds['XXRP'] = locked_funds.get('XXRP', 0) + vol
                        Logger.info(f"  🔒 Locked {vol:.2f} XRP from XRP/BTC sell (pair: {pair_str})")
            
            # Calculate and store available balances (total - locked)
            self.available_balances = {}
            for asset, total_balance in self.balances.items():
                total = float(total_balance)
                locked = locked_funds.get(asset, 0)
                available = total - locked
                self.available_balances[asset] = available
                if locked > 0:
                    Logger.info(f"  {asset}: {total:.6f} total, {locked:.6f} locked, {available:.6f} available")
                else:
                    Logger.info(f"  {asset}: {total:.6f} total, {available:.6f} available (no locked funds)")
            
            # Debug: Verify available_balances was set correctly
            if hasattr(self, 'available_balances') and self.available_balances:
                Logger.info(f"✅ Available balances calculated: {len(self.available_balances)} assets")
                for asset, avail in self.available_balances.items():
                    total = float(self.balances.get(asset, 0))
                    if abs(avail - total) > 0.000001:  # Only log if there's a difference
                        Logger.info(f"   {asset}: {avail:.6f} available (of {total:.6f} total)")
            
            return True
            
        except Exception as e:
            Logger.error(f"❌ Error getting balance: {str(e)}")
            import traceback
            traceback.print_exc()
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
            
            # Also fetch BTC/USD for XRP/BTC order value conversion
            if "XRP/BTC" in self.enabled_pairs:
                kraken_pairs.append("XXBTZUSD")  # BTC/USD pair
                pair_mapping["XXBTZUSD"] = "BTC/USD"
            
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
                    
                    # Debug: log what pairs we received
                    Logger.info(f"📊 Received ticker data for {len(ticker_data)} pairs: {list(ticker_data.keys())}")
                    
                    for kraken_pair, data in ticker_data.items():
                        if 'c' in data:  # 'c' is the last trade price
                            price = float(data['c'][0])
                            display_pair = pair_mapping.get(kraken_pair, kraken_pair)
                            if display_pair == "BTC/USD":
                                # Store BTC/USD price for order value conversion
                                self.btc_usd_price = price
                                Logger.success(f"✅ {display_pair}: {price:.2f} (for XRP/BTC order value conversion)")
                            else:
                                self.current_prices[display_pair] = price
                                Logger.success(f"✅ {display_pair}: {price:.7f}")
                    
                    # If BTC/USD wasn't fetched but we need it, estimate from ETH/USD
                    if "XRP/BTC" in self.enabled_pairs and self.btc_usd_price is None:
                        Logger.warning(f"⚠️ BTC/USD price NOT in ticker response (received pairs: {list(ticker_data.keys())})")
                        if "ETH/USD" in self.current_prices:
                            eth_price = self.current_prices["ETH/USD"]
                            # Rough estimate: BTC is typically 15-20x ETH price
                            self.btc_usd_price = eth_price * 18
                            Logger.warning(f"⚠️ Estimating BTC/USD from ETH/USD: ${self.btc_usd_price:.2f} (ETH: ${eth_price:.2f} × 18)")
                        else:
                            self.btc_usd_price = 90000.0  # Conservative fallback
                            Logger.warning(f"⚠️ BTC/USD price not available, using fallback: ${self.btc_usd_price:.2f}")
                    elif "XRP/BTC" in self.enabled_pairs:
                        Logger.info(f"✅ BTC/USD price successfully fetched: ${self.btc_usd_price:.2f} (will be used for XRP/BTC order value conversion)")
                    
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
            elif pair == "XRP/BTC":
                # For XRP/BTC, order_value is in BTC, need to convert to USD
                order_value_btc = rounded_volume * rounded_price  # BTC value
                
                # Get BTC/USD price for conversion
                btc_usd = self.btc_usd_price
                if btc_usd is None:
                    # Fallback: estimate from ETH/USD if available, or use default
                    if "ETH/USD" in self.current_prices:
                        # Rough estimate: BTC is typically 15-20x ETH price
                        eth_price = self.current_prices.get("ETH/USD", 3000)
                        btc_usd = eth_price * 18  # Conservative estimate
                        Logger.warning(f"⚠️ BTC/USD price not available, estimating from ETH: ${btc_usd:.2f}")
                    else:
                        btc_usd = 90000.0  # Conservative fallback estimate
                        Logger.warning(f"⚠️ BTC/USD price not available, using fallback: ${btc_usd:.2f}")
                
                order_value_usd = order_value_btc * btc_usd
                
                # Debug logging to help diagnose issues
                Logger.info(f"🔍 {pair} order value calculation: {rounded_volume} XRP × {rounded_price:.8f} BTC = {order_value_btc:.8f} BTC × ${btc_usd:.2f}/BTC = ${order_value_usd:.2f} USD")
                
                if order_value_usd < min_order_size:
                    Logger.warning(f"⚠️ Order value too small for {pair}: ${order_value_usd:.2f} < ${min_order_size:.2f} (BTC value: {order_value_btc:.8f} BTC @ ${btc_usd:.2f}/BTC)")
                    Logger.warning(f"   Volume: {rounded_volume} XRP, Price: {rounded_price:.8f} BTC/XRP")
                    return None
                else:
                    Logger.info(f"✅ Order value for {pair}: ${order_value_usd:.2f} USD (BTC: {order_value_btc:.8f} @ ${btc_usd:.2f}/BTC) - PASSES minimum ${min_order_size:.2f}")
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
        """Calculate order volume based on available balance (accounting for locked funds) and number of orders"""
        try:
            base_asset = config.get('base_asset')
            quote_asset = config.get('quote_asset')
            
            # Get available balances (total - locked funds in open orders)
            # Use available_balances if calculated, otherwise fall back to total balances
            if hasattr(self, 'available_balances') and self.available_balances:
                base_balance = float(self.available_balances.get(base_asset, self.balances.get(base_asset, 0)))
                quote_balance = float(self.available_balances.get(quote_asset, self.balances.get(quote_asset, 0)))
                # Debug logging to verify we're using available balances
                total_base = float(self.balances.get(base_asset, 0))
                total_quote = float(self.balances.get(quote_asset, 0))
                Logger.info(f"🔍 {pair} {side}: Using AVAILABLE balances - {base_asset}: {base_balance:.6f} (total: {total_base:.6f}), {quote_asset}: {quote_balance:.6f} (total: {total_quote:.6f})")
            else:
                # Fallback to total balances if available_balances not calculated yet
                base_balance = float(self.balances.get(base_asset, 0))
                quote_balance = float(self.balances.get(quote_asset, 0))
                Logger.warning(f"⚠️ {pair} {side}: Using TOTAL balances (available_balances not set) - {base_asset}: {base_balance:.6f}, {quote_asset}: {quote_balance:.6f}")
            
            if pair == "ETH/USD":
                # For ETH/USD: base is ZUSD, quote is XETH
                min_order_eth = config.get('min_order_size', 0.005)
                min_order_usd = current_price * min_order_eth
                
                if side == 'buy':
                    # Buy orders: need USD, buying ETH
                    available_usd = base_balance * 0.95  # Use 95% of USD
                    if available_usd < min_order_usd:  # Check if we can afford at least one order
                        Logger.warning(f"⚠️ Insufficient USD for buy orders: ${available_usd:.2f} < ${min_order_usd:.2f} minimum")
                        return None
                    # Distribute USD across buy orders
                    usd_per_order = available_usd / orders_count
                    volume = usd_per_order / current_price  # ETH volume
                    # Verify volume meets minimum
                    if volume < min_order_eth:
                        Logger.warning(f"⚠️ Calculated buy volume {volume:.6f} ETH < {min_order_eth} minimum")
                        return None
                    Logger.info(f"📊 Calculated buy volume for {pair}: {volume:.6f} ETH (${usd_per_order:.2f} per order, {orders_count} orders)")
                else:  # sell
                    # Sell orders: need ETH, selling for USD
                    # quote_balance should already be available balance (locked funds subtracted)
                    available_eth = quote_balance * 0.95  # Use 95% of available ETH
                    total_eth = float(self.balances.get(quote_asset, 0))
                    if available_eth < min_order_eth:  # Check if we can afford at least one order
                        Logger.warning(f"⚠️ Insufficient ETH balance for sell order: {available_eth:.6f} < {min_order_eth}")
                        Logger.warning(f"   Total ETH: {total_eth:.6f}, Available (unlocked): {quote_balance:.6f}, After 95%: {available_eth:.6f}")
                        return None
                    # Distribute ETH across sell orders
                    volume = available_eth / orders_count
                    # Verify volume meets minimum
                    if volume < min_order_eth:
                        Logger.warning(f"⚠️ Calculated sell volume {volume:.6f} ETH < {min_order_eth} minimum (try fewer orders)")
                        return None
                    Logger.info(f"📊 Calculated sell volume for {pair}: {volume:.6f} ETH (from {available_eth:.6f} available after 95%, {quote_balance:.6f} total available, {total_eth:.6f} total ETH, {orders_count} orders)")
            else:
                # For XRP/BTC: base is XXBT, quote is XXRP
                # Calculate minimum XRP per order based on $10 USD minimum
                min_order_usd = config.get('min_order_size', 10.0)  # $10 USD minimum
                btc_usd = self.btc_usd_price if self.btc_usd_price else 90000.0
                xrp_price_usd = current_price * btc_usd  # XRP price in USD
                min_xrp_per_order = min_order_usd / xrp_price_usd if xrp_price_usd > 0 else 5.0
                min_btc_per_order = min_order_usd / btc_usd if btc_usd > 0 else 0.0001
                
                if side == 'buy':
                    # Buy orders: need BTC, buying XRP
                    available_btc = base_balance * 0.95
                    if available_btc < min_btc_per_order:  # Check if we can afford at least one order
                        Logger.warning(f"⚠️ Insufficient BTC for buy orders: {available_btc:.8f} < {min_btc_per_order:.8f} minimum")
                        return None
                    btc_per_order = available_btc / orders_count
                    volume = btc_per_order / current_price  # XRP volume
                    # Verify volume meets minimum
                    if volume < min_xrp_per_order:
                        Logger.warning(f"⚠️ Calculated buy volume {volume:.2f} XRP < {min_xrp_per_order:.2f} minimum")
                        return None
                    Logger.info(f"📊 Calculated buy volume for {pair}: {volume:.2f} XRP ({btc_per_order:.8f} BTC per order, {orders_count} orders)")
                else:  # sell
                    # Sell orders: need XRP, selling for BTC
                    available_xrp = quote_balance * 0.95
                    if available_xrp < min_xrp_per_order:  # Check if we can afford at least one order
                        Logger.warning(f"⚠️ Insufficient XRP balance for sell order: {available_xrp:.2f} < {min_xrp_per_order:.2f} XRP (${min_order_usd} min)")
                        return None
                    volume = available_xrp / orders_count
                    # Verify volume meets minimum
                    if volume < min_xrp_per_order:
                        Logger.warning(f"⚠️ Calculated sell volume {volume:.2f} XRP < {min_xrp_per_order:.2f} minimum (try fewer orders)")
                        return None
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
                # Use available balances (accounting for locked funds) if calculated
                if hasattr(self, 'available_balances') and self.available_balances:
                    base_balance = float(self.available_balances.get(base_asset, self.balances.get(base_asset, 0)))  # USD
                    quote_balance = float(self.available_balances.get(quote_asset, self.balances.get(quote_asset, 0)))  # ETH
                    Logger.info(f"📊 {pair}: Using available balances - USD: {base_balance:.2f}, ETH: {quote_balance:.6f} (locked funds already subtracted)")
                else:
                    base_balance = float(self.balances.get(base_asset, 0))  # USD
                    quote_balance = float(self.balances.get(quote_asset, 0))  # ETH
                    Logger.warning(f"⚠️ {pair}: Using total balances (available_balances not calculated yet) - USD: {base_balance:.2f}, ETH: {quote_balance:.6f}")
                
                # Calculate orders per side (use 95% of available to leave buffer)
                usd_available = base_balance * 0.95
                eth_available = quote_balance * 0.95
                
                # Get minimum order size from config
                min_order_eth = config.get('min_order_size', 0.005)
                min_order_value_usd = current_price * min_order_eth
                
                # Buy orders: calculate how many we can ACTUALLY afford (not forcing minimum)
                max_affordable_buys = int(usd_available / min_order_value_usd) if min_order_value_usd > 0 else 0
                buy_orders_count = min(max_orders_per_side, max_affordable_buys)
                if buy_orders_count < min_orders_per_side and buy_orders_count > 0:
                    Logger.warning(f"⚠️ {pair}: Can only afford {buy_orders_count} buy orders (desired min: {min_orders_per_side}, USD available: ${usd_available:.2f})")
                elif buy_orders_count == 0 and usd_available > 0:
                    Logger.warning(f"⚠️ {pair}: Cannot afford any buy orders - need ${min_order_value_usd:.2f} per order, have ${usd_available:.2f}")
                
                # Sell orders: calculate how many we can ACTUALLY afford (not forcing minimum)
                max_affordable_sells = int(eth_available / min_order_eth) if min_order_eth > 0 else 0
                sell_orders_count = min(max_orders_per_side, max_affordable_sells)
                if sell_orders_count < min_orders_per_side and sell_orders_count > 0:
                    Logger.warning(f"⚠️ {pair}: Can only afford {sell_orders_count} sell orders (desired min: {min_orders_per_side}, ETH available: {eth_available:.6f})")
            else:
                # XRP/BTC logic - use available balances (accounting for locked funds) if calculated
                if hasattr(self, 'available_balances') and self.available_balances:
                    base_balance = float(self.available_balances.get(base_asset, self.balances.get(base_asset, 0)))  # BTC
                    quote_balance = float(self.available_balances.get(quote_asset, self.balances.get(quote_asset, 0)))  # XRP
                    Logger.info(f"📊 {pair}: Using available balances - BTC: {base_balance:.8f}, XRP: {quote_balance:.2f}")
                else:
                    base_balance = float(self.balances.get(base_asset, 0))  # BTC
                    quote_balance = float(self.balances.get(quote_asset, 0))  # XRP
                    Logger.warning(f"⚠️ {pair}: Using total balances - BTC: {base_balance:.8f}, XRP: {quote_balance:.2f}")
                
                # Calculate minimum XRP per order based on $10 USD minimum
                min_order_usd = config.get('min_order_size', 10.0)  # $10 USD minimum
                btc_usd = self.btc_usd_price if self.btc_usd_price else 90000.0
                xrp_price_usd = current_price * btc_usd  # XRP price in USD
                min_xrp_per_order = min_order_usd / xrp_price_usd if xrp_price_usd > 0 else 10.0
                min_btc_per_order = min_order_usd / btc_usd if btc_usd > 0 else 0.0001
                
                Logger.info(f"📊 {pair}: Min order: ${min_order_usd} = {min_xrp_per_order:.2f} XRP or {min_btc_per_order:.8f} BTC (XRP=${xrp_price_usd:.4f})")
                
                # Buy orders: calculate how many we can ACTUALLY afford
                btc_available = base_balance * 0.95
                max_affordable_buys = int(btc_available / min_btc_per_order) if min_btc_per_order > 0 else 0
                buy_orders_count = min(max_orders_per_side, max_affordable_buys)
                if buy_orders_count < min_orders_per_side and buy_orders_count > 0:
                    Logger.warning(f"⚠️ {pair}: Can only afford {buy_orders_count} buy orders (desired min: {min_orders_per_side})")
                elif buy_orders_count == 0 and btc_available > 0:
                    Logger.warning(f"⚠️ {pair}: Cannot afford any buy orders - need {min_btc_per_order:.8f} BTC, have {btc_available:.8f} BTC")
                
                # Sell orders: calculate how many we can ACTUALLY afford
                xrp_available = quote_balance * 0.95
                max_affordable_sells = int(xrp_available / min_xrp_per_order) if min_xrp_per_order > 0 else 0
                sell_orders_count = min(max_orders_per_side, max_affordable_sells)
                if sell_orders_count < min_orders_per_side and sell_orders_count > 0:
                    Logger.warning(f"⚠️ {pair}: Can only afford {sell_orders_count} sell orders (desired min: {min_orders_per_side})")
            
            orders_placed = 0
            buy_orders_placed = 0
            sell_orders_placed = 0
            
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
                            buy_orders_placed += 1
                        
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
                            sell_orders_placed += 1
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.1)
            
            Logger.success(f"✅ Created {orders_placed} grid orders for {pair}")
            
            # Track grid center price for dynamic repositioning
            self.grid_center_prices[pair] = current_price
            
            # Track expected order counts based on ACTUAL orders placed, not intended counts
            # CRITICAL: Use buy_orders_placed and sell_orders_placed, NOT buy_orders_count and sell_orders_count
            # This ensures we only expect orders that were actually successfully placed
            # FORCE update expected counts - this MUST happen after grid creation
            self.expected_order_counts[pair] = {
                'buy': buy_orders_placed,
                'sell': sell_orders_placed
            }
            
            # CRITICAL LOG: This must appear in logs to verify expected counts are set correctly
            Logger.error(f"🔴 {pair}: ✅✅✅ FORCED expected counts update: {buy_orders_placed} buy, {sell_orders_placed} sell (intended was: {buy_orders_count} buy, {sell_orders_count} sell) ✅✅✅")
            Logger.warning(f"⚠️ {pair}: Expected counts verification - buy_orders_placed={buy_orders_placed}, sell_orders_placed={sell_orders_placed}, stored={self.expected_order_counts[pair]}")
            
            # Verify the values were actually stored
            stored = self.expected_order_counts.get(pair, {})
            if stored.get('buy') != buy_orders_placed or stored.get('sell') != sell_orders_placed:
                Logger.error(f"❌ {pair}: CRITICAL BUG - Expected counts mismatch! Placed: {buy_orders_placed}/{sell_orders_placed}, Stored: {stored.get('buy')}/{stored.get('sell')}")
                # Force correct it
                self.expected_order_counts[pair] = {
                    'buy': buy_orders_placed,
                    'sell': sell_orders_placed
                }
                Logger.error(f"🔴 {pair}: FORCED CORRECTION - Reset expected counts to {buy_orders_placed} buy, {sell_orders_placed} sell")
            
            # Save expected counts to file (survives restarts)
            self._save_expected_counts()
            
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

    def match_order_to_pair(self, order_pair):
        """Match an order's pair string to a configured trading pair"""
        if not order_pair:
            return None
        
        order_pair_upper = order_pair.upper().strip()
        
        # Known pair format mappings (Kraken returns different formats than we send)
        # When we place orders with XETHZUSD, Kraken returns them as ETHUSD
        pair_mappings = {
            'ETHUSD': 'XETHZUSD',
            'ETH/USD': 'XETHZUSD',
            'XETHUSD': 'XETHZUSD',
            'ETHZUSD': 'XETHZUSD',
            'XRPBTC': 'XXRPXXBT',
            'XRP/BTC': 'XXRPXXBT',
            'XRPXXBT': 'XXRPXXBT',
            'XXRPXBT': 'XXRPXXBT',
            'XRPXBT': 'XXRPXXBT',
        }
        
        # First, normalize the order_pair to the kraken_pair format we use
        normalized_pair = pair_mappings.get(order_pair_upper, order_pair_upper)
        
        # Now match against configured pairs
        for pair, config in self.enabled_pairs.items():
            kraken_pair = config.get('kraken_pair')
            if not kraken_pair:
                continue
            
            # Try exact match (case-insensitive)
            if kraken_pair.upper() == normalized_pair.upper():
                Logger.info(f"📊 ✅ Matched '{order_pair}' -> '{pair}' (normalized: '{normalized_pair}')")
                return pair
            
            # Also try direct match with original order_pair
            if kraken_pair.upper() == order_pair_upper:
                Logger.info(f"📊 ✅ Matched '{order_pair}' -> '{pair}' (direct)")
                return pair
        
        # If no match, try normalization (remove X/Z characters)
        normalized_order = ''.join(c for c in order_pair_upper if c not in 'XZ')
        for pair, config in self.enabled_pairs.items():
            kraken_pair = config.get('kraken_pair')
            if not kraken_pair:
                continue
            normalized_kraken = ''.join(c for c in kraken_pair.upper() if c not in 'XZ')
            if normalized_kraken == normalized_order:
                Logger.info(f"📊 ✅ Matched '{order_pair}' -> '{pair}' via normalization")
                return pair
        
        Logger.warning(f"⚠️ Could not match '{order_pair}' to any configured pair")
        return None
    
    async def monitor_and_replace_orders(self):
        """Monitor open orders and replace filled ones"""
        try:
            open_orders = await self.get_open_orders()
            
            # Track orders by pair
            orders_by_pair = {}
            unmatched_orders = []
            for order_id, order_data in open_orders.items():
                # Find which pair this order belongs to
                desc = order_data.get('descr', {})
                order_pair = desc.get('pair', '')
                
                # Debug: log what we're trying to match
                if not order_pair:
                    Logger.warning(f"⚠️ Order {order_id} has no pair in desc: {desc}")
                    continue
                
                try:
                    pair_name = self.match_order_to_pair(order_pair)
                except Exception as e:
                    Logger.error(f"❌ Exception in match_order_to_pair for '{order_pair}': {str(e)}")
                    import traceback
                    traceback.print_exc()
                    pair_name = None
                
                # If still no match, log it for debugging
                if not pair_name:
                    unmatched_orders.append({
                        'order_id': order_id,
                        'order_pair': order_pair,
                        'desc': desc
                    })
                else:
                    if pair_name not in orders_by_pair:
                        orders_by_pair[pair_name] = {'buy': 0, 'sell': 0}
                    
                    order_type = desc.get('type', '')
                    if order_type == 'buy':
                        orders_by_pair[pair_name]['buy'] += 1
                    elif order_type == 'sell':
                        orders_by_pair[pair_name]['sell'] += 1
            
            # Log unmatched orders for debugging
            if unmatched_orders:
                Logger.warning(f"⚠️ Found {len(unmatched_orders)} orders that couldn't be matched to configured pairs:")
                for unmatched in unmatched_orders[:5]:  # Show first 5
                    Logger.warning(f"   Order {unmatched['order_id']}: pair='{unmatched['order_pair']}', desc={unmatched['desc']}")
                if len(unmatched_orders) > 5:
                    Logger.warning(f"   ... and {len(unmatched_orders) - 5} more unmatched orders")
            
            # Log matched orders for debugging
            if orders_by_pair:
                Logger.info(f"📊 Matched orders: {orders_by_pair}")
            else:
                Logger.warning(f"⚠️ No orders matched to configured pairs! Total open orders: {len(open_orders)}")
                # Debug: show what pairs we're looking for
                Logger.info(f"   Looking for pairs: {[config.get('kraken_pair') for config in self.enabled_pairs.values()]}")
                if open_orders:
                    # Show first order's pair format
                    first_order = list(open_orders.values())[0]
                    first_desc = first_order.get('descr', {})
                    first_pair = first_desc.get('pair', 'N/A')
                    Logger.info(f"   First order pair format: '{first_pair}'")
            
            # Initialize expected counts from current orders if not set (handles bot restart)
            # IMPORTANT: We only initialize if not set - we don't update them here because
            # that would mask missing orders. Expected counts should only decrease when orders fill.
            # CRITICAL: Only initialize if we actually matched orders - if no orders matched,
            # don't set expected counts to 0 (that would cause false "all orders filled" detection)
            for pair, config in self.enabled_pairs.items():
                pair_orders = orders_by_pair.get(pair, {'buy': 0, 'sell': 0})
                current_buy = pair_orders['buy']
                current_sell = pair_orders['sell']
                
                # Only initialize if we don't have expected counts yet AND we found some orders
                # If no orders matched, skip initialization (orders might be there but unmatched)
                # CRITICAL: Never override expected counts that were set during grid creation
                # Grid creation sets them from actual placed orders, which is the source of truth
                if pair not in self.expected_order_counts:
                    # Only initialize if we actually found orders for this pair
                    # OR if we have no unmatched orders at all (meaning matching worked)
                    # CRITICAL: Only initialize from ACTUAL current orders, never from intended counts
                    if current_buy > 0 or current_sell > 0 or not unmatched_orders:
                        self.expected_order_counts[pair] = {
                            'buy': current_buy,  # Use ACTUAL current orders, not intended counts
                            'sell': current_sell  # Use ACTUAL current orders, not intended counts
                        }
                        Logger.info(f"📊 {pair}: Initialized expected counts from ACTUAL current orders: {current_buy} buy, {current_sell} sell")
                    else:
                        # Orders exist but couldn't be matched - don't initialize to 0
                        Logger.warning(f"⚠️ {pair}: Skipping expected count initialization - orders exist but couldn't be matched (matching issue)")
                else:
                    # Expected counts already exist (loaded from file or set during grid creation)
                    expected = self.expected_order_counts[pair]
                    expected_buy = expected.get('buy', 0)
                    expected_sell = expected.get('sell', 0)
                    
                    # Log the comparison - this is how we detect fills!
                    if expected_buy != current_buy or expected_sell != current_sell:
                        Logger.info(f"📊 {pair}: Current orders: {current_buy} buy, {current_sell} sell | Expected: {expected_buy} buy, {expected_sell} sell")
                    
                    # IMPORTANT: expected > current means orders FILLED - this is NORMAL and should trigger replacement
                    # DO NOT reset expected to current here - that would prevent fill detection!
                    
                    # Only reset expected if expected > current AND no orders exist at all (indicates stale data)
                    if expected_sell > current_sell:
                        Logger.info(f"📊 {pair}: Expected {expected_sell} sells but have {current_sell} - {expected_sell - current_sell} may have filled!")
                    if expected_buy > current_buy:
                        Logger.info(f"📊 {pair}: Expected {expected_buy} buys but have {current_buy} - {expected_buy - current_buy} may have filled!")
                    
                    # Only reset if expected is impossibly high (more than max configured)
                    max_orders = config.get('max_orders_per_side', 20)
                    if expected_buy > max_orders:
                        Logger.warning(f"⚠️ {pair}: Expected buy count ({expected_buy}) > max ({max_orders}), resetting to current ({current_buy})")
                        self.expected_order_counts[pair]['buy'] = current_buy
                    if expected_sell > max_orders:
                        Logger.warning(f"⚠️ {pair}: Expected sell count ({expected_sell}) > max ({max_orders}), resetting to current ({current_sell})")
                        self.expected_order_counts[pair]['sell'] = current_sell
            
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
                        # Refresh order counts to get actual new counts after placing orders
                        await asyncio.sleep(0.5)  # Small delay for orders to register
                        refreshed_orders = await self.get_open_orders()
                        refreshed_pair_orders = {'buy': 0, 'sell': 0}
                        for order_id, order_data in refreshed_orders.items():
                            desc = order_data.get('descr', {})
                            order_pair = desc.get('pair', '')
                            matched_pair = self.match_order_to_pair(order_pair)
                            if matched_pair == pair:
                                order_type = desc.get('type', '')
                                if order_type == 'buy':
                                    refreshed_pair_orders['buy'] += 1
                                elif order_type == 'sell':
                                    refreshed_pair_orders['sell'] += 1
                        
                        # Update expected counts based on actual refreshed counts
                        self.expected_order_counts[pair] = {
                            'buy': refreshed_pair_orders['buy'],
                            'sell': refreshed_pair_orders['sell']
                        }
                        Logger.success(f"✅ Placed {orders_placed} new buy order(s) after sell fill(s). Updated expected: {refreshed_pair_orders['buy']} buy, {refreshed_pair_orders['sell']} sell")
                    else:
                        Logger.warning(f"⚠️ Failed to place replacement buy orders for {pair}")
                        # Still update expected sell count to match actual (to prevent false positives)
                        self.expected_order_counts[pair] = {'buy': expected_buy, 'sell': sell_count}
                
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
                        # Refresh order counts to get actual new counts after placing orders
                        await asyncio.sleep(0.5)  # Small delay for orders to register
                        refreshed_orders = await self.get_open_orders()
                        refreshed_pair_orders = {'buy': 0, 'sell': 0}
                        for order_id, order_data in refreshed_orders.items():
                            desc = order_data.get('descr', {})
                            order_pair = desc.get('pair', '')
                            matched_pair = self.match_order_to_pair(order_pair)
                            if matched_pair == pair:
                                order_type = desc.get('type', '')
                                if order_type == 'buy':
                                    refreshed_pair_orders['buy'] += 1
                                elif order_type == 'sell':
                                    refreshed_pair_orders['sell'] += 1
                        
                        # Update expected counts based on actual refreshed counts
                        self.expected_order_counts[pair] = {
                            'buy': refreshed_pair_orders['buy'],
                            'sell': refreshed_pair_orders['sell']
                        }
                        Logger.success(f"✅ Placed {orders_placed} new sell order(s) after buy fill(s). Updated expected: {refreshed_pair_orders['buy']} buy, {refreshed_pair_orders['sell']} sell")
                    else:
                        Logger.warning(f"⚠️ Failed to place replacement sell orders for {pair}")
                        # Still update expected buy count to match actual (to prevent false positives)
                        self.expected_order_counts[pair] = {'buy': buy_count, 'sell': expected_sell}
                
                # Also check if we need to add orders to maintain minimum grid
                # Check if we need to add buy orders
                if buy_count < min_orders_per_side:
                    # Calculate how many orders we can actually afford
                    base_asset = config.get('base_asset')
                    if hasattr(self, 'available_balances') and self.available_balances:
                        base_balance = float(self.available_balances.get(base_asset, self.balances.get(base_asset, 0)))
                    else:
                        base_balance = float(self.balances.get(base_asset, 0))
                    
                    available_balance = base_balance * 0.95
                    if pair == "ETH/USD":
                        # For ETH/USD: calculate based on min ETH order size
                        min_order_eth = config.get('min_order_size', 0.005)
                        min_order_usd = current_price * min_order_eth
                        max_affordable = int(available_balance / min_order_usd) if min_order_usd > 0 else 0
                    else:
                        # For XRP/BTC: calculate based on $10 USD minimum
                        min_order_usd = config.get('min_order_size', 10.0)
                        btc_usd = self.btc_usd_price if self.btc_usd_price else 90000.0
                        min_btc_per_order = min_order_usd / btc_usd if btc_usd > 0 else 0.0001
                        max_affordable = int(available_balance / min_btc_per_order) if min_btc_per_order > 0 else 0
                    
                    max_affordable = min(max_orders_per_side, max_affordable)
                    needed = max(0, min(max_affordable - buy_count, max_orders_per_side - buy_count))
                    
                    if needed > 0:
                        Logger.info(f"📊 {pair}: Need {needed} more buy orders (current: {buy_count}, can afford up to {max_affordable} total)")
                        
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
                    # Use available_balances if calculated, otherwise fall back to total
                    base_asset = config.get('base_asset')
                    if hasattr(self, 'available_balances') and self.available_balances:
                        base_balance = float(self.available_balances.get(base_asset, self.balances.get(base_asset, 0)))
                    else:
                        base_balance = float(self.balances.get(base_asset, 0))
                    
                    available_balance = base_balance * 0.95
                    
                    # Calculate minimum order value based on pair
                    if pair == "ETH/USD":
                        min_order_eth = config.get('min_order_size', 0.005)
                        min_order_value = current_price * min_order_eth
                    else:  # XRP/BTC
                        min_order_usd = config.get('min_order_size', 10.0)
                        btc_usd = self.btc_usd_price if self.btc_usd_price else 90000.0
                        min_order_value = min_order_usd / btc_usd  # BTC needed per order
                    
                    # Calculate how many more we can afford
                    max_affordable = int(available_balance / min_order_value) if min_order_value > 0 else 0
                    can_add = min(max_orders_per_side - buy_count, max(0, max_affordable - buy_count))
                    
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
                    # Calculate how many orders we can actually place based on available balance
                    quote_asset = config.get('quote_asset')
                    if hasattr(self, 'available_balances') and self.available_balances:
                        quote_balance = float(self.available_balances.get(quote_asset, self.balances.get(quote_asset, 0)))
                    else:
                        quote_balance = float(self.balances.get(quote_asset, 0))
                    
                    # Calculate maximum total orders we can place based on config minimums
                    available_balance = quote_balance * 0.95  # Use 95% of available
                    if pair == "ETH/USD":
                        # For ETH/USD: use config min_order_size (default 0.005 ETH)
                        min_order_size = config.get('min_order_size', 0.005)
                        max_possible_total = int(available_balance / min_order_size) if min_order_size > 0 else 0
                    else:
                        # For XRP/BTC: calculate minimum XRP based on $10 USD minimum
                        min_order_usd = config.get('min_order_size', 10.0)
                        btc_usd = self.btc_usd_price if self.btc_usd_price else 90000.0
                        xrp_price_usd = current_price * btc_usd
                        min_xrp_per_order = min_order_usd / xrp_price_usd if xrp_price_usd > 0 else 5.0
                        max_possible_total = int(available_balance / min_xrp_per_order) if min_xrp_per_order > 0 else 0
                    
                    # Cap at max_orders_per_side
                    max_possible_total = min(max_orders_per_side, max_possible_total)
                    
                    # Calculate how many NEW orders to place
                    needed = max(0, min(max_possible_total - sell_count, max_orders_per_side - sell_count))
                    
                    if needed > 0:
                        Logger.info(f"📊 {pair}: Need {needed} more sell orders (current: {sell_count}, can place up to {max_possible_total} total)")
                        
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
                    # Use available_balances if calculated, otherwise fall back to total
                    quote_asset = config.get('quote_asset')
                    if hasattr(self, 'available_balances') and self.available_balances:
                        quote_balance = float(self.available_balances.get(quote_asset, self.balances.get(quote_asset, 0)))
                    else:
                        quote_balance = float(self.balances.get(quote_asset, 0))
                    
                    available_balance = quote_balance * 0.95
                    
                    # Calculate minimum order size based on pair
                    if pair == "ETH/USD":
                        min_order_size = config.get('min_order_size', 0.005)  # ETH per order
                    else:  # XRP/BTC
                        # Calculate minimum XRP based on $10 USD minimum
                        min_order_usd = config.get('min_order_size', 10.0)
                        btc_usd = self.btc_usd_price if self.btc_usd_price else 90000.0
                        xrp_price_usd = current_price * btc_usd
                        min_order_size = min_order_usd / xrp_price_usd if xrp_price_usd > 0 else 5.0  # XRP per order
                    
                    # Calculate how many more we can afford
                    max_affordable = int(available_balance / min_order_size) if min_order_size > 0 else 0
                    can_add = min(max_orders_per_side - sell_count, max(0, max_affordable - sell_count))
                    
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
            
            # Save expected counts to file (survives restarts)
            self._save_expected_counts()
            
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
                # CRITICAL: Refresh balances after canceling orders to get correct available amounts
                await asyncio.sleep(1)  # Small delay for Kraken to process cancellations
                await self.get_account_balance()
            
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
