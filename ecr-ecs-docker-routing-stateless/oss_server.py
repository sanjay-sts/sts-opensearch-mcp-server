#!/usr/bin/env python3
"""
FastMCP 2.0 OpenSearch Server - AWS ECS Stateless Version
Provides OpenSearch functionality as MCP tools for Claude Desktop with stateless HTTP support
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

# AWS IAM authentication
from requests_aws4auth import AWS4Auth
import boto3

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
    use_iam: bool = False
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

        use_iam = os.getenv("OPENSEARCH_USE_IAM", "false").lower() == "true"
        username = os.getenv("OPENSEARCH_USERNAME", "")
        password = os.getenv("OPENSEARCH_PASSWORD", "")

        # For IAM authentication, username/password are not required
        if not use_iam and (not username or not password):
            raise ValueError("OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD must be set when not using IAM")

        return cls(
            host=os.getenv("OPENSEARCH_HOST", "localhost"),
            port=safe_int(os.getenv("OPENSEARCH_PORT", "9200"), 9200),
            username=username,
            password=password,
            use_iam=use_iam,
            use_ssl=os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true",
            ssl_verify=os.getenv("OPENSEARCH_SSL_VERIFY", "false").lower() == "true",
            ssl_show_warn=os.getenv("OPENSEARCH_SSL_SHOW_WARN", "false").lower() == "true",
            timeout=safe_int(os.getenv("OPENSEARCH_TIMEOUT", "30"), 30),
            max_retries=safe_int(os.getenv("OPENSEARCH_MAX_RETRIES", "3"), 3),
            default_index=os.getenv("OPENSEARCH_DEFAULT_INDEX", "documents"),
            max_results=safe_int(os.getenv("OPENSEARCH_MAX_RESULTS", "100"), 100)
        )


class OpenSearchClient:
    """OpenSearch client wrapper with automatic credential refresh"""

    def __init__(self, config: OpenSearchConfig):
        self.config = config
        self.client = None
        self.last_auth_refresh = 0
        self.auth_refresh_interval = 300  # Refresh every 5 minutes (300 seconds) for testing
        self._refresh_client()

    def _get_fresh_auth(self):
        """Get fresh AWS authentication"""
        if self.config.use_iam:
            try:
                # Create fresh session and credentials each time
                print("🔄 Creating fresh AWS session and credentials...")
                session = boto3.Session()
                credentials = session.get_credentials()

                # Force refresh to get latest token
                if hasattr(credentials, 'refresh'):
                    print("🔄 Refreshing credentials...")
                    credentials.refresh()
                else:
                    print("⚠️  Credentials do not support refresh, creating new session...")
                    # For some credential types, we need to recreate the session
                    session = boto3.Session()
                    credentials = session.get_credentials()

                # Log token expiry info if available
                if hasattr(credentials, 'token') and credentials.token:
                    print(f"🔑 Using session token (length: {len(credentials.token)} chars)")
                else:
                    print("🔑 Using access key/secret (no session token)")

                awsauth = AWS4Auth(
                    credentials.access_key,
                    credentials.secret_key,
                    session.region_name or 'us-east-1',
                    'es',
                    session_token=credentials.token
                )
                print("✅ Fresh AWS4Auth created successfully")
                return awsauth
            except Exception as e:
                print(f"❌ Error creating fresh auth: {str(e)}")
                raise
        else:
            return (self.config.username, self.config.password)

    def _refresh_client(self):
        """Refresh OpenSearch client with fresh credentials"""
        import time

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

        # Get fresh authentication
        http_auth = self._get_fresh_auth()

        self.client = OpenSearch(
            hosts=[{'host': host, 'port': self.config.port}],
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=self.config.ssl_verify,
            ssl_show_warn=self.config.ssl_show_warn,
            connection_class=RequestsHttpConnection,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_on_timeout=True
        )

        self.last_auth_refresh = time.time()

    def _ensure_fresh_client(self):
        """Ensure client has fresh credentials"""
        import time
        current_time = time.time()

        # Refresh if more than auth_refresh_interval seconds have passed
        if current_time - self.last_auth_refresh > self.auth_refresh_interval:
            print(f"🔄 Refreshing OpenSearch credentials (last refresh: {self.auth_refresh_interval}s ago)")
            self._refresh_client()

    def _execute_with_retry(self, operation_func, *args, **kwargs):
        """Execute operation with automatic credential refresh on auth errors"""
        self._ensure_fresh_client()

        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Check for various auth error patterns
            if any(pattern in error_str for pattern in ['expired', 'unauthorized', 'forbidden', 'authorizationexception', 'securitytoken']):
                print(f"🔑 Authentication error detected, refreshing credentials: {str(e)}")
                self._refresh_client()
                # Retry once with fresh credentials
                return operation_func(*args, **kwargs)
            else:
                # Re-raise non-auth errors
                raise

    async def test_connection(self) -> Dict[str, Any]:
        """Test OpenSearch connection asynchronously with credential refresh"""
        try:
            loop = asyncio.get_event_loop()

            # Use retry mechanism for both calls
            info = await loop.run_in_executor(None, self._execute_with_retry, lambda: self.client.info())
            health = await loop.run_in_executor(None, self._execute_with_retry, lambda: self.client.cluster.health())

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


# Initialize FastMCP in stateless mode to handle load balancing without session affinity
mcp = FastMCP("OpenSearch MCP Server", stateless_http=True)


@mcp.custom_route("/ossserver-stateless/health", methods=["GET"])
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
    """List all indices in the OpenSearch cluster with automatic credential refresh"""
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            opensearch_client._execute_with_retry,
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
        # Get configuration from environment - ECS-friendly defaults
        port = int(os.getenv("MCP_PORT", "9898"))  # Changed to 9898 for ECS
        host = os.getenv("MCP_HOST", "0.0.0.0")  # ECS requires 0.0.0.0 binding
        custom_path = os.getenv("MCP_PATH", "/ossserver-stateless/ossmcp")

        # Run the FastMCP server in stateless HTTP mode
        print("🌐 Starting OpenSearch MCP server in STATELESS HTTP mode...")
        print(f"📍 Server running at: http://{host}:{port}{custom_path}")
        print("✨ Stateless mode enabled - supports load balancing without session affinity")
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=custom_path
        )
    else:
        print("❌ Server startup failed")
        exit(1)