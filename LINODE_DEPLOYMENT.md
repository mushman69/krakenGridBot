# GridBot Linode Deployment Guide
========================================

## Prerequisites
- Linode server with Docker and Docker Compose installed
- Your Kraken API key and secret
- WinSCP or similar tool for file transfer

## Step 1: Prepare Local Files

1. Ensure your kraken.env file has your actual credentials:
   ```
   KRAKEN_API_KEY=your_actual_api_key
   KRAKEN_API_SECRET=your_actual_secret_key
   DATABASE_FILE=/app/data/gridbot_pnl.db
   PNL_REPORT_INTERVAL=300
   ```

2. Test locally first (recommended):
   ```bash
   python docker-deploy.py setup
   python docker-deploy.py logs
   ```

## Step 2: Create Deployment Package

1. Create a compressed package of all necessary files:
   ```bash
   # Create a clean directory structure
   mkdir gridbot-deploy
   
   # Copy essential files
   copy improved_gridbot.py gridbot-deploy/
   copy pnl_analyzer.py gridbot-deploy/
   copy db_viewer.py gridbot-deploy/
   copy docker-compose.yml gridbot-deploy/
   copy Dockerfile gridbot-deploy/
   copy requirements.txt gridbot-deploy/
   copy docker-deploy.py gridbot-deploy/
   copy .dockerignore gridbot-deploy/
   copy kraken.env gridbot-deploy/
   
   # Create data directories
   mkdir gridbot-deploy\data
   mkdir gridbot-deploy\exports
   mkdir gridbot-deploy\charts
   mkdir gridbot-deploy\logs
   
   # Create a compressed archive
   tar -czf gridbot-linode.tar.gz gridbot-deploy/
   ```

## Step 3: Transfer to Linode

1. Use WinSCP to connect to your Linode server
2. Upload gridbot-linode.tar.gz to your home directory
3. Connect via SSH to your Linode server

## Step 4: Deploy on Linode

1. Extract the files:
   ```bash
   tar -xzf gridbot-linode.tar.gz
   cd gridbot-deploy
   ```

2. Install Docker and Docker Compose (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. Verify your kraken.env file:
   ```bash
   cat kraken.env
   ```

4. Deploy the GridBot:
   ```bash
   python3 docker-deploy.py setup
   ```

## Step 5: Monitor and Manage

1. Check status:
   ```bash
   python3 docker-deploy.py status
   ```

2. View logs:
   ```bash
   python3 docker-deploy.py logs
   ```

3. Check PnL reports:
   ```bash
   python3 docker-deploy.py analyze
   ```

4. Health check:
   ```bash
   python3 docker-deploy.py health
   ```

## Step 6: Set Up Automatic Startup (Optional)

1. Create a systemd service:
   ```bash
   sudo nano /etc/systemd/system/gridbot.service
   ```

2. Add this content:
   ```ini
   [Unit]
   Description=Kraken GridBot
   Requires=docker.service
   After=docker.service

   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/home/yourusername/gridbot-deploy
   ExecStart=/usr/bin/python3 docker-deploy.py start
   ExecStop=/usr/bin/python3 docker-deploy.py stop
   User=yourusername

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable gridbot.service
   sudo systemctl start gridbot.service
   ```

## Troubleshooting

1. If container won't start:
   ```bash
   python3 docker-deploy.py logs-tail --tail 100
   ```

2. If API credentials fail:
   ```bash
   docker exec kraken_gridbot_pnl env | grep KRAKEN
   ```

3. If database issues:
   ```bash
   python3 docker-deploy.py verify-pnl
   ```

4. Clean restart:
   ```bash
   python3 docker-deploy.py stop
   python3 docker-deploy.py clean
   python3 docker-deploy.py build
   python3 docker-deploy.py start
   ```

## Security Notes

- Keep your kraken.env file secure (600 permissions)
- Consider using a firewall to restrict access
- Regularly backup your data directory
- Monitor logs for suspicious activity

## Backup Strategy

1. Manual backup:
   ```bash
   python3 docker-deploy.py backup
   ```

2. Automated backup script:
   ```bash
   #!/bin/bash
   cd /home/yourusername/gridbot-deploy
   python3 docker-deploy.py backup
   # Optional: Upload to cloud storage
   ```

## Support

- Check logs: `python3 docker-deploy.py logs`
- Run health check: `python3 docker-deploy.py health`
- View PnL reports: `python3 docker-deploy.py analyze`
