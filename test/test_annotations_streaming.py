"""
Test script specifically for verifying annotation streaming from both agents.
This is a simplified version that just checks if annotations are properly streamed.
"""

import asyncio
import os
import sys
import time

# Add the project root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_annotations_streaming():
    """
    Test that annotations from both community and reports agents are properly streamed.
    """
    from agentMain import stream_agent_response
    
    # Test query - using a simple query to speed up testing
    test_query = "SaaS pricing models"
    print(f"\n🔍 Testing annotation streaming with query: '{test_query}'")
    
    # Set a timeout for the test
    timeout = 60  # seconds
    start_time = time.time()
    
    # Collect annotations
    community_annotations = []
    report_annotations = []
    other_annotations = []
    
    # Stream the agent response with timeout
    try:
        async for event in stream_agent_response(test_query):
            # Check for timeout
            if time.time() - start_time > timeout:
                print(f"\n⏱️ Test timed out after {timeout} seconds")
                break
                
            # Process annotations
            if event["type"] == "annotation":
                annotation = event["data"]
                title = annotation.get("file_citation", {}).get("title", "")
                
                # Categorize the annotation
                if "[Community]" in title:
                    community_annotations.append(annotation)
                    print(f"📚 Found community annotation: {title}")
                elif "[Report]" in title:
                    report_annotations.append(annotation)
                    print(f"📊 Found report annotation: {title}")
                else:
                    other_annotations.append(annotation)
                    print(f"📄 Found other annotation: {title}")
                
                # If we have at least one annotation from each source, we can stop
                if community_annotations and report_annotations:
                    print("\n✅ Found annotations from both sources!")
                    break
            
            # For text deltas, just print a dot to show progress
            elif event["type"] == "text_delta":
                if "Status Update" in event["data"]:
                    print(event["data"], end="")
                else:
                    print(".", end="", flush=True)
    except Exception as e:
        print(f"\n❌ Error during streaming: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print("\n\n📊 Annotation Streaming Test Results:")
    print(f"- Community annotations: {len(community_annotations)}")
    print(f"- Report annotations: {len(report_annotations)}")
    print(f"- Other annotations: {len(other_annotations)}")
    
    # Print sample annotations if available
    if community_annotations:
        print(f"\nSample community annotation: {community_annotations[0]}")
    if report_annotations:
        print(f"\nSample report annotation: {report_annotations[0]}")
    
    # Verify we have annotations from both sources
    if len(community_annotations) > 0 and len(report_annotations) > 0:
        print("\n✅ Test passed: Annotations from both sources were properly streamed")
        return True
    else:
        print("\n❌ Test failed: Missing annotations from one or both sources")
        if len(community_annotations) == 0:
            print("   - No community annotations found")
        if len(report_annotations) == 0:
            print("   - No report annotations found")
        return False

if __name__ == "__main__":
    print("Starting Annotation Streaming Test...")
    print("This test verifies that annotations from both Community and Reports agents are properly streamed.")
    
    try:
        # Run the test
        success = asyncio.run(test_annotations_streaming())
        
        # Exit with appropriate code
        if success:
            print("Test completed successfully!")
            sys.exit(0)
        else:
            print("Test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError running the test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
