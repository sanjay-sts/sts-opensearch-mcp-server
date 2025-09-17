#!/usr/bin/env python3
"""
FastMCP 2.0 OpenSearch Server - Docker Version
Provides OpenSearch functionality as MCP tools for Claude Desktop
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# FastMCP imports - correct pattern
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# OpenSearch imports
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import OpenSearchException, NotFoundError
import urllib3

# SSL warnings will be suppressed conditionally in client creation

# Load environment variables
load_dotenv()


@dataclass
class OpenSearchConfig:
    """OpenSearch configuration"""
    host: str = "localhost"
    port: int = 9200
    username: str = ""
    password: str = ""
    use_ssl: bool = False
    ssl_verify: bool = False
    ssl_show_warn: bool = False
    timeout: int = 30
    max_retries: int = 3
    default_index: str = "documents"
    max_results: int = 100

    @classmethod
    def from_env(cls) -> 'OpenSearchConfig':
        """Create config from environment variables with validation"""

        def safe_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        username = os.getenv("OPENSEARCH_USERNAME", "")
        password = os.getenv("OPENSEARCH_PASSWORD", "")

        if not username or not password:
            raise ValueError("OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD must be set")

        return cls(
            host=os.getenv("OPENSEARCH_HOST", "localhost"),
            port=safe_int(os.getenv("OPENSEARCH_PORT", "9200"), 9200),
            username=username,
            password=password,
            use_ssl=os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true",
            ssl_verify=os.getenv("OPENSEARCH_SSL_VERIFY", "false").lower() == "true",
            ssl_show_warn=os.getenv("OPENSEARCH_SSL_SHOW_WARN", "false").lower() == "true",
            timeout=safe_int(os.getenv("OPENSEARCH_TIMEOUT", "30"), 30),
            max_retries=safe_int(os.getenv("OPENSEARCH_MAX_RETRIES", "3"), 3),
            default_index=os.getenv("OPENSEARCH_DEFAULT_INDEX", "documents"),
            max_results=safe_int(os.getenv("OPENSEARCH_MAX_RESULTS", "100"), 100)
        )


class OpenSearchClient:
    """OpenSearch client wrapper"""

    def __init__(self, config: OpenSearchConfig):
        self.config = config
        self.client = self._create_client()

    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client"""
        if not self.config.ssl_show_warn:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Parse host URL if it includes protocol
        host = self.config.host
        if host.startswith('https://'):
            host = host[8:]  # Remove https://
            use_ssl = True
        elif host.startswith('http://'):
            host = host[7:]  # Remove http://
            use_ssl = False
        else:
            use_ssl = self.config.use_ssl

        return OpenSearch(
            hosts=[{'host': host, 'port': self.config.port}],
            http_auth=(self.config.username, self.config.password),
            use_ssl=use_ssl,
            verify_certs=self.config.ssl_verify,
            ssl_show_warn=self.config.ssl_show_warn,
            connection_class=RequestsHttpConnection,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_on_timeout=True
        )

    async def test_connection(self) -> Dict[str, Any]:
        """Test OpenSearch connection asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self.client.info)
            health = await loop.run_in_executor(None, self.client.cluster.health)
            return {
                "status": "connected",
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
                "health": health.get("status")
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Initialize FastMCP using the correct pattern
mcp = FastMCP("OpenSearch MCP Server")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring"""
    try:
        if opensearch_client:
            connection_status = await opensearch_client.test_connection()
            return JSONResponse({
                "status": "healthy",
                "service": "OpenSearch MCP Server",
                "opensearch": connection_status
            })
        else:
            return JSONResponse({
                "status": "unhealthy",
                "service": "OpenSearch MCP Server",
                "error": "OpenSearch client not initialized"
            }, status_code=503)
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "service": "OpenSearch MCP Server",
            "error": str(e)
        }, status_code=500)


# Global OpenSearch client - will be initialized after env validation
config = None
opensearch_client = None


def initialize_client():
    """Initialize OpenSearch client with error handling"""
    global config, opensearch_client
    try:
        config = OpenSearchConfig.from_env()
        opensearch_client = OpenSearchClient(config)
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


@mcp.tool
async def list_indices() -> Dict[str, Any]:
    """List all indices in the OpenSearch cluster"""
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: opensearch_client.client.cat.indices(
                format="json",
                h="index,docs.count,docs.deleted,store.size,health,status"
            )
        )

        return {
            "success": True,
            "indices": response
        }

    except OpenSearchException as e:
        return {
            "success": False,
            "error": f"OpenSearch error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


@mcp.resource("config://opensearch")
async def get_config() -> str:
    """Get current OpenSearch configuration"""
    if not config:
        return json.dumps({"error": "Configuration not initialized"}, indent=2)

    return json.dumps({
        "host": config.host,
        "port": config.port,
        "default_index": config.default_index,
        "max_results": config.max_results,
        "timeout": config.timeout
    }, indent=2)


# Add startup logic
async def startup():
    """Test connection on startup"""
    print(f"🚀 Starting OpenSearch MCP Server...")

    if not initialize_client():
        print("❌ Failed to initialize OpenSearch client")
        return False

    connection_status = await opensearch_client.test_connection()
    if connection_status["status"] == "connected":
        print(f"✅ Connected to OpenSearch cluster: {connection_status['cluster_name']}")
        print(f"   Version: {connection_status['version']}")
        print(f"   Health: {connection_status['health']}")
        return True
    else:
        print(f"❌ Failed to connect to OpenSearch: {connection_status['error']}")
        return False


if __name__ == "__main__":
    # Test connection before starting
    if asyncio.run(startup()):
        # Get configuration from environment - Docker-friendly defaults
        port = int(os.getenv("MCP_PORT", "8000"))
        host = os.getenv("MCP_HOST", "0.0.0.0")  # Docker requires 0.0.0.0 binding
        custom_path = os.getenv("MCP_PATH", "/ossmcp")

        # Run the FastMCP server in HTTP mode
        print("🌐 Starting OpenSearch MCP server in HTTP mode...")
        print(f"📍 Server running at: http://{host}:{port}{custom_path}")
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=custom_path
        )
    else:
        print("❌ Server startup failed")
        exit(1)