#!/bin/bash

# OpenSearch MCP Server - Target Group Creation Script
# Creates ALB target group for the OpenSearch MCP service

set -e

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
TARGET_GROUP_NAME="opensearch-mcp-tg"
VPC_ID=""  # Will be auto-detected from ALB
ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:892551050452:loadbalancer/app/fastmcp-alb/fcd5b72e858fbe0d"
PORT=9898

echo "🎯 Creating ALB target group for OpenSearch MCP Server..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Get VPC ID from ALB
echo "🔍 Getting VPC ID from ALB..."
VPC_ID=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'LoadBalancers[0].VpcId' \
    --output text)

echo "📍 VPC ID: $VPC_ID"

# Create target group
echo "🎯 Creating target group..."
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_NAME \
    --protocol HTTP \
    --port $PORT \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-enabled \
    --health-check-path "//health" \
    --health-check-protocol HTTP \
    --health-check-port $PORT \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 10 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --matcher HttpCode=200 \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "✅ Target group created successfully!"
echo "📍 Target Group ARN: $TARGET_GROUP_ARN"

# Save target group ARN for other scripts
echo $TARGET_GROUP_ARN > .target-group-arn

# Get ALB listener ARN (assuming HTTP:80 listener exists)
echo "🔍 Finding ALB listener..."
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'Listeners[?Port==`80`].ListenerArn' \
    --output text)

if [ -z "$LISTENER_ARN" ]; then
    echo "⚠️  No HTTP:80 listener found on ALB"
    echo "📝 You'll need to create a listener rule manually or run ./05-create-listener-rule.sh"
else
    echo "📍 Listener ARN: $LISTENER_ARN"
    echo $LISTENER_ARN > .listener-arn
fi

echo ""
echo "🎯 Next steps:"
echo "1. Run ./03-create-task-definition.sh to create ECS task definition"
echo "2. Run ./05-create-listener-rule.sh to create ALB routing rule (BEFORE service)"
echo "3. Run ./04-create-service.sh to create ECS service"