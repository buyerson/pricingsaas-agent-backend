"""
Test script for the updated Agent Main with direct streaming from both agents.
Shows real-time streaming of both text and annotations.
"""

import asyncio
import os
import sys
import time
import json
from collections import defaultdict

# Add the project root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ANSI color codes for prettier output
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

async def run_test_query(test_query=None, timeout=120):
    """
    Run a test query through the agent and display the results with real-time streaming.
    
    Args:
        test_query: The query to test with. If None, a default query is used.
        timeout: Maximum time in seconds to wait for a response.
    """
    from agentMain import stream_agent_response
    
    # Use default query if none provided
    if test_query is None:
        test_query = "What are the best pricing strategies for SaaS products?"
    
    print(f"\n{BOLD}🔍 Testing with query:{RESET} '{test_query}'")
    
    # Track annotations by source
    annotations_by_source = defaultdict(list)
    total_annotations = 0
    
    # Track start time for timeout
    start_time = time.time()
    
    # Stream the agent response
    try:
        async for event in stream_agent_response(test_query):
            # Check for timeout
            if time.time() - start_time > timeout:
                print(f"\n{RED}⏱️ Test timed out after {timeout} seconds{RESET}")
                break
                
            if event["type"] == "text_delta":
                # Print text deltas in real-time
                # Check if this is a status message
                text = event["data"]
                if any(emoji in text for emoji in ["🔍", "📚", "⏳", "✅", "🔄"]):
                    # Status message - print in blue
                    print(f"{BLUE}{text}{RESET}", end="", flush=True)
                else:
                    # Regular response - print in normal color
                    print(text, end="", flush=True)
                    
            elif event["type"] == "annotation":
                # Process and display annotation in real-time
                annotation = event["data"]
                title = annotation.get("file_citation", {}).get("title", "")
                file_id = annotation.get("file_citation", {}).get("file_id", "")
                
                # Determine the source
                source = "Other"
                if "[Community]" in title:
                    source = "Community"
                    color = GREEN
                elif "[Report]" in title:
                    source = "Report"
                    color = YELLOW
                else:
                    color = RESET
                
                # Add to appropriate list
                annotations_by_source[source].append(annotation)
                total_annotations += 1
                
                # Print annotation notification
                print(f"\n{color}📎 {source} citation: {title} (ID: {file_id}){RESET}")
    
    except asyncio.CancelledError:
        print(f"\n{RED}Operation cancelled{RESET}")
        raise
    except Exception as e:
        print(f"\n{RED}Error during streaming: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()
        raise
    
    # Print summary of annotations
    elapsed_time = time.time() - start_time
    print(f"\n\n{BOLD}📊 Test Results (completed in {elapsed_time:.1f} seconds):{RESET}")
    print(f"- Total annotations: {total_annotations}")
    
    for source, annotations in annotations_by_source.items():
        if source == "Community":
            color = GREEN
        elif source == "Report":
            color = YELLOW
        else:
            color = RESET
            
        print(f"- {color}{source} annotations: {len(annotations)}{RESET}")
    
    # Print sample annotations if available
    if annotations_by_source["Community"]:
        print(f"\n{GREEN}Sample community annotation:{RESET}")
        print(json.dumps(annotations_by_source["Community"][0], indent=2))
        
    if annotations_by_source["Report"]:
        print(f"\n{YELLOW}Sample report annotation:{RESET}")
        print(json.dumps(annotations_by_source["Report"][0], indent=2))
    
    # Verify we have annotations from both sources
    if annotations_by_source["Community"] and annotations_by_source["Report"]:
        print(f"\n{GREEN}✅ Test passed: Annotations from both sources were properly streamed{RESET}")
        return True
    else:
        print(f"\n{RED}❌ Test failed: Missing annotations from one or both sources{RESET}")
        if not annotations_by_source["Community"]:
            print(f"{RED}   - No community annotations found{RESET}")
        if not annotations_by_source["Report"]:
            print(f"{RED}   - No report annotations found{RESET}")
        return False

async def interactive_mode():
    """
    Run the agent in interactive mode, allowing the user to enter multiple queries.
    """
    from agentMain import stream_agent_response
    
    print(f"\n{BOLD}🤖 Interactive Agent Testing Mode{RESET}")
    print("Type 'exit' to quit, or 'timeout X' to set a new timeout value (in seconds)")
    
    timeout = 120  # Default timeout in seconds
    
    while True:
        # Get user input
        try:
            user_input = input(f"\n{BOLD}Enter your query:{RESET} ")
        except EOFError:
            print("\nInput stream closed. Exiting.")
            break
            
        # Check for exit command
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Exiting interactive mode.")
            break
            
        # Check for timeout command
        if user_input.lower().startswith('timeout '):
            try:
                new_timeout = int(user_input.split(' ')[1])
                timeout = new_timeout
                print(f"Timeout set to {timeout} seconds")
            except (IndexError, ValueError):
                print(f"{RED}Invalid timeout value. Using current timeout of {timeout} seconds.{RESET}")
            continue
            
        # Skip empty input
        if not user_input.strip():
            continue
            
        # Run the query with the current timeout
        await run_test_query(user_input, timeout)

if __name__ == "__main__":
    print(f"{BOLD}Starting Agent Main Test...{RESET}")
    print("This test streams responses directly from both Community and Reports agents.")
    
    # Check if we should run in interactive mode
    interactive = "--interactive" in sys.argv or "-i" in sys.argv
    
    # Get custom query from command line if provided
    custom_query = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            custom_query = arg
            break
    
    try:
        if interactive:
            # Run in interactive mode
            asyncio.run(interactive_mode())
        else:
            # Run with the provided query or default
            asyncio.run(run_test_query(custom_query))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user.{RESET}")
    except ImportError as e:
        print(f"{RED}Error importing modules: {e}{RESET}")
        print("This script requires the virtual environment to be activated.")
        print("Please make sure all required packages are installed:")
        print("  pip install -r requirements.txt")
    except Exception as e:
        print(f"\n{RED}Error running the Agent Main test: {e}{RESET}")
        import traceback
        traceback.print_exc()
