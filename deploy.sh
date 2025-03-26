#!/bin/bash

set -e

# Define variables
FUNCTION_NAME="ws_sendmessage_handler"
PYTHON_FILE="lambda_function.py"
ZIP_FILE="build/lambda_function.zip"
VENV_DIR="build/venv"
REGION="us-east-1"
RUNTIME="python3.13"
HANDLER="lambda_function.lambda_handler"
PROFILE="account2"

# Create build directory
mkdir -p build
rm -f $ZIP_FILE

# Create virtual environment
python3.13 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install dependencies with correct platform
pip install --upgrade pip
pip install \
    --platform manylinux2014_x86_64 \
    --target=$VENV_DIR/lib/python3.13/site-packages \
    --implementation cp \
    --python-version 3.13 \
    --only-binary=:all: \
    --upgrade pydantic jiter openai-agents

# Detect site-packages path dynamically
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

# Package dependencies from site-packages
cd "$SITE_PACKAGES"
zip -r9 "$OLDPWD/$ZIP_FILE" ./* > /dev/null
cd "$OLDPWD"

# Add your lambda handler and agent files to the root of the zip
zip -g "$ZIP_FILE" "$PYTHON_FILE" agent.py > /dev/null

# Update the existing Lambda function code
echo "🔄 Updating Lambda function code..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://$ZIP_FILE \
    --region $REGION \
    --profile $PROFILE

# Wait for the update to complete
echo "⏳ Waiting for Lambda update to finish..."

MAX_RETRIES=30
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    STATUS=$(aws lambda get-function-configuration \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --profile $PROFILE \
        --query 'LastUpdateStatus' \
        --output text)

    STATE=$(aws lambda get-function-configuration \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --profile $PROFILE \
        --query 'State' \
        --output text)

    echo "🔍 LastUpdateStatus: $STATUS, State: $STATE"

    if [[ "$STATUS" == "Successful" && "$STATE" == "Active" ]]; then
        echo "✅ Lambda function is active and ready!"
        break
    elif [[ "$STATUS" == "Failed" || "$STATE" == "Failed" ]]; then
        echo "❌ Lambda deployment failed."
        exit 1
    fi

    RETRY=$((RETRY+1))
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "⚠️ Timed out waiting for Lambda to become ready. Check the AWS Console for more info."
    exit 1
fi
