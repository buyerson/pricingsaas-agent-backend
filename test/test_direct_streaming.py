"""
Test script for the updated stream_agent_response function that directly streams
from reports and community agents without using pricingAgent.
"""

import asyncio
import json

async def mock_stream_agent_response(prompt):
    """Mock implementation of stream_agent_response for testing"""
    # Initial status
    yield {"type": "text_delta", "data": "🔍 Processing your question...\n\n"}
    
    # Reports agent
    yield {"type": "text_delta", "data": "📊 Analyzing expert reports...\n\n"}
    await asyncio.sleep(0.5)  # Simulate processing time
    
    # Reports agent content
    yield {"type": "text_delta", "data": "Subscription-based pricing is the most common model for SaaS products.\n"}
    yield {"type": "text_delta", "data": "It provides predictable recurring revenue and is easy for customers to understand.\n"}
    yield {"type": "annotation", "data": {
        "type": "file_citation",
        "file_citation": {
            "file_id": "report-1",
            "title": "[Report] SaaS Pricing Strategies 2023",
            "source": "report"
        }
    }}
    yield {"type": "text_delta", "data": "Tiered pricing allows you to target different customer segments with appropriate feature sets.\n"}
    
    # Reports completion
    yield {"type": "text_delta", "data": "\n\n---\n\n"}
    yield {"type": "text_delta", "data": "   ✅ Expert reports analysis complete\n\n"}
    
    # Community agent
    yield {"type": "text_delta", "data": "📚 Searching community knowledge...\n\n"}
    await asyncio.sleep(0.5)  # Simulate processing time
    
    # Community agent content
    yield {"type": "text_delta", "data": "Many startups in our community have found success with freemium models.\n"}
    yield {"type": "text_delta", "data": "This allows users to try basic features before committing to a paid plan.\n"}
    yield {"type": "annotation", "data": {
        "type": "post_citation",
        "post_citation": {
            "post_id": "12345",
            "topic_id": "community-1",
            "title": "[Community] Freemium Success Stories",
            "url": "https://community.example.com/t/12345",
            "source": "community"
        }
    }}
    yield {"type": "text_delta", "data": "Usage-based pricing is gaining popularity for infrastructure and API-based SaaS products.\n"}
    
    # Community completion
    yield {"type": "text_delta", "data": "\n\n"}
    yield {"type": "text_delta", "data": "   ✅ Community knowledge search complete\n\n"}
    yield {"type": "completion", "data": None}

async def test_direct_streaming():
    """Test the direct streaming from reports and community agents"""
    query = "What is the best pricing model for a SaaS product?"
    
    print(f"Testing direct streaming with query: {query}")
    print("This simulates the updated agentMain.py behavior without pricingAgent\n")
    
    # Collect all events
    events = []
    report_content = []
    community_content = []
    current_section = "none"
    
    try:
        async for event in mock_stream_agent_response(query):
            event_type = event.get("type", "unknown")
            events.append(event)
            
            if event_type == "text_delta":
                data = event.get("data", "")
                
                # Determine which section we're in
                if "📊 Analyzing expert reports" in data:
                    current_section = "reports"
                    print(f"\n{data}", end="")
                elif "📚 Searching community knowledge" in data:
                    current_section = "community"
                    print(f"\n{data}", end="")
                elif "---" in data:
                    print(f"\n{data}", end="")
                elif "✅" in data:
                    print(f"{data}", end="")
                else:
                    # Add content to the appropriate section
                    if current_section == "reports":
                        report_content.append(data)
                    elif current_section == "community":
                        community_content.append(data)
                    print(f"{data}", end="")
                
            elif event_type == "annotation":
                annotation = event.get("data", {})
                if "file_citation" in annotation:
                    title = annotation.get("file_citation", {}).get("title", "Unknown")
                    print(f"\nREPORT ANNOTATION: {title}\n")
                elif "post_citation" in annotation:
                    title = annotation.get("post_citation", {}).get("title", "Unknown")
                    print(f"\nCOMMUNITY ANNOTATION: {title}\n")
                
            elif event_type == "completion":
                print("\n\nCOMPLETION")
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
    
    print("\nREPORTS CONTENT:")
    print("".join(report_content))
    
    print("\nCOMMUNITY CONTENT:")
    print("".join(community_content))

if __name__ == "__main__":
    asyncio.run(test_direct_streaming())
