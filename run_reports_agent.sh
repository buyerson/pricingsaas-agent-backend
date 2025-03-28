#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Run the reports agent test script
python test_reports_agent.py

# Deactivate the virtual environment
deactivate
