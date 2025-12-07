# 🚀 Deployment Checklist - Latest Fixes

## ✅ Code Changes Made

1. **Balance Calculation Fix** - Now properly accounts for locked funds
2. **XRP/BTC Order Value Fix** - Converts BTC to USD correctly
3. **Enhanced Debug Logging** - Shows available vs total balances

## ❌ Current Status

The container is **STILL RUNNING OLD CODE**. Evidence:
- ❌ No "Available balances calculated" message
- ❌ No "BTC/USD" price fetch messages
- ❌ Still showing "$0.00" for XRP/BTC orders
- ❌ Still showing "from 0.060924 available" (locked amount, not available)

## 📋 Deployment Steps

### Step 1: Verify Code is Updated on Server

```bash
# On your Linode server, check if improved_gridbot.py has the latest code
grep -n "Available balances calculated" improved_gridbot.py
grep -n "BTC/USD.*for XRP/BTC" improved_gridbot.py
grep -n "Order value for XRP/BTC" improved_gridbot.py
```

If these don't appear, the file needs to be updated.

### Step 2: Upload Latest Code (if needed)

If using file upload:
1. Upload `improved_gridbot.py` to your server
2. Make sure it's in the same directory as `Dockerfile`

If using git:
```bash
git pull origin main  # or your branch name
```

### Step 3: Clean Up Disk Space

```bash
# Run the cleanup script
chmod +x cleanup_disk_space.sh
./cleanup_disk_space.sh

# OR manually:
docker system prune -a --volumes -f
sudo apt-get clean
sudo apt-get autoclean
df -h /  # Check disk space
```

### Step 4: Rebuild Docker Container

```bash
# Stop the container
docker-compose down

# Rebuild with no cache (IMPORTANT!)
docker build --no-cache -t gridbot-pnl .

# OR using docker-compose
docker-compose build --no-cache

# Start the container
docker-compose up -d
```

### Step 5: Verify New Code is Running

Check the logs for these NEW messages:

```bash
docker-compose logs -f gridbot
```

**Look for:**
- ✅ `✅ Available balances calculated: X assets`
- ✅ `XETH: 0.064131 total, 0.060924 locked, 0.003207 available`
- ✅ `✅ BTC/USD: [price] (for XRP/BTC order value conversion)`
- ✅ `✅ Order value for XRP/BTC: $[amount] USD` (NOT $0.00)
- ✅ `📊 Calculated sell volume for ETH/USD: [volume] ETH (from 0.003207 available...)` (NOT 0.060924)

## 🔍 Troubleshooting

### If logs still show old code:

1. **Check file timestamps:**
   ```bash
   ls -lh improved_gridbot.py
   ```

2. **Verify Docker is using the right file:**
   ```bash
   docker exec kraken_gridbot_pnl cat /app/improved_gridbot.py | grep "Available balances calculated"
   ```

3. **Force rebuild:**
   ```bash
   docker-compose down
   docker rmi gridbot-pnl
   docker build --no-cache -t gridbot-pnl .
   docker-compose up -d
   ```

### If disk space is still an issue:

1. **Check disk usage:**
   ```bash
   df -h /
   du -sh /var/lib/docker
   ```

2. **Clean Docker more aggressively:**
   ```bash
   docker system prune -a --volumes -f --filter "until=24h"
   ```

3. **Remove old images:**
   ```bash
   docker images | grep gridbot
   docker rmi <old-image-id>
   ```

## ✅ Success Indicators

After successful deployment, you should see:

1. **Balance logs show locked funds:**
   ```
   XETH: 0.064131 total, 0.060924 locked, 0.003207 available
   ✅ Available balances calculated: 5 assets
   ```

2. **XRP/BTC orders show correct USD value:**
   ```
   ✅ Order value for XRP/BTC: $20.44 USD (BTC: 0.00022836 @ $89500.00/BTC)
   ```

3. **ETH/USD uses correct available balance:**
   ```
   📊 Calculated sell volume for ETH/USD: 0.000534 ETH (from 0.003207 available after 95%, 0.003207 total available, 6 orders)
   ```

4. **No more "Insufficient funds" errors** (when there's actually available balance)

## 📝 Notes

- The new code calculates available balance by subtracting locked funds from total balance
- XRP/BTC order values are now converted from BTC to USD using BTC/USD price
- All balance calculations now use `available_balances` instead of `balances`
- Debug logging shows exactly what balances are being used

