import json

def lambda_handler(event, context):
    # Get the API Key from headers
    headers = event.get('headers', {})
    api_key = headers.get('ps-key', 'Not Provided')

    # Log the API key (for debugging)
    print(f"Received API Key: {api_key}")

    # Check if the API key matches the expected value
    if api_key != "0a762ff1-5a66-4de4-9140-01039b14b50a":
        return {
            'statusCode': 403,  # Forbidden
            'body': json.dumps({'error': 'Invalid API Key'})
        }

    # Parse the body of the request
    body = event.get('body', '{}')  # Default to '{}' if body is not provided
    body_params = json.loads(body)  # Parse the JSON body

    # Log the body parameters for debugging
    print(f"Received body parameters: {body_params}")

    # Return the body parameters as the response
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'API Key is valid', 'body_params': body_params})
    }
