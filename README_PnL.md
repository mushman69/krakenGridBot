# 🚀 Enhanced Kraken GridBot with PnL Tracking

## Overview

This enhanced version of your Kraken grid trading bot includes comprehensive PnL (Profit and Loss) tracking using SQLite database. It monitors all trades, calculates performance metrics, and provides detailed analytics.

## New Features

### 📊 SQLite PnL Tracking
- **Comprehensive Trade Recording**: Every order placement and execution is logged
- **Real-time PnL Calculation**: Automatic profit/loss calculation for each trade
- **Portfolio Snapshots**: Regular snapshots of your portfolio state
- **Performance Metrics**: Win rate, hourly PnL, total returns, and more

### 🔍 Enhanced Console Reporting
- **Live PnL Updates**: Quick stats displayed during monitoring
- **Periodic Reports**: Detailed reports every 5 minutes (configurable)
- **Session Summaries**: Complete session analytics on startup/shutdown

### 📈 Advanced Analytics
- **PnL Analyzer Tool**: Standalone script for detailed analysis
- **Data Export**: Export all data to CSV for external analysis
- **Performance Charts**: Visual charts of your trading performance
- **Historical Analysis**: Analyze performance over custom time periods

## Files Added/Modified

### Core Files
- `improved_gridbot_with_db.py` - Enhanced bot with PnL tracking
- `pnl_analyzer.py` - Standalone PnL analysis tool
- `requirements_pnl.txt` - Additional Python dependencies
- `gridbot_pnl.db` - SQLite database (created automatically)

### Database Schema
The bot creates 4 tables automatically:
1. **orders** - All placed orders
2. **executions** - Completed trades with PnL
3. **portfolio_snapshots** - Portfolio state over time
4. **pnl_summary** - Aggregated performance metrics

## Installation & Setup

### 1. Install Additional Dependencies
```bash
cd C:\Users\dougg\Documents\GridBot-Kraken\gridbot-clean\
pip install -r requirements_pnl.txt
```

### 2. Run the Enhanced Bot
```bash
python improved_gridbot_with_db.py
```

The bot will:
- Create the SQLite database automatically
- Start tracking all trades and orders
- Display PnL updates in the console
- Generate periodic reports

### 3. Monitor PnL (Live)
```bash
# View live updating PnL report
python pnl_analyzer.py --live

# View PnL for specific trading pair
python pnl_analyzer.py --pair "ETH/USD"

# View last 7 days only
python pnl_analyzer.py --days 7
```

### 4. Generate Reports & Charts
```bash
# One-time comprehensive report
python pnl_analyzer.py

# Export all data to CSV
python pnl_analyzer.py --export

# Generate visual charts
python pnl_analyzer.py --charts --days 7
```

## PnL Tracking Features

### Real-time Console Updates
During bot operation, you'll see:
```
[12:34:56][PNL] 💰 Session PnL: $45.67 | Executions: 23 | Hourly Rate: $12.34/hr
```

### Comprehensive Reports
Every 5 minutes (configurable), detailed reports show:
- Total executions and volume
- Realized PnL with win/loss breakdown
- Performance by trading pair
- Recent trading activity
- Hourly performance rates

### Advanced Analytics
The `pnl_analyzer.py` provides:
- **Performance Metrics**: Win rate, average PnL per trade, best/worst trades
- **Time Analysis**: Hourly rates, daily performance, session duration
- **Pair Comparison**: Performance breakdown by XRP/BTC vs ETH/USD
- **Visual Charts**: Cumulative PnL, distribution charts, daily performance
- **Data Export**: CSV files for external analysis

## Configuration

### PnL Reporting Interval
In `improved_gridbot_with_db.py`:
```python
PNL_REPORT_INTERVAL = 300  # Report every 5 minutes (300 seconds)
```

### Database File Location
```python
DATABASE_FILE = "gridbot_pnl.db"  # SQLite database file
```

## Usage Examples

### Basic Operation
```bash
# Start the enhanced bot (same as before, but with PnL tracking)
python improved_gridbot_with_db.py
```

### Live Monitoring
```bash
# Watch live PnL updates in a separate terminal
python pnl_analyzer.py --live
```

### Analysis Commands
```bash
# Quick status check
python pnl_analyzer.py

# Last 24 hours only
python pnl_analyzer.py --days 1

# Focus on ETH/USD performance
python pnl_analyzer.py --pair "ETH/USD"

# Export everything to CSV
python pnl_analyzer.py --export

# Generate performance charts
python pnl_analyzer.py --charts
```

## Sample Output

### Console During Trading
```
[15:30:15][SUCCESS] XRP/BTC: SELL Level 3 EXECUTED!
[15:30:15][SUCCESS]     Volume: 125.50 @ Price: 0.00062340
[15:30:15][SUCCESS] 💰 Execution recorded: XRP/BTC SELL 125.50 @ 0.00062340 (PnL: $8.45)
[15:30:15][PNL] 💰 Session PnL: $127.89 | Executions: 34 | Hourly Rate: $42.63/hr
```

### PnL Report Sample
```
================================================================================
🚀 GRIDBOT PnL COMPREHENSIVE ANALYSIS
================================================================================
📅 Analysis Period: Last 7 days
🕐 Generated: 2025-06-29 15:30:15
--------------------------------------------------------------------------------
📊 OVERALL PERFORMANCE
----------------------------------------
Total Executions: 156
Total Volume: $12,450.67
Total PnL: $387.23
Average PnL/Trade: $2.48
Win Rate: 67.3% (105/156)
Best Trade: $15.67
Worst Trade: -$8.23
Session Duration: 28.5 hours
Hourly PnL Rate: $13.58/hour
Performance Rating: ✅ GOOD
```

## Data Export

The `--export` option creates CSV files with:
- **executions_YYYYMMDD_HHMMSS.csv** - All trade executions
- **orders_YYYYMMDD_HHMMSS.csv** - All order placements
- **portfolio_YYYYMMDD_HHMMSS.csv** - Portfolio snapshots

These can be imported into Excel, Google Sheets, or any data analysis tool.

## Visual Charts

The `--charts` option generates:
1. **Cumulative PnL Over Time** - Your profit curve
2. **PnL by Trading Pair** - XRP/BTC vs ETH/USD performance
3. **Trade PnL Distribution** - Histogram of trade outcomes
4. **Daily PnL** - Bar chart of daily performance

## Troubleshooting

### Database Issues
```bash
# Check if database exists
ls -la gridbot_pnl.db

# If database is corrupted, delete and restart
rm gridbot_pnl.db
python improved_gridbot_with_db.py
```

### Missing Dependencies
```bash
# Install missing packages
pip install pandas matplotlib seaborn

# Or install all at once
pip install -r requirements_pnl.txt
```

### Performance Impact
- SQLite operations are very fast and lightweight
- Database writes happen asynchronously
- Minimal impact on trading performance
- Database file grows ~1MB per 10,000 trades

## Original Bot Features

All original features remain unchanged:
- ✅ Multi-pair trading (XRP/BTC + ETH/USD)
- ✅ Aggressive grid strategy
- ✅ Dynamic order sizing
- ✅ Smart rebalancing
- ✅ WebSocket monitoring
- ✅ Order replacement
- ✅ Cycle-aware protection

## Support

The enhanced bot maintains full compatibility with your existing configuration and trading strategy while adding comprehensive PnL tracking and analytics capabilities.

For questions about the PnL tracking features, check the database contents:
```bash
# Simple database inspection
sqlite3 gridbot_pnl.db ".tables"
sqlite3 gridbot_pnl.db "SELECT COUNT(*) FROM executions;"
```
