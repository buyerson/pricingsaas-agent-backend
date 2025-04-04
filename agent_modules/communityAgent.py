"""
Community Pricing Agent - A specialized agent for answering pricing questions
using community knowledge from Discourse forums.
"""

from __future__ import annotations as _annotations

import os
import json
import asyncio
import uuid
import re
import time
from typing import List, Dict, Any

from pydantic import BaseModel

# Import from the openai-agents package, not our local agents directory
from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextAnnotationDeltaEvent
from pinecone import Pinecone, ServerlessSpec

# Import helper functions
from helpers.community_helpers import (
    process_pinecone_results,
    format_search_results,
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE
)

# Initialize Pinecone client if API key is available
pc = None
index = None

if PINECONE_API_KEY:
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(PINECONE_INDEX_NAME)
        print(f"Successfully connected to Pinecone index: {PINECONE_INDEX_NAME}")
    except Exception as e:
        print(f"Error connecting to Pinecone: {e}")
        print("Community knowledge search will not be available.")


### CONTEXT

class PricingAgentContext(BaseModel):
    """Context for the Pricing Agent, storing query, search results, and annotations."""
    query: str | None = None
    last_search_results: Dict[str, Any] | None = None
    full_topics: Dict[str, Any] = {}
    annotations: List[Dict[str, Any]] = []


### TOOLS

@function_tool(
    name_override="community_knowledge_search", 
    description_override="Search the community knowledge base for information about pricing topics."
)
async def community_knowledge_search(
    context: RunContextWrapper[PricingAgentContext], 
    query: str
) -> str:
    """
    Search the community knowledge base for information about pricing topics.
    
    Args:
        query: The pricing question or topic to search for in the community knowledge base.
    """
    # Store the query in context
    context.context.query = query
    
    # Reset previous results
    context.context.full_topics = {}
    context.context.annotations = []
    
    # Check if required clients are initialized
    if not OPENAI_API_KEY:
        return "Error: OpenAI API key is not set or client initialization failed. Please set the OPENAI_API_KEY environment variable."
            
    if not pc or not index:
        return "Error: Pinecone client is not initialized or connection failed. Please set the PINECONE_API_KEY environment variable and ensure the index exists."
    
    print(f"Processing query: '{query}'")
    print("Optimizing query for embedding-based search...")
    
    # Process search results with query optimization and limited to top 5 matches
    results = await process_pinecone_results(index, query, context.context)
    
    # Store the results in context for future reference
    context.context.last_search_results = results
    
    # Format the results as a readable string
    formatted_results = format_search_results(results, context.context)
    
    return formatted_results


### AGENTS

