@echo off
REM GridBot Linode Deployment Package Creator
REM Run this from the gridbot-clean directory

echo ================================================
echo  GridBot Linode Deployment Package Creator
echo ================================================

echo.
echo Checking current directory...
if not exist "improved_gridbot.py" (
    echo ERROR: improved_gridbot.py not found!
    echo Please run this script from the gridbot-clean directory
    pause
    exit /b 1
)

echo ✅ Found improved_gridbot.py

echo.
echo Creating deployment package directory...
if exist "gridbot-linode-deploy" rmdir /s /q "gridbot-linode-deploy"
mkdir "gridbot-linode-deploy"

echo.
echo Copying essential files...
copy "improved_gridbot.py" "gridbot-linode-deploy\" >nul
copy "pnl_analyzer.py" "gridbot-linode-deploy\" >nul
copy "db_viewer.py" "gridbot-linode-deploy\" >nul
copy "docker-compose.yml" "gridbot-linode-deploy\" >nul
copy "Dockerfile" "gridbot-linode-deploy\" >nul
copy "requirements.txt" "gridbot-linode-deploy\" >nul
copy "docker-deploy.py" "gridbot-linode-deploy\" >nul
copy ".dockerignore" "gridbot-linode-deploy\" >nul
copy "LINODE_DEPLOYMENT.md" "gridbot-linode-deploy\" >nul

echo.
echo Copying API credentials...
if exist "kraken.env" (
    copy "kraken.env" "gridbot-linode-deploy\" >nul
    echo ✅ Copied kraken.env with your API credentials
) else (
    echo ⚠️  WARNING: kraken.env not found!
    echo Please create kraken.env with your API credentials before deploying
    copy "kraken.env.example" "gridbot-linode-deploy\kraken.env" >nul
    echo Created template kraken.env - ADD YOUR CREDENTIALS!
)

echo.
echo Creating data directories...
mkdir "gridbot-linode-deploy\data" >nul 2>&1
mkdir "gridbot-linode-deploy\exports" >nul 2>&1
mkdir "gridbot-linode-deploy\charts" >nul 2>&1
mkdir "gridbot-linode-deploy\logs" >nul 2>&1

echo.
echo Creating deployment instructions...
echo # GridBot Linode Deployment Instructions > "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo ============================================= >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo. >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo 1. Upload this entire folder to your Linode server >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo 2. SSH into your Linode server >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo 3. Navigate to this directory >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo 4. Run: python3 docker-deploy.py setup >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo 5. Monitor: python3 docker-deploy.py logs >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo. >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"
echo See LINODE_DEPLOYMENT.md for detailed instructions >> "gridbot-linode-deploy\DEPLOY_INSTRUCTIONS.txt"

echo.
echo ✅ Deployment package created successfully!
echo.
echo 📁 Package location: gridbot-linode-deploy\
echo 📋 Files included:
dir /b "gridbot-linode-deploy\"

echo.
echo 🚀 Next Steps:
echo 1. Check kraken.env has your real API credentials
echo 2. Use WinSCP to upload gridbot-linode-deploy folder to Linode
echo 3. SSH to Linode and run: python3 docker-deploy.py setup
echo 4. Follow LINODE_DEPLOYMENT.md for detailed instructions

echo.
echo ⚠️  IMPORTANT: Verify kraken.env contains your actual API credentials!
if exist "gridbot-linode-deploy\kraken.env" (
    echo.
    echo Current kraken.env contents:
    type "gridbot-linode-deploy\kraken.env"
)

echo.
pause
