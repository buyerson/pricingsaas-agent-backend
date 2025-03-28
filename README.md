# PricingSaaS Agent Backend

This repository contains the backend code for the PricingSaaS agent system, which provides AI-powered assistance for pricing-related questions.

## Project Structure

```
pricingsaas-agent-backend/
├── agent_modules/           # Agent implementations
│   ├── __init__.py          # Package initialization
│   ├── agent.py             # Base agent implementation
│   └── communityAgent.py    # Community knowledge agent
├── helpers/                 # Helper modules and utilities
│   ├── __init__.py          # Package initialization
│   └── community_helpers.py # Helpers for community agent
├── requirements.txt         # Project dependencies
├── test_community_agent.py  # Test script for community agent
└── README.md                # This file
```

## Setup

1. Create and activate a virtual environment (recommended):

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

If you encounter any import errors, make sure all dependencies are installed correctly:

```bash
pip install pydantic openai-agents pinecone-client aiohttp
```

2. Set up the required environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_INDEX_NAME="discourse-topics"  # or your custom index name
export PINECONE_NAMESPACE="community"  # or your custom namespace
export DISCOURSE_URL="https://community.pricingsaas.com"  # or your Discourse URL
```

## Running the Community Agent

You can run the community agent using the provided test script:

```bash
python test_community_agent.py
```

## Features

- **AI-Optimized Query Processing**: Uses OpenAI to optimize queries for better embedding-based search results
- **Community Knowledge Search**: Search through community knowledge to find answers to pricing questions
- **High-Confidence Matching**: Only returns results with 80% or higher confidence score
- **Top 5 Relevant Results**: Limits results to the top 5 most relevant matches for higher quality
- **Full Topic Retrieval**: Fetches complete conversations from Discourse for comprehensive answers
- **Annotated Responses**: Provides references to the source topics in the responses
