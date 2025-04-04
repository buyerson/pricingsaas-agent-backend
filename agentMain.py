import time
import re
from agents import Runner, ItemHelpers
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextAnnotationDeltaEvent
from agent_modules.reportsAgent import create_reports_agent
from agent_modules.communityAgent import community_pricing_agent, PricingAgentContext as CommunityAgentContext

async def stream_agent_response(prompt: str):
    """
    Stream responses from reports and community agents sequentially.
    Runs reports agent first, then community agent, streaming responses as they come.
    
    Args:
        prompt: The user's pricing question
        
    Yields:
        Events containing text deltas, annotations, status updates, or completion signals
        
    Format:
    - Text deltas: {"type": "text_delta", "data": "text content"}
    - Annotations: {"type": "annotation", "data": {"type": "citation", "citation": {...}}}
    - Completion: {"type": "completion", "data": None}
    
    Universal Citation Format:
    {
        "id": "unique-id",           # File ID, topic ID, or generated ID
        "title": "Document Title",   # Document title with source prefix
        "source": "report|community", # Source of the citation
        "url": "optional-url",       # URL for community posts (optional)
        "content": "optional-content", # Preview content if available (optional)
        "metadata": {}               # Additional source-specific metadata (optional)
    }
    """
    print(f"Processing query: {prompt}")
    
    # Send initial status message
    yield {"type": "text_delta", "data": "🔍 Processing your question...\n\n"}
    
    # Run reports agent first
    try:
        # Start reports agent with markdown header
        yield {"type": "text_delta", "data": "\n\n## 📊 INSIGHTS FROM EXPERT REPORTS\n\n"}
        
        # Create and run the reports agent with streaming
        reports_agent = create_reports_agent()
        reports_result = Runner.run_streamed(reports_agent, prompt)
        
        # Process the streaming events from reports agent
        async for event in reports_result.stream_events():
            # Handle annotation events
            if event.type == "raw_response_event" and event.data.type == "response.output_text.annotation.added":
                # Format annotation for the UI client using universal format
                annotation = event.data.annotation
                
                # Debug: Print raw report annotation
                print(f"Raw report annotation: {annotation}")
                
                # Extract fields with proper fallbacks
                citation_id = getattr(annotation, "file_id", f"report-{time.time()}")
                citation_title = getattr(annotation, 'filename', 'Expert Report')
                
                # Ensure we have a valid ID
                if not citation_id:
                    citation_id = f"report-{time.time()}"
                
                formatted_annotation = {
                    "type": "citation",
                    "citation": {
                        "id": citation_id,
                        "title": f"[Report] {citation_title}",
                        "source": "report",
                        "content": getattr(annotation, 'content', ''),
                        "metadata": {
                            "original_type": "file_citation",
                            "file_id": citation_id
                        }
                    }
                }
                
                # Debug: Print formatted report annotation
                print(f"Formatted report annotation: {formatted_annotation}")
                
                yield {"type": "annotation", "data": formatted_annotation}

            # Handle text delta events
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):  
                if event.data.type == "response.output_text.delta":
                    # Normalize text to prevent excessive newlines
                    delta_text = event.data.delta
                    # Replace 3 or more consecutive newlines with just 2
                    delta_text = re.sub(r'\n{3,}', '\n\n', delta_text)
                    yield {"type": "text_delta", "data": delta_text}
                elif event.data.type == "response.completion":
                    # Reports agent completed
                    yield {"type": "text_delta", "data": "\n\n---\n\n"}  # Add separator between agents
                    yield {"type": "text_delta", "data": "   ✅ Expert reports analysis complete\n\n"}
            
    except Exception as e:
        print(f"Error during reports execution: {e}")
        yield {"type": "text_delta", "data": f"\n⚠️ Error retrieving reports: {str(e)}\n\n"}
    
    # Then run community agent
    try:
        # Start community agent with markdown header
        yield {"type": "text_delta", "data": "\n\n## 📚 COMMUNITY KNOWLEDGE\n\n"}
        
        # Create and run the community agent with streaming
        community_context = CommunityAgentContext()
        community_result = Runner.run_streamed(
            community_pricing_agent,
            [{"content": prompt, "role": "user"}],
            context=community_context
        )
        
        # Process the streaming events from community agent
        async for event in community_result.stream_events():
            # Handle annotation events
            if event.type == "raw_response_event" and event.data.type == "response.output_text.annotation.added":
                # Format annotation for the UI client using universal format
                annotation = event.data.annotation
                
                # Debug: Print raw community annotation
                print(f"Raw community annotation: {annotation}")
                
                # Extract fields with proper fallbacks
                post_id = getattr(annotation, "post_id", "")
                topic_id = getattr(annotation, "topic_id", getattr(annotation, "file_id", f"community-{time.time()}"))
                citation_title = getattr(annotation, 'title', getattr(annotation, 'filename', 'Community Post'))
                citation_url = getattr(annotation, "discourse_url", getattr(annotation, "url", ""))
                
                # Ensure we have a valid ID
                if not topic_id:
                    topic_id = f"community-{time.time()}"
                
                formatted_annotation = {
                    "type": "citation",
                    "citation": {
                        "id": topic_id,
                        "title": f"[Community] {citation_title}",
                        "source": "community",
                        "url": citation_url,
                        "content": getattr(annotation, 'content', ''),
                        "metadata": {
                            "original_type": "post_citation",
                            "post_id": post_id,
                            "topic_id": topic_id
                        }
                    }
                }
                
                # Debug: Print formatted community annotation
                print(f"Formatted community annotation: {formatted_annotation}")
                
                yield {"type": "annotation", "data": formatted_annotation}

            # Handle text delta events
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):  
                if event.data.type == "response.output_text.delta":
                    # Normalize text to prevent excessive newlines
                    delta_text = event.data.delta
                    # Replace 3 or more consecutive newlines with just 2
                    delta_text = re.sub(r'\n{3,}', '\n\n', delta_text)
                    yield {"type": "text_delta", "data": delta_text}
                elif event.data.type == "response.completion":
                    # Community agent completed
                    yield {"type": "text_delta", "data": "\n\n"}
                    yield {"type": "text_delta", "data": "   ✅ Community knowledge search complete\n\n"}
        
        # Check for annotations stored in the context and yield them
        if hasattr(community_context, 'annotations') and community_context.annotations:
            print(f"Found {len(community_context.annotations)} annotations in community context")
            for annotation_data in community_context.annotations:
                # Format annotation for the UI client using universal format
                topic_id = annotation_data.get("topic_id", f"community-{time.time()}")
                title = annotation_data.get("title", "Community Post")
                url = annotation_data.get("url", "")
                
                formatted_annotation = {
                    "type": "citation",
                    "citation": {
                        "id": topic_id,
                        "title": f"[Community] {title}",
                        "source": "community",
                        "url": url,
                        "content": annotation_data.get("content", ""),
                        "metadata": {
                            "original_type": "post_citation",
                            "topic_id": topic_id
                        }
                    }
                }
                
                print(f"Yielding community context annotation: {formatted_annotation}")
                yield {"type": "annotation", "data": formatted_annotation}
        
        # Send completion event after all annotations have been processed
        yield {"type": "completion", "data": None}
            
    except Exception as e:
        print(f"Error during community execution: {e}")
        yield {"type": "text_delta", "data": f"\n⚠️ Error retrieving community knowledge: {str(e)}\n\n"}
        yield {"type": "completion", "data": None}
