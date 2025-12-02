#!/usr/bin/env python3
"""
Script to export GridBot logs
Can be used to export Docker logs or local log files
"""

import os
import sys
import subprocess
from datetime import datetime

def export_docker_logs(container_name="kraken_gridbot_pnl", output_file=None):
    """Export logs from Docker container"""
    try:
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"gridbot_logs_{timestamp}.txt"
        
        print(f"📥 Exporting logs from Docker container: {container_name}")
        print(f"📁 Output file: {output_file}")
        
        # Get Docker logs
        result = subprocess.run(
            ['docker', 'logs', '--tail', '10000', container_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"GridBot Logs Export\n")
            f.write(f"Container: {container_name}\n")
            f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print(f"✅ Logs exported successfully to: {output_file}")
        print(f"📊 Total lines: {len(result.stdout.splitlines())}")
        return output_file
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting Docker logs: {e}")
        print(f"   Make sure the container '{container_name}' is running")
        return None
    except FileNotFoundError:
        print("❌ Docker not found. Trying to export from log files...")
        return export_log_files()

def export_log_files(log_dir="logs", output_file=None):
    """Export logs from log files"""
    try:
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"gridbot_logs_{timestamp}.txt"
        
        print(f"📥 Exporting logs from directory: {log_dir}")
        print(f"📁 Output file: {output_file}")
        
        if not os.path.exists(log_dir):
            print(f"❌ Log directory not found: {log_dir}")
            return None
        
        # Try to read latest.log first
        latest_log = os.path.join(log_dir, "latest.log")
        log_files = []
        
        if os.path.exists(latest_log):
            log_files.append(("latest.log", latest_log))
        
        # Also get all timestamped log files
        for filename in sorted(os.listdir(log_dir)):
            if filename.startswith("gridbot_") and filename.endswith(".log"):
                log_files.append((filename, os.path.join(log_dir, filename)))
        
        if not log_files:
            print(f"⚠️ No log files found in {log_dir}")
            return None
        
        # Combine all log files
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write(f"GridBot Logs Export\n")
            outfile.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write("=" * 80 + "\n\n")
            
            for name, path in log_files:
                try:
                    outfile.write(f"\n{'=' * 80}\n")
                    outfile.write(f"File: {name}\n")
                    outfile.write(f"{'=' * 80}\n\n")
                    
                    with open(path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        outfile.write(content)
                        outfile.write("\n")
                    
                    print(f"✅ Exported: {name}")
                except Exception as e:
                    print(f"⚠️ Error reading {name}: {e}")
        
        print(f"✅ Logs exported successfully to: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ Error exporting log files: {e}")
        return None

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export GridBot logs')
    parser.add_argument('--docker', action='store_true', help='Export from Docker container')
    parser.add_argument('--container', default='kraken_gridbot_pnl', help='Docker container name')
    parser.add_argument('--log-dir', default='logs', help='Log directory for file export')
    parser.add_argument('--output', help='Output file name')
    
    args = parser.parse_args()
    
    if args.docker:
        export_docker_logs(args.container, args.output)
    else:
        # Try Docker first, fallback to files
        result = export_docker_logs(args.container, args.output)
        if result is None:
            export_log_files(args.log_dir, args.output)

if __name__ == "__main__":
    main()


