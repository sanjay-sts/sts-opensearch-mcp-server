#!/bin/bash

# OpenSearch MCP Server - ECS Task Definition Creation Script
# Creates ECS task definition with the Docker image from ECR

set -e

# Disable Git Bash path conversion for Windows
export MSYS_NO_PATHCONV=1

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
TASK_DEFINITION_FILE="task-definition.json"
LOG_GROUP_NAME="/ecs/opensearch-mcp-server-routing"

echo "📋 Creating ECS task definition..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Check if image URI exists
if [ ! -f ".image-uri" ]; then
    echo "❌ Image URI not found. Please run ./01-setup-ecr.sh first"
    exit 1
fi

IMAGE_URI=$(cat .image-uri)
echo "📍 Using image: $IMAGE_URI"

# Create CloudWatch log group if it doesn't exist
echo "📝 Creating CloudWatch log group..."
aws logs create-log-group \
    --log-group-name $LOG_GROUP_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    2>/dev/null || echo "Log group already exists"

# Verify log group was created
echo "🔍 Verifying log group exists..."
LOG_GROUP_EXISTS=$(aws logs describe-log-groups \
    --log-group-name-prefix $LOG_GROUP_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'logGroups[?logGroupName==`'$LOG_GROUP_NAME'`].logGroupName' \
    --output text)

if [ -z "$LOG_GROUP_EXISTS" ]; then
    echo "❌ Failed to create log group. Retrying..."
    aws logs create-log-group \
        --log-group-name $LOG_GROUP_NAME \
        --region $AWS_REGION \
        --profile $AWS_PROFILE
    echo "✅ Log group created successfully"
else
    echo "✅ Log group verified: $LOG_GROUP_EXISTS"
fi

# Replace placeholder in task definition with actual image URI
echo "🔧 Updating task definition with image URI..."
sed "s|PLACEHOLDER_IMAGE_URI|$IMAGE_URI|g" $TASK_DEFINITION_FILE > task-definition-updated.json

# Register task definition
echo "📋 Registering ECS task definition..."
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://task-definition-updated.json \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ Task definition created successfully!"
echo "📍 Task Definition ARN: $TASK_DEFINITION_ARN"

# Save task definition ARN for other scripts
echo $TASK_DEFINITION_ARN > .task-definition-arn

# Clean up temporary file
rm task-definition-updated.json

echo ""
echo "🎯 Next steps:"
echo "1. Update the environment variables in the task definition if needed"
echo "2. Run ./04-create-service.sh to create ECS service"
echo ""
echo "⚠️  Important: Make sure to update the OpenSearch connection details in the task definition:"
echo "   - OPENSEARCH_HOST: your OpenSearch cluster endpoint"
echo "   - OPENSEARCH_USERNAME: your OpenSearch username"
echo "   - OPENSEARCH_PASSWORD: your OpenSearch password"