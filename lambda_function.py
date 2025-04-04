import json
import asyncio
import boto3
import re
import time
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from agentMain import stream_agent_response

async def send_streamed_response(apigateway, connection_id, prompt):
    """
    Stream the agent's response over WebSocket to the client.
    
    Args:
        apigateway: The API Gateway client
        connection_id: The WebSocket connection ID
        prompt: The user's pricing question
    """
    try:
        # Track annotations by source to ensure we include both types
        report_annotations = []
        community_annotations = []
        all_annotations = []
        
        print(f"Streaming response for prompt: {prompt}")
        
        async for event in stream_agent_response(prompt):
            print(event)  # Output raw stream events to console
            
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
                # Process the universal citation format
                annotation_dict = {}
                
                # Debug: Print raw annotation event
                print(f"Raw annotation event: {json.dumps(event)}")
                
                if isinstance(event["data"], dict):
                    # Check if it's already in the universal format
                    if "type" in event["data"] and event["data"]["type"] == "citation" and "citation" in event["data"]:
                        # Already in the universal format, use as is
                        annotation_dict = event["data"]
                        print(f"Using universal format annotation: {json.dumps(annotation_dict)}")
                    
                    # Handle legacy format with file_citation or post_citation
                    elif "type" in event["data"] and event["data"]["type"] in ["file_citation", "post_citation"]:
                        citation_type = event["data"]["type"]
                        citation_data = event["data"].get(citation_type, {})
                        source = citation_data.get("source", "report" if citation_type == "file_citation" else "community")
                        
                        print(f"Converting legacy {citation_type} to universal format")
                        
                        # Convert to universal format
                        if citation_type == "file_citation":
                            file_id = citation_data.get("file_id", f"report-{time.time()}")
                            title = citation_data.get("title", "Unknown Report")
                            
                            annotation_dict = {
                                "type": "citation",
                                "citation": {
                                    "id": file_id,
                                    "title": title if title.startswith("[Report]") else f"[Report] {title}",
                                    "source": "report",
                                    "content": citation_data.get("content", ""),
                                    "metadata": {
                                        "original_type": "file_citation",
                                        "file_id": file_id
                                    }
                                }
                            }
                        else:  # post_citation
                            topic_id = citation_data.get("topic_id", f"community-{time.time()}")
                            title = citation_data.get("title", "Unknown Community Post")
                            
                            annotation_dict = {
                                "type": "citation",
                                "citation": {
                                    "id": topic_id,
                                    "title": title if title.startswith("[Community]") else f"[Community] {title}",
                                    "source": "community",
                                    "url": citation_data.get("url", ""),
                                    "content": citation_data.get("content", ""),
                                    "metadata": {
                                        "original_type": "post_citation",
                                        "post_id": citation_data.get("post_id", ""),
                                        "topic_id": topic_id
                                    }
                                }
                            }
                    
                    # Handle raw annotation data (direct from agent)
                    else:
                        # Determine if this is from reports or community
                        is_community = False
                        if any(key in event["data"] for key in ["topic_id", "post_id", "discourse_url"]):
                            is_community = True
                        
                        print(f"Processing raw annotation data, is_community={is_community}")
                        
                        if is_community:
                            # Create a community citation
                            post_id = event["data"].get("post_id", "")
                            topic_id = event["data"].get("topic_id", event["data"].get("file_id", f"community-{time.time()}"))
                            title = event["data"].get("title", event["data"].get("filename", f"Topic {topic_id}"))
                            url = event["data"].get("discourse_url", event["data"].get("url", ""))
                            
                            annotation_dict = {
                                "type": "citation",
                                "citation": {
                                    "id": topic_id,
                                    "title": f"[Community] {title}",
                                    "source": "community",
                                    "url": url,
                                    "content": event["data"].get("content", ""),
                                    "metadata": {
                                        "original_type": "post_citation",
                                        "post_id": post_id,
                                        "topic_id": topic_id
                                    }
                                }
                            }
                        else:
                            # Create a report citation
                            file_id = event["data"].get("file_id", f"report-{time.time()}")
                            title = event["data"].get("title", event["data"].get("filename", f"Document {file_id}"))
                            
                            annotation_dict = {
                                "type": "citation",
                                "citation": {
                                    "id": file_id,
                                    "title": f"[Report] {title}",
                                    "source": "report",
                                    "content": event["data"].get("content", ""),
                                    "metadata": {
                                        "original_type": "file_citation",
                                        "file_id": file_id
                                    }
                                }
                            }
                
                # Debug: Print final processed annotation
                print(f"Final processed annotation: {json.dumps(annotation_dict)}")
                
                # Track annotations by source
                all_annotations.append(annotation_dict)
                
                # Determine the source and add to the appropriate list
                if annotation_dict.get("type") == "citation":
                    source = annotation_dict.get("citation", {}).get("source")
                    if source == "report":
                        report_annotations.append(annotation_dict)
                        print(f"Added report annotation: {annotation_dict.get('citation', {}).get('title')}")
                    elif source == "community":
                        community_annotations.append(annotation_dict)
                        print(f"Added community annotation: {annotation_dict.get('citation', {}).get('title')}")
                
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
                # Filter out annotations with empty titles or IDs
                valid_report_annotations = []
                valid_community_annotations = []
                
                # Process report annotations
                for annotation in report_annotations:
                    if annotation.get("type") == "citation":
                        citation = annotation.get("citation", {})
                        if citation.get("title") and citation.get("id"):
                            valid_report_annotations.append(annotation)
                
                # Process community annotations
                for annotation in community_annotations:
                    if annotation.get("type") == "citation":
                        citation = annotation.get("citation", {})
                        if citation.get("title") and citation.get("id"):
                            valid_community_annotations.append(annotation)
                
                # Combine both types of annotations
                valid_annotations = valid_report_annotations + valid_community_annotations
                
                # Log annotation counts
                print(f"Valid report annotations: {len(valid_report_annotations)}")
                print(f"Valid community annotations: {len(valid_community_annotations)}")
                print(f"Total valid annotations: {len(valid_annotations)}")
                
                # When we get a completion event, send the annotations
                apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        'text': '',
                        'done': False,
                        'annotations': valid_annotations
                    }).encode('utf-8')
                )

        # Final message to indicate the stream is done
        valid_report_annotations = []
        valid_community_annotations = []
        
        # Debug: Print all collected annotations by source
        print(f"Report annotations collected: {len(report_annotations)}")
        for i, annotation in enumerate(report_annotations):
            print(f"Report annotation {i+1}: {json.dumps(annotation)}")
            
            # Validate and add to final list
            if annotation.get("type") == "citation":
                citation = annotation.get("citation", {})
                if citation.get("title") and citation.get("id"):
                    valid_report_annotations.append(annotation)
                    print(f"  ✓ Valid report citation: {citation.get('title')}")
                else:
                    print(f"  ✗ Invalid report citation: missing title or id")
        
        print(f"Community annotations collected: {len(community_annotations)}")
        for i, annotation in enumerate(community_annotations):
            print(f"Community annotation {i+1}: {json.dumps(annotation)}")
            
            # Validate and add to final list
            if annotation.get("type") == "citation":
                citation = annotation.get("citation", {})
                if citation.get("title") and citation.get("id"):
                    valid_community_annotations.append(annotation)
                    print(f"  ✓ Valid community citation: {citation.get('title')}")
                else:
                    print(f"  ✗ Invalid community citation: missing title or id")
        
        # Combine both types of annotations
        final_annotations = valid_report_annotations + valid_community_annotations
        
        # Debug: Print final annotations by source
        print(f"Final report annotations: {len(valid_report_annotations)}")
        print(f"Final community annotations: {len(valid_community_annotations)}")
        print(f"Total final annotations: {len(final_annotations)}")
        
        # List all final annotations
        for i, annotation in enumerate(final_annotations):
            if annotation.get("type") == "citation":
                source = annotation.get("citation", {}).get("source", "unknown")
                title = annotation.get("citation", {}).get("title", "untitled")
                print(f"  {i+1}. [{source}] {title}")
        
        # Send final message with all valid annotations from both sources
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                'text': '',
                'annotations': final_annotations,
                'done': True
            }).encode('utf-8')
        )
    except Exception as e:
        print(f"Error during WebSocket streaming: {e}")
        import traceback
        traceback.print_exc()
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'error': str(e), 'done': True}).encode('utf-8')
        )

def normalize_text(text):
    """
    Normalize text by removing excessive newlines.
    
    Args:
        text: The text to normalize
        
    Returns:
        Normalized text with no more than 2 consecutive newlines
    """
    # Replace 3 or more consecutive newlines with just 2
    return re.sub(r'\n{3,}', '\n\n', text)

def lambda_handler(event, context):
    print("Current IAM Role ARN:", context.invoked_function_arn)

    # Extract connection ID and set up API Gateway client
    connection_id = event['requestContext']['connectionId']
    domain = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    endpoint_url = f"https://{domain}/{stage}"

    apigateway = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=endpoint_url
    )

    # Parse the prompt from the event body
    try:
        body = event.get('body', '{}')
        body_data = json.loads(body)
        prompt = body_data.get('prompt', 'Tell me something.')
        print(f"Prompt: {prompt}")
    except Exception as e:
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'error': f'Invalid request body: {str(e)}'}).encode('utf-8')
        )
        return {'statusCode': 400}

    # Create and run the async loop for streaming
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_streamed_response(apigateway, connection_id, prompt))
    loop.close()

    return {
        'statusCode': 200
    }
