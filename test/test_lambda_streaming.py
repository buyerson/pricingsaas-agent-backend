"""
Test script for the updated Lambda function with streaming.
"""

import json
import asyncio
import boto3
from unittest.mock import MagicMock
from lambda_function import send_streamed_response

class MockAPIGateway:
    """Mock API Gateway client for testing."""
    
    def __init__(self):
        self.messages = []
    
    def post_to_connection(self, ConnectionId, Data):
        """Mock the post_to_connection method."""
        data = json.loads(Data.decode('utf-8'))
        self.messages.append(data)
        print(f"Sent message: {data}")
        return {'ResponseMetadata': {'HTTPStatusCode': 200}}

async def test_lambda_streaming():
    """Test the Lambda function's streaming capability."""
    # Create a mock API Gateway client
    mock_apigateway = MockAPIGateway()
    
    # Test connection ID
    connection_id = "test-connection-id"
    
    # Test prompt
    prompt = "What is the best pricing model for a SaaS product?"
    
    print(f"Testing Lambda streaming with prompt: {prompt}")
    
    # Call the send_streamed_response function
    await send_streamed_response(mock_apigateway, connection_id, prompt)
    
    # Analyze the results
    print(f"\nTotal messages sent: {len(mock_apigateway.messages)}")
    
    # Count message types
    text_messages = sum(1 for m in mock_apigateway.messages if 'text' in m and m['text'])
    annotation_messages = sum(1 for m in mock_apigateway.messages if 'annotation' in m)
    annotations_messages = sum(1 for m in mock_apigateway.messages if 'annotations' in m)
    done_messages = sum(1 for m in mock_apigateway.messages if 'done' in m and m['done'])
    
    print(f"Text messages: {text_messages}")
    print(f"Individual annotation messages: {annotation_messages}")
    print(f"Batch annotations messages: {annotations_messages}")
    print(f"Done messages: {done_messages}")
    
    # Check if we got a final done message
    if done_messages > 0:
        print("✅ Test passed: Received final done message")
    else:
        print("❌ Test failed: Did not receive final done message")

if __name__ == "__main__":
    asyncio.run(test_lambda_streaming())
