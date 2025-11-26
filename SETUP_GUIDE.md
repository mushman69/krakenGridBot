# GridBot with PnL Tracking - Complete Setup Guide

## 🚀 **Features**
- **Multi-pair grid trading** (XRP/BTC + ETH/USD)
- **Real-time PnL tracking** with SQLite database
- **Docker deployment** with persistent data storage
- **Advanced analytics** and performance monitoring
- **Order execution tracking** and portfolio analysis

## 📁 **Project Structure**
```
gridbot-clean/
├── improved_gridbot.py          # Main bot with database integration
├── pnl_analyzer.py              # PnL analysis and reporting
├── db_viewer.py                 # Database viewer utility
├── docker-deploy.py             # Docker management script
├── docker-compose.yml           # Docker service configuration
├── Dockerfile                   # Docker image definition
├── requirements.txt             # Python dependencies
├── kraken.env                   # Your API credentials (create this)
├── kraken.env.example           # Template for credentials
├── docker.env.example          # Docker environment template
├── README.md                    # Project documentation
├── README_PnL.md               # PnL tracking documentation
├── .dockerignore               # Docker ignore file
├── .gitignore                  # Git ignore file
├── data/                       # Database and persistent data
├── exports/                    # CSV exports and reports
├── charts/                     # Generated charts and graphs
└── logs/                       # Application logs
```

## 🛠️ **Setup Instructions**

### **Option A: Docker Deployment (Recommended)**

#### **Prerequisites**
- Docker and Docker Compose installed
- Kraken API credentials

#### **Step 1: Configure API Credentials**
```bash
# Copy the example file
cp kraken.env.example kraken.env

# Edit with your credentials
nano kraken.env
```

Add your Kraken API credentials:
```
KRAKEN_API_KEY=your_api_key_here
KRAKEN_API_SECRET=your_api_secret_here
```

#### **Step 2: Deploy with Docker**
```bash
# Complete setup and deployment
python docker-deploy.py setup

# Monitor the bot
python docker-deploy.py logs

# Check status
python docker-deploy.py status
```

#### **Step 3: Monitor and Analyze**
```bash
# Live PnL monitoring
python docker-deploy.py monitor

# Run PnL analysis
python docker-deploy.py analyze

# Check database status
python docker-deploy.py db-status

# Health check
python docker-deploy.py health
```

### **Option B: Local Installation**

#### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

#### **Step 2: Configure Environment**
```bash
cp kraken.env.example kraken.env
# Edit kraken.env with your API credentials
```

#### **Step 3: Run the Bot**
```bash
# Start the bot with PnL tracking
python improved_gridbot.py

# Monitor PnL (in another terminal)
python pnl_analyzer.py --live

# View database
python db_viewer.py
```

## 🐳 **Docker Commands Reference**

| Command | Description |
|---------|-------------|
| `python docker-deploy.py setup` | Complete setup and deployment |
| `python docker-deploy.py start` | Start the GridBot container |
| `python docker-deploy.py stop` | Stop the GridBot container |
| `python docker-deploy.py restart` | Restart the GridBot container |
| `python docker-deploy.py logs` | Show live logs |
| `python docker-deploy.py status` | Show container status |
| `python docker-deploy.py monitor` | Start PnL monitoring |
| `python docker-deploy.py analyze` | Run PnL analysis |
| `python docker-deploy.py backup` | Backup database and data |
| `python docker-deploy.py health` | Comprehensive health check |
| `python docker-deploy.py clean` | Clean up Docker resources |
| `python docker-deploy.py update` | Update and restart bot |

## 📊 **Database & PnL Features**

### **Automatic Tracking**
- Every order placement recorded
- All executions tracked with timestamps
- Portfolio snapshots for trend analysis
- Real-time PnL calculations

### **Reports & Analytics**
- Win rate and performance metrics
- Hourly PnL tracking
- Trading volume analysis
- Pair-specific performance

### **Data Persistence**
- SQLite database stored in `./data/` volume
- Automatic backups available
- CSV exports for external analysis
- Charts and visualizations

## 🔧 **Configuration**

### **Trading Pairs**
- **XRP/BTC** (60% allocation): 2.5% grid spacing, 20 orders/side
- **ETH/USD** (40% allocation): 1.5% grid spacing, 18 orders/side

### **Key Settings**
- Auto-rebalancing: DISABLED (let winners run)
- Order monitoring: Every 10 seconds
- PnL reporting: Every 5 minutes
- Trend protection: ENABLED for XRP/BTC

### **Environment Variables**
```bash
DATABASE_FILE=/app/data/gridbot_pnl.db    # Database path
PNL_REPORT_INTERVAL=300                   # Report frequency (seconds)
DOCKER_DEPLOYMENT=1                       # Docker mode flag
TZ=UTC                                    # Timezone
```

## 🛡️ **Security & Safety**

### **API Permissions Required**
- Query Funds
- Create & Modify Orders
- Query Open Orders and Trade History

### **Risk Management**
- 95% balance utilization (5% reserve)
- Dynamic order sizing based on available funds
- Trend protection for cyclical pairs
- Maximum allocation limits

## 📈 **Monitoring & Maintenance**

### **Health Checks**
```bash
# Comprehensive system check
python docker-deploy.py health

# Database status
python docker-deploy.py db-status

# Container resource usage
python docker-deploy.py status
```

### **Data Backup**
```bash
# Create backup
python docker-deploy.py backup

# Backups stored in: backups/YYYYMMDD_HHMMSS.tar.gz
```

### **Log Analysis**
```bash
# Live logs
python docker-deploy.py logs

# Last 100 lines
python docker-deploy.py logs-tail --tail 100
```

## 🔄 **Updates & Maintenance**

### **Updating the Bot**
```bash
# Update code and restart
python docker-deploy.py update

# Or manual update:
python docker-deploy.py stop
# Update files
python docker-deploy.py build
python docker-deploy.py start
```

### **Database Maintenance**
```bash
# View database contents
python db_viewer.py

# Generate reports
python pnl_analyzer.py --export

# Backup before maintenance
python docker-deploy.py backup
```

## 🆘 **Troubleshooting**

### **Common Issues**

**Docker not starting:**
```bash
python docker-deploy.py health
# Check output for specific issues
```

**Database issues:**
```bash
python docker-deploy.py db-status
# Verify database file exists and is accessible
```

**API connection problems:**
```bash
# Verify credentials in kraken.env
# Check Kraken API permissions
# Test with: python docker-deploy.py health
```

**Resource issues:**
```bash
# Check container resources
python docker-deploy.py status

# Clean up Docker
python docker-deploy.py clean
```

## 📞 **Support**

For issues or questions:
1. Check the health status: `python docker-deploy.py health`
2. Review logs: `python docker-deploy.py logs`
3. Verify configuration files are correct
4. Ensure Kraken API credentials have proper permissions

---

**Ready to start trading with advanced PnL tracking!** 🚀
