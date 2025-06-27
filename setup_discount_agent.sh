#!/bin/bash

echo "Setting up dependencies for the discount classifier..."

# Check if pip or pip3 is available
if command -v pip3 &> /dev/null; then
  PIP="pip3"
elif command -v pip &> /dev/null; then
  PIP="pip"
else
  echo "Error: pip is not installed. Please install pip to continue."
  exit 1
fi

# Install required packages
echo "Installing required packages..."
$PIP install pandas openai

echo "Setup complete. You can now run ./run_discount_agent.sh"
echo "Remember to set your OpenAI API key with: export OPENAI_API_KEY='your-api-key'"
