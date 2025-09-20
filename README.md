# OpenSearch MCP Server

A Model Context Protocol (MCP) server that provides OpenSearch functionality as tools for Claude Desktop. This repository contains multiple deployment options for running the OpenSearch MCP server in different environments.

## 🎬 Current Status

✅ **Deployed and Running** - Live on AWS ECS with ALB integration
✅ **OpenSearch Connected** - Connected to AWS OpenSearch Service cluster
✅ **Data Loaded** - 84,661 MovieLens movie documents indexed
✅ **Claude Desktop Integration** - Working with HTTP transport

**Live Endpoints:**
- Health: `http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/health`
- MCP: `http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossmcp`

## 📁 Repository Structure

```
├── local/                     # Local development deployment
├── local_docker/             # Docker-based local deployment
├── ecr-ecs-docker/          # AWS ECS production deployment
├── load_sample_data/        # MovieLens data loader scripts
└── sample_data/             # Sample MovieLens metadata
```

## 🚀 Deployment Options

### 1. Local Development (`local/`)
Run the MCP server directly on your machine for development and testing.

**Features:**
- Direct Python execution
- Environment variable configuration
- Health check endpoint
- MCP tools for listing indices

**Quick Start:**
```bash
cd local
pip install -r requirements.txt
# Configure .env file
python oss_server.py
```

### 2. Docker Local (`local_docker/`)
Containerized version for local testing with Docker.

**Features:**
- Full Docker containerization
- Docker Compose orchestration
- Isolated environment
- Port 8000 mapping

**Quick Start:**
```bash
cd local_docker
cp .env.example .env
# Edit .env with your credentials
docker-compose up --build
```

### 3. AWS ECS Production (`ecr-ecs-docker/`) ✅ **Currently Deployed**
Full production deployment on AWS using ECS, ECR, and ALB.

**Infrastructure:**
- **ECS Cluster**: `fastmcp-time-server-cluster`
- **ALB**: `fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com`
- **Target Group**: `opensearch-mcp-tg` (port 9898)
- **ECR Repository**: `opensearch-mcp-server`
- **CloudWatch Logs**: `/ecs/opensearch-mcp-server`

**Features:**
- Auto-scaling (max 1 task)
- Health checks and monitoring
- Load balancer integration
- SSL-enabled OpenSearch connection

## 📊 Data

### MovieLens Dataset
The server currently contains **84,661 movie documents** from the MovieLens dataset:

**Index:** `sts-movielens-metadata-index`
**Size:** 24MB
**Documents:** 84,661 movies
**Health:** Green

**Sample Document Structure:**
```json
{
  "title": "Toy Story (1995)",
  "directedBy": "John Lasseter",
  "starring": "Tim Allen, Tom Hanks, Don Rickles...",
  "avgRating": 3.89146,
  "imdbId": "0114709",
  "item_id": 1,
  "year": 1995
}
```

### Data Loading
Use the `load_sample_data/` scripts to load MovieLens data:

```bash
cd load_sample_data
pip install -r requirements.txt
python load_movielens_metadata.py
```

**Features:**
- Batch processing with rate limiting
- Exponential backoff for errors
- Progress tracking and error reporting
- Optimized index mapping for movies

## 🔧 Configuration

### OpenSearch Connection
```env
OPENSEARCH_HOST=https://your-cluster.aos.us-east-1.on.aws
OPENSEARCH_PORT=443
OPENSEARCH_USERNAME=your_username
OPENSEARCH_PASSWORD=your_password
OPENSEARCH_USE_SSL=true
OPENSEARCH_SSL_VERIFY=true
```

### MCP Server Settings
```env
MCP_HOST=0.0.0.0
MCP_PORT=9898  # ECS deployment
MCP_PATH=/ossmcp
```

## 🖥️ Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "opensearch": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossmcp", "--allow-http"]
    }
  }
}
```

**Config Locations:**
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/claude-desktop/claude_desktop_config.json`

## 🛠️ Available Tools

### Current Tools
- `list_indices` - Lists all OpenSearch indices with stats

### Planned Tools (Coming Soon)
- `search_documents` - Search through movie database
- `index_document` - Add new documents
- `get_document` - Retrieve specific documents
- `delete_document` - Remove documents
- `get_mapping` - View index mappings
- `cluster_health` - Check cluster status
- `bulk_operations` - Batch operations

## 📈 Monitoring

### AWS CloudWatch
- **Log Group:** `/ecs/opensearch-mcp-server`
- **Metrics:** ECS service and task metrics
- **Alarms:** Health check failures

