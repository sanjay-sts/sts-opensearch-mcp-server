#!/bin/bash

# OpenSearch MCP Server - ALB Listener Rule Creation Script
# Creates ALB listener rule to route traffic to the target group

set -e

# Disable Git Bash path conversion for Windows
export MSYS_NO_PATHCONV=1

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:892551050452:loadbalancer/app/fastmcp-alb/fcd5b72e858fbe0d"
PATH_PATTERN="/ossserver/*"  # Route all /ossserver paths to our service
PRIORITY=100  # Adjust if needed based on existing rules

echo "🔗 Creating ALB listener rule..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Check required files
if [ ! -f ".target-group-arn" ]; then
    echo "❌ Target group ARN not found. Please run ./02-create-target-group.sh first"
    exit 1
fi

TARGET_GROUP_ARN=$(cat .target-group-arn)
echo "📍 Target Group: $TARGET_GROUP_ARN"

# Get ALB listener ARN (HTTP:80)
echo "🔍 Finding ALB listener..."
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'Listeners[?Port==`80`].ListenerArn' \
    --output text)

if [ -z "$LISTENER_ARN" ]; then
    echo "❌ No HTTP:80 listener found on ALB"
    echo "📝 Creating HTTP:80 listener..."

    # Create HTTP listener if it doesn't exist
    LISTENER_ARN=$(aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=fixed-response,FixedResponseConfig='{MessageBody="Service not found",StatusCode="404",ContentType="text/plain"}' \
        --region $AWS_REGION \
        --profile $AWS_PROFILE \
        --query 'Listeners[0].ListenerArn' \
        --output text)

    echo "✅ HTTP:80 listener created"
fi

echo "📍 Listener ARN: $LISTENER_ARN"

# Check for existing rules to avoid conflicts
echo "🔍 Checking existing listener rules..."
EXISTING_RULES=$(aws elbv2 describe-rules \
    --listener-arn $LISTENER_ARN \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'Rules[?Priority!=`default`].Priority' \
    --output text)

echo "📝 Existing rule priorities: $EXISTING_RULES"

# Find available priority
while [[ " $EXISTING_RULES " =~ " $PRIORITY " ]]; do
    PRIORITY=$((PRIORITY + 1))
done

echo "📍 Using priority: $PRIORITY"

# Create listener rule
echo "🔗 Creating listener rule..."
RULE_ARN=$(aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority $PRIORITY \
    --conditions Field=path-pattern,Values="$PATH_PATTERN" \
    --actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'Rules[0].RuleArn' \
    --output text)

echo "✅ ALB listener rule created successfully!"
echo "📍 Rule ARN: $RULE_ARN"

# Save rule ARN
echo $RULE_ARN > .listener-rule-arn

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📍 Service endpoints:"
echo "   Health check: http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/health"
echo "   MCP endpoint: http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/ossmcp"
echo ""
echo "🔧 Claude Desktop configuration:"
echo '{'
echo '  "mcpServers": {'
echo '    "opensearch": {'
echo '      "command": "npx",'
echo '      "args": ["-y", "mcp-remote", "http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/ossmcp", "--allow-http"]'
echo '    }'
echo '  }'
echo '}'
echo ""
echo "📝 To test the deployment:"
echo "   curl http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/health"