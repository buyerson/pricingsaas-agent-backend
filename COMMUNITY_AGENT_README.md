# Community Pricing Agent

This agent provides answers to pricing questions by querying community knowledge stored in Pinecone.

## Setup

1. Set the required environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_INDEX_NAME="discourse-topics"  # or your custom index name
export PINECONE_NAMESPACE="community"  # or your custom namespace
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Agent Locally

You can run the community agent locally using the provided test script:

```bash
python test_community_agent.py
```

Or use the shell script that sets the environment variables:

```bash
# First, edit run_community_agent.sh to add your API keys
chmod +x run_community_agent.sh
./run_community_agent.sh
```

## Using the Agent in Lambda

The agent is integrated with the Lambda function. To use it, send a request with the `agent_type` parameter set to `community`:

```json
{
  "prompt": "What are the benefits of outcome-based pricing?",
  "agent_type": "community"
}
```

If the `agent_type` is not specified or set to anything other than `community`, the default agent will be used.

## How It Works

1. The agent takes a user query about pricing.
2. It generates an embedding for the query using OpenAI's embedding model.
3. It searches the Pinecone vector database for relevant community content.
4. It formats the search results and provides them to the LLM.
5. The LLM generates a comprehensive answer based on the community knowledge.

## Troubleshooting

If you encounter issues with the agent, check the following:

1. Make sure your API keys are set correctly.
2. Verify that the Pinecone index and namespace exist.
3. Check the logs for any error messages.

## Extending the Agent

You can extend the agent by:

1. Adding more tools to the agent definition.
2. Modifying the search logic to include different types of content.
3. Adjusting the agent's instructions to focus on specific aspects of pricing.
