import json
import asyncio
import boto3
from agents import Agent, FileSearchTool, Runner
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextAnnotationDeltaEvent
# Import additional response types if needed for annotations
# This is the asynchronous function to stream agent's response
async def stream_agent_response(prompt: str):
    agent = Agent(
        name="Assistant",
        instructions="You are a SaaS pricing assistant that answers questions based on knowledge base using files search tool.", 
        tools=[
            FileSearchTool(
                max_num_results=3,
                vector_store_ids=["vs_67e02282782c819183c40c7413cb1a6e"],
                include_search_results=True,
            )
        ],
    )
    result = Runner.run_streamed(agent, input=prompt)

    async for event in result.stream_events():
        if event.type == "raw_response_event" and event.data.type == "response.output_text.annotation.added":
            print("event.data")
            print(event.data)
            print("endof event.data")
            yield {"type": "annotation", "data": event.data.annotation}

        # Handle text delta events (same as before)
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):  
            if event.data.type == "response.output_text.delta":
                yield {"type": "text_delta", "data": event.data.delta}
            # elif event.type == "response.output_text.annotation.added":
            #     print(event.data)
            #     yield {"type": "annotation", "data": event.annotation}
            elif event.type == "response.completion":
                yield {"type": "completion", "data": None}


# Sends streamed data over WebSocket to the client
async def send_streamed_response(apigateway, connection_id, prompt):
    try:
        annotations = []
        
        async for event in stream_agent_response(prompt):
            
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
