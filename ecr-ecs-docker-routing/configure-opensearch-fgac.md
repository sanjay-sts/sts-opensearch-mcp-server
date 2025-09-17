# OpenSearch Fine-Grained Access Control (FGAC) Configuration

This guide explains how to configure OpenSearch FGAC to allow the IAM role `ecsTaskRole` to access the cluster.

## 🎯 Overview

To use IAM role authentication with OpenSearch, you need to configure the OpenSearch cluster to recognize and allow the IAM role. This is done through Fine-Grained Access Control (FGAC).

## 📋 Prerequisites

- OpenSearch cluster with FGAC enabled
- Master user credentials for OpenSearch
- IAM role created by `./00-setup-iam-roles.sh`

## 🔧 Configuration Options

### Option 1: Using OpenSearch Dashboards (Recommended)

1. **Access OpenSearch Dashboards**
   ```
   https://search-sts-use1-oss-poc-cluster-3w2nvvdxkhlytzzquhqrr62hay.aos.us-east-1.on.aws/_dashboards
   ```

2. **Login as Master User**
   - Use your master username and password

3. **Navigate to Security**
   - Click on the hamburger menu (☰)
   - Go to "Security" section

4. **Create Role Mapping**
   - Click on "Roles"
   - Find or create a role with appropriate permissions (e.g., `all_access` for admin, or create custom role)
   - Click on the role name
   - Go to "Mapped users" tab
   - Click "Manage mapping"
   - Add the IAM role ARN: `arn:aws:iam::892551050452:role/ecsTaskRole`

### Option 2: Using AWS CLI (Alternative)

```bash
# Get OpenSearch domain configuration
aws opensearch describe-domain \
  --domain-name sts-use1-oss-poc-cluster \
  --profile mainadmin

# Note: Role mapping typically requires master user credentials
# and is usually done through the Dashboard or REST API
```

### Option 3: Using REST API

```bash
# Create role mapping via REST API (requires master user auth)
curl -X PUT "https://search-sts-use1-oss-poc-cluster-3w2nvvdxkhlytzzquhqrr62hay.aos.us-east-1.on.aws/_plugins/_security/api/rolesmapping/all_access" \
  -H "Content-Type: application/json" \
  -u "master-username:master-password" \
  -d '{
    "backend_roles": ["arn:aws:iam::892551050452:role/ecsTaskRole"],
    "hosts": [],
    "users": []
  }'
```

## 🛡️ Recommended Role Configuration

For the MCP server, create a custom role with minimal required permissions:

### Custom Role: `mcp_server_role`

**Cluster Permissions:**
- `cluster_composite_ops`
- `cluster_monitor`

**Index Permissions:**
```json
{
  "index_patterns": ["sts-*", "movielens-*", "documents"],
  "allowed_actions": [
    "indices_all",
    "read",
    "write",
    "create_index",
    "manage"
  ]
}
```

### Creating Custom Role via Dashboards

1. Go to Security → Roles
2. Click "Create role"
3. Set role name: `mcp_server_role`
4. Add cluster permissions: `cluster_composite_ops`, `cluster_monitor`
5. Add index permissions for patterns: `sts-*`, `movielens-*`, `documents`
6. Save the role
7. Go to Role Mappings
8. Map the IAM role ARN to this custom role

## 🧪 Testing the Configuration

After configuring FGAC, test the connection:

```bash
# Deploy the service and test
./01-setup-ecr.sh
./02-create-target-group.sh
./03-create-task-definition.sh
./05-create-listener-rule.sh
./04-create-service.sh

# Test health endpoint
curl http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/health
```

Expected response with IAM authentication:
```json
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

## ❌ Troubleshooting

### Common Issues

1. **403 Forbidden Error**
   - IAM role not mapped in OpenSearch FGAC
   - Role doesn't have sufficient permissions
   - Check CloudWatch logs for detailed error messages

2. **Connection Timeout**
   - Security groups not allowing traffic
   - OpenSearch cluster not accessible from ECS

3. **Authentication Failed**
   - IAM role ARN incorrect
   - ECS task not assuming the correct role

### Debug Steps

```bash
# Check ECS task logs
aws logs tail /ecs/opensearch-mcp-server-routing --follow --profile mainadmin

# Check IAM role
aws iam get-role --role-name ecsTaskRole --profile mainadmin

# Check OpenSearch domain status
aws opensearch describe-domain --domain-name sts-use1-oss-poc-cluster --profile mainadmin
```

## 📚 References

- [OpenSearch Fine-Grained Access Control](https://opensearch.org/docs/latest/security/access-control/)
- [AWS OpenSearch IAM Integration](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)
- [OpenSearch Security Plugin](https://opensearch.org/docs/latest/security/)

## 🎯 Next Steps

Once FGAC is configured:
1. Deploy the service using the deployment scripts
2. Test the health endpoint
3. Verify OpenSearch connectivity
4. Configure Claude Desktop to use the new endpoints