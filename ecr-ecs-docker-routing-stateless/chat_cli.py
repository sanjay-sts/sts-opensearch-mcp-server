#!/usr/bin/env python3
"""
Simple Chat CLI for Testing MCP Servers
Tests both stateful and stateless OpenSearch MCP servers
"""

import asyncio
import json
import argparse
import aiohttp
import sys
from typing import Dict, List, Any
from datetime import datetime

class MCPClient:
    """Simple MCP client for testing MCP servers via HTTP"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        try:
            # Extract the path from base_url and construct health endpoint
            if '/ossmcp' in self.base_url:
                health_url = self.base_url.replace('/ossmcp', '/health')
            else:
                health_url = f"{self.base_url}/health"

            async with self.session.get(health_url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}", "details": await response.text()}
        except Exception as e:
            return {"error": str(e)}

    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        try:
            # Make a request to list tools - this is MCP protocol specific
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            async with self.session.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}", "details": await response.text()}
        except Exception as e:
            return {"error": str(e)}

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific MCP tool"""
        if parameters is None:
            parameters = {}

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }

            async with self.session.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}", "details": await response.text()}
        except Exception as e:
            return {"error": str(e)}

def print_response(title: str, response: Dict[str, Any]):
    """Pretty print response"""
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print(f"{'='*50}")

    if "error" in response:
        print(f"❌ Error: {response['error']}")
        if "details" in response:
            print(f"📝 Details: {response['details']}")
    else:
        print(json.dumps(response, indent=2, default=str))

async def test_server(server_name: str, base_url: str):
    """Test a single MCP server"""
    print(f"\n🚀 Testing {server_name} MCP Server")
    print(f"📍 URL: {base_url}")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with MCPClient(base_url) as client:
        # 1. Health check
        health = await client.health_check()
        print_response("Health Check", health)

        # 2. List available tools
        tools = await client.list_tools()
        print_response("Available Tools", tools)

        # 3. Test list_indices tool if available
        if "result" in tools and "tools" in tools["result"]:
            tool_names = [tool["name"] for tool in tools["result"]["tools"]]
            if "list_indices" in tool_names:
                indices = await client.call_tool("list_indices")
                print_response("OpenSearch Indices", indices)
            else:
                print("\n⚠️  list_indices tool not found in available tools")

        # 4. Multiple rapid requests to test stateless behavior
        print(f"\n📊 Testing Multiple Rapid Requests (Stateless Behavior)")
        print(f"{'='*50}")

        tasks = []
        for i in range(5):
            tasks.append(client.call_tool("list_indices"))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        error_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Request {i+1}: Exception - {str(result)}")
                error_count += 1
            elif "error" in result:
                print(f"❌ Request {i+1}: Error - {result['error']}")
                error_count += 1
            else:
                print(f"✅ Request {i+1}: Success")
                success_count += 1

        print(f"\n📈 Results: {success_count} success, {error_count} errors")

        if error_count == 0:
            print("🎉 All requests successful - stateless behavior working correctly!")
        else:
            print("⚠️  Some requests failed - potential session affinity issues")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test MCP servers")
    parser.add_argument(
        "--server",
        choices=["stateful", "stateless", "both"],
        default="both",
        help="Which server to test"
    )
    parser.add_argument(
        "--alb-host",
        default="fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com",
        help="ALB hostname"
    )

    args = parser.parse_args()

    # Server configurations
    servers = {}

    if args.server in ["stateful", "both"]:
        servers["Stateful"] = f"http://{args.alb_host}/ossserver/ossmcp"

    if args.server in ["stateless", "both"]:
        servers["Stateless"] = f"http://{args.alb_host}/ossserver-stateless/ossmcp"

    # Test each server
    for server_name, base_url in servers.items():
        try:
            await test_server(server_name, base_url)
        except Exception as e:
            print(f"\n❌ Failed to test {server_name} server: {str(e)}")

    print(f"\n{'='*60}")
    print("🎯 Testing Complete!")
    print(f"{'='*60}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)