#!/bin/bash

# OpenSearch MCP Server - Cleanup Script
# Removes all AWS resources created for the OpenSearch MCP service

set -e

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
CLUSTER_ARN="arn:aws:ecs:us-east-1:892551050452:cluster/fastmcp-time-server-cluster"
SERVICE_NAME="opensearch-mcp-server"
TARGET_GROUP_NAME="opensearch-mcp-tg"
REPOSITORY_NAME="opensearch-mcp-server"
LOG_GROUP_NAME="//ecs//opensearch-mcp-server"

echo "🧹 Cleaning up OpenSearch MCP Server resources..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Function to check if file exists and read it
read_file_if_exists() {
    if [ -f "$1" ]; then
        cat "$1"
    else
        echo ""
    fi
}

# Delete ECS service
if [ -f ".service-arn" ]; then
    echo "🗑️  Deleting ECS service..."
    aws ecs update-service \
        --cluster $CLUSTER_ARN \
        --service $SERVICE_NAME \
        --desired-count 0 \
        --region $AWS_REGION \
        --profile $AWS_PROFILE >/dev/null

    aws ecs wait services-stable \
        --cluster $CLUSTER_ARN \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --profile $AWS_PROFILE

    aws ecs delete-service \
        --cluster $CLUSTER_ARN \
        --service $SERVICE_NAME \
        --region $AWS_REGION \
        --profile $AWS_PROFILE >/dev/null

    echo "✅ ECS service deleted"
    rm -f .service-arn
fi

# Delete ALB listener rule
RULE_ARN=$(read_file_if_exists ".listener-rule-arn")
if [ -n "$RULE_ARN" ]; then
    echo "🗑️  Deleting ALB listener rule..."
    aws elbv2 delete-rule \
        --rule-arn $RULE_ARN \
        --region $AWS_REGION \
        --profile $AWS_PROFILE >/dev/null
    echo "✅ ALB listener rule deleted"
    rm -f .listener-rule-arn
fi

# Delete target group
TARGET_GROUP_ARN=$(read_file_if_exists ".target-group-arn")
if [ -n "$TARGET_GROUP_ARN" ]; then
    echo "🗑️  Deleting target group..."
    aws elbv2 delete-target-group \
        --target-group-arn $TARGET_GROUP_ARN \
        --region $AWS_REGION \
        --profile $AWS_PROFILE >/dev/null
    echo "✅ Target group deleted"
    rm -f .target-group-arn
fi

# Deregister task definition (optional - keeps history)
TASK_DEFINITION_ARN=$(read_file_if_exists ".task-definition-arn")
if [ -n "$TASK_DEFINITION_ARN" ]; then
    echo "🗑️  Deregistering task definition..."
    aws ecs deregister-task-definition \
        --task-definition $TASK_DEFINITION_ARN \
        --region $AWS_REGION \
        --profile $AWS_PROFILE >/dev/null
    echo "✅ Task definition deregistered"
    rm -f .task-definition-arn
fi

# Delete CloudWatch log group
echo "🗑️  Deleting CloudWatch log group..."
aws logs delete-log-group \
    --log-group-name $LOG_GROUP_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE 2>/dev/null || echo "Log group already deleted or doesn't exist"

# Delete ECR repository (optional - removes all images)
read -p "🤔 Do you want to delete the ECR repository and all images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Deleting ECR repository..."
    aws ecr delete-repository \
        --repository-name $REPOSITORY_NAME \
        --force \
        --region $AWS_REGION \
        --profile $AWS_PROFILE >/dev/null 2>&1 || echo "Repository already deleted or doesn't exist"
    echo "✅ ECR repository deleted"
    rm -f .image-uri
fi

# Clean up local files
rm -f .listener-arn

echo ""
echo "✅ Cleanup complete!"
echo "📝 Remaining resources (if any):"
echo "   - ECS cluster: $CLUSTER_ARN (shared resource, not deleted)"
echo "   - ALB: Not deleted (shared resource)"
echo ""
echo "💡 If you deleted the ECR repository, you'll need to run ./01-setup-ecr.sh again to redeploy"