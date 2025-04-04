"""
Test script for the updated stream_agent_response function.
"""

import asyncio
import json
from agentMain import stream_agent_response

async def test_stream_agent():
    """Test the stream_agent_response function with a simple query."""
    query = "What is the best pricing model for a SaaS product?"
    
    print(f"Testing stream_agent_response with query: {query}")
    
    # Collect all events
    events = []
    
    try:
        async for event in stream_agent_response(query):
            # Just print the event type and a sample of the data to keep output clean
            event_type = event.get("type", "unknown")
            
            if event_type == "text_delta":
                data_sample = event.get("data", "")[:30] + "..." if len(event.get("data", "")) > 30 else event.get("data", "")
                print(f"Received {event_type} event: {data_sample}")
            elif event_type == "annotation":
                print(f"Received {event_type} event")
            elif event_type == "completion":
                print(f"Received {event_type} event")
            else:
                print(f"Received unknown event type: {event_type}")
            
            events.append(event)
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Received {len(events)} total events")
    
    # Count event types
    text_delta_count = sum(1 for e in events if e.get("type") == "text_delta")
    annotation_count = sum(1 for e in events if e.get("type") == "annotation")
    completion_count = sum(1 for e in events if e.get("type") == "completion")
    
    print(f"Text delta events: {text_delta_count}")
    print(f"Annotation events: {annotation_count}")
    print(f"Completion events: {completion_count}")

if __name__ == "__main__":
    asyncio.run(test_stream_agent())
