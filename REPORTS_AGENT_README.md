# Reports Agent

The Reports Agent is a specialized agent for answering pricing questions using document search with FileSearchTool.

## Features

- Uses FileSearchTool to search through document knowledge
- Provides comprehensive answers based on document knowledge
- Includes annotations for referenced documents
- Streams responses with annotations to clients via WebSocket

## Usage

### Running Locally

You can run the Reports Agent locally using the provided script:

```bash
./run_reports_agent.sh
```

This will start an interactive session where you can ask pricing-related questions.

### Using in Lambda Function

The Reports Agent is integrated into the Lambda function. To use it, send a WebSocket message with the following format:

```json
{
  "prompt": "Your pricing question here",
  "agent_type": "reports"
}
```

The `agent_type` parameter should be set to `"reports"` to use the Reports Agent. If not specified or set to any other value, the default agent will be used.

## Implementation Details

The Reports Agent uses the FileSearchTool from the openai-agents package to search through document knowledge. It is configured to return the top 3 most relevant results and includes annotations for referenced documents.

The agent streams responses with annotations to clients via WebSocket, providing a seamless user experience.
