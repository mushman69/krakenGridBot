# 🚀 Enhanced GridBot - Clean Implementation

This is a clean, essential implementation of the Enhanced Multi-Pair GridBot with Docker deployment capabilities.

## 🎯 Strategy Overview

**AGGRESSIVE GRIDBOT - OPTIMIZED FOR ALTCOIN CYCLE**

- **Strategy**: High-risk, high-reward grid trading during altcoin season
- **Target Returns**: 37-59% annual (XRP/BTC 45-75%, ETH/USD 25-35%)
- **Market Timing**: Early altcoin season (BTC dominance dropping)

### Trading Pairs:
- **XRP/BTC (60%)**: Cyclical opportunity, 1.5% grid, 20 orders/side
- **ETH/USD (40%)**: Stable performer, 0.7% grid, 18 orders/side

### Smart Features:
- ❌ Auto-rebalancing DISABLED (let winners run)
- 🧠 Cycle-aware protection for trending assets  
- ⚡ Aggressive monitoring (20s intervals)
- 🎯 Dense grids for maximum capture
- 🛡️ Trend protection logic

## 📁 Files Included

### Core Application
- `improved_gridbot.py` - Main trading bot implementation
- `requirements.txt` - Python dependencies

### Docker Deployment
- `docker-deploy.py` - Interactive Docker deployment manager
- `Dockerfile` - Container configuration
- `docker-compose.yml` - Service orchestration
- `docker-entrypoint.sh` - Container startup script

### Configuration
- `kraken.env.example` - API credentials template
- `.dockerignore` - Docker build optimization
- `.gitignore` - Git version control

## 🚀 Quick Start

### 1. Setup API Credentials
```bash
cp kraken.env.example kraken.env
# Edit kraken.env with your Kraken API credentials
```

### 2. Docker Deployment (Recommended)
```bash
python docker-deploy.py
# Choose option 1: Deploy GridBot (build & start)
```

### 3. Manual Python Deployment
```bash
pip install -r requirements.txt
python improved_gridbot.py
```

## 🔧 Configuration

The bot is pre-configured with aggressive settings for altcoin season:

- **XRP/BTC**: 1.5% grid spacing, 60% target allocation
- **ETH/USD**: 0.7% grid spacing, 40% target allocation
- **Order Check**: Every 20 seconds (aggressive monitoring)
- **Rebalance Tolerance**: 25% (wide tolerance to let winners run)

## 🐳 Docker Management

Use `docker-deploy.py` for easy container management:

1. 🚀 Deploy GridBot (build & start)
2. 📊 Show status
3. 📋 Show logs
4. 🔄 Restart GridBot
5. 🛑 Stop GridBot
6. 🔨 Rebuild container
7. 🧹 Clean up
8. ❌ Exit

## ⚠️ Important Notes

- **High-Risk Strategy**: This is an aggressive configuration optimized for altcoin cycles
- **API Permissions**: Ensure your Kraken API key has trading permissions
- **Minimum Balance**: Ensure sufficient balance for grid orders
- **Monitoring**: The bot will cancel existing orders on startup

## 🎯 Expected Performance

- **Overall Target**: 37-59% annual returns
- **XRP/BTC**: 45-75% (cyclical opportunity)
- **ETH/USD**: 25-35% (stable performance)

## 🛡️ Safety Features

- **10% Reserve**: Bot uses only 90% of available balances
- **Smart Rebalancing**: Protects trending assets from rebalancing
- **Docker Isolation**: Secure containerized deployment
- **Enhanced Nonce Handling**: Prevents API conflicts

## 📞 Support

This is a clean implementation focusing on essential functionality. For issues:

1. Check Docker logs: `docker-compose logs -f gridbot`
2. Verify API credentials in `kraken.env`
3. Ensure sufficient account balance
4. Check Kraken API status

---

**Disclaimer**: Trading cryptocurrencies involves risk. This bot is for educational purposes. Trade responsibly.