community_pricing_agent = Agent[PricingAgentContext](
    name="Community Pricing Agent",
    handoff_description="A helpful agent that can answer pricing questions by querying community knowledge.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a SaaS pricing expert. You help users with pricing questions by searching through community knowledge.
    
    # Routine
    1. When a user asks a pricing question, use the community_knowledge_search tool to find relevant information.
    2. The search will optimize the query using AI to get the best possible matches from the vector database.
    3. The search will only return the top 5 high-confidence matches (80% or higher) and will fetch full topic data from Discourse.
    4. Analyze the search results and provide a comprehensive answer based on the community knowledge.
    5. For each unique topic referenced in your answer, include an annotation with [Topic X] where X is the topic number.
    6. Your response should be a single, coherent answer that synthesizes information from all relevant topics.
    7. If the search doesn't return relevant results, acknowledge the limitations and provide general pricing advice based on your knowledge.
    8. Focus on practical, actionable advice about SaaS pricing strategies, models, and best practices.
    
    # Working with Full Topic Data
    - The search tool now uses AI to optimize queries for better embedding-based search results
    - The search is limited to the top 5 most relevant matches to ensure high quality results
    - The tool fetches complete conversations for each relevant topic
    - Use this detailed information to provide more accurate and comprehensive answers
    - When referencing information from a specific topic, use the annotation format [Topic X] where X corresponds to the topic number
    - Make sure to integrate insights from all relevant topics into a cohesive response
    
    Remember that you are a pricing expert, so frame your responses in a professional, knowledgeable manner.
    """,
    tools=[community_knowledge_search],
)


### STREAMING FUNCTIONS

async def stream_community_agent_response(prompt: str):
    """Stream the community agent's response with annotations.
    
    Args:
        prompt: The user's pricing question
        
    Yields:
        Events containing text deltas, annotations, or completion signals
    """
    context = PricingAgentContext()
    result = Runner.run_streamed(
        community_pricing_agent, 
        [{"content": prompt, "role": "user"}],
        context=context
    )

    async for event in result.stream_events():
        # Handle annotation events
        if event.type == "raw_response_event" and event.data.type == "response.output_text.annotation.added":
            yield {"type": "annotation", "data": event.data.annotation}

        # Handle text delta events
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):  
            if event.data.type == "response.output_text.delta":
                # Normalize text to prevent excessive newlines
                delta_text = event.data.delta
                # Replace 3 or more consecutive newlines with just 2
                delta_text = re.sub(r'\n{3,}', '\n\n', delta_text)
                yield {"type": "text_delta", "data": delta_text}
            elif event.data.type == "response.completion":
                # Don't yield completion yet, we'll do it after processing context annotations
                pass
    
    # Send any annotations stored in the context
    if hasattr(context, 'annotations') and context.annotations:
        print(f"Found {len(context.annotations)} annotations in community context")
        for annotation in context.annotations:
            print(f"Yielding community context annotation: {annotation}")
            yield {"type": "annotation", "data": annotation}
    
    # Now yield completion after all annotations have been processed
    yield {"type": "completion", "data": None}


# Sends streamed data over WebSocket to the client
async def send_community_streamed_response(apigateway, connection_id, prompt):
    """Send the streamed response to the client via WebSocket.
    
    Args:
        apigateway: The API Gateway client
        connection_id: The WebSocket connection ID
        prompt: The user's pricing question
    """
    try:
        annotations = []
        
        async for event in stream_community_agent_response(prompt):
            
            if event["type"] == "text_delta":
                # Normalize text to prevent excessive newlines
                text_data = event["data"]
                # Replace 3 or more consecutive newlines with just 2
                text_data = re.sub(r'\n{3,}', '\n\n', text_data)
                
                # Send text deltas immediately
                apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({'text': text_data, 'done': False}).encode('utf-8')
                )
            elif event["type"] == "annotation":
                # Process annotation data
                if isinstance(event["data"], dict):
                    if "file_citation" in event["data"]:
                        # Convert to the universal citation format
                        file_id = event["data"]["file_citation"].get("file_id", f"community-{time.time()}")
                        title = event["data"]["file_citation"].get("title", "Community Post")
                        
                        annotation_dict = {
                            "type": "citation",
                            "citation": {
                                "id": file_id,
                                "title": f"[Community] {title}" if not title.startswith("[Community]") else title,
                                "source": "community",
                                "content": "",
                                "metadata": {
                                    "original_type": "post_citation",
                                    "topic_id": file_id
                                }
                            }
                        }
                    elif "type" in event["data"] and event["data"]["type"] == "topic_citation":
                        # Handle topic_citation from context.annotations
                        topic_id = event["data"].get("topic_id", f"community-{time.time()}")
                        title = event["data"].get("title", "Community Post")
                        url = event["data"].get("url", "")
                        
                        annotation_dict = {
                            "type": "citation",
                            "citation": {
                                "id": topic_id,
                                "title": f"[Community] {title}" if not title.startswith("[Community]") else title,
                                "source": "community",
                                "url": url,
                                "content": event["data"].get("content", ""),
                                "metadata": {
                                    "original_type": "post_citation",
                                    "topic_id": topic_id
                                }
                            }
                        }
                    else:
                        # Convert to the universal citation format
                        topic_id = event["data"].get("topic_id", event["data"].get("file_id", f"community-{time.time()}"))
                        title = event["data"].get("title", event["data"].get("filename", "Community Post"))
                        url = event["data"].get("url", "")
                        
                        annotation_dict = {
                            "type": "citation",
                            "citation": {
                                "id": topic_id,
                                "title": f"[Community] {title}" if not title.startswith("[Community]") else title,
                                "source": "community",
                                "url": url,
                                "content": event["data"].get("content", ""),
                                "metadata": {
                                    "original_type": "post_citation",
                                    "topic_id": topic_id,
                                    "post_id": event["data"].get("post_id", "")
                                }
                            }
                        }
                else:
                    # Convert to the universal citation format
                    topic_id = getattr(event["data"], "topic_id", getattr(event["data"], "file_id", f"community-{time.time()}"))
                    title = getattr(event["data"], "title", getattr(event["data"], "filename", "Community Post"))
                    url = getattr(event["data"], "discourse_url", getattr(event["data"], "url", ""))
                    
                    annotation_dict = {
                        "type": "citation",
                        "citation": {
                            "id": topic_id,
                            "title": f"[Community] {title}" if not title.startswith("[Community]") else title,
                            "source": "community",
                            "url": url,
                            "content": getattr(event["data"], "content", ""),
                            "metadata": {
                                "original_type": "post_citation",
                                "topic_id": topic_id,
                                "post_id": getattr(event["data"], "post_id", "")
                            }
                        }
                    }
                
                # Debug: Print community annotation
                print(f"Community agent generated annotation: {json.dumps(annotation_dict)}")
                
                annotations.append(annotation_dict)
                
                # Send individual annotation immediately for real-time display
                apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        'text': '',
                        'done': False,
                        'annotation': annotation_dict
                    }).encode('utf-8')
                )

            elif event["type"] == "completion":
                # When we get a completion event, send the annotations
                apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        'text': '',
                        'done': False,
                        'annotations': annotations
                    }).encode('utf-8')
                )

        # Final message to indicate the stream is done
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'text': '', 'annotations': annotations, 'done': True}).encode('utf-8')
        )
    except Exception as e:
        print(f"Error during WebSocket streaming: {e}")
        import traceback
        traceback.print_exc()
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'error': str(e), 'done': True}).encode('utf-8')
        )


### RUN

async def main():
    """Main function to run the Community Pricing Agent interactively."""
    current_agent = community_pricing_agent
    input_items: list[TResponseInputItem] = []
    context = PricingAgentContext()

    # Use a random UUID for the conversation ID
    conversation_id = uuid.uuid4().hex[:16]

    print("\nCommunity Pricing Agent")
    print("======================")
    print("Ask questions about SaaS pricing strategies, models, and best practices.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("Enter your pricing question: ")
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        print("Processing your question...")
        annotations = []
        
        async for event in stream_community_agent_response(user_input):
            if event["type"] == "text_delta":
                # Normalize text to prevent excessive newlines
                text_data = event["data"]
                # Replace 3 or more consecutive newlines with just 2
                text_data = re.sub(r'\n{3,}', '\n\n', text_data)
                print(text_data, end="", flush=True)
            elif event["type"] == "annotation":
                annotation_dict = {
                    "type": getattr(event["data"], "type", "file_citation"),
                    "file_citation": {
                        "file_id": getattr(event["data"], "file_id", ""),
                        "title": getattr(event["data"], "filename", "")
                    }
                }
                annotations.append(annotation_dict)
        
        if annotations:
            print("\n\nReferences:")
            for i, annotation in enumerate(annotations, 1):
                file_citation = annotation.get("file_citation", {})
                print(f"[{i}] {file_citation.get('title', 'Unknown')} - {file_citation.get('file_id', 'Unknown ID')}")
        
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
