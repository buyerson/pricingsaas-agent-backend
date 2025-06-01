#!/bin/bash

# Usage: ./deployFunction.sh <function-name>

if [ -z "$1" ]; then
  echo "Usage: $0 <function-name>"
  exit 1
fi

supabase functions deploy "$1"
