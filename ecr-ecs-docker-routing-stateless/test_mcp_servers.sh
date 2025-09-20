#!/bin/bash

# Test MCP Servers Script
# Tests both stateful and stateless MCP servers

echo "🧪 Setting up Python environment for testing..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Install requirements if needed
echo "📦 Installing Python requirements..."
pip3 install -r chat_cli_requirements.txt

echo ""
echo "🚀 Starting MCP Server Tests..."
echo ""

# Test both servers
python3 chat_cli.py --server both

echo ""
echo "✅ Testing complete!"

# Optionally test just stateless
echo ""
echo "🔄 Running additional stateless-only test..."
python3 chat_cli.py --server stateless