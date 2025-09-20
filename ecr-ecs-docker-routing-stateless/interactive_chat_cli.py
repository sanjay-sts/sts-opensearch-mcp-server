#!/usr/bin/env python3
"""
Interactive Chat CLI for Testing MCP Servers
Provides an interactive session to test OpenSearch MCP servers
"""

import asyncio
import json
import aiohttp
import sys
import argparse
from datetime import datetime

class InteractiveMCPClient:
    """Interactive MCP client for testing MCP servers"""

    def __init__(self, base_url: str, server_name: str):
        self.base_url = base_url.rstrip('/')
        self.server_name = server_name
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def health_check(self):
        """Check server health"""
        try:
            if '/ossmcp' in self.base_url:
                health_url = self.base_url.replace('/ossmcp', '/health')
            else:
                health_url = f"{self.base_url}/health"

            async with self.session.get(health_url, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ {self.server_name} server is healthy!")
                    print(f"   OpenSearch: {result.get('opensearch', {}).get('status', 'unknown')}")
                    print(f"   Cluster: {result.get('opensearch', {}).get('cluster_name', 'unknown')}")
                    return True
                else:
                    print(f"❌ {self.server_name} health check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ {self.server_name} health check error: {str(e)}")
            return False

    async def list_tools(self):
        """List available MCP tools"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }

            async with self.session.post(self.base_url, json=payload, headers=headers, timeout=10) as response:
                if response.status == 200:
                    # Handle Server-Sent Events response
                    content = await response.text()
                    if content.startswith('event:'):
                        # Parse SSE format
                        lines = content.strip().split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                if 'result' in data and 'tools' in data['result']:
                                    tools = data['result']['tools']
                                    print(f"🔧 Available tools on {self.server_name}:")
                                    for tool in tools:
                                        print(f"   - {tool['name']}: {tool['description']}")
                                    return tools
                    else:
                        # Regular JSON response
                        data = json.loads(content)
                        if 'result' in data and 'tools' in data['result']:
                            tools = data['result']['tools']
                            print(f"🔧 Available tools on {self.server_name}:")
                            for tool in tools:
                                print(f"   - {tool['name']}: {tool['description']}")
                            return tools
                else:
                    print(f"❌ Failed to list tools: HTTP {response.status}")
                    return []
        except Exception as e:
            print(f"❌ Error listing tools: {str(e)}")
            return []

    async def call_tool(self, tool_name: str, parameters: dict = None):
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

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }

            print(f"🚀 Calling tool '{tool_name}' on {self.server_name}...")

            async with self.session.post(self.base_url, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    if content.startswith('event:'):
                        # Parse SSE format
                        lines = content.strip().split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                data = json.loads(line[6:])
                                if 'result' in data:
                                    if 'content' in data['result'] and data['result']['content']:
                                        # Get the text content
                                        text_content = data['result']['content'][0]['text']
                                        try:
                                            # Try to parse as JSON for pretty printing
                                            parsed = json.loads(text_content)
                                            print("✅ Tool executed successfully!")
                                            print(json.dumps(parsed, indent=2))
                                        except:
                                            print("✅ Tool executed successfully!")
                                            print(text_content)
                                    else:
                                        print("✅ Tool executed successfully!")
                                        print(json.dumps(data['result'], indent=2))
                                elif 'error' in data:
                                    print(f"❌ Tool error: {data['error']}")
                    return True
                else:
                    print(f"❌ Tool call failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error calling tool: {str(e)}")
            return False

    async def stress_test(self, tool_name: str, count: int = 5):
        """Test multiple concurrent requests"""
        print(f"🧪 Running stress test: {count} concurrent '{tool_name}' calls on {self.server_name}...")

        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {}
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        try:
            tasks = []
            for i in range(count):
                tasks.append(self.session.post(self.base_url, json=payload, headers=headers, timeout=30))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            error_count = 0

            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"   Request {i+1}: ❌ Exception - {str(response)}")
                    error_count += 1
                else:
                    if response.status == 200:
                        print(f"   Request {i+1}: ✅ Success")
                        success_count += 1
                    else:
                        print(f"   Request {i+1}: ❌ HTTP {response.status}")
                        error_count += 1
                    response.close()

            print(f"\n📊 Stress Test Results: {success_count}/{count} successful")

            if error_count == 0:
                print(f"🎉 EXCELLENT: All requests successful - {self.server_name} handles concurrency perfectly!")
            elif success_count > 0:
                print(f"⚠️  WARNING: Some requests failed - potential session/scaling issues")
            else:
                print(f"💥 CRITICAL: All requests failed - {self.server_name} not handling load")

            return success_count, error_count

        except Exception as e:
            print(f"❌ Stress test error: {str(e)}")
            return 0, count

async def interactive_session(client, tools):
    """Run interactive session"""
    print(f"\n🎮 Interactive Mode - {client.server_name} MCP Server")
    print("=" * 50)
    print("Available commands:")
    print("  health      - Check server health")
    print("  tools       - List available tools")
    print("  list        - Call list_indices tool")
    print("  stress [N]  - Run stress test with N concurrent requests (default: 5)")
    print("  quit/exit   - Exit interactive mode")
    print("=" * 50)

    while True:
        try:
            command = input(f"\n[{client.server_name}] > ").strip().lower()

            if command in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            elif command == 'health':
                await client.health_check()

            elif command == 'tools':
                await client.list_tools()

            elif command == 'list':
                await client.call_tool('list_indices')

            elif command.startswith('stress'):
                parts = command.split()
                count = 5
                if len(parts) > 1:
                    try:
                        count = int(parts[1])
                    except ValueError:
                        print("❌ Invalid number for stress test count")
                        continue

                if 'list_indices' in [tool['name'] for tool in tools]:
                    await client.stress_test('list_indices', count)
                else:
                    print("❌ list_indices tool not available")

            elif command == '':
                continue

            else:
                print(f"❌ Unknown command: {command}")
                print("Type 'health', 'tools', 'list', 'stress [N]', or 'quit'")

        except KeyboardInterrupt:
            print("\n👋 Interrupted. Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Interactive MCP Server Testing")
    parser.add_argument(
        "--server",
        choices=["stateful", "stateless"],
        default="stateless",
        help="Which server to test interactively"
    )
    parser.add_argument(
        "--alb-host",
        default="fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com",
        help="ALB hostname"
    )

    args = parser.parse_args()

    # Server configurations
    if args.server == "stateful":
        server_name = "Stateful"
        base_url = f"http://{args.alb_host}/ossserver/ossmcp"
    else:
        server_name = "Stateless"
        base_url = f"http://{args.alb_host}/ossserver-stateless/ossmcp"

    print(f"🚀 Starting Interactive MCP Client")
    print(f"📍 Server: {server_name}")
    print(f"🌐 URL: {base_url}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with InteractiveMCPClient(base_url, server_name) as client:
        # Initial health check and tool discovery
        print(f"\n🔍 Initial connection test...")
        if await client.health_check():
            tools = await client.list_tools()
            if tools:
                await interactive_session(client, tools)
            else:
                print("❌ No tools available or connection failed")
        else:
            print("❌ Health check failed. Server may not be running.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)