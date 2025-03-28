"""
Simple verification script for the Reports Agent.
"""

import os
import sys
import asyncio

# Add the project root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_agent():
    """Test the Reports Agent with a simple query."""
    from agent_modules.reportsAgent import stream_reports_agent_response
    
    test_query = "What are the best pricing strategies for SaaS products?"
    print(f"Testing Reports Agent with query: '{test_query}'")
    
    # Process a few events to verify the agent is working
    count = 0
    async for event in stream_reports_agent_response(test_query):
        if count < 5:  # Just process the first 5 events to keep it short
            print(f"Event type: {event['type']}")
            if event['type'] == 'text_delta':
                print(f"Text: {event['data']}")
            elif event['type'] == 'annotation':
                print(f"Annotation: {event['data']}")
            count += 1
        else:
            break
    
    print("Agent verification completed successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(test_agent())
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("This script requires the virtual environment to be activated.")
        print("Please run the script using the shell script:")
        print("  ./verify_reports_agent.sh")
        print("Or activate the virtual environment manually:")
        print("  source venv/bin/activate")
        print("  python3 ./verify_reports_agent.py")
        print("  deactivate")
    except Exception as e:
        print(f"Error testing the Reports Agent: {e}")
