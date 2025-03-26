import json
import asyncio
import boto3
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from agent import send_streamed_response

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
