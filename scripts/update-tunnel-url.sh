#!/bin/bash

# Cloudflare Tunnel URL Watcher Script
# Monitors cloudflared logs and updates environment files when URL changes

set -e

ENV_FILE="/home/ataide/developer/Ensign/internjobs/.env"
FRONTEND_ENV_FILE="/home/ataide/developer/Ensign/internjobs/frontend/.env.local"
COMPOSE_FILE="/home/ataide/developer/Ensign/internjobs/docker-compose.yml"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Starting Cloudflare Tunnel URL Watcher...${NC}"

# Function to extract URL from cloudflared logs
extract_tunnel_url() {
    docker logs cloudflared 2>&1 | grep -oP 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1
}

# Function to update environment files
update_env_files() {
    local new_url=$1
    
    # Update root .env file
    if grep -q "^NEXTAUTH_URL=" "$ENV_FILE"; then
        sed -i "s|^NEXTAUTH_URL=.*|NEXTAUTH_URL=$new_url|" "$ENV_FILE"
    else
        echo "NEXTAUTH_URL=$new_url" >> "$ENV_FILE"
    fi
    
    if grep -q "^AUTH_URL=" "$ENV_FILE"; then
        sed -i "s|^AUTH_URL=.*|AUTH_URL=$new_url|" "$ENV_FILE"
    else
        echo "AUTH_URL=$new_url" >> "$ENV_FILE"
    fi
    
    # Update frontend .env.local file
    if [ -f "$FRONTEND_ENV_FILE" ]; then
        if grep -q "^NEXTAUTH_URL=" "$FRONTEND_ENV_FILE"; then
            sed -i "s|^NEXTAUTH_URL=.*|NEXTAUTH_URL=$new_url|" "$FRONTEND_ENV_FILE"
        else
            echo "NEXTAUTH_URL=$new_url" >> "$FRONTEND_ENV_FILE"
        fi
        
        if grep -q "^AUTH_URL=" "$FRONTEND_ENV_FILE"; then
            sed -i "s|^AUTH_URL=.*|AUTH_URL=$new_url|" "$FRONTEND_ENV_FILE"
        else
            echo "AUTH_URL=$new_url" >> "$FRONTEND_ENV_FILE"
        fi
        
        if grep -q "^NEXT_PUBLIC_API_URL=" "$FRONTEND_ENV_FILE"; then
            sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=$new_url|" "$FRONTEND_ENV_FILE"
        else
            echo "NEXT_PUBLIC_API_URL=$new_url" >> "$FRONTEND_ENV_FILE"
        fi
    fi
    
    echo -e "${GREEN}✅ Updated environment files with new URL${NC}"
}

# Function to rebuild frontend
rebuild_frontend() {
    echo -e "${YELLOW}🔄 Rebuilding frontend with new URL...${NC}"
    cd /home/ataide/developer/Ensign/internjobs
    docker compose up --build --force-recreate -d frontend
    echo -e "${GREEN}✅ Frontend rebuilt successfully${NC}"
}

# Main loop
previous_url=""
attempts=0
max_attempts=60

echo -e "${BLUE}⏳ Waiting for Cloudflare Tunnel to be ready...${NC}"

while [ $attempts -lt $max_attempts ]; do
    current_url=$(extract_tunnel_url)
    
    if [ -n "$current_url" ]; then
        if [ "$current_url" != "$previous_url" ]; then
            echo -e "${GREEN}🌐 Tunnel URL detected: $current_url${NC}"
            echo -e "${YELLOW}📝 URL changed or first run. Updating configuration...${NC}"
            update_env_files "$current_url"
            rebuild_frontend
            previous_url="$current_url"
            
            echo -e "${GREEN}✨ Tunnel is ready!${NC}"
            echo -e "${BLUE}🔗 Your app is available at: ${GREEN}$current_url${NC}"
            echo -e "${BLUE}📋 Add this to Google Cloud Console OAuth redirect URIs:${NC}"
            echo -e "${GREEN}   $current_url/api/auth/callback/google${NC}"
        fi
        
        # Continue monitoring for URL changes
        sleep 10
        attempts=0
    else
        attempts=$((attempts + 1))
        echo -e "${YELLOW}⏳ Waiting for tunnel... (attempt $attempts/$max_attempts)${NC}"
        sleep 2
    fi
done

echo -e "${YELLOW}⚠️  Timeout waiting for tunnel. Please check cloudflared logs.${NC}"
exit 1
