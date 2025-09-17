#!/bin/bash

# OpenSearch MCP Server - ECR Setup Script
# This script creates ECR repository and pushes the Docker image

set -e

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
REPOSITORY_NAME="opensearch-mcp-server"
IMAGE_TAG="latest"

echo "🚀 Setting up ECR repository and pushing Docker image..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr create-repository \
    --repository-name $REPOSITORY_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    2>/dev/null || echo "Repository already exists"

# Get repository URI
REPOSITORY_URI=$(aws ecr describe-repositories \
    --repository-names $REPOSITORY_NAME \
    --region $AWS_REGION \
    --profile $AWS_PROFILE \
    --query 'repositories[0].repositoryUri' \
    --output text)

echo "📍 Repository URI: $REPOSITORY_URI"

# Get login token for ECR
echo "🔑 Logging into ECR..."
aws ecr get-login-password \
    --region $AWS_REGION \
    --profile $AWS_PROFILE | docker login --username AWS --password-stdin $REPOSITORY_URI

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t $REPOSITORY_NAME:$IMAGE_TAG .

# Tag image for ECR
echo "🏷️  Tagging image for ECR..."
docker tag $REPOSITORY_NAME:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push $REPOSITORY_URI:$IMAGE_TAG

echo "✅ Docker image successfully pushed to ECR!"
echo "📍 Image URI: $REPOSITORY_URI:$IMAGE_TAG"

# Save image URI for other scripts
echo $REPOSITORY_URI:$IMAGE_TAG > .image-uri

echo ""
echo "🎯 Next steps:"
echo "1. Run ./02-create-target-group.sh to create ALB target group"
echo "2. Run ./03-create-task-definition.sh to create ECS task definition"
echo "3. Run ./04-create-service.sh to create ECS service"