### Health Checks
```bash
# Test server health
curl http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/health

# Expected response
{
  "status": "healthy",
  "service": "OpenSearch MCP Server",
  "opensearch": {
    "status": "connected",
    "cluster_name": "892551050452:sts-use1-oss-poc-cluster",
    "version": "3.1.0",
    "health": "green"
  }
}
```

## 🔄 Deployment Commands

### AWS Deployment (Production)
```bash
cd ecr-ecs-docker
./01-setup-ecr.sh           # Create ECR and push image
./02-create-target-group.sh # Create ALB target group
./03-create-task-definition.sh # Create ECS task definition
./05-create-listener-rule.sh   # Create ALB routing
./04-create-service.sh      # Create ECS service
```

### Update Deployment
```bash
# Update task definition and service
./03-create-task-definition.sh
aws ecs update-service \
  --cluster arn:aws:ecs:us-east-1:892551050452:cluster/fastmcp-time-server-cluster \
  --service opensearch-mcp-server \
  --task-definition opensearch-mcp-server \
  --profile mainadmin
```

### Cleanup
```bash
cd ecr-ecs-docker
./cleanup.sh  # Remove all AWS resources
```

## 🐛 Troubleshooting

### Common Issues

1. **Claude Desktop connection fails:**
   - Add `--allow-http` flag for HTTP URLs
   - Restart Claude Desktop after config changes
   - Verify JSON syntax in config file

2. **OpenSearch authentication errors:**
   - Check username/password in task definition
   - Verify SSL settings for HTTPS endpoints
   - Test credentials with curl

3. **ECS service startup issues:**
   - Check CloudWatch logs for errors
   - Verify environment variables
   - Ensure security groups allow traffic

4. **Data loading errors:**
   - Use batching with rate limiting
   - Check OpenSearch cluster capacity
   - Verify index mapping compatibility

## 📜 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test locally
4. Update documentation
5. Submit a pull request

## 📚 Resources

- [FastMCP Documentation](https://gofastmcp.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [OpenSearch Documentation](https://opensearch.org/docs/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)

---

**Current Deployment Status:** ✅ Production Ready
**Last Updated:** September 2025
**Maintainer:** [@sanjay-sts](https://github.com/sanjay-sts)




    Migrate from the current stateful MCP server deployment to a stateless version         
    that can handle load balancing without session affinity issues.

    Phase 1: Environment Setup & Code Migration

    1. Copy existing routing deployment structure to ecr-ecs-docker-routing-stateless/     
    2. Modify FastMCP server to enable stateless mode (stateless_http=True)
    3. Update deployment scripts with new resource names to avoid conflicts
    4. Create implementation plan document in the stateless folder

    Phase 2: Stateless Configuration

    1. Update oss_server.py - Add stateless_http=True to FastMCP initialization
    2. Modify environment variables - Add stateless configuration options
    3. Update resource naming - Change all AWS resource names to include "-stateless"      
    suffix
    4. Review health check endpoints - Ensure they work in stateless mode

    Phase 3: Deployment Infrastructure

    1. Update all deployment scripts (01-05-*.sh) with stateless resource names
    2. Modify task definition with stateless environment variables
    3. Update ALB routing paths - Use /ossserver-stateless/* paths
    4. Configure new target groups for stateless deployment

    Phase 4: Testing Setup

    1. Find/create chat CLI tool for testing MCP functionality
    2. Set up test scenarios to verify stateless behavior works correctly
    3. Create validation scripts to compare stateful vs stateless responses
    4. Document testing procedures

    Phase 5: Deployment & Validation

    1. Deploy stateless version alongside existing stateful deployment
    2. Test both deployments using chat CLI to ensure functionality parity
    3. Validate load balancing works correctly without session affinity
    4. Performance comparison between stateful and stateless versions

    Phase 6: Cleanup & Migration

    1. Clean up existing stateful deployment (ECS service, target groups, etc.)
    2. Update routing to point to stateless version
    3. Archive stateful deployment configuration for rollback if needed
    4. Update documentation with new endpoints and configuration

    Key Changes Required

    - FastMCP Server: Add stateless_http=True parameter
    - Resource Names: All AWS resources get "-stateless" suffix
    - ALB Paths: Change from /ossserver/* to /ossserver-stateless/*
    - Deployment Scripts: Update all 6 shell scripts with new names
    - Testing: Verify no session dependencies remain

    Success Criteria

    - Stateless MCP server responds correctly to all tool calls
    - No HTTP 404 "Session not found" errors under load balancing
    - Performance comparable to stateful version
    - Clean deployment with no resource conflicts
    - Successful testing with chat CLI demonstrates full functionality
