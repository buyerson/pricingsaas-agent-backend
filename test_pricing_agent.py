"""
Test script for the Pricing Agent.
"""

import asyncio
import os
import sys

# Add the project root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Pricing Agent test...")
    print("This agent combines results from both Community and Reports agents.")
    
    try:
        # Import the main function from the pricingAgent module
        from agent_modules.pricingAgent import main
        
        # Run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("This script requires the virtual environment to be activated.")
        print("Please make sure all required packages are installed:")
        print("  pip install -r requirements.txt")
    except Exception as e:
        print(f"\nError running the Pricing Agent: {e}")
