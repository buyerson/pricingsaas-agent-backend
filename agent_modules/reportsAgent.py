"""
Reports Pricing Agent - A specialized agent for answering pricing questions
using document search with FileSearchTool.
"""

import json
import asyncio
import uuid
from typing import List, Dict, Any

# Import from openai-agents package
from agents import Agent, FileSearchTool, Runner
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextAnnotationDeltaEvent

### CONTEXT

# Simple context class without BaseModel dependency
class ReportsAgentContext:
    """Context for the Reports Agent, storing query, search results, and annotations."""
    def __init__(self):
        self.query = None
        self.last_search_results = None
        self.annotations = []


### AGENTS

# Create the reports pricing agent
def create_reports_agent():
    """Create and return the reports pricing agent."""
    return Agent(
        name="Reports Pricing Agent",
        instructions="""You are a SaaS pricing expert. You help users with pricing questions by searching through document knowledge.
        
        # Routine
        1. When a user asks a pricing question, use the file search tool to find relevant information.
        2. Analyze the search results and provide a comprehensive answer based on the document knowledge.
        3. For each unique document referenced in your answer, include an annotation with [Doc X] where X is the document number.
        4. Your response should be a single, coherent answer that synthesizes information from all relevant documents.
        5. If the search doesn't return relevant results, acknowledge the limitations and provide general pricing advice based on your knowledge.
        6. Focus on practical, actionable advice about SaaS pricing strategies, models, and best practices.
        
        # Working with Document Data
        - The search is limited to the top 3 most relevant matches to ensure high quality results
        - When referencing information from a specific document, use the annotation format [Doc X] where X corresponds to the document number
        - Make sure to integrate insights from all relevant documents into a cohesive response
        
        Remember that you are a pricing expert, so frame your responses in a professional, knowledgeable manner.
        """,
        tools=[
            FileSearchTool(
                max_num_results=3,
                vector_store_ids=["vs_67e02282782c819183c40c7413cb1a6e"],
                include_search_results=True,
            )
        ],
    )


### STREAM FUNCTIONS

async def stream_reports_agent_response(prompt: str):
    """Stream the agent's response with annotations."""
    agent = create_reports_agent()
    result = Runner.run_streamed(agent, input=prompt)

    async for event in result.stream_events():
        if event.type == "raw_response_event" and event.data.type == "response.output_text.annotation.added":
            # print("event.data")
            # print(event.data)
            # print("endof event.data")
            yield {"type": "annotation", "data": event.data.annotation}

        # Handle text delta events
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):  
            if event.data.type == "response.output_text.delta":
                yield {"type": "text_delta", "data": event.data.delta}
            elif event.data.type == "response.completion":
                yield {"type": "completion", "data": None}


# Sends streamed data over WebSocket to the client
async def send_reports_streamed_response(apigateway, connection_id, prompt):
    """Send the streamed response to the client via WebSocket."""
    try:
        annotations = []
        
        async for event in stream_reports_agent_response(prompt):
            
            if event["type"] == "text_delta":
                # Send text deltas immediately
                apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({'text': event["data"], 'done': False}).encode('utf-8')
                )
            elif event["type"] == "annotation":                
                annotation_dict = {
                    "type": getattr(event["data"], "type", "file_citation"),
                    "file_citation": {
                        "file_id": getattr(event["data"], "file_id", ""),
                        "title": getattr(event["data"], "filename", "")
                    }
                }
                annotations.append(annotation_dict)

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
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'error': str(e), 'done': True}).encode('utf-8')
        )


### RUN

async def main():
    """Main function to run the Reports Pricing Agent interactively."""
    print("\nReports Pricing Agent")
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
        
        async for event in stream_reports_agent_response(user_input):
            if event["type"] == "text_delta":
                print(event["data"], end="", flush=True)
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
