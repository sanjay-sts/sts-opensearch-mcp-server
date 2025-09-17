# OpenSearch MCP Server - Docker Deployment

This directory contains the Docker deployment setup for the OpenSearch MCP Server, providing OpenSearch functionality as MCP tools for Claude Desktop in a containerized environment.

> **Note:** For production deployment, see the `ecr-ecs-docker/` folder which contains the currently deployed AWS ECS version.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- OpenSearch cluster (local or remote)
- Valid OpenSearch credentials

## Quick Start

1. **Clone and navigate to the directory:**
```bash
cd local_docker
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your OpenSearch credentials
```

3. **Build and run the container:**
```bash
docker-compose up --build
```

4. **Test the server:**
```bash
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin

# Optional (with defaults)
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USE_SSL=false
OPENSEARCH_SSL_VERIFY=false
OPENSEARCH_SSL_SHOW_WARN=false
OPENSEARCH_TIMEOUT=30
OPENSEARCH_MAX_RETRIES=3
OPENSEARCH_DEFAULT_INDEX=documents
OPENSEARCH_MAX_RESULTS=100
```

### Docker Network Configuration

For connecting to OpenSearch running on the host machine:
- **Linux/macOS**: Use `host.docker.internal` as `OPENSEARCH_HOST`
- **Windows**: Use `host.docker.internal` as `OPENSEARCH_HOST`
- **Custom network**: Ensure containers are on the same Docker network

## Docker Commands

### Build and Run
```bash
# Build and start services
docker-compose up --build

# Run in background
docker-compose up -d --build

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

### Docker Build Only
```bash
# Build the image
docker build -t opensearch-mcp-server .

# Run the container
docker run -p 8000:8000 --env-file .env opensearch-mcp-server
```

## Testing

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "OpenSearch MCP Server",
  "opensearch": {
    "status": "connected",
    "cluster_name": "your-cluster",
    "version": "2.x.x",
    "health": "green"
  }
}
```

### Available Endpoints
- **Health**: `GET /health`
- **MCP Endpoint**: `POST /ossmcp` (for Claude Desktop)

### Available Tools
- `list_indices` - List all indices in the OpenSearch cluster

### Configuration Resource
- Resource URI: `config://opensearch`

## Claude Desktop Integration

### Recommended: Using mcp-remote (HTTP Transport)

Add to your Claude Desktop MCP configuration (`~/.config/claude-desktop/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "opensearch": {
      "command": "npx",
      "args": ["mcp-remote@latest", "http://localhost:8000/ossmcp"]
    }
  }
}
```

**Alternative with -y flag to avoid prompts:**
```json
{
  "mcpServers": {
    "opensearch": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/ossmcp"]
    }
  }
}
```

### Manual HTTP Client (Alternative)

If you prefer not to use npx, install the MCP HTTP client globally:
```bash
npm install -g @modelcontextprotocol/http-client
```

```json
{
  "mcpServers": {
    "opensearch": {
      "command": "mcp-http-client",
      "args": ["http://localhost:8000/ossmcp"]
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Container can't connect to OpenSearch**
   - Use `host.docker.internal` instead of `localhost` for `OPENSEARCH_HOST`
   - Check firewall settings
   - Verify OpenSearch is accessible from within Docker network

2. **Permission denied errors**
   - Check that `.env` file is readable
   - Verify Docker has permission to bind to port 8000

3. **Health check failures**
   - Check OpenSearch credentials in `.env`
   - Verify OpenSearch is running and accessible
   - Check container logs: `docker-compose logs`

### Debug Mode

Run with debug output:
```bash
docker-compose up --build
# Watch logs in real-time
docker-compose logs -f opensearch-mcp-server
```

### Container Shell Access
```bash
# Access running container
docker-compose exec opensearch-mcp-server /bin/bash

# Or run a new container with shell
docker run -it --env-file .env opensearch-mcp-server /bin/bash
```

## Development

### Local Development with Docker

1. **Mount source code for live reload:**
```yaml
# Add to docker-compose.yml under opensearch-mcp-server service
volumes:
  - ./oss_server.py:/app/oss_server.py:ro
  - ./.env:/app/.env:ro
```

2. **Rebuild on changes:**
```bash
docker-compose up --build
```

### Production Deployment

For production use:

1. **Use multi-stage builds** for smaller images
2. **Set proper resource limits** in docker-compose.yml
3. **Use Docker secrets** for sensitive credentials
4. **Enable logging drivers** for centralized logging
5. **Set up monitoring** with health checks

Example production docker-compose additions:
```yaml
services:
  opensearch-mcp-server:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Key Differences from Local Version

- **Host Binding**: Server binds to `0.0.0.0:8000` instead of `localhost:8000` for Docker networking
- **Container Networking**: Uses Docker networks for service communication
- **Health Checks**: Built-in Docker health checks for monitoring
- **Security**: Runs as non-root user inside container
- **Environment**: All configuration via environment variables and `.env` file

## License

MIT License - see LICENSE file for details.