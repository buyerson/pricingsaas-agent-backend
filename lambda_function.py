import json
import asyncio
from agents import Agent, Runner

# This is the asynchronous function to process the agent's response
async def get_agent_response(prompt: str):
    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
    )

    # Run the agent and get the final output based on the prompt
    result = await Runner.run(agent, prompt)
    return result.final_output

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

    # Extract the prompt from the body parameters
    prompt = body_params.get('prompt', 'Tell me something.')

    # Run the asynchronous function and get the response
    loop = asyncio.get_event_loop()
    agent_response = loop.run_until_complete(get_agent_response(prompt))

    # Return the agent's response as the result
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'API Key is valid', 'response': agent_response})
    }
