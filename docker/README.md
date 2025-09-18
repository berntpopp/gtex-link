# GTEx-Link Docker Configurations

This directory contains multiple Docker Compose configurations for different deployment scenarios.

## Available Configurations


### 🌐 NPM Production
**File**: `docker-compose.npm.yml`
**Purpose**: Production deployment with Nginx Proxy Manager
**Containers**: 2 separate containers (API + MCP)
**Ports**: None (NPM handles all routing)
**Features**: Dual-container architecture, NPM network integration, resource limits

**Architecture**:
- `gtex_link_api` (port 8000): FastAPI server for `/api/*` endpoints
- `gtex_link_mcp` (port 8001): MCP HTTP server for `/mcp` endpoint

**Prerequisites**:
- Copy `.env.docker.example` to `.env.docker` and configure your domain
- NPM network must exist (`npm_default`)
- **Recommended**: Run `make setup` or `../setup_gtex_link.sh` for automated setup

```bash
# Automated setup (recommended)
../setup_gtex_link.sh

# OR manual setup:
cp ../.env.docker.example ../.env.docker
# Edit .env.docker with your domain

# Deploy both containers
docker-compose -f docker-compose.npm.yml --env-file ../.env.docker up -d --build

# Test (replace with your domain)
curl https://gtex-link.example.com/api/health/
curl https://gtex-link.example.com/mcp
```

**NPM Configuration Required**:

1. **Main Proxy Host**:
   - Domain: `gtex-link.yourdomain.com`
   - Forward to: `gtex_link_api:8000`
   - SSL: Let's Encrypt with Force SSL

2. **Custom Location** (Required for MCP):
   - Location: `/mcp`
   - Proxy Pass: `http://gtex_link_mcp:8001`

   **⚠️ Without the `/mcp` custom location, MCP endpoints won't work!**

### 🚀 Standalone Production
**File**: `docker-compose.yml`
**Purpose**: Direct production deployment
**Ports**: 8000:8000
**Features**: Health checks, JSON logging, isolated network

```bash
# Basic production deployment
docker-compose up -d

# Test
curl http://localhost:8000/api/health/
```

### 📈 Enhanced Production
**Files**: `docker-compose.yml` + `docker-compose.prod.yml`
**Purpose**: Production with enhanced settings
**Features**: Resource limits, log rotation, optimized caching

```bash
# Enhanced production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 🔌 MCP-Only Server
**File**: `docker-compose.mcp.yml`
**Purpose**: Standalone MCP server
**Ports**: 8001:8001
**Features**: HTTP transport, MCP-only endpoint

```bash
# MCP-only server
docker-compose -f docker-compose.mcp.yml up -d

# Test MCP endpoint
curl http://localhost:8001/mcp
```

## Configuration Summary

| Configuration | Port | Use Case | Network | Features |
|---------------|------|----------|---------|----------|
| `npm.yml` | None | NPM Production | NPM shared | No ports, proxy ready |
| `yml` | 8000 | Standalone Prod | Isolated | Basic production |
| `yml` + `prod.yml` | 8000 | Enhanced Prod | Isolated | Resource limits, logging |
| `mcp.yml` | 8001 | MCP Only | Isolated | MCP HTTP transport |

## Quick Commands

```bash
# NPM Production (recommended)
docker-compose -f docker-compose.npm.yml --env-file ../.env.docker up -d --build

# Standalone Production
docker-compose up -d

# MCP Only
docker-compose -f docker-compose.mcp.yml up -d

# Stop any configuration
docker-compose -f [config-file] down

# View logs
docker-compose -f [config-file] logs -f
```

## Environment Variables

All configurations support environment variables. For NPM deployment, copy and configure:

```bash
cp ../.env.docker.example ../.env.docker
# Edit .env.docker with your settings
```

## Health Checks

All configurations include health check endpoints:
- **API Health**: `/api/health/`
- **MCP Health**: `/mcp` (for MCP-enabled configs)

## Troubleshooting

- **Port conflicts**: Use different configurations or check `API_PORT_HOST` in `.env.docker`
- **NPM network missing**: Ensure NPM is running or create network manually
- **Build issues**: Run `docker-compose build --no-cache`
- **Permission issues**: Check file permissions and Docker daemon access
