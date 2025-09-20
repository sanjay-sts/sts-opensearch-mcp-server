#!/usr/bin/env python3
"""
Simple test for MCP servers without Unicode emojis
"""

import asyncio
import json
import aiohttp
import sys

async def test_health(url):
    """Test health endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
    except Exception as e:
        return {"error": str(e)}

async def test_mcp_tools(url):
    """Test MCP tools endpoint"""
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

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
    except Exception as e:
        return {"error": str(e)}

async def test_list_indices(url):
    """Test list_indices tool"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_indices",
                "arguments": {}
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
    except Exception as e:
        return {"error": str(e)}

async def multiple_requests_test(url, count=5):
    """Test multiple concurrent requests for stateless behavior"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_indices",
                "arguments": {}
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(count):
                tasks.append(session.post(url, json=payload, headers=headers, timeout=30))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            error_count = 0

            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"  Request {i+1}: Exception - {str(response)}")
                    error_count += 1
                else:
                    if response.status == 200:
                        print(f"  Request {i+1}: Success")
                        success_count += 1
                    else:
                        print(f"  Request {i+1}: Error - HTTP {response.status}")
                        error_count += 1
                    response.close()

            return success_count, error_count

    except Exception as e:
        return 0, count

async def main():
    """Main test function"""
    alb_host = "fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com"

    servers = {
        "Stateful": {
            "health": f"http://{alb_host}/ossserver/health",
            "mcp": f"http://{alb_host}/ossserver/ossmcp"
        },
        "Stateless": {
            "health": f"http://{alb_host}/ossserver-stateless/health",
            "mcp": f"http://{alb_host}/ossserver-stateless/ossmcp"
        }
    }

    for server_name, urls in servers.items():
        print(f"\n{'='*50}")
        print(f"Testing {server_name} MCP Server")
        print(f"{'='*50}")

        # Test health
        print(f"\n1. Health Check ({urls['health']})")
        health = await test_health(urls['health'])
        if "error" in health:
            print(f"   ERROR: {health['error']}")
        else:
            print(f"   Status: {health.get('status', 'unknown')}")
            if 'opensearch' in health:
                print(f"   OpenSearch: {health['opensearch'].get('status', 'unknown')}")

        # Test MCP tools list
        print(f"\n2. MCP Tools List ({urls['mcp']})")
        tools = await test_mcp_tools(urls['mcp'])
        if "error" in tools:
            print(f"   ERROR: {tools['error']}")
        else:
            if 'result' in tools and 'tools' in tools['result']:
                tool_names = [tool['name'] for tool in tools['result']['tools']]
                print(f"   Available tools: {', '.join(tool_names)}")
            else:
                print("   No tools found in response")

        # Test list_indices
        print(f"\n3. List Indices Tool")
        indices = await test_list_indices(urls['mcp'])
        if "error" in indices:
            print(f"   ERROR: {indices['error']}")
        else:
            if 'result' in indices and 'content' in indices['result']:
                try:
                    content = json.loads(indices['result']['content'][0]['text'])
                    if content.get('success'):
                        index_count = len(content.get('indices', []))
                        print(f"   SUCCESS: Found {index_count} indices")
                    else:
                        print(f"   ERROR: {content.get('error', 'Unknown error')}")
                except:
                    print("   SUCCESS: Got response (could not parse)")
            else:
                print("   ERROR: Unexpected response format")

        # Test multiple concurrent requests
        print(f"\n4. Multiple Concurrent Requests (Stateless Test)")
        success_count, error_count = await multiple_requests_test(urls['mcp'])
        print(f"   Results: {success_count} success, {error_count} errors")

        if error_count == 0:
            print(f"   EXCELLENT: All requests successful - {server_name} working correctly!")
        elif success_count > 0:
            print(f"   WARNING: Some requests failed - potential issues with {server_name}")
        else:
            print(f"   CRITICAL: All requests failed - {server_name} not working")

if __name__ == "__main__":
    try:
        asyncio.run(main())
        print(f"\n{'='*50}")
        print("Testing Complete!")
        print(f"{'='*50}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)