# Lambda Function Local Testing

This document explains how to use the provided scripts to test the AWS Lambda function locally.

## Test Scripts

Two test scripts are provided:

1. `test_lambda_locally.py` - Basic test script that mocks AWS services
2. `test_lambda_advanced.py` - Advanced test script with more comprehensive mocking and customizable prompts

## Prerequisites

Make sure you have all the required dependencies installed:

```bash
pip install -r requirements.txt
```

## Running the Basic Test

To run the basic test:

```bash
python test_lambda_locally.py
```

This will execute the lambda function with a default prompt "Tell me a joke" and display the results.

## Running the Advanced Test

The advanced test allows you to specify a custom prompt:

```bash
python test_lambda_advanced.py --prompt "What is the capital of France?"
```

If you don't specify a prompt, it will use the default "Tell me a joke".

## What the Tests Do

Both test scripts:

1. Create mock objects for AWS Lambda context and API Gateway
2. Generate a test event similar to what API Gateway would send
3. Call the lambda_handler function with these mocks
4. Display the messages that would be sent to the WebSocket client
5. Show a summary of the response

## Mocked Components

The tests mock the following components:

- AWS Lambda context
- API Gateway Management API client
- Agent and Runner classes (in the advanced test)
- OpenAI response events (in the advanced test)

## Troubleshooting

If you encounter import errors, make sure all dependencies are installed and that the project structure is correct.

If you see errors related to the Agent or Runner classes, you may need to adjust the mocks in the test scripts to match your actual implementation.
