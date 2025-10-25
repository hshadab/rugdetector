#!/bin/bash
# Render.com Helper Script
# Quick commands for managing your Render deployment

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load configuration
if [ -f .render-config ]; then
    source .render-config
fi

echo -e "${BLUE}🚀 Render.com Helper for RugDetector${NC}\n"

# Function to show menu
show_menu() {
    echo "What would you like to do?"
    echo ""
    echo "  1) 📊 Open Dashboard"
    echo "  2) 🔍 Check Deployment Status"
    echo "  3) 📝 View Recent Logs"
    echo "  4) 🔄 Trigger Manual Deploy"
    echo "  5) 💚 Check Health"
    echo "  6) 🌐 Open Live Site"
    echo "  7) ❌ Exit"
    echo ""
}

# Function to open dashboard
open_dashboard() {
    echo -e "${GREEN}Opening Render.com dashboard...${NC}"
    if command -v xdg-open &> /dev/null; then
        xdg-open "$RENDER_BLUEPRINT_URL"
    elif command -v open &> /dev/null; then
        open "$RENDER_BLUEPRINT_URL"
    else
        echo "Dashboard URL: $RENDER_BLUEPRINT_URL"
    fi
}

# Function to check deployment status
check_status() {
    echo -e "${GREEN}Checking deployment status...${NC}"
    curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services" | \
        jq -r '.[] | select(.name=="rugdetector") | "Status: \(.status)\nLast Deploy: \(.updatedAt)"'
}

# Function to view logs
view_logs() {
    echo -e "${GREEN}Fetching recent logs...${NC}"
    echo "Visit: https://dashboard.render.com/web/$SERVICE_NAME/logs"
    echo ""
    echo "Or use Render CLI:"
    echo "  render logs -s $SERVICE_NAME --tail 100"
}

# Function to trigger deploy
trigger_deploy() {
    echo -e "${YELLOW}⚠️  Manual deploy will restart your service${NC}"
    echo "This will pull latest from GitHub and redeploy."
    echo ""
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Triggering deploy...${NC}"
        echo "Visit dashboard to confirm: $RENDER_BLUEPRINT_URL"
    fi
}

# Function to check health
check_health() {
    echo -e "${GREEN}Checking service health...${NC}"
    RESPONSE=$(curl -s -w "\n%{http_code}" "$SERVICE_URL/health")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Service is healthy!${NC}"
        echo "$BODY" | jq '.'
    else
        echo -e "${YELLOW}⚠️  Health check failed (HTTP $HTTP_CODE)${NC}"
        echo "$BODY"
    fi
}

# Function to open live site
open_site() {
    echo -e "${GREEN}Opening live site...${NC}"
    if command -v xdg-open &> /dev/null; then
        xdg-open "$SERVICE_URL"
    elif command -v open &> /dev/null; then
        open "$SERVICE_URL"
    else
        echo "Live site: $SERVICE_URL"
    fi
}

# Main menu loop
while true; do
    show_menu
    read -p "Enter choice [1-7]: " choice
    echo ""

    case $choice in
        1) open_dashboard ;;
        2) check_status ;;
        3) view_logs ;;
        4) trigger_deploy ;;
        5) check_health ;;
        6) open_site ;;
        7) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option. Please try again." ;;
    esac

    echo ""
    read -p "Press enter to continue..."
    clear
done
