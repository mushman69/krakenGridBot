#!/usr/bin/env python3
"""
GridBot Docker Management Script (Python)
=========================================

Comprehensive Docker deployment and management tool for Kraken GridBot with PnL tracking.
Fully compatible with the SQLite database system and provides all Docker operations.

Usage:
    python docker-deploy.py [command] [options]

Commands:
    build       - Build the Docker image
    start       - Start the GridBot container
    stop        - Stop the GridBot container
    restart     - Restart the GridBot container
    logs        - Show live logs from the container
    logs-tail   - Show last N lines of logs (default: 100)
    status      - Show container status and resource usage
    shell       - Open shell in running container
    monitor     - Start PnL monitoring in separate container
    analyze     - Run PnL analysis
    db-status   - Check database status and PnL overview
    backup      - Backup database and exports
    clean       - Remove stopped containers and unused images
    update      - Rebuild image and restart container
    setup       - Complete setup and deployment
    verify-pnl  - Verify PnL tracking system is working
    health      - Comprehensive health check
"""

import os
import sys
import subprocess
import time
import json
import argparse
import platform
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Configuration
CONTAINER_NAME = "kraken_gridbot_pnl"
IMAGE_NAME = "gridbot-pnl"
COMPOSE_FILE = "docker-compose.yml"
DATABASE_FILE_HOST = "./data/gridbot_pnl.db"
DATABASE_FILE_CONTAINER = "/app/data/gridbot_pnl.db"

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    @classmethod
    def disable_on_windows(cls):
        """Disable colors on Windows if not supported"""
        if platform.system() == "Windows":
            # Try to enable ANSI support on Windows 10+
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                # Disable colors if ANSI not supported
                for attr in dir(cls):
                    if not attr.startswith('_') and attr != 'disable_on_windows':
                        setattr(cls, attr, '')

# Initialize colors
Colors.disable_on_windows()

