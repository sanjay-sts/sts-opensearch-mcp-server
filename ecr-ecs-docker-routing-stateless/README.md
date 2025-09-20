# OpenSearch MCP Server - Routing Deployment

This folder contains the AWS ECS deployment configuration for the OpenSearch MCP Server with custom routing paths.

## 🎯 Key Features

- **Custom Path Routing**: Routes traffic through `/ossserver/*` paths
- **Dedicated Resources**: Uses separate resource names to avoid conflicts
- **Health Check Integration**: Configured for `/ossserver/health` endpoint
- **MCP Endpoint**: Serves MCP tools at `/ossserver/ossmcp`

## 📍 Endpoints

- **Health Check**: `http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/health`
- **MCP Endpoint**: `http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/ossmcp`

## Prerequisites

- AWS CLI configured with SSO profile `mainadmin`
- Docker installed and running
- OpenSearch cluster with FGAC enabled
- Permissions to create ECS, ECR, ALB, and IAM resources

## 🚀 Deployment Steps

### 0. Setup IAM Roles (First Time Only)
```bash
./00-setup-iam-roles.sh
```
This script will:
- Create ECS task role with OpenSearch permissions
- Configure IAM policies for OpenSearch access
- Update task definition with correct role ARN

### 1. Build and Push Docker Image
```bash
./01-setup-ecr.sh
```

### 2. Create Target Group (with routing paths)
```bash
./02-create-target-group.sh
```

### 3. Create Task Definition (with routing configuration)
```bash
./03-create-task-definition.sh
```

### 4. Create ALB Listener Rule (for /ossserver/* routing)
```bash
./05-create-listener-rule.sh
```

### 5. Create ECS Service
```bash
./04-create-service.sh
```

## Files

### Core Application Files
- `oss_server.py` - OpenSearch MCP server configured for port 9898
- `Dockerfile` - Container definition with health checks
- `requirements.txt` - Python dependencies
- `task-definition.json` - ECS task definition template

### Deployment Scripts
- `01-setup-ecr.sh` - Creates ECR repository and pushes Docker image
- `02-create-target-group.sh` - Creates ALB target group with health checks
- `03-create-task-definition.sh` - Creates ECS task definition
- `04-create-service.sh` - Creates ECS service with ALB integration
- `05-create-listener-rule.sh` - Creates ALB routing rule
- `cleanup.sh` - Removes all created AWS resources

## Configuration

### AWS Profile
All scripts use the `mainadmin` profile:
```bash
aws sso login --profile mainadmin
```

### OpenSearch Configuration
The deployment uses IAM role authentication for secure, credential-less access to OpenSearch. Connection details are configured as environment variables in the task definition, with authentication handled automatically through AWS IAM.

## 🔐 Security Features

### IAM Role Authentication
- **No Credentials**: Uses IAM role authentication, no passwords to manage
- **ECS Task Role**: `ecsTaskRole` with minimal OpenSearch permissions
- **Automatic Rotation**: Credentials automatically rotated by AWS STS
- **Fine-Grained Access**: Configured through OpenSearch FGAC

### IAM Role Configuration
The deployment creates an ECS task role with OpenSearch permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "es:ESHttpPost",
                "es:ESHttpPut",
                "es:ESHttpGet",
                "es:ESHttpDelete",
                "es:ESHttpHead"
            ],
            "Resource": [
                "arn:aws:es:us-east-1:892551050452:domain/sts-use1-oss-poc-cluster",
                "arn:aws:es:us-east-1:892551050452:domain/sts-use1-oss-poc-cluster/*"
            ]
        }
    ]
}
```

### Environment Variables
The task definition includes these environment variables:
```json
{
  "name": "OPENSEARCH_HOST",
  "value": "https://search-sts-use1-oss-poc-cluster-..."
},
{
  "name": "OPENSEARCH_USE_IAM",
  "value": "true"
},
{
  "name": "OPENSEARCH_USE_SSL",
  "value": "true"
}
```

### OpenSearch FGAC Configuration
After running the IAM setup script, you need to configure OpenSearch Fine-Grained Access Control:

1. **Map IAM Role**: Add `arn:aws:iam::892551050452:role/ecsTaskRole` to OpenSearch role mappings
2. **See Guide**: Check `configure-opensearch-fgac.md` for detailed instructions
3. **Access Methods**: Use OpenSearch Dashboards, AWS CLI, or REST API

## Deployment Steps

### 1. ECR Setup (`01-setup-ecr.sh`)
- Creates ECR repository `opensearch-mcp-server`
- Builds Docker image from current directory
- Pushes image to ECR
- Saves image URI to `.image-uri`

### 2. Target Group (`02-create-target-group.sh`)
- Creates target group `opensearch-mcp-tg`
- Configures health checks on `/health` endpoint
- Uses port 9898 for routing
- Auto-detects VPC from ALB

### 3. Task Definition (`03-create-task-definition.sh`)
- Creates CloudWatch log group
- Registers ECS task definition
- Configures 256 CPU / 512 MB memory
- Sets up environment variables

### 4. ECS Service (`04-create-service.sh`)
- Creates Fargate service with 1 task
- Integrates with ALB target group
- Uses default subnets and security groups
- Waits for service to become stable

### 5. ALB Routing (`05-create-listener-rule.sh`)
- Creates listener rule for `/ossmcp*` paths
- Routes traffic to target group
- Auto-detects available priority
- Creates HTTP:80 listener if needed

## Testing

### Health Check
```bash
curl http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "OpenSearch MCP Server",
  "opensearch": {
    "status": "connected",
    "cluster_name": "your-cluster"
  }
}
```

### MCP Endpoint
```bash
curl http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossmcp
```

## Claude Desktop Integration

✅ **Currently Working** - Add to your Claude Desktop configuration:

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

**Important:** The `--allow-http` flag is required for HTTP URLs. Restart Claude Desktop after configuration changes.

## Monitoring

### ECS Service Status
```bash
aws ecs describe-services \
  --cluster arn:aws:ecs:us-east-1:892551050452:cluster/fastmcp-time-server-cluster \
  --services opensearch-mcp-server \
  --profile mainadmin
