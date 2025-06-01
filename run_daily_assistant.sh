#!/bin/bash

# Activate the virtual environment 
source venv/bin/activate

# Run the daily assistant agent test script
python test/test_daily_assistant.py

# Deactivate the virtual environment
deactivate
