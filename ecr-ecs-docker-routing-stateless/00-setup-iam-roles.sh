#!/bin/bash

# OpenSearch MCP Server - IAM Role Setup
# Creates IAM role with OpenSearch permissions for ECS tasks

set -e

# Disable Git Bash path conversion for Windows
export MSYS_NO_PATHCONV=1

# Configuration
AWS_PROFILE="mainadmin"
AWS_REGION="us-east-1"
ECS_TASK_ROLE_NAME="ecsTaskRole"
OPENSEARCH_DOMAIN_ARN="arn:aws:es:us-east-1:892551050452:domain/sts-use1-oss-poc-cluster"
ACCOUNT_ID="892551050452"

echo "🔐 Setting up IAM role for OpenSearch MCP Server..."

# Set AWS profile
export AWS_PROFILE=$AWS_PROFILE

# Function to check if IAM policy exists
policy_exists() {
    aws iam get-role-policy \
        --role-name $ECS_TASK_ROLE_NAME \
        --policy-name OpenSearchAccess \
        --profile $AWS_PROFILE \
        --output text \
        --query 'PolicyName' 2>/dev/null || echo ""
}

# Check if ECS task role exists, create if it doesn't
echo "🔍 Checking if ECS task role exists..."
if aws iam get-role --role-name $ECS_TASK_ROLE_NAME --profile $AWS_PROFILE >/dev/null 2>&1; then
    echo "✅ ECS task role already exists"
else
    echo "🆕 Creating ECS task role..."

    # Create trust policy for ECS tasks
    cat > ecs-task-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # Create the role
    aws iam create-role \
        --role-name $ECS_TASK_ROLE_NAME \
        --assume-role-policy-document file://ecs-task-trust-policy.json \
        --description "ECS task role for OpenSearch MCP server" \
        --profile $AWS_PROFILE

    echo "✅ ECS task role created successfully!"

    # Clean up trust policy file
    rm ecs-task-trust-policy.json
fi

# Update task definition to use the correct task role ARN
TASK_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ECS_TASK_ROLE_NAME"

# Update IAM role with OpenSearch permissions
echo "🔍 Checking IAM role permissions..."
if [ -z "$(policy_exists)" ]; then
    echo "🔐 Adding OpenSearch permissions to ECS task role..."

    # Create policy document for OpenSearch access
    cat > opensearch-policy.json << EOF
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
                "$OPENSEARCH_DOMAIN_ARN",
                "$OPENSEARCH_DOMAIN_ARN/*"
            ]
        }
    ]
}
EOF

    # Attach policy to role
    aws iam put-role-policy \
        --role-name $ECS_TASK_ROLE_NAME \
        --policy-name OpenSearchAccess \
        --policy-document file://opensearch-policy.json \
        --profile $AWS_PROFILE

    echo "✅ IAM permissions added successfully!"

    # Clean up policy file
    rm opensearch-policy.json
else
    echo "✅ IAM permissions already exist"
fi

# Update task definition with correct role ARN
echo "🔧 Updating task definition with task role ARN..."
sed -i "s|\"taskRoleArn\": \".*\"|\"taskRoleArn\": \"$TASK_ROLE_ARN\"|g" task-definition.json

echo ""
echo "🎉 IAM role setup complete!"
echo ""
echo "📍 IAM Role Details:"
echo "   Role Name: $ECS_TASK_ROLE_NAME"
echo "   Role ARN: $TASK_ROLE_ARN"
echo "   Policy: OpenSearchAccess"
echo ""
echo "🔐 OpenSearch Permissions Granted:"
echo "   Domain: $OPENSEARCH_DOMAIN_ARN"
echo "   Actions: ESHttpPost, ESHttpPut, ESHttpGet, ESHttpDelete, ESHttpHead"
echo ""
echo "⚠️  Next Step - Configure OpenSearch FGAC:"
echo "   You need to add the IAM role to OpenSearch fine-grained access control"
echo "   This can be done through:"
echo "   1. OpenSearch Dashboards Security plugin"
echo "   2. AWS OpenSearch console"
echo "   3. OpenSearch REST API"
echo ""
echo "🎯 Next deployment steps:"
echo "1. Configure OpenSearch FGAC to allow the IAM role"
echo "2. Run ./01-setup-ecr.sh to build and push Docker image"
echo "3. Run ./02-create-target-group.sh to create target group"
echo "4. Run ./03-create-task-definition.sh to create task definition"
echo "5. Continue with remaining deployment scripts"
echo ""
echo "💡 The task definition now uses IAM role authentication!"