```

### CloudWatch Logs
View logs in AWS Console:
- Log Group: `/ecs/opensearch-mcp-server`
- Region: `us-east-1`

### Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn $(cat .target-group-arn) \
  --profile mainadmin
```

## Resource Details

### Created Resources
- **ECR Repository**: `opensearch-mcp-server`
- **Target Group**: `opensearch-mcp-tg` (port 9898)
- **ECS Task Definition**: `opensearch-mcp-server`
- **ECS Service**: `opensearch-mcp-server` (1 task max)
- **CloudWatch Log Group**: `/ecs/opensearch-mcp-server`
- **ALB Listener Rule**: Routes `/ossmcp*` to target group

### Shared Resources (Not Modified)
- ECS Cluster: `fastmcp-time-server-cluster`
- ALB: `fastmcp-alb`
- VPC, Subnets, Security Groups

## Scaling Configuration

The service is configured with:
- **Desired Count**: 1
- **Maximum**: 1 (no auto-scaling)
- **Minimum Healthy**: 50%
- **Maximum Percent**: 200%

To modify scaling:
```bash
aws ecs update-service \
  --cluster arn:aws:ecs:us-east-1:892551050452:cluster/fastmcp-time-server-cluster \
  --service opensearch-mcp-server \
  --desired-count 1 \
  --profile mainadmin
```

## Troubleshooting

### Common Issues

1. **Service fails to start**
   - Check CloudWatch logs for errors
   - Verify OpenSearch credentials in task definition
   - Ensure security groups allow inbound traffic

2. **Health checks failing**
   - Verify `/health` endpoint responds
   - Check OpenSearch connectivity
   - Review target group health check settings

3. **ALB routing not working**
   - Check listener rule priority
   - Verify path pattern `/ossmcp*`
   - Ensure target group is healthy

### Debug Commands

```bash
# Check service events
aws ecs describe-services \
  --cluster arn:aws:ecs:us-east-1:892551050452:cluster/fastmcp-time-server-cluster \
  --services opensearch-mcp-server \
  --profile mainadmin \
  --query 'services[0].events'

# Check task logs
aws logs get-log-events \
  --log-group-name /ecs/opensearch-mcp-server \
  --log-stream-name ecs/opensearch-mcp-server/TASK_ID \
  --profile mainadmin

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $(cat .target-group-arn) \
  --profile mainadmin
```

## Cleanup

To remove all created resources:
```bash
./cleanup.sh
```

This will:
- Delete ECS service and wait for termination
- Remove ALB listener rule
- Delete target group
- Deregister task definition
- Delete CloudWatch log group
- Optionally delete ECR repository

## Security Considerations

- Container runs as non-root user
- Uses IAM task execution role
- Environment variables in task definition (consider AWS Secrets Manager for production)
- Security groups should be reviewed for production use
- Enable VPC Flow Logs for network monitoring

## Cost Optimization

- **Fargate**: Pay only for running tasks
- **Single Task**: Minimal compute costs
- **CloudWatch Logs**: Retention policy can be adjusted
- **ALB**: Shared with other services

## Production Recommendations

1. **Secrets Management**: Use AWS Secrets Manager for credentials
2. **Monitoring**: Set up CloudWatch alarms
3. **Security**: Review and harden security groups
4. **Backup**: Document configuration for disaster recovery
5. **Load Testing**: Verify performance under load