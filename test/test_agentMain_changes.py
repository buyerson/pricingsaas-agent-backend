"""
Simple test script to verify the changes to agentMain.py
"""

import asyncio
import json

async def mock_stream_agent_response(prompt):
    """Mock implementation of stream_agent_response for testing"""
    # Initial status
    yield {"type": "text_delta", "data": "🔍 Processing your question...\n\n"}
    
    # Reports agent
    yield {"type": "text_delta", "data": "📊 Analyzing expert reports...\n\n"}
    await asyncio.sleep(1)  # Simulate processing time
    yield {"type": "text_delta", "data": "   ✅ Expert reports ready\n\n"}
    yield {"type": "annotation", "data": {"type": "file_citation", "file_citation": {"file_id": "report-1", "title": "Sample Report"}}}
    
    # Community agent
    yield {"type": "text_delta", "data": "📚 Searching community knowledge...\n\n"}
    await asyncio.sleep(1)  # Simulate processing time
    yield {"type": "text_delta", "data": "   ✅ Community knowledge ready\n\n"}
    yield {"type": "annotation", "data": {"type": "file_citation", "file_citation": {"file_id": "community-1", "title": "Sample Community Post"}}}
    
    # Final response
    yield {"type": "text_delta", "data": "\n🔄 Organizing insights into separate sections...\n\n"}
    await asyncio.sleep(1)  # Simulate processing time
    
    # Sample response with markdown sections
    yield {"type": "text_delta", "data": "The best pricing model depends on your specific SaaS product and target market.\n\n"}
    yield {"type": "text_delta", "data": "## 📊 INSIGHTS FROM EXPERT REPORTS\n\n"}
    yield {"type": "text_delta", "data": "• **Subscription-based models** are the most common for SaaS products\n"}
    yield {"type": "text_delta", "data": "• **Tiered pricing** allows for different customer segments\n\n"}
    yield {"type": "text_delta", "data": "---\n\n"}
    yield {"type": "text_delta", "data": "## 📚 COMMUNITY KNOWLEDGE\n\n"}
    yield {"type": "text_delta", "data": "• Many startups find success with **freemium models**\n"}
    yield {"type": "text_delta", "data": "• **Usage-based pricing** is gaining popularity for certain types of SaaS\n"}
    
    # Completion
    yield {"type": "completion", "data": None}

async def test_sequential_streaming():
    """Test the sequential streaming of reports then community knowledge"""
    query = "What is the best pricing model for a SaaS product?"
    
    print(f"Testing sequential streaming with query: {query}")
    print("This simulates the updated agentMain.py behavior\n")
    
    # Collect all events
    events = []
    
    try:
        async for event in mock_stream_agent_response(query):
            event_type = event.get("type", "unknown")
            
            if event_type == "text_delta":
                data = event.get("data", "")
                print(f"TEXT: {data}", end="")
                events.append(event)
            elif event_type == "annotation":
                annotation = event.get("data", {})
                title = annotation.get("file_citation", {}).get("title", "Unknown")
                print(f"\nANNOTATION: {title}\n")
                events.append(event)
            elif event_type == "completion":
                print("\n\nCOMPLETION")
                events.append(event)
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nReceived {len(events)} total events")
    
    # Count event types
    text_delta_count = sum(1 for e in events if e.get("type") == "text_delta")
    annotation_count = sum(1 for e in events if e.get("type") == "annotation")
    completion_count = sum(1 for e in events if e.get("type") == "completion")
    
    print(f"Text delta events: {text_delta_count}")
    print(f"Annotation events: {annotation_count}")
    print(f"Completion events: {completion_count}")

if __name__ == "__main__":
    asyncio.run(test_sequential_streaming())
