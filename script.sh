#!/bin/bash

# Define variables
FUNCTION_NAME="AskAgent"
PYTHON_FILE="lambda_function.py"
ZIP_FILE="build/lambda_function.zip"
VENV_DIR="build/venv"
ROLE_ARN="arn:aws:iam::969400485878:role/agent-lambda-execution-role"  # ARN of the IAM Role
REGION="us-east-1"  # Replace with your desired region
RUNTIME="python3.8"  # Replace with your Lambda runtime
HANDLER="lambda_function.lambda_handler"  # Replace with your handler function
API_NAME="AskAgentAPI"  # Name of the API Gateway
STAGE_NAME="prod"  # Stage name for deployment

# Step 1: Create the build directory (if it doesn't exist)
echo "Creating build directory..."
mkdir -p build

# Step 2: Clean up old files if they exist
echo "Cleaning up old files..."
rm -f $ZIP_FILE
rm -rf $VENV_DIR

# Step 3: Create a virtual environment (if dependencies are needed)
echo "Creating virtual environment..."
python3 -m venv $VENV_DIR

# Step 4: Install dependencies (if any)
echo "Installing dependencies..."
source $VENV_DIR/bin/activate  # Activate virtual environment
pip install --quiet requests  # Install any dependencies your Lambda function requires, e.g., requests

# Step 5: Package your Python code and dependencies into a .zip file
echo "Packaging Python code and dependencies into $ZIP_FILE..."

# Clean the build directory and recreate it
rm -rf build/*
mkdir -p build

# Copy the lambda function file to the build directory
cp $PYTHON_FILE build/

# Copy dependencies from the virtual environment
cp -r $VENV_DIR/lib/python3*/site-packages/* build/

# Create the .zip file with the correct structure
cd build
zip -r ../$ZIP_FILE .  # . indicates the current directory
cd ..

echo "Package created: $ZIP_FILE"

# Step 6: Upload the .zip file to AWS Lambda
echo "Uploading the .zip file to Lambda function $FUNCTION_NAME..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://$ZIP_FILE \
  --region $REGION \
  --profile account2

echo "Lambda function $FUNCTION_NAME updated."

# Step 7: Deploy the API Gateway (if needed)
echo "Deploying API Gateway $API_NAME to stage $STAGE_NAME..."

# Get the API Gateway ID
API_ID=$(aws apigateway get-rest-apis --region $REGION --profile account2 --query "items[?name=='$API_NAME'].id" --output text)

# Check if the API_ID is empty or "None"
if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
  echo "API Gateway $API_NAME does not exist. Skipping API Gateway deployment."
else
  echo "API Gateway $API_NAME found with ID: $API_ID"
  
  # Step 8: Create deployment for the API Gateway
  aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $STAGE_NAME \
    --region $REGION \
    --profile account2

  echo "API Gateway $API_NAME deployed to stage: $STAGE_NAME"
fi

# Step 9: Clean up
echo "Cleaning up..."
deactivate  # Deactivate virtual environment
rm -rf build  # Remove the build directory containing all build files
rm -f $ZIP_FILE  # Remove the .zip file

echo "Deployment complete and cleaned up!"
