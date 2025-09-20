# Stateless MCP Server Implementation Plan

## Overview
This document outlines the migration from a stateful to stateless OpenSearch MCP server deployment to resolve HTTP 404 "Session not found" errors in load-balanced environments.

## Problem Statement
The current FastMCP server defaults to stateful HTTP sessions per container. In a load-balanced remote setup, requests can land on replicas that don't know the session, resulting in HTTP 404 errors.

## Solution Approach
Implement stateless FastMCP server configuration (`stateless_http=True`) so requests can land on any replica without session pinning.

## Implementation Tasks

### Phase 1: Core Configuration Changes
- [x] Copy existing deployment structure
- [ ] **Modify oss_server.py**: Add `stateless_http=True` to FastMCP initialization
- [ ] **Update environment variables**: Add stateless-specific configuration
- [ ] **Test locally**: Verify stateless mode works correctly

### Phase 2: Infrastructure Updates
- [ ] **Resource naming**: Update all AWS resource names with "-stateless" suffix
- [ ] **Deployment scripts**: Modify 6 shell scripts (00-05-*.sh, cleanup.sh)
- [ ] **Task definition**: Update with stateless environment variables
- [ ] **ALB routing**: Change paths from `/ossserver/*` to `/ossserver-stateless/*`

### Phase 3: Testing & Validation
- [ ] **Find/create chat CLI**: Locate or build testing tool for MCP functionality
- [ ] **Test scenarios**: Create validation scripts for stateless behavior
- [ ] **Load testing**: Verify no session affinity issues
- [ ] **Performance comparison**: Compare stateful vs stateless performance

### Phase 4: Deployment
- [ ] **Deploy alongside existing**: Run both stateful and stateless versions
- [ ] **Functional testing**: Verify all MCP tools work correctly
- [ ] **Load balancer testing**: Confirm requests work across multiple replicas
- [ ] **Documentation update**: Update README with new endpoints

### Phase 5: Migration & Cleanup
- [ ] **Route traffic**: Point production traffic to stateless version
- [ ] **Clean up stateful**: Remove old ECS service, target groups, etc.
- [ ] **Archive configuration**: Keep stateful config for potential rollback
- [ ] **Monitor**: Verify no issues in production

## Key Changes Required

### 1. FastMCP Server (oss_server.py)
```python
# Current
mcp = FastMCP("OpenSearch MCP Server")

# Updated
mcp = FastMCP("OpenSearch MCP Server", stateless_http=True)
```

### 2. Resource Naming Convention
All AWS resources get "-stateless" suffix:
- ECR: `opensearch-mcp-server-stateless`
- Target Group: `opensearch-mcp-tg-stateless`
- ECS Service: `opensearch-mcp-server-stateless`
- Log Group: `/ecs/opensearch-mcp-server-stateless`

### 3. ALB Routing Paths
- Current: `/ossserver/health`, `/ossserver/ossmcp`
- Updated: `/ossserver-stateless/health`, `/ossserver-stateless/ossmcp`

### 4. Environment Variables
```bash
# Add stateless-specific configuration
MCP_STATELESS=true
MCP_PATH=/ossserver-stateless/ossmcp
```

## Success Criteria
1. ✅ **No session errors**: No HTTP 404 "Session not found" under load balancing
2. ✅ **Functional parity**: All OpenSearch tools work identically
3. ✅ **Performance**: Comparable or better performance than stateful version
4. ✅ **Scalability**: Multiple replicas handle requests without issues
5. ✅ **Clean deployment**: No resource conflicts with existing deployment

## Testing Strategy

### 1. Unit Testing
- Test individual MCP tools (list_indices, health_check)
- Verify stateless mode initialization
- Confirm environment variable handling

### 2. Integration Testing
- Deploy alongside existing stateful version
- Test with chat CLI tool
- Verify ALB routing to correct endpoints

### 3. Load Testing
- Multiple concurrent requests across replicas
- Session affinity disabled
- Performance metrics comparison

### 4. Rollback Plan
- Keep stateful deployment configuration
- Documented rollback procedure
- Quick switch capability if issues arise

## Risk Mitigation
1. **Deploy alongside**: Run both versions during testing
2. **Gradual migration**: Test thoroughly before switching traffic
3. **Monitoring**: Watch for errors and performance issues
4. **Quick rollback**: Maintain ability to revert quickly

## Current Deployment Info
- **GitHub Branch**: https://github.com/sanjay-sts/sts-opensearch-mcp-server/tree/ecr-esc-docker-routing-server
- **Current ALB**: `fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com`
- **Health Check**: `/ossserver/health`
- **MCP Endpoint**: `/ossserver/ossmcp`

## Timeline
- **Phase 1-2**: 2-3 hours (configuration changes)
- **Phase 3**: 2-3 hours (testing setup and execution)
- **Phase 4**: 1-2 hours (deployment and validation)
- **Phase 5**: 1 hour (migration and cleanup)

**Total Estimated Time**: 6-9 hours

## Notes
- This implementation follows the session_issue.md architecture recommendations
- Stateless mode is essential for production load-balanced deployments
- All changes are backward compatible and allow for easy rollback