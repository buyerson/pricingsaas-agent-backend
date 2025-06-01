# PricingSaaS Knowledge Base

## Overview

The Knowledge Base is a user-editable component of the PricingSaaS Agent Backend that allows storing, retrieving, updating, and deleting knowledge entries with semantic search capabilities. It's integrated into the multi-agent architecture and provides both direct API access for client applications and agent-based access for AI assistants.

## Architecture

The Knowledge Base implementation consists of:

1. **Backend Components**:
   - Knowledge Base Helper: Core functionality for CRUD operations and search
   - Schema Definitions: Validation and type support
   - Knowledge Base Agent: Integration with the agent system

2. **API Layer**:
   - Supabase Edge Functions: REST API for client access
   - Authentication & Authorization: Permission control

3. **Client SDK**:
   - TypeScript SDK: For frontend application integration

4. **Storage**:
   - Pinecone: Vector database for embeddings and metadata
   - Supabase Storage: Optional storage for large content

## Core Features

- **Flexible Schema**: Core fields (id, title, content) with extended metadata support
- **Vector Search**: Semantic search using OpenAI embeddings
- **Access Control**: Public, team, and private visibility levels
- **Custom Fields**: Extensible schema for domain-specific metadata
- **Integration**: Seamless integration with existing agent system

## Usage

### Using the Knowledge Base Agent

The Knowledge Base Agent is automatically integrated into the main agent flow in `agentMain.py`. It processes queries after the Reports Agent and Community Agent, providing relevant knowledge base entries as results.

```python
# Example agent integration (already implemented in agentMain.py)
kb_agent = KnowledgeBaseAgent()
kb_response = await kb_agent.process_query(query, context)
# Stream responses with citations
```

### Using the Knowledge Base Helper Directly

```python
from helpers.knowledge_base_helper import KnowledgeBaseManager

# Initialize
kb_manager = KnowledgeBaseManager()

# Create entry
entry_data = {
    "title": "Example Entry",
    "content": "This is a knowledge base entry.",
    "tags": ["example", "documentation"]
}
entry_id = kb_manager.create_entry(entry_data, user_id)

# Search
results = kb_manager.search("example query", user_id)
```

### Using the Client SDK

```typescript
import { createKnowledgeBaseClient } from './client/knowledge-base-sdk';

// Initialize with Supabase client
const kbClient = createKnowledgeBaseClient(supabaseClient, supabaseUrl);

// Create entry
const entryId = await kbClient.createEntry({
  title: "Example Entry",
  content: "This is a knowledge base entry.",
  tags: ["example", "documentation"]
});

// Search
const results = await kbClient.semanticSearch("example query");
```

## API Endpoints

The following REST API endpoints are available through Supabase Edge Functions:

- **GET /knowledge-base/entries**: List entries or get a specific entry
- **POST /knowledge-base/entries**: Create a new entry
- **PUT /knowledge-base/entries**: Update an existing entry
- **DELETE /knowledge-base/entries**: Delete an entry
- **POST /knowledge-base/search**: Search entries (semantic, metadata, or hybrid)
- **GET /knowledge-base/schema**: Get schema definition

## Examples

A demonstration script is available in `examples/knowledge_base_demo.py` that shows how to use the Knowledge Base features.

## File Structure

```
pricingsaas-agent-backend/
├── agent_modules/
│   └── knowledgeBaseAgent.py      # Agent implementation
├── helpers/
│   ├── knowledge_base_helper.py   # Core functionality
│   └── schema_definitions.py      # Data models
├── supabase/
│   └── edge-functions/
│       └── knowledge-base-api/    # API implementation
│           ├── index.ts
│           ├── handlers.ts
│           ├── entries-handler.ts
│           ├── search-handler.ts
│           └── schema-handler.ts
├── client/
│   └── knowledge-base-sdk.ts      # TypeScript client SDK
├── examples/
│   └── knowledge_base_demo.py     # Usage examples
└── test/
    └── test_knowledge_base.py     # Unit tests
```

## Configuration

The Knowledge Base requires the following environment variables:

- `OPENAI_API_KEY`: For generating embeddings
- `PINECONE_API_KEY`: For accessing the vector database
- `PINECONE_ENVIRONMENT`: Pinecone environment

## Testing

Run the Knowledge Base tests:

```bash
python -m unittest test/test_knowledge_base.py
```

## Dependencies

- `pydantic>=2.0.0`: Data validation
- `pinecone-client>=2.2.1`: Vector database interaction
- `openai>=1.0.0`: Embedding generation
- `jsonschema>=4.17.3`: Schema validation
- `tenacity>=8.2.2`: Retry logic for API calls