class GridBotDeployer:
    """Main class for GridBot Docker deployment and management"""
    
    def __init__(self):
        self.container_name = CONTAINER_NAME
        self.image_name = IMAGE_NAME
        self.compose_file = COMPOSE_FILE
        self.work_dir = Path.cwd()
        
        # Ensure data directories exist
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories for data persistence"""
        directories = ['data', 'exports', 'charts', 'logs']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def print_status(self, message: str, color: str = Colors.BLUE):
        """Print colored status message"""
        print(f"{color}[INFO]{Colors.RESET} {message}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")
    
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Colors.PURPLE}{Colors.BOLD}=== {title} ==={Colors.RESET}")
    
    def run_command(self, command: List[str], capture_output: bool = False, 
                   check: bool = True) -> subprocess.CompletedProcess:
        """Run a command with error handling"""
        try:
            if capture_output:
                result = subprocess.run(command, capture_output=True, text=True, check=check)
            else:
                result = subprocess.run(command, check=check)
            return result
        except subprocess.CalledProcessError as e:
            if capture_output:
                self.print_error(f"Command failed: {' '.join(command)}")
                if e.stdout:
                    print(f"STDOUT: {e.stdout}")
                if e.stderr:
                    print(f"STDERR: {e.stderr}")
            raise
        except FileNotFoundError:
            self.print_error(f"Command not found: {command[0]}")
            self.print_error("Please ensure Docker and Docker Compose are installed")
            sys.exit(1)
    
    def check_docker_availability(self) -> bool:
        """Check if Docker and Docker Compose are available"""
        try:
            # Check Docker
            result = self.run_command(['docker', '--version'], capture_output=True)
            docker_version = result.stdout.strip()
            
            # Check Docker Compose
            result = self.run_command(['docker-compose', '--version'], capture_output=True)
            compose_version = result.stdout.strip()
            
            self.print_success(f"Docker: {docker_version}")
            self.print_success(f"Docker Compose: {compose_version}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("Docker or Docker Compose not found!")
            self.print_error("Please install Docker and Docker Compose:")
            self.print_error("- Windows/Mac: https://www.docker.com/products/docker-desktop")
            self.print_error("- Linux: https://docs.docker.com/engine/install/")
            return False
    
    def check_environment_file(self) -> bool:
        """Check if kraken.env file exists and is properly configured"""
        env_file = Path("kraken.env")
        if not env_file.exists():
            self.print_error("kraken.env file not found!")
            self.print_error("Please create kraken.env with your Kraken API credentials:")
            print("KRAKEN_API_KEY=your_api_key_here")
            print("KRAKEN_API_SECRET=your_api_secret_here")
            return False
        
        # Check file contents
        try:
            content = env_file.read_text()
            has_key = 'KRAKEN_API_KEY' in content
            has_secret = 'KRAKEN_API_SECRET' in content
            
            if has_key and has_secret:
                self.print_success("API credentials configured")
                return True
            else:
                self.print_warning("API credentials may be incomplete")
                if not has_key:
                    self.print_warning("Missing: KRAKEN_API_KEY")
                if not has_secret:
                    self.print_warning("Missing: KRAKEN_API_SECRET")
                return False
                
        except Exception as e:
            self.print_error(f"Error reading kraken.env: {e}")
            return False
    
    def check_required_files(self) -> bool:
        """Check if all required files exist"""
        required_files = [
            'improved_gridbot.py',
            'pnl_analyzer.py',
            'db_viewer.py',
            'Dockerfile',
            'docker-compose.yml',
            'requirements.txt',
            'docker-entrypoint.sh'
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
            else:
                self.print_success(f"✓ {file}")
        
        if missing_files:
            self.print_error("Missing required files:")
            for file in missing_files:
                print(f"  - {file}")
            return False
        
        return True
    
    def get_container_status(self) -> Dict:
        """Get detailed container status"""
        try:
            # Check if container exists and is running
            result = self.run_command(['docker', 'ps', '-a', '--filter', f'name={self.container_name}', 
                                     '--format', 'json'], capture_output=True)
            
            if result.stdout.strip():
                container_info = json.loads(result.stdout.strip())
                
                # Get additional stats if running
                if container_info['State'] == 'running':
                    stats_result = self.run_command(['docker', 'stats', '--no-stream', '--format', 
                                                   'json', self.container_name], capture_output=True)
                    if stats_result.stdout.strip():
                        stats_info = json.loads(stats_result.stdout.strip())
                        container_info.update(stats_info)
                
                return container_info
            else:
                return {'State': 'not_found'}
                
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return {'State': 'error'}
    
    def build_image(self) -> bool:
        """Build the Docker image"""
        self.print_header("Building Docker Image")
        
        try:
            self.run_command(['docker', 'build', '-t', self.image_name, '.'])
            self.print_success("Docker image built successfully")
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to build Docker image")
            return False
    
    def start_container(self) -> bool:
        """Start the GridBot container"""
        self.print_header("Starting GridBot Container")
        
        # Check if container is already running
        status = self.get_container_status()
        if status.get('State') == 'running':
            self.print_warning("Container is already running")
            return True
        
        # Remove stopped container if it exists
        if status.get('State') in ['exited', 'dead']:
            self.print_status("Removing stopped container...")
            try:
                self.run_command(['docker', 'rm', self.container_name])
            except subprocess.CalledProcessError:
                pass
        
        # Start the container using docker-compose
        try:
            self.run_command(['docker-compose', 'up', '-d', 'gridbot'])
            
            # Wait for container to start
            time.sleep(3)
            
            # Verify it's running
            status = self.get_container_status()
            if status.get('State') == 'running':
                self.print_success("GridBot started successfully")
                self.print_status("Use 'python docker-deploy.py logs' to view live logs")
                self.print_status("Use 'python docker-deploy.py monitor' to start PnL monitoring")
                return True
            else:
                self.print_error("Container failed to start")
                self.print_status("Check logs with: docker logs " + self.container_name)
                return False
                
        except subprocess.CalledProcessError:
            self.print_error("Failed to start container")
            return False
    
    def stop_container(self) -> bool:
        """Stop the GridBot container"""
        self.print_header("Stopping GridBot Container")
        
        try:
            self.run_command(['docker-compose', 'down'])
            self.print_success("GridBot stopped")
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to stop container")
            return False
    
    def restart_container(self) -> bool:
        """Restart the GridBot container"""
        self.print_header("Restarting GridBot")
        
        if self.stop_container():
            time.sleep(2)
            return self.start_container()
        return False
    
    def show_logs(self, follow: bool = True, tail: int = None) -> bool:
        """Show container logs"""
        if follow:
            self.print_status("Showing live logs (Ctrl+C to exit)...")
        else:
            self.print_status(f"Showing last {tail or 'all'} log lines...")
        
        try:
            cmd = ['docker', 'logs']
            if follow:
                cmd.append('-f')
            if tail:
                cmd.extend(['--tail', str(tail)])
            cmd.append(self.container_name)
            
            self.run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to show logs")
            return False
        except KeyboardInterrupt:
            print("\nLog viewing stopped")
            return True
    
    def show_status(self) -> bool:
        """Show comprehensive container status"""
        self.print_header("GridBot Status")
        
        status = self.get_container_status()
        
        if status.get('State') == 'not_found':
            self.print_error("GridBot container not found")
            return False
        elif status.get('State') == 'error':
            self.print_error("Error getting container status")
            return False
        elif status.get('State') == 'running':
            self.print_success("GridBot is running")
            
            # Show detailed info
            print(f"\n{Colors.CYAN}Container Details:{Colors.RESET}")
            print(f"  Name: {status.get('Names', 'N/A')}")
            print(f"  Status: {status.get('Status', 'N/A')}")
            print(f"  Image: {status.get('Image', 'N/A')}")
            
            # Show resource usage if available
            if 'CPUPerc' in status:
                print(f"\n{Colors.CYAN}Resource Usage:{Colors.RESET}")
                print(f"  CPU: {status.get('CPUPerc', 'N/A')}")
                print(f"  Memory: {status.get('MemUsage', 'N/A')} ({status.get('MemPerc', 'N/A')})")
                print(f"  Network I/O: {status.get('NetIO', 'N/A')}")
                print(f"  Block I/O: {status.get('BlockIO', 'N/A')}")
            
            return True
        else:
            self.print_warning(f"GridBot is not running (Status: {status.get('State')})")
            return False
    
    def open_shell(self) -> bool:
        """Open shell in running container"""
        self.print_status("Opening shell in container...")
        
        try:
            self.run_command(['docker', 'exec', '-it', self.container_name, '/bin/bash'])
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to open shell (is container running?)")
            return False
    
    def start_monitor(self) -> bool:
        """Start PnL monitoring in separate container"""
        self.print_header("Starting PnL Monitor")
        
        try:
            self.run_command(['docker-compose', '--profile', 'monitoring', 'up', 'pnl-monitor'])
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to start PnL monitor")
            return False
    
    def run_analysis(self, args: List[str] = None) -> bool:
        """Run PnL analysis"""
        self.print_header("Running PnL Analysis")
        
        try:
            cmd = ['docker', 'run', '--rm', 
                   '-v', f'{self.work_dir}/data:/app/data:ro',
                   '-v', f'{self.work_dir}/exports:/app/exports',
                   '-v', f'{self.work_dir}/charts:/app/charts',
                   '-e', f'DATABASE_FILE={DATABASE_FILE_CONTAINER}',
                   self.image_name, 'python', 'pnl_analyzer.py']
            
            if args:
                cmd.extend(args)
            
            self.run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to run PnL analysis")
            return False
    
    def check_database_status(self) -> bool:
        """Check database status and show PnL overview"""
        self.print_header("Database Status")
        
        # Check if database file exists
        db_path = Path(DATABASE_FILE_HOST)
        if not db_path.exists():
            self.print_warning("Database file not found - bot may not have started trading yet")
            return False
        
        # Get database info
        db_size = db_path.stat().st_size / 1024  # KB
        self.print_success(f"Database file exists: {db_path}")
        self.print_status(f"Database size: {db_size:.1f} KB")
        
        # Run database status check through container
        try:
            cmd = ['docker', 'run', '--rm',
                   '-v', f'{self.work_dir}/data:/app/data:ro',
                   '-e', f'DATABASE_FILE={DATABASE_FILE_CONTAINER}',
                   self.image_name, 'python', 'db_viewer.py', 'status']
            
            self.run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            self.print_error("Failed to check database status")
            return False
    
    def backup_data(self) -> bool:
        """Create backup of database and exports"""
        self.print_header("Creating Data Backup")
        
        import datetime
        backup_dir = Path(f"backups/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy data directory
            import shutil
            if Path('data').exists():
                shutil.copytree('data', backup_dir / 'data')
                self.print_success("Database backed up")
            
            # Copy exports if they exist
            if Path('exports').exists():
                shutil.copytree('exports', backup_dir / 'exports')
                self.print_success("Exports backed up")
            
            # Copy charts if they exist
            if Path('charts').exists():
                shutil.copytree('charts', backup_dir / 'charts')
                self.print_success("Charts backed up")
            
            # Create compressed archive
            archive_path = f"{backup_dir}.tar.gz"
            self.run_command(['tar', '-czf', archive_path, '-C', 'backups', backup_dir.name])
            
            # Remove uncompressed directory
            shutil.rmtree(backup_dir)
            
            self.print_success(f"Backup created: {archive_path}")
            return True
            
        except Exception as e:
            self.print_error(f"Backup failed: {e}")
            return False
    
    def clean_docker(self) -> bool:
        """Clean up Docker resources"""
        self.print_header("Cleaning Docker Resources")
        
        try:
            self.run_command(['docker', 'system', 'prune', '-f'])
            self.print_success("Docker cleanup complete")
            return True
        except subprocess.CalledProcessError:
            self.print_error("Docker cleanup failed")
            return False
    
    def update_bot(self) -> bool:
        """Update bot by rebuilding and restarting"""
        self.print_header("Updating GridBot")
        
        if self.stop_container():
            if self.build_image():
                return self.start_container()
        return False
    
    def verify_pnl_system(self) -> bool:
        """Verify that PnL tracking system is working correctly"""
        self.print_header("Verifying PnL Tracking System")
        
        # Check environment variables
        self.print_status("Checking environment configuration...")
        
        # Verify database file paths
        self.print_status(f"Host database path: {DATABASE_FILE_HOST}")
        self.print_status(f"Container database path: {DATABASE_FILE_CONTAINER}")
        
        # Check if container is running
        status = self.get_container_status()
        if status.get('State') != 'running':
            self.print_warning("Container is not running - start it first to verify PnL tracking")
            return False
        
        # Fix permissions first
        self.print_status("Fixing directory permissions in container...")
        try:
            fix_cmd = ['docker', 'exec', self.container_name, 'bash', '-c', 
                      'chmod -R 777 /app/data /app/exports /app/charts /app/logs 2>/dev/null || true']
            self.run_command(fix_cmd, capture_output=True)
        except:
            pass  # Ignore permission fix errors
        
        # Test database connection through container
        try:
            self.print_status("Testing database connection...")
            cmd = ['docker', 'exec', self.container_name, 'python', '-c', '''
import os
import sqlite3
import sys

db_path = os.getenv("DATABASE_FILE", "/app/data/gridbot_pnl.db")
print(f"Database path in container: {db_path}")

# Ensure directory exists
db_dir = os.path.dirname(db_path)
if db_dir:
    try:
        os.makedirs(db_dir, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create directory {db_dir}: {e}", file=sys.stderr)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    table_names = [t[0] for t in tables]
    print(f"Database tables: {table_names}")
    
    if 'orders' in table_names:
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        print(f"Orders recorded: {order_count}")
    else:
        print("Orders table not yet created (will be created on first order)")
    
    if 'executions' in table_names:
        cursor.execute("SELECT COUNT(*) FROM executions")
        execution_count = cursor.fetchone()[0]
        print(f"Executions recorded: {execution_count}")
    else:
        print("Executions table not yet created (will be created on first execution)")
    
    conn.close()
    print("✅ Database connection successful!")
except sqlite3.OperationalError as e:
    error_msg = str(e)
    if "unable to open database file" in error_msg.lower():
        print(f"Error: Cannot open database file: {db_path}", file=sys.stderr)
        print(f"Directory exists: {os.path.exists(db_dir) if db_dir else 'N/A'}", file=sys.stderr)
        if db_dir and os.path.exists(db_dir):
            print(f"Directory writable: {os.access(db_dir, os.W_OK)}", file=sys.stderr)
    raise
''']
            
            result = self.run_command(cmd, capture_output=True)
            print(result.stdout)
            
            self.print_success("PnL tracking system verification complete")
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_error("Database verification failed")
            if e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            return False
    
    def health_check(self) -> bool:
        """Comprehensive health check"""
        self.print_header("GridBot Health Check")
        
        all_checks_passed = True
        
        # Check 1: Docker availability
        self.print_status("1. Checking Docker availability...")
        if not self.check_docker_availability():
            all_checks_passed = False
        
        # Check 2: Required files
        self.print_status("2. Checking required files...")
        if not self.check_required_files():
            all_checks_passed = False
        
        # Check 3: Environment configuration
        self.print_status("3. Checking environment configuration...")
        if not self.check_environment_file():
            all_checks_passed = False
        
        # Check 4: Container status
        self.print_status("4. Checking container status...")
        container_running = self.show_status()
        
        # Check 5: Database status (if container is running)
        if container_running:
            self.print_status("5. Checking database status...")
            if not self.check_database_status():
                self.print_warning("Database not ready (may be normal for new deployment)")
        
        # Check 6: PnL system verification (if container is running)
        if container_running:
            self.print_status("6. Verifying PnL tracking system...")
            if not self.verify_pnl_system():
                all_checks_passed = False
        
        # Summary
        if all_checks_passed:
            self.print_success("🎉 All health checks passed!")
        else:
            self.print_warning("⚠️ Some health checks failed - see details above")
        
        return all_checks_passed
    
    def complete_setup(self) -> bool:
        """Complete setup and deployment"""
        self.print_header("GridBot Complete Setup")
        
        # Step 1: Health check
        self.print_status("Step 1: Running pre-setup health check...")
        if not self.check_docker_availability():
            return False
        
        if not self.check_required_files():
            return False
        
        if not self.check_environment_file():
            return False
        
        # Step 2: Ensure data directories exist with proper permissions
        self.print_status("Step 2: Ensuring data directories exist...")
        import pathlib
        import stat
        data_dirs = ['./data', './exports', './charts', './logs']
        for dir_path in data_dirs:
            dir_obj = pathlib.Path(dir_path)
            dir_obj.mkdir(parents=True, exist_ok=True)
            # Set permissions if on Unix-like system
            if hasattr(os, 'chmod'):
                try:
                    # Set to 777 to ensure container can write
                    os.chmod(dir_path, 0o777)
                    # Also try to change ownership if possible (requires root or same user)
                    if hasattr(os, 'getuid') and os.getuid() == 0:  # Running as root
                        try:
                            import pwd
                            # Try to get the user that will run docker (usually current user)
                            uid = os.getuid()
                            gid = os.getgid()
                            os.chown(dir_path, uid, gid)
                        except:
                            pass
                except PermissionError:
                    self.print_warning(f"Could not set permissions for {dir_path} - may need sudo")
                except Exception as e:
                    self.print_warning(f"Could not set permissions for {dir_path}: {e}")
        
        # Verify permissions
        for dir_path in data_dirs:
            if os.path.exists(dir_path):
                if hasattr(os, 'access'):
                    writable = os.access(dir_path, os.W_OK)
                    if not writable:
                        self.print_warning(f"Directory {dir_path} is not writable - this may cause issues")
        
        self.print_success("Data directories ready")
        
        # Step 3: Build image
        self.print_status("Step 3: Building Docker image...")
        if not self.build_image():
            return False
        
        # Step 4: Fix host directory permissions (critical for database access)
        self.print_status("Step 4: Fixing host directory permissions...")
        try:
            # Use docker run to fix permissions with proper user context
            fix_perms_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{os.path.abspath("./data")}:/data',
                '-v', f'{os.path.abspath("./exports")}:/exports',
                '-v', f'{os.path.abspath("./charts")}:/charts',
                '-v', f'{os.path.abspath("./logs")}:/logs',
                'alpine:latest',
                'sh', '-c', 'chmod -R 777 /data /exports /charts /logs 2>/dev/null || true'
            ]
            self.run_command(fix_perms_cmd, capture_output=True)
            self.print_success("Host directory permissions fixed")
        except Exception as e:
            self.print_warning(f"Could not fix permissions via Docker: {e}")
            self.print_warning("You may need to run: sudo chmod -R 777 ./data ./exports ./charts ./logs")
        
        # Step 5: Start container
        self.print_status("Step 5: Starting GridBot...")
        if not self.start_container():
            return False
        
        # Step 6: Verify deployment
        self.print_status("Step 6: Verifying deployment...")
        time.sleep(5)  # Give container time to start
        
        if not self.show_status():
            return False
        
        # Step 7: Verify PnL system
        self.print_status("Step 7: Verifying PnL tracking...")
        if not self.verify_pnl_system():
            self.print_warning("PnL verification failed, but container is running")
        
        self.print_header("Setup Complete!")
        self.print_success("🎉 GridBot is now running with PnL tracking!")
        print(f"\n{Colors.CYAN}Next steps:{Colors.RESET}")
        print("• View logs: python docker-deploy.py logs")
        print("• Check status: python docker-deploy.py status")
        print("• Monitor PnL: python docker-deploy.py monitor")
        print("• Run analysis: python docker-deploy.py analyze")
        print("• Health check: python docker-deploy.py health")
        
        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GridBot Docker Management")
    parser.add_argument('command', nargs='?', default='help',
                       choices=['build', 'start', 'stop', 'restart', 'logs', 'logs-tail',
                               'status', 'shell', 'monitor', 'analyze', 'db-status',
                               'backup', 'clean', 'update', 'setup', 'verify-pnl',
                               'health', 'help'])
    parser.add_argument('--tail', type=int, default=100,
                       help='Number of log lines to show (for logs-tail)')
    parser.add_argument('--days', type=int, help='Number of days for analysis')
    parser.add_argument('--pair', type=str, help='Trading pair for analysis')
    parser.add_argument('--export', action='store_true', help='Export data to CSV')
    parser.add_argument('--charts', action='store_true', help='Generate charts')
    parser.add_argument('--live', action='store_true', help='Live monitoring')
    
    args = parser.parse_args()
    
    deployer = GridBotDeployer()
    
    # Show help
    if args.command == 'help':
        parser.print_help()
        print(f"\n{Colors.CYAN}Examples:{Colors.RESET}")
        print("  python docker-deploy.py setup")
        print("  python docker-deploy.py logs")
        print("  python docker-deploy.py analyze --days 7")
        print("  python docker-deploy.py analyze --export")
        print("  python docker-deploy.py verify-pnl")
        return
    
    # Execute commands
    success = True
    
    if args.command == 'build':
        success = deployer.build_image()
    elif args.command == 'start':
        success = deployer.start_container()
    elif args.command == 'stop':
        success = deployer.stop_container()
    elif args.command == 'restart':
        success = deployer.restart_container()
    elif args.command == 'logs':
        success = deployer.show_logs(follow=True)
    elif args.command == 'logs-tail':
        success = deployer.show_logs(follow=False, tail=args.tail)
    elif args.command == 'status':
        success = deployer.show_status()
    elif args.command == 'shell':
        success = deployer.open_shell()
    elif args.command == 'monitor':
        success = deployer.start_monitor()
    elif args.command == 'analyze':
        # Build arguments for analysis
        analysis_args = []
        if args.days:
            analysis_args.extend(['--days', str(args.days)])
        if args.pair:
            analysis_args.extend(['--pair', args.pair])
        if args.export:
            analysis_args.append('--export')
        if args.charts:
            analysis_args.append('--charts')
        if args.live:
            analysis_args.append('--live')
        
        success = deployer.run_analysis(analysis_args)
    elif args.command == 'db-status':
        success = deployer.check_database_status()
    elif args.command == 'backup':
        success = deployer.backup_data()
    elif args.command == 'clean':
        success = deployer.clean_docker()
    elif args.command == 'update':
        success = deployer.update_bot()
    elif args.command == 'setup':
        success = deployer.complete_setup()
    elif args.command == 'verify-pnl':
        success = deployer.verify_pnl_system()
    elif args.command == 'health':
        success = deployer.health_check()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
