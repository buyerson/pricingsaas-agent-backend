#!/bin/bash

# Set OpenAI API key if not already set
if [ -z "$OPENAI_API_KEY" ]; then
  echo "Warning: OPENAI_API_KEY environment variable is not set."
  echo "Please set it before running the script to use the LLM classification."
  echo "You can set it with: export OPENAI_API_KEY='your-api-key'"
fi

# Check if python3 is available
if command -v python3 &> /dev/null; then
  # Run the discount classifier with python3
  python3 -c "from tools.classifier import classify_discounts, get_classification_stats, print_stats; results = classify_discounts(); stats = get_classification_stats(results); print_stats(stats);"
else
  # Try with python as fallback
  if command -v python &> /dev/null; then
    python -c "from tools.classifier import classify_discounts, get_classification_stats, print_stats; results = classify_discounts(); stats = get_classification_stats(results); print_stats(stats);"
  else
    echo "Error: Neither python3 nor python was found. Please install Python to run this script."
    exit 1
  fi
fi

echo "Script execution complete."
