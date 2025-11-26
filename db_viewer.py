#!/usr/bin/env python3
"""
Simple GridBot Database Viewer
=============================

Quick and easy way to inspect the GridBot SQLite database.
Perfect for checking if the bot is working and recording trades.

Usage:
    python db_viewer.py [command]

Commands:
    status    - Show database status and quick stats (default)
    orders    - Show recent orders
    trades    - Show recent executions/trades
    tables    - Show all database tables and row counts
    schema    - Show database schema
"""

import sqlite3
import sys
import os
from datetime import datetime

DATABASE_FILE = os.getenv('DATABASE_FILE', "gridbot_pnl.db")

def check_database():
    """Check if database exists"""
    if not os.path.exists(DATABASE_FILE):
        print(f"❌ Database file '{DATABASE_FILE}' not found!")
        print("   Make sure you've run the GridBot first to create the database.")
        return False
    return True

def get_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_FILE)

def show_status():
    """Show database status and quick stats"""
    if not check_database():
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print("🚀 GRIDBOT DATABASE STATUS")
    print("=" * 50)
    
    # Database info
    file_size = os.path.getsize(DATABASE_FILE) / 1024  # KB
    print(f"Database file: {DATABASE_FILE}")
    print(f"File size: {file_size:.1f} KB")
    print(f"Last modified: {datetime.fromtimestamp(os.path.getmtime(DATABASE_FILE)).strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Table counts
    tables = ['orders', 'executions', 'portfolio_snapshots', 'pnl_summary']
    print("📊 TABLE SUMMARY:")
    total_records = 0
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_records += count
            print(f"   {table:20} {count:8,} records")
        except sqlite3.OperationalError:
            print(f"   {table:20} {'N/A':>8} (table not found)")
    
    print(f"   {'TOTAL':20} {total_records:8,} records")
    print()
    
    # Quick stats from executions
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(pnl_contribution) as total_pnl,
                AVG(pnl_contribution) as avg_pnl,
                MIN(timestamp) as first_trade,
                MAX(timestamp) as last_trade
            FROM executions
        """)
        
        result = cursor.fetchone()
        if result and result[0] > 0:
            total_trades, total_pnl, avg_pnl, first_trade, last_trade = result
            print("💰 TRADING SUMMARY:")
            print(f"   Total trades: {total_trades:,}")
            print(f"   Total PnL: ${total_pnl:.2f}")
            print(f"   Average PnL per trade: ${avg_pnl:.2f}")
            print(f"   First trade: {first_trade}")
            print(f"   Last trade: {last_trade}")
            
            # Calculate session duration
            if first_trade and last_trade:
                first = datetime.fromisoformat(first_trade)
                last = datetime.fromisoformat(last_trade)
                duration = last - first
                hours = duration.total_seconds() / 3600
                hourly_rate = total_pnl / hours if hours > 0 else 0
                print(f"   Session duration: {hours:.1f} hours")
                print(f"   Hourly PnL rate: ${hourly_rate:.2f}/hour")
        else:
            print("💰 TRADING SUMMARY:")
            print("   No trades recorded yet")
    except sqlite3.OperationalError:
        print("💰 TRADING SUMMARY: N/A (executions table not found)")
    
    print()
    
    # Trading pairs activity
    try:
        cursor.execute("""
            SELECT pair, COUNT(*) as trades, SUM(pnl_contribution) as pnl
            FROM executions 
            GROUP BY pair 
            ORDER BY trades DESC
        """)
        
        results = cursor.fetchall()
        if results:
            print("🎯 ACTIVITY BY PAIR:")
            for pair, trades, pnl in results:
                print(f"   {pair:12} {trades:8,} trades, ${pnl:8.2f} PnL")
    except sqlite3.OperationalError:
        pass
    
    conn.close()

def show_recent_orders(limit=10):
    """Show recent orders"""
    if not check_database():
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print(f"📋 RECENT ORDERS (Last {limit})")
    print("=" * 80)
    
    try:
        cursor.execute("""
            SELECT order_id, pair, side, volume, price, status, timestamp
            FROM orders 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        if results:
            print(f"{'Timestamp':19} {'Pair':10} {'Side':4} {'Volume':12} {'Price':12} {'Status':8} {'Order ID':15}")
            print("-" * 80)
            for row in results:
                order_id, pair, side, volume, price, status, timestamp = row
                timestamp = datetime.fromisoformat(timestamp).strftime('%m-%d %H:%M:%S')
                print(f"{timestamp:19} {pair:10} {side:4} {volume:12.6f} {price:12.6f} {status:8} {order_id[:15]:15}")
        else:
            print("No orders found")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    
    conn.close()

def show_recent_trades(limit=10):
    """Show recent trade executions"""
    if not check_database():
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print(f"💰 RECENT TRADES (Last {limit})")
    print("=" * 80)
    
    try:
        cursor.execute("""
            SELECT pair, side, volume, price, pnl_contribution, timestamp
            FROM executions 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        if results:
            print(f"{'Timestamp':19} {'Pair':10} {'Side':4} {'Volume':12} {'Price':12} {'PnL':10}")
            print("-" * 80)
            for row in results:
                pair, side, volume, price, pnl, timestamp = row
                timestamp = datetime.fromisoformat(timestamp).strftime('%m-%d %H:%M:%S')
                pnl_str = f"${pnl:.2f}"
                print(f"{timestamp:19} {pair:10} {side:4} {volume:12.6f} {price:12.6f} {pnl_str:>10}")
        else:
            print("No trades found")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    
    conn.close()

def show_tables():
    """Show all tables and their row counts"""
    if not check_database():
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print("📊 DATABASE TABLES")
    print("=" * 40)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    if tables:
        print(f"{'Table Name':25} {'Row Count':>10}")
        print("-" * 40)
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"{table_name:25} {count:10,}")
    else:
        print("No tables found")
    
    conn.close()

def show_schema():
    """Show database schema"""
    if not check_database():
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    print("🏗️  DATABASE SCHEMA")
    print("=" * 50)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        print(f"\n📋 {table_name.upper()} TABLE:")
        print("-" * 30)
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        for column in columns:
            cid, name, data_type, not_null, default_value, pk = column
            pk_str = " (PRIMARY KEY)" if pk else ""
            not_null_str = " NOT NULL" if not_null else ""
            default_str = f" DEFAULT {default_value}" if default_value else ""
            print(f"   {name:20} {data_type:15}{not_null_str}{default_str}{pk_str}")
    
    conn.close()

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = 'status'
    
    if command == 'status':
        show_status()
    elif command == 'orders':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_recent_orders(limit)
    elif command == 'trades':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_recent_trades(limit)
    elif command == 'tables':
        show_tables()
    elif command == 'schema':
        show_schema()
    else:
        print("Unknown command. Available commands:")
        print("  status  - Show database status and quick stats")
        print("  orders  - Show recent orders")
        print("  trades  - Show recent executions/trades")
        print("  tables  - Show all database tables")
        print("  schema  - Show database schema")

if __name__ == "__main__":
    main()
