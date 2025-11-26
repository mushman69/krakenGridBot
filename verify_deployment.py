#!/usr/bin/env python3
"""
GridBot Deployment Verification Script
=====================================

Quick verification that all files are ready for Linode deployment.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename, required=True):
    """Check if a file exists and show its status"""
    path = Path(filename)
    if path.exists():
        size = path.stat().st_size
        print(f"✅ {filename} - {size} bytes")
        return True
    else:
        status = "❌ REQUIRED" if required else "⚠️  OPTIONAL"
        print(f"{status} {filename} - MISSING")
        return not required

def check_file_content(filename, required_content):
    """Check if file contains required content"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            for item in required_content:
                if item not in content:
                    print(f"⚠️  {filename} missing: {item}")
                    return False
        return True
    except FileNotFoundError:
        print(f"❌ {filename} not found for content check")
        return False

def main():
    print("GridBot Deployment Verification")
    print("=" * 40)
    
    # Check current directory
    print(f"📁 Current directory: {Path.cwd()}")
    print()
    
    all_good = True
    
    # Check required files
    print("1. Checking required files...")
    required_files = [
        'improved_gridbot.py',
        'pnl_analyzer.py', 
        'db_viewer.py',
        'Dockerfile',
        'docker-compose.yml',
        'requirements.txt',
        'docker-deploy.py',
        '.dockerignore'
    ]
    
    for file in required_files:
        if not check_file_exists(file):
            all_good = False
    
    # Check optional files
    print("\n2. Checking optional files...")
    optional_files = [
        'LINODE_DEPLOYMENT.md',
        'create_linode_package.bat',
        'kraken.env.example'
    ]
    
    for file in optional_files:
        check_file_exists(file, required=False)
    
    # Check critical file - API credentials
    print("\n3. Checking API credentials...")
    if Path('kraken.env').exists():
        if check_file_content('kraken.env', ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET']):
            print("✅ kraken.env has required keys")
            
            # Check if still contains example values
            with open('kraken.env', 'r') as f:
                content = f.read()
                if 'your_kraken_api_key_here' in content or 'your_actual_api_key' in content:
                    print("⚠️  kraken.env still contains example values!")
                    print("   Please add your real API credentials")
                    all_good = False
                else:
                    print("✅ kraken.env appears to have real credentials")
        else:
            all_good = False
    else:
        print("❌ kraken.env missing - create it with your API credentials")
        all_good = False
    
    # Check Python imports
    print("\n4. Checking Python dependencies...")
    try:
        import aiohttp
        print("✅ aiohttp available")
    except ImportError:
        print("❌ aiohttp missing - run: pip install aiohttp")
        all_good = False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv available")
    except ImportError:
        print("❌ python-dotenv missing - run: pip install python-dotenv")
        all_good = False
    
    # Check Docker files
    print("\n5. Checking Docker configuration...")
    if check_file_content('Dockerfile', ['FROM python', 'COPY improved_gridbot.py']):
        print("✅ Dockerfile looks good")
    else:
        all_good = False
    
    if check_file_content('docker-compose.yml', ['gridbot:', 'volumes:', './data:/app/data']):
        print("✅ docker-compose.yml looks good")
    else:
        all_good = False
    
    # Summary
    print("\n" + "=" * 40)
    if all_good:
        print("🎉 All checks passed! Ready for deployment!")
        print("\n🚀 Next steps:")
        print("1. Run: create_linode_package.bat")
        print("2. Upload to Linode using WinSCP")
        print("3. SSH to Linode and run: python3 docker-deploy.py setup")
    else:
        print("⚠️  Issues found - fix the problems above before deploying")
        print("\n💡 Common fixes:")
        print("- Add real API credentials to kraken.env")
        print("- Install missing Python packages")
        print("- Ensure all required files are present")
    
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
