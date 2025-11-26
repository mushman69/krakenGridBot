#!/usr/bin/env python3
"""
🚀 GRIDBOT PnL ANALYZER
======================

Comprehensive PnL analysis tool for the Kraken GridBot SQLite database.
Provides detailed analytics, charts, and performance metrics.

Usage:
    python pnl_analyzer.py [options]

Options:
    --live      Show live updates (refreshes every 30 seconds)
    --export    Export data to CSV files
    --days N    Show data for last N days (default: 7)
    --pair PAIR Show data for specific trading pair only
"""

import sqlite3
import argparse
import time
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, List, Tuple

# Database file
DATABASE_FILE = os.getenv('DATABASE_FILE', "gridbot_pnl.db")

class PnLAnalyzer:
    """Comprehensive PnL analyzer for GridBot data"""
    
    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Check if database exists"""
        if not os.path.exists(self.db_file):
            print(f"❌ Database file {self.db_file} not found!")
            print("   Run the GridBot first to generate trading data.")
            sys.exit(1)
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_file)
    
    def get_overall_stats(self, days: Optional[int] = None) -> Dict:
        """Get overall trading statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build date filter
        date_filter = ""
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            date_filter = f"WHERE timestamp > '{cutoff_date.isoformat()}'"
        
        # Overall statistics
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_executions,
                SUM(usd_value) as total_volume,
                SUM(pnl_contribution) as total_pnl,
                AVG(pnl_contribution) as avg_pnl_per_trade,
                MIN(timestamp) as first_trade,
                MAX(timestamp) as last_trade,
                SUM(CASE WHEN pnl_contribution > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl_contribution < 0 THEN 1 ELSE 0 END) as losing_trades,
                MAX(pnl_contribution) as best_trade,
                MIN(pnl_contribution) as worst_trade
            FROM executions
            {date_filter}
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] > 0:
            stats = {
                'total_executions': result[0],
                'total_volume': result[1] or 0,
                'total_pnl': result[2] or 0,
                'avg_pnl_per_trade': result[3] or 0,
                'first_trade': result[4],
                'last_trade': result[5],
                'winning_trades': result[6] or 0,
                'losing_trades': result[7] or 0,
                'best_trade': result[8] or 0,
                'worst_trade': result[9] or 0
            }
            
            # Calculate additional metrics
            if stats['total_executions'] > 0:
                stats['win_rate'] = (stats['winning_trades'] / stats['total_executions']) * 100
            else:
                stats['win_rate'] = 0
                
            # Calculate session duration and hourly rate
            if stats['first_trade'] and stats['last_trade']:
                first = datetime.fromisoformat(stats['first_trade'])
                last = datetime.fromisoformat(stats['last_trade'])
                duration = last - first
                stats['session_hours'] = duration.total_seconds() / 3600
                stats['hourly_pnl'] = stats['total_pnl'] / stats['session_hours'] if stats['session_hours'] > 0 else 0
            else:
                stats['session_hours'] = 0
                stats['hourly_pnl'] = 0
                
            return stats
        
        return None
    
    def get_pair_stats(self, days: Optional[int] = None) -> List[Dict]:
        """Get statistics by trading pair"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        date_filter = ""
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            date_filter = f"WHERE timestamp > '{cutoff_date.isoformat()}'"
        
        cursor.execute(f'''
            SELECT 
                pair,
                COUNT(*) as executions,
                SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buys,
                SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sells,
                SUM(usd_value) as volume,
                SUM(pnl_contribution) as pnl,
                AVG(price) as avg_price,
                SUM(CASE WHEN pnl_contribution > 0 THEN 1 ELSE 0 END) as winning_trades,
                MAX(pnl_contribution) as best_trade,
                MIN(pnl_contribution) as worst_trade
            FROM executions 
            {date_filter}
            GROUP BY pair
            ORDER BY pnl DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        pair_stats = []
        for result in results:
            stats = {
                'pair': result[0],
                'executions': result[1],
                'buys': result[2],
                'sells': result[3],
                'volume': result[4] or 0,
                'pnl': result[5] or 0,
                'avg_price': result[6] or 0,
                'winning_trades': result[7] or 0,
                'best_trade': result[8] or 0,
                'worst_trade': result[9] or 0
            }
            
            if stats['executions'] > 0:
                stats['win_rate'] = (stats['winning_trades'] / stats['executions']) * 100
            else:
                stats['win_rate'] = 0
                
            pair_stats.append(stats)
        
        return pair_stats
    
    def get_recent_trades(self, limit: int = 20, pair: Optional[str] = None) -> List[Dict]:
        """Get recent trading activity"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        pair_filter = ""
        if pair:
            pair_filter = f"WHERE pair = '{pair}'"
        
        cursor.execute(f'''
            SELECT 
                pair, side, volume, price, pnl_contribution, timestamp, order_id
            FROM executions 
            {pair_filter}
            ORDER BY timestamp DESC 
            LIMIT {limit}
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        trades = []
        for result in results:
            trades.append({
                'pair': result[0],
                'side': result[1],
                'volume': result[2],
                'price': result[3],
                'pnl': result[4],
                'timestamp': result[5],
                'order_id': result[6]
            })
        
        return trades
    
    def get_portfolio_history(self, days: Optional[int] = None) -> List[Dict]:
        """Get portfolio value history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        date_filter = ""
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            date_filter = f"WHERE timestamp > '{cutoff_date.isoformat()}'"
        
        cursor.execute(f'''
            SELECT 
                timestamp, pair, total_value_usd, allocation_percentage, current_price
            FROM portfolio_snapshots 
            {date_filter}
            ORDER BY timestamp DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        snapshots = []
        for result in results:
            snapshots.append({
                'timestamp': result[0],
                'pair': result[1],
                'total_value_usd': result[2],
                'allocation_percentage': result[3],
                'current_price': result[4]
            })
        
        return snapshots
    
    def print_comprehensive_report(self, days: Optional[int] = None, pair: Optional[str] = None):
        """Print comprehensive PnL report"""
        print("=" * 80)
        print("🚀 GRIDBOT PnL COMPREHENSIVE ANALYSIS")
        print("=" * 80)
        
        # Time period info
        if days:
            print(f"📅 Analysis Period: Last {days} days")
        else:
            print("📅 Analysis Period: All time")
        
        if pair:
            print(f"🎯 Focused on: {pair}")
        
        print(f"🕐 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
        # Overall statistics
        overall_stats = self.get_overall_stats(days)
        if overall_stats:
            print("📊 OVERALL PERFORMANCE")
            print("-" * 40)
            print(f"Total Executions: {overall_stats['total_executions']:,}")
            print(f"Total Volume: ${overall_stats['total_volume']:,.2f}")
            print(f"Total PnL: ${overall_stats['total_pnl']:,.2f}")
            print(f"Average PnL/Trade: ${overall_stats['avg_pnl_per_trade']:.2f}")
            print(f"Win Rate: {overall_stats['win_rate']:.1f}% ({overall_stats['winning_trades']}/{overall_stats['total_executions']})")
            print(f"Best Trade: ${overall_stats['best_trade']:.2f}")
            print(f"Worst Trade: ${overall_stats['worst_trade']:.2f}")
            print(f"Session Duration: {overall_stats['session_hours']:.1f} hours")
            print(f"Hourly PnL Rate: ${overall_stats['hourly_pnl']:.2f}/hour")
            
            # Performance rating
            if overall_stats['total_pnl'] > 0:
                if overall_stats['win_rate'] >= 60:
                    rating = "🔥 EXCELLENT"
                elif overall_stats['win_rate'] >= 50:
                    rating = "✅ GOOD"
                else:
                    rating = "⚠️ FAIR"
            else:
                rating = "❌ NEEDS IMPROVEMENT"
            
            print(f"Performance Rating: {rating}")
        else:
            print("📊 No trading data found for the specified period")
            return
        
        print()
        
        # Per-pair statistics
        pair_stats = self.get_pair_stats(days)
        if pair_stats:
            print("🎯 PERFORMANCE BY TRADING PAIR")
            print("-" * 40)
            for stats in pair_stats:
                if pair and stats['pair'] != pair:
                    continue
                    
                print(f"\n📈 {stats['pair']}:")
                print(f"   Executions: {stats['executions']} ({stats['buys']} buys, {stats['sells']} sells)")
                print(f"   Volume: ${stats['volume']:,.2f}")
                print(f"   PnL: ${stats['pnl']:,.2f}")
                print(f"   Avg Price: {stats['avg_price']:.6f}")
                print(f"   Win Rate: {stats['win_rate']:.1f}%")
                print(f"   Best Trade: ${stats['best_trade']:.2f}")
                print(f"   Worst Trade: ${stats['worst_trade']:.2f}")
        
        print()
        
        # Recent activity
        recent_trades = self.get_recent_trades(limit=15, pair=pair)
        if recent_trades:
            print("🕐 RECENT TRADING ACTIVITY")
            print("-" * 40)
            for trade in recent_trades:
                timestamp = datetime.fromisoformat(trade['timestamp']).strftime('%m-%d %H:%M')
                side_color = "🟢" if trade['side'] == 'buy' else "🔴"
                pnl_color = "💚" if trade['pnl'] > 0 else "❤️" if trade['pnl'] < 0 else "💛"
                print(f"{timestamp} | {side_color} {trade['pair']} {trade['side'].upper()} "
                      f"{trade['volume']:.6f} @ {trade['price']:.6f} | {pnl_color} ${trade['pnl']:.2f}")
        
        print()
        print("=" * 80)
    
    def export_to_csv(self, output_dir: str = "pnl_exports"):
        """Export data to CSV files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        conn = self.get_connection()
        
        # Export executions
        executions_df = pd.read_sql_query("SELECT * FROM executions ORDER BY timestamp DESC", conn)
        executions_file = os.path.join(output_dir, f"executions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        executions_df.to_csv(executions_file, index=False)
        print(f"📁 Executions exported to: {executions_file}")
        
        # Export orders
        orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY timestamp DESC", conn)
        orders_file = os.path.join(output_dir, f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        orders_df.to_csv(orders_file, index=False)
        print(f"📁 Orders exported to: {orders_file}")
        
        # Export portfolio snapshots
        portfolio_df = pd.read_sql_query("SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC", conn)
        portfolio_file = os.path.join(output_dir, f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        portfolio_df.to_csv(portfolio_file, index=False)
        print(f"📁 Portfolio snapshots exported to: {portfolio_file}")
        
        conn.close()
        print(f"✅ All data exported to {output_dir}/")
    
    def create_charts(self, days: Optional[int] = 7):
        """Create PnL charts"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            plt.style.use('seaborn-v0_8')
            sns.set_palette("husl")
            
            conn = self.get_connection()
            
            # Date filter
            date_filter = ""
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                date_filter = f"WHERE timestamp > '{cutoff_date.isoformat()}'"
            
            # Get PnL over time
            df = pd.read_sql_query(f'''
                SELECT 
                    datetime(timestamp) as timestamp,
                    pair,
                    pnl_contribution,
                    SUM(pnl_contribution) OVER (ORDER BY timestamp) as cumulative_pnl
                FROM executions
                {date_filter}
                ORDER BY timestamp
            ''', conn)
            
            if len(df) == 0:
                print("❌ No data available for charting")
                return
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'GridBot PnL Analysis - Last {days or "All"} Days', fontsize=16, fontweight='bold')
            
            # 1. Cumulative PnL over time
            ax1.plot(df['timestamp'], df['cumulative_pnl'], linewidth=2, color='#2E86AB')
            ax1.fill_between(df['timestamp'], df['cumulative_pnl'], alpha=0.3, color='#2E86AB')
            ax1.set_title('Cumulative PnL Over Time', fontweight='bold')
            ax1.set_ylabel('Cumulative PnL ($)')
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
            
            # 2. PnL distribution by pair
            pair_pnl = df.groupby('pair')['pnl_contribution'].sum().sort_values(ascending=True)
            colors = ['#FF6B6B' if x < 0 else '#4ECDC4' for x in pair_pnl.values]
            pair_pnl.plot(kind='barh', ax=ax2, color=colors)
            ax2.set_title('Total PnL by Trading Pair', fontweight='bold')
            ax2.set_xlabel('Total PnL ($)')
            
            # 3. Trade PnL distribution
            ax3.hist(df['pnl_contribution'], bins=30, alpha=0.7, color='#A8E6CF', edgecolor='black')
            ax3.axvline(df['pnl_contribution'].mean(), color='red', linestyle='--', 
                       label=f'Mean: ${df["pnl_contribution"].mean():.2f}')
            ax3.set_title('Trade PnL Distribution', fontweight='bold')
            ax3.set_xlabel('PnL per Trade ($)')
            ax3.set_ylabel('Frequency')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 4. Daily PnL
            daily_pnl = df.set_index('timestamp').resample('D')['pnl_contribution'].sum()
            colors = ['#FF6B6B' if x < 0 else '#4ECDC4' for x in daily_pnl.values]
            daily_pnl.plot(kind='bar', ax=ax4, color=colors, alpha=0.8)
            ax4.set_title('Daily PnL', fontweight='bold')
            ax4.set_ylabel('Daily PnL ($)')
            ax4.tick_params(axis='x', rotation=45)
            ax4.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save chart
            chart_file = f"pnl_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            print(f"📊 Charts saved to: {chart_file}")
            
            # Show chart
            plt.show()
            
            conn.close()
            
        except ImportError:
            print("❌ Charting requires matplotlib and seaborn:")
            print("   pip install matplotlib seaborn")
        except Exception as e:
            print(f"❌ Error creating charts: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='GridBot PnL Analyzer')
    parser.add_argument('--live', action='store_true', help='Show live updates')
    parser.add_argument('--export', action='store_true', help='Export data to CSV')
    parser.add_argument('--charts', action='store_true', help='Generate PnL charts')
    parser.add_argument('--days', type=int, help='Show data for last N days')
    parser.add_argument('--pair', type=str, help='Show data for specific trading pair only')
    
    args = parser.parse_args()
    
    analyzer = PnLAnalyzer()
    
    if args.export:
        print("📁 Exporting data to CSV files...")
        analyzer.export_to_csv()
        return
    
    if args.charts:
        print("📊 Generating PnL charts...")
        analyzer.create_charts(args.days)
        return
    
    if args.live:
        print("🔄 Starting live PnL monitoring (Ctrl+C to stop)...")
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
                analyzer.print_comprehensive_report(args.days, args.pair)
                print("\n🔄 Refreshing in 30 seconds... (Ctrl+C to stop)")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n👋 Live monitoring stopped")
    else:
        analyzer.print_comprehensive_report(args.days, args.pair)

if __name__ == "__main__":
    main()
