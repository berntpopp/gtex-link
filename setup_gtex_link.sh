#!/bin/bash

# setup_gtex_link.sh - Comprehensive setup script for GTEx-Link with Docker and NPM
# This script automates initial setup for GTEx-Link deployment with Docker and Nginx Proxy Manager

# Exit on error
set -e

# Print colored output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== GTEx-Link Docker + NPM Setup ===${NC}"
echo "This script will prepare your environment for running GTEx-Link with Nginx Proxy Manager."
echo "GTEx-Link provides both REST API and MCP access to GTEx Portal genetic expression data."

# --- Dependency Checks ---
echo -e "\n${YELLOW}Step 0: Checking Dependencies...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed.${NC}"

# Determine docker compose command (V1 vs V2)
if docker compose version &> /dev/null; then
    COMPOSE_COMMAND="docker compose"
    echo "Using Docker Compose V2 (docker compose plugin)."
elif command -v docker-compose &> /dev/null; then
    COMPOSE_COMMAND="docker-compose"
    echo "Using Docker Compose V1 (docker-compose command)."
else
    echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is available (using '$COMPOSE_COMMAND').${NC}"

if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is not installed. Please install curl for API testing.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ curl is installed.${NC}"

# Ensure we're in the repository root directory
if [ ! -f "docker/docker-compose.npm.yml" ] || [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Key project files (docker/docker-compose.npm.yml, pyproject.toml) not found.${NC}"
    echo "Please ensure you are running this script from the GTEx-Link repository root directory."
    exit 1
fi
echo -e "${GREEN}✓ Running from project root directory.${NC}"

# --- Environment Configuration ---
echo -e "\n${YELLOW}Step 1: Checking Docker Environment Configuration (.env.docker)...${NC}"

# Create .env.docker if it doesn't exist
if [ ! -f ".env.docker" ]; then
    echo "'.env.docker' file not found. Creating from example..."
    if [ ! -f ".env.docker.example" ]; then
        echo -e "${RED}Error: '.env.docker.example' template not found! Cannot create .env.docker.${NC}"
        exit 1
    fi
    cp .env.docker.example .env.docker
    echo -e "${GREEN}✓ Created .env.docker from template.${NC}"
fi

# Ask for base URL configuration
echo ""
echo -e "${BLUE}Domain Configuration${NC}"
echo "Please enter your domain for GTEx-Link deployment:"
echo "Examples: gtex-link.genefoundry.org, gtex-link.mydomain.com"
echo ""

# Get domain from user
while true; do
    read -p "Enter your domain (without https://): " DOMAIN_INPUT

    if [ -z "$DOMAIN_INPUT" ]; then
        echo -e "${RED}Domain cannot be empty. Please try again.${NC}"
        continue
    fi

    # Remove https:// or http:// if user included it
    DOMAIN_INPUT=$(echo "$DOMAIN_INPUT" | sed -E 's|^https?://||')

    # Validate domain format (basic check)
    if [[ ! "$DOMAIN_INPUT" =~ ^[a-zA-Z0-9][a-zA-Z0-9\.-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
        echo -e "${RED}Invalid domain format. Please enter a valid domain (e.g., gtex-link.yourdomain.com).${NC}"
        continue
    fi

    break
done

# Construct URLs
GTEX_API_URL="https://$DOMAIN_INPUT"
GTEX_MCP_URL="https://$DOMAIN_INPUT/mcp"

echo ""
echo -e "${GREEN}Using configuration:${NC}"
echo "  API URL: $GTEX_API_URL"
echo "  MCP URL: $GTEX_MCP_URL"
echo ""

# Update .env.docker with the provided domain
sed -i "s|GTEX_API_URL_PUBLIC=.*|GTEX_API_URL_PUBLIC=$GTEX_API_URL|g" .env.docker
sed -i "s|GTEX_MCP_URL_PUBLIC=.*|GTEX_MCP_URL_PUBLIC=$GTEX_MCP_URL|g" .env.docker

# Ask about NPM network name
echo -e "${BLUE}Docker Network Configuration${NC}"
echo "What is your NPM (Nginx Proxy Manager) Docker network name?"
echo "Common values: npm_default, nginx-proxy-manager_default"
echo ""

read -p "NPM network name [npm_default]: " NPM_NETWORK_INPUT
NPM_NETWORK_NAME=${NPM_NETWORK_INPUT:-npm_default}

# Update .env.docker with network name
sed -i "s|NPM_SHARED_NETWORK_NAME=.*|NPM_SHARED_NETWORK_NAME=$NPM_NETWORK_NAME|g" .env.docker

echo -e "${GREEN}✓ Environment configuration updated automatically.${NC}"

# Ask if user wants to edit manually
echo ""
read -p "Would you like to edit .env.docker manually for additional settings? (y/N): " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v nano &> /dev/null; then
        echo "Opening .env.docker in nano for you. Save (Ctrl+O, Enter) and Exit (Ctrl+X) when done."
        sleep 2
        nano .env.docker
    else
        echo "Please manually edit the '.env.docker' file now."
        read -p "Press Enter once you have edited and saved .env.docker..."
    fi
fi

echo "Loading environment variables from .env.docker..."
if [ -f ".env.docker" ]; then
    set -o allexport
    source ".env.docker"
    set +o allexport
else
    echo -e "${RED}Error: .env.docker file is still missing after attempting to create it!${NC}"
    exit 1
fi

# Use the configured values (they should now be set from user input)
GTEX_API_URL_PUBLIC=${GTEX_API_URL_PUBLIC:-$GTEX_API_URL}
GTEX_MCP_URL_PUBLIC=${GTEX_MCP_URL_PUBLIC:-$GTEX_MCP_URL}
NPM_SHARED_NETWORK_NAME=${NPM_SHARED_NETWORK_NAME:-$NPM_NETWORK_NAME}

if [ -z "$GTEX_API_URL_PUBLIC" ]; then
    echo -e "${RED}Error: GTEX_API_URL_PUBLIC is not set in .env.docker.${NC}"
    echo "Please set it to your domain (e.g., https://gtex-link.yourdomain.com)"
    exit 1
fi
echo -e "${GREEN}✓ GTEX_API_URL_PUBLIC is set to: $GTEX_API_URL_PUBLIC${NC}"

# --- Shared Docker Network with NPM ---
echo -e "\n${YELLOW}Step 2: Checking Shared Docker Network '$NPM_SHARED_NETWORK_NAME'...${NC}"
if ! docker network inspect "$NPM_SHARED_NETWORK_NAME" &> /dev/null; then
    echo -e "${YELLOW}Warning: Docker network '$NPM_SHARED_NETWORK_NAME' does not exist.${NC}"
    echo "This network is required for NPM integration. You can:"
    echo "  1. Create it manually: docker network create $NPM_SHARED_NETWORK_NAME"
    echo "  2. Ensure NPM is running (it usually creates this network automatically)"
    echo ""
    read -p "Do you want me to create the network now? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker network create "$NPM_SHARED_NETWORK_NAME"
        echo -e "${GREEN}✓ Created Docker network '$NPM_SHARED_NETWORK_NAME'.${NC}"
    else
        echo -e "${YELLOW}⚠️  Continuing without creating network. Ensure it exists before deployment.${NC}"
    fi
else
    echo -e "${GREEN}✓ Docker network '$NPM_SHARED_NETWORK_NAME' found.${NC}"
fi

# --- GTEx Portal API Connectivity Test ---
echo -e "\n${YELLOW}Step 3: Testing GTEx Portal API Connectivity...${NC}"
echo "Testing connection to GTEx Portal API (https://gtexportal.org/api/v2/)..."

GTEX_TEST_URL="https://gtexportal.org/api/v2/reference/geneSearch?geneId=BRCA1&gencodeVersion=v26&genomeBuild=GRCh38%2Fhg38&pageSize=1"
if curl -f -s --max-time 10 "$GTEX_TEST_URL" > /dev/null; then
    echo -e "${GREEN}✓ GTEx Portal API is accessible.${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Could not reach GTEx Portal API. This may affect functionality.${NC}"
    echo "   Check your internet connection and firewall settings."
    echo "   GTEx-Link requires outbound HTTPS access to gtexportal.org"
fi

# --- Build GTEx-Link Docker Images ---
echo -e "\n${YELLOW}Step 4: Building GTEx-Link Docker images...${NC}"
echo "This may take a few minutes for the first build..."
echo "Building API and MCP containers..."
cd docker
$COMPOSE_COMMAND -f docker-compose.npm.yml --env-file ../.env.docker build
cd ..
echo -e "${GREEN}✓ GTEx-Link API and MCP image builds completed.${NC}"

# --- Container Health Test ---
echo -e "\n${YELLOW}Step 5: Testing GTEx-Link container functionality...${NC}"
echo "Starting temporary containers to test API and MCP endpoints..."

# Start both containers for testing
cd docker
echo "Starting API container for testing..."
API_CONTAINER_ID=$($COMPOSE_COMMAND -f docker-compose.npm.yml --env-file ../.env.docker run -d --rm gtex_link_api)

echo "Starting MCP container for testing..."
MCP_CONTAINER_ID=$($COMPOSE_COMMAND -f docker-compose.npm.yml --env-file ../.env.docker run -d --rm gtex_link_mcp)
cd ..

# Wait for containers to be ready
echo "Waiting for containers to initialize..."
sleep 15

# Test API health endpoint
echo "Testing API health endpoint..."
if docker exec "$API_CONTAINER_ID" curl -f -s http://localhost:8000/api/health/ > /dev/null; then
    echo -e "${GREEN}✓ API health endpoint is working.${NC}"
else
    echo -e "${RED}✗ API health endpoint failed.${NC}"
fi

# Test MCP endpoint
echo "Testing MCP endpoint..."
if docker exec "$MCP_CONTAINER_ID" curl -f -s http://localhost:8001/mcp > /dev/null; then
    echo -e "${GREEN}✓ MCP endpoint is working.${NC}"
else
    echo -e "${YELLOW}⚠️  MCP endpoint test failed. This may be expected for HTTP transport.${NC}"
fi

# Test GTEx API proxy functionality
echo "Testing GTEx API proxy functionality..."
if docker exec "$API_CONTAINER_ID" curl -f -s --max-time 15 "http://localhost:8000/api/reference/geneSearch?geneId=BRCA1" > /dev/null; then
    echo -e "${GREEN}✓ GTEx API proxy is working.${NC}"
else
    echo -e "${YELLOW}⚠️  GTEx API proxy test failed. Check GTEx Portal availability.${NC}"
fi

# Stop test containers
echo "Cleaning up test containers..."
docker stop "$API_CONTAINER_ID" > /dev/null
docker stop "$MCP_CONTAINER_ID" > /dev/null
echo -e "${GREEN}✓ Container functionality tests completed.${NC}"

# --- Configuration Validation ---
echo -e "\n${YELLOW}Step 6: Validating Docker Compose configuration...${NC}"
cd docker
if $COMPOSE_COMMAND -f docker-compose.npm.yml --env-file ../.env.docker config > /dev/null; then
    echo -e "${GREEN}✓ Docker Compose configuration is valid.${NC}"
else
    echo -e "${RED}✗ Docker Compose configuration has errors.${NC}"
    exit 1
fi
cd ..

# --- Final Instructions ---
echo ""
echo -e "${GREEN}=== GTEx-Link Setup Script Finished ===${NC}"
echo -e "\n${YELLOW}IMPORTANT NEXT STEPS:${NC}"
echo ""

# Extract domain from URL for cleaner display
DOMAIN_NAME=$(echo "$GTEX_API_URL_PUBLIC" | sed -E 's|https?://||' | sed -E 's|/.*||')

echo -e "${BLUE}1. DNS Configuration:${NC}"
echo "   Ensure your DNS record points to this server's public IP:"
echo "   $DOMAIN_NAME -> YOUR_SERVER_IP"
echo ""

echo -e "${BLUE}2. Nginx Proxy Manager Configuration:${NC}"
echo "   Access your NPM Web UI and add a Proxy Host:"
echo "   - Domain Names: $DOMAIN_NAME"
echo "   - Scheme: http"
echo "   - Forward Hostname/IP: gtex_link_api"
echo "   - Forward Port: 8000"
echo "   - Cache Assets: Yes"
echo "   - Block Common Exploits: Yes"
echo "   - Websockets Support: Yes"
echo "   - SSL: Request a new SSL Certificate, enable 'Force SSL'"
echo ""
echo "   ${YELLOW}IMPORTANT:${NC} Add these custom locations in the Advanced tab:"
echo "   ${GREEN}Custom Location 1:${NC}"
echo "     Location: /mcp"
echo "     Proxy Pass: http://gtex_link_mcp:8001"
echo ""
echo "   ${GREEN}Custom Location 2 (Optional):${NC}"
echo "     Location: /api/health/"
echo "     Custom config: access_log off;"
echo ""
echo "   ${RED}Without the /mcp custom location, MCP won't work!${NC}"
echo ""

echo -e "${BLUE}3. Start GTEx-Link:${NC}"
echo "   Run from the GTEx-Link project root directory:"
echo "   ${GREEN}$COMPOSE_COMMAND -f docker/docker-compose.npm.yml --env-file .env.docker up -d --build${NC}"
echo ""

echo -e "${BLUE}4. Test Your Deployment:${NC}"
echo "   Once DNS propagates and NPM is configured with custom locations:"
echo "   - API Health: ${GREEN}curl $GTEX_API_URL_PUBLIC/api/health/${NC}"
echo "   - Gene Search: ${GREEN}curl '$GTEX_API_URL_PUBLIC/api/reference/geneSearch?geneId=BRCA1'${NC}"
echo "   - MCP Endpoint: ${GREEN}curl $GTEX_MCP_URL_PUBLIC${NC} ${YELLOW}(requires /mcp custom location)${NC}"
echo "   - API Documentation: ${GREEN}$GTEX_API_URL_PUBLIC/docs${NC}"
echo ""
echo "   ${YELLOW}Note:${NC} API calls route to gtex_link_api:8000, MCP calls route to gtex_link_mcp:8001"
echo ""

echo -e "${BLUE}5. MCP Integration:${NC}"
echo "   For Claude Desktop, add to your MCP configuration:"
echo '   {'
echo '     "mcpServers": {'
echo "       \"gtex-link\": {"
echo "         \"command\": \"node\","
echo "         \"args\": [\"path/to/mcp-client.js\", \"$GTEX_MCP_URL_PUBLIC\"]"
echo '       }'
echo '     }'
echo '   }'
echo ""

echo -e "${GREEN}Setup complete! 🎉${NC}"
echo "GTEx-Link is ready for deployment with NPM."

# --- Development Mode Instructions ---
echo ""
echo -e "${YELLOW}For local development (without NPM):${NC}"
echo "Run: ${GREEN}$COMPOSE_COMMAND -f docker/docker-compose.dev.yml up${NC}"
echo "Test: ${GREEN}curl http://localhost:8002/api/health/${NC}"
