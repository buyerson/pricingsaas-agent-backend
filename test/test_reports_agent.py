"""
Test script for the Reports Agent.
"""

import asyncio
import os
import sys

# Add the project root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Reports Agent test...")
    
    try:
        # Import the main function from the reportsAgent module
        from agent_modules.reportsAgent import main
        
        # Run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("This script requires the virtual environment to be activated.")
        print("Please run the script using the shell script:")
        print("  ./run_reports_agent.sh")
        print("Or activate the virtual environment manually:")
        print("  source venv/bin/activate")
        print("  python3 ./test/test_reports_agent.py")
        print("  deactivate")
    except Exception as e:
        print(f"\nError running the Reports Agent: {e}")
