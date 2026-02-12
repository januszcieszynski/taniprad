#!/bin/bash
# Deployment script for DigitalOcean Droplet
# Usage: ./deploy.sh

set -e  # Exit on error

echo "🚀 Starting deployment of Tani Prąd..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/taniprad"
NGINX_SITE="/etc/nginx/sites-available/prad.januszcieszynski.pl"
FRONTEND_DIR="/var/www/taniprad"

echo -e "${YELLOW}📦 Pulling latest code from GitHub...${NC}"
cd $APP_DIR
git pull origin main

echo -e "${YELLOW}🔨 Building and restarting backend...${NC}"
docker-compose -f docker-compose.droplet.yml down
docker-compose -f docker-compose.droplet.yml build --no-cache
docker-compose -f docker-compose.droplet.yml up -d

echo -e "${YELLOW}📄 Deploying frontend...${NC}"
# Create frontend directory if it doesn't exist
sudo mkdir -p $FRONTEND_DIR

# Copy frontend files
sudo cp $APP_DIR/index.html $FRONTEND_DIR/

# Set proper permissions
sudo chown -R www-data:www-data $FRONTEND_DIR
sudo chmod -R 755 $FRONTEND_DIR

echo -e "${YELLOW}🔧 Checking nginx configuration...${NC}"
if [ -f "$NGINX_SITE" ]; then
    # Test nginx configuration
    if sudo nginx -t; then
        echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
        echo -e "${YELLOW}🔄 Reloading nginx...${NC}"
        sudo systemctl reload nginx
    else
        echo -e "${RED}✗ Nginx configuration has errors!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Nginx site configuration not found at $NGINX_SITE${NC}"
    echo "Please set up nginx configuration first. See DROPLET_SETUP.md"
fi

echo -e "${YELLOW}🧹 Cleaning up old Docker images...${NC}"
docker system prune -f

echo -e "${YELLOW}📊 Checking service status...${NC}"
docker-compose -f docker-compose.droplet.yml ps

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Check status:"
echo "  Backend:  curl http://localhost:8080/api/health"
echo "  Frontend: curl https://prad.januszcieszynski.pl"
echo ""
echo "View logs:"
echo "  docker-compose -f docker-compose.droplet.yml logs -f backend"
