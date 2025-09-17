#!/bin/bash

# OpenSearch MCP Server - ECS Service Creation Script
# Creates ECS service with ALB integration (max 1 task, no auto-scaling)

set -e

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
CLUSTER_ARN="arn:aws:ecs:us-east-1:892551050452:cluster/fastmcp-time-server-cluster"
SERVICE_NAME="opensearch-mcp-server-routing"
DESIRED_COUNT=1

echo "🚀 Creating ECS service..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Check required files
if [ ! -f ".task-definition-arn" ]; then
    echo "❌ Task definition ARN not found. Please run ./03-create-task-definition.sh first"
    exit 1
fi

if [ ! -f ".target-group-arn" ]; then
    echo "❌ Target group ARN not found. Please run ./02-create-target-group.sh first"
    exit 1
fi

TASK_DEFINITION_ARN=$(cat .task-definition-arn)
TARGET_GROUP_ARN=$(cat .target-group-arn)

echo "📍 Task Definition: $TASK_DEFINITION_ARN"
echo "📍 Target Group: $TARGET_GROUP_ARN"

# Get subnets from the ECS cluster (assuming they exist)
echo "🔍 Getting subnet information..."
SUBNETS=$(aws ec2 describe-subnets \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --filters "Name=default-for-az,Values=true" \
    --query 'Subnets[*].SubnetId' \
    --output text | tr '\t' ',')

echo "📍 Using subnets: $SUBNETS"

# Get default security group
VPC_ID=$(aws ec2 describe-subnets \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --subnet-ids $(echo $SUBNETS | cut -d',' -f1) \
    --query 'Subnets[0].VpcId' \
    --output text)

SECURITY_GROUP=$(aws ec2 describe-security-groups \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --filters "Name=group-name,Values=default" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

echo "📍 Using security group: $SECURITY_GROUP"

# Create ECS service with ALB integration
echo "🚀 Creating ECS service..."
SERVICE_ARN=$(aws ecs create-service \
    --cluster $CLUSTER_ARN \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_DEFINITION_ARN \
    --desired-count $DESIRED_COUNT \
    --launch-type FARGATE \
    --platform-version LATEST \
    --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=opensearch-mcp-server-routing,containerPort=9898 \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
    --enable-execute-command \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'service.serviceArn' \
    --output text)

echo "✅ ECS service created successfully!"
echo "📍 Service ARN: $SERVICE_ARN"

# Save service ARN
echo $SERVICE_ARN > .service-arn

# Wait for service to become stable
echo "⏳ Waiting for service to become stable (this may take a few minutes)..."
aws ecs wait services-stable \
    --cluster $CLUSTER_ARN \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE

echo "✅ Service is now stable!"

# Get service status
echo "📊 Service status:"
aws ecs describe-services \
    --cluster $CLUSTER_ARN \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'services[0].{ServiceName:serviceName,Status:status,RunningCount:runningCount,DesiredCount:desiredCount}'

echo ""
echo "🎯 Next steps:"
echo "1. Run ./05-create-listener-rule.sh to create ALB routing rule"
echo "2. Test the service at: http://fastmcp-alb-1326912822.us-east-1.elb.amazonaws.com/ossserver/health"
echo ""
echo "📝 Service Configuration:"
echo "   - Max tasks: 1 (no auto-scaling)"
echo "   - Platform: Fargate"
echo "   - Port: 9898"
echo "   - Health check: /ossserver/health endpoint"