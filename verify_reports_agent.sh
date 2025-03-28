#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Run the verification script
python verify_reports_agent.py

# Deactivate the virtual environment
deactivate
