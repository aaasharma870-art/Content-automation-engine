#!/bin/bash

# ACE v1.5 - Cloud Deployment Script (Ubuntu 20.04/22.04)
# Usage: ./deploy.sh

set -e

echo "=== ☁️  ACE v1.5 Cloud Deployer ==="
echo "Target: Ubuntu VPS (DigitalOcean/AWS/Hetzner)"

# 1. Update System
echo "\n🔄 Updating System Packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Docker & Compose
if ! command -v docker &> /dev/null
then
    echo "\n🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed."
else
    echo "✅ Docker already installed."
fi

if ! command -v docker-compose &> /dev/null
then
    echo "\n🐳 Installing Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
    # Alias if needed, but newer docker uses 'docker compose'
    echo "✅ Docker Compose plugin installed."
fi

# 3. Setup Project
echo "\n📂 Setting up Project Directory..."
PROJECT_DIR="Content-automation-engine"

if [ -d "$PROJECT_DIR" ]; then
    echo "   Repo exists. Pulling latest..."
    cd $PROJECT_DIR
    git pull
else
    echo "   Cloning repository..."
    git clone https://github.com/aaasharma870-art/Content-automation-engine.git
    cd $PROJECT_DIR
fi

# 4. Environment Configuration
if [ ! -f ".env" ]; then
    echo "\n⚠️  Configuring Environment..."
    cp .env.example .env
    echo "❗ IMPORTANT: You need to edit .env with your API keys."
    echo "   Running 'nano .env' now..."
    read -p "Press Enter to open editor..."
    nano .env
fi

# 5. Launch
echo "\n🚀 Launching Stack..."
docker compose up -d --build

echo "\n=== ✅ Deployment Complete! ==="
echo "Status: System is running in background."
echo "API: http://$(curl -s ifconfig.me):8000/docs"
echo "Grafana: http://$(curl -s ifconfig.me):3000"
echo "MinIO: http://$(curl -s ifconfig.me):9001"
