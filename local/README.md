# OpenSearch MCP Server - Local Deployment

This directory contains the local deployment setup for the OpenSearch MCP Server, which provides OpenSearch functionality as MCP tools for Claude Desktop.

> **Note:** For production deployment, see the `ecr-ecs-docker/` folder which contains the currently deployed AWS ECS version.

## Prerequisites

- Python 3.8+
- OpenSearch cluster (local or remote)
- Valid OpenSearch credentials

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in this directory with your OpenSearch configuration:

```env
# Required
OPENSEARCH_USERNAME=your_username
OPENSEARCH_PASSWORD=your_password

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

# MCP Server Settings
MCP_PORT=8000
MCP_HOST=localhost
MCP_PATH=/ossmcp
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENSEARCH_USERNAME` | OpenSearch username | **Required** |
| `OPENSEARCH_PASSWORD` | OpenSearch password | **Required** |
| `OPENSEARCH_HOST` | OpenSearch host (can include protocol) | `localhost` |
| `OPENSEARCH_PORT` | OpenSearch port | `9200` |
| `OPENSEARCH_USE_SSL` | Use SSL/TLS connection | `false` |
| `OPENSEARCH_SSL_VERIFY` | Verify SSL certificates | `false` |
| `OPENSEARCH_SSL_SHOW_WARN` | Show SSL warnings | `false` |
| `OPENSEARCH_TIMEOUT` | Connection timeout in seconds | `30` |
| `OPENSEARCH_MAX_RETRIES` | Maximum retry attempts | `3` |
| `OPENSEARCH_DEFAULT_INDEX` | Default index for operations | `documents` |
| `OPENSEARCH_MAX_RESULTS` | Maximum results per query | `100` |
| `MCP_PORT` | MCP server port | `8000` |
| `MCP_HOST` | MCP server host | `localhost` |
| `MCP_PATH` | MCP server path | `/ossmcp` |

## Running the Server

Start the OpenSearch MCP server:

```bash
python oss_server.py
```

The server will:
1. Load configuration from environment variables
2. Test connection to OpenSearch
3. Start the MCP server in HTTP mode

### Expected Output

```
🚀 Starting OpenSearch MCP Server...
✅ Connected to OpenSearch cluster: your-cluster-name
   Version: 2.x.x
   Health: green
🌐 Starting OpenSearch MCP server in HTTP mode...
📍 Server running at: http://localhost:8000/ossmcp
```

## Testing

### Health Check

Test the server health endpoint:

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

### Available Tools

Currently available MCP tools:
- `list_indices` - List all indices in the OpenSearch cluster

### Configuration Resource

Access current configuration:
- Resource URI: `config://opensearch`

## Troubleshooting

### Connection Issues

1. **Authentication Error**: Verify `OPENSEARCH_USERNAME` and `OPENSEARCH_PASSWORD`
2. **Connection Refused**: Check `OPENSEARCH_HOST` and `OPENSEARCH_PORT`
3. **SSL Issues**: Adjust `OPENSEARCH_USE_SSL` and `OPENSEARCH_SSL_VERIFY` settings

### Common Error Messages

- `OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD must be set`: Add credentials to `.env`
- `Failed to connect to OpenSearch`: Check network connectivity and credentials
- `Configuration not initialized`: Environment variables not loaded properly

### Debug Mode

For detailed SSL debugging, set:
```env
OPENSEARCH_SSL_SHOW_WARN=true
```

## Integration with Claude Desktop

To use this server with Claude Desktop, add the following to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "opensearch": {
      "command": "python",
      "args": ["path/to/oss_server.py"],
      "env": {
        "OPENSEARCH_USERNAME": "your_username",
        "OPENSEARCH_PASSWORD": "your_password",
        "OPENSEARCH_HOST": "your_host"
      }
    }
  }
}
```

## Development

The server uses FastMCP 2.0 framework. To add new tools:

1. Uncomment existing tools in `oss_server.py`
2. Add new `@mcp.tool` decorated functions
3. Follow the existing async pattern for OpenSearch operations

## License

MIT License - see LICENSE file for details.