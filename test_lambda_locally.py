import json
import asyncio
import boto3
import lambda_function
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

prompt="Give me 3 examples of Thersholds with License modality"

class MockContext:
    """Mock AWS Lambda context object"""
    def __init__(self):
        self.function_name = "test-function"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        self.memory_limit_in_mb = 128
        self.aws_request_id = "00000000-0000-0000-0000-000000000000"
        self.log_group_name = "/aws/lambda/test-function"
        self.log_stream_name = "2023/01/01/[$LATEST]00000000000000000000000000000000"
        self.remaining_time_in_millis = 3000

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

def create_test_event():
    """Create a test event similar to what API Gateway would send"""
    return {
        "requestContext": {
            "connectionId": "test-connection-id",
            "domainName": "test-domain.execute-api.us-east-1.amazonaws.com",
            "stage": "test"
        },
        "body": json.dumps({"prompt": prompt})
    }

@patch('boto3.client')
def test_lambda_handler(mock_boto3_client):
    """Test the lambda_handler function with a mock API Gateway client"""
    # Create mock API Gateway client
    mock_apigateway = MockApiGatewayClient()
    mock_boto3_client.return_value = mock_apigateway
    
    # Create test event and context
    test_event = create_test_event()
    test_context = MockContext()
    
    # Call the lambda handler
    print("\n=== Testing Lambda Handler ===")
    print(f"Input prompt: {json.loads(test_event['body'])['prompt']}")
    print("Invoking lambda_handler...")
    
    try:
        response = lambda_function.lambda_handler(test_event, test_context)
        print(f"Lambda response: {response}")
        
        # Print summary of messages sent
        print("\n=== Messages Sent to WebSocket ===")
        text_chunks = [msg['text'] for msg in mock_apigateway.messages if 'text' in msg]
        complete_response = ''.join(text_chunks)
        
        print(f"Number of messages: {len(mock_apigateway.messages)}")
        print(f"Complete response: {complete_response}")
        
        # Check if the stream completed successfully
        done_messages = [msg for msg in mock_apigateway.messages if msg.get('done') is True]
        if done_messages:
            print("Stream completed successfully")
        else:
            print("Stream did not complete")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    # Run the test
    test_lambda_handler()
    print("\nTest completed.")
