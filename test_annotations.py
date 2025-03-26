import json
import asyncio
from unittest.mock import MagicMock
from agent import stream_agent_response, send_streamed_response

class MockApiGatewayClient:
    """Mock API Gateway Management API client"""
    def __init__(self):
        self.messages = []
    
    def post_to_connection(self, ConnectionId, Data):
        """Mock method to post to a WebSocket connection"""
        message = json.loads(Data.decode('utf-8'))
        self.messages.append(message)
        print(f"Message sent to connection {ConnectionId}: {message}")
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

async def test_annotations(custom_prompt=None):
    """Test the annotation streaming functionality"""
    mock_apigateway = MockApiGatewayClient()
    connection_id = "test-connection-id"
    prompt = custom_prompt or "Tell me about SaaS pricing models (short version)"
    
    print("\n=== Testing Annotation Streaming ===")
    print(f"Input prompt: {prompt}")
    
    try:
        await send_streamed_response(mock_apigateway, connection_id, prompt)
        
        # Print summary of messages sent
        print("\n=== Messages Sent to WebSocket ===")
        
        # Count different types of messages
        text_messages = [msg for msg in mock_apigateway.messages if 'text' in msg and msg['text']]
        annotation_messages = [msg for msg in mock_apigateway.messages if 'annotations' in msg]
        done_messages = [msg for msg in mock_apigateway.messages if msg.get('done') is True]
        
        print(f"Number of text messages: {len(text_messages)}")
        print(f"Number of annotation messages: {len(annotation_messages)}")
        
        # Print annotations if any
        if annotation_messages:
            print("\n=== Annotations ===")
            for msg in annotation_messages:
                print(f"Annotations: {msg['annotations']}")
        
        # Check if the stream completed successfully
        if done_messages:
            print("\nStream completed successfully")
        else:
            print("\nStream did not complete")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_annotations())
    print("\nTest completed.")
