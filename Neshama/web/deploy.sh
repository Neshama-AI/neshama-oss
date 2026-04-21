#!/bin/bash

# Neshama Web Deployment Script v0.4

set -e

APP_DIR="/opt/neshama"
SERVICE_NAME="neshama-web"

echo "🚀 Starting Neshama Web Deployment..."

# Stop existing service
echo "📦 Stopping existing service..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true

# Backup current version
if [ -d "$APP_DIR" ]; then
    echo "💾 Backing up current version..."
    sudo cp -r $APP_DIR ${APP_DIR}.backup.$(date +%Y%m%d%H%M%S)
fi

# Deploy new version
echo "📂 Deploying new version..."
sudo cp -r ./web $APP_DIR/
sudo chmod +x $APP_DIR/web/deploy.sh

# Install dependencies
echo "📚 Installing dependencies..."
pip install flask gunicorn

# Start service
echo "▶️ Starting service..."
sudo systemctl start $SERVICE_NAME
sudo systemctl enable $SERVICE_NAME

# Verify deployment
echo "✅ Verifying deployment..."
sleep 2
curl -f http://localhost:5000/health || echo "⚠️ Health check failed"

echo "🎉 Deployment complete!"
