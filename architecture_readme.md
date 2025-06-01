# PricingSaaS Agent Backend Architecture

## Overview

The PricingSaaS Agent Backend is a specialized system designed to answer pricing-related questions by leveraging AI agents that access different knowledge sources. The application is built using a modular, agent-based architecture where each agent specializes in retrieving and processing information from a specific knowledge source.

## System Architecture

The system follows a multi-agent architecture with the following core components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PricingSaaS Agent Backend                    │
├─────────────────┬─────────────────────────┬─────────────────────┤
│                 │                         │                     │
│  Reports Agent  │    Community Agent      │    Triage Agent     │
│                 │                         │                     │
├─────────────────┼─────────────────────────┼─────────────────────┤
│ Knowledge Base  │                         │                     │
│    Agent        │         Agent Runner    │                     │
├─────────────────┴─────────────────────────┴─────────────────────┤
│                     Knowledge Sources                           │
│                                                                 │
│  ┌───────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Expert Reports│    │ Community    │    │ User Knowledge   │  │
│  │ (Vector Store)│    │ (Pinecone)   │    │ Base (Pinecone)  │  │
│  └───────────────┘    └──────────────┘    └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Main Application (agentMain.py)

This is the primary entry point for the application. It:
- Orchestrates the execution of different agents
- Streams responses from the agents in sequence (Reports Agent first, then Community Agent)
- Handles formatting and aggregation of responses and citations
- Manages the response streaming protocol

### Agent Modules

#### Reports Agent (agent_modules/reportsAgent.py)

- Specializes in answering pricing questions using document knowledge
- Uses a FileSearchTool to access a vector store of expert reports
- Generates citations for referenced documents
- Provides comprehensive, actionable advice about SaaS pricing strategies

#### Community Agent (agent_modules/communityAgent.py)

- Specializes in retrieving pricing knowledge from community forums
- Uses Pinecone for vector search in community content
- Provides real-time citation of community posts and topics
- Synthesizes community expertise into coherent answers

#### Triage Agent (agent_modules/triageAgent.py)

- Performs initial analysis of user questions
- Routes questions to appropriate specialized agents
- May provide direct answers for simple queries

#### Profile Agent (agent_modules/profileAgent.py)

- Handles user profile and personalization aspects
- May adapt responses based on user preferences or history

#### Knowledge Base Agent (agent_modules/knowledgeBaseAgent.py)

- Manages user-defined knowledge base entries
- Provides tools for storing, retrieving, updating, and deleting knowledge items
- Maintains knowledge schema and validates entries
- Creates and manages embeddings for semantic search

### Authentication System (helpers/auth_helper.py)

- Integrates with Supabase for user authentication
- Supports Google OAuth for authentication
- Manages user sessions and tokens
- Provides authentication bypass for local development

### Key Infrastructure

#### Agent Runner

- Manages the execution of agents
- Provides streaming capabilities for real-time responses
- Handles tool execution and context management

#### Knowledge Sources

1. **Expert Reports**
   - Structured reports stored in a vector database
   - Accessed via vector search tools

2. **Community Knowledge**
   - User-generated content from community forums
   - Stored in Pinecone vector database
   - Accessed via Pinecone search API

3. **User Knowledge Base**
   - Client-editable structured knowledge entries
   - Stored in Pinecone vector database with metadata schema
   - Accessed via Knowledge Base Agent tools
   - Editable through client application interface

## Data Flow

1. User submits a pricing question
2. Main application receives the question and begins processing
3. Reports Agent executes first, searching expert reports for relevant information
4. Reports Agent streams its response with citations
5. Community Agent executes next, searching community knowledge
6. Community Agent streams its response with citations
7. Combined response with all citations is delivered to the user

## Deployment Model

The application is designed to be deployed as a backend service that can:
- Run as a Lambda function (via lambda_function.py)
- Support WebSocket connections for streaming responses
- Interact with various frontend interfaces
- Run in local development mode (via run_local_server.py)

### Authentication Flow

```
┌─────────────┐        ┌────────────────┐        ┌───────────────┐
│  Frontend   │        │ Backend Server │        │   Supabase    │
│  (Browser)  │        │  (Lambda/Local)│        │   Auth API    │
└──────┬──────┘        └────────┬───────┘        └───────┬───────┘
       │                        │                        │
       │ 1. Login Request      │                        │
       │───────────────────────►                        │
       │                        │  2. Redirect to       │
       │                        │  Supabase Auth        │
       │                        │───────────────────────►
       │                        │                        │
       │                        │                        │ 3. Google OAuth
       │                        │                        │    Flow
       │                        │                        │
       │                        │  4. Return JWT Token   │
       │                        │◄───────────────────────┤
       │  5. Return Token       │                        │
       │◄───────────────────────┤                        │
       │                        │                        │
       │ 6. API Request with    │                        │
       │    Bearer Token        │                        │
       │───────────────────────►│                        │
       │                        │ 7. Verify Token        │
       │                        │───────────────────────►│
       │                        │                        │
       │                        │ 8. Token Valid/Invalid │
       │                        │◄───────────────────────┤
       │                        │                        │
       │ 9. API Response        │                        │
       │◄───────────────────────┤                        │
       │                        │                        │
```

## Key Files

- **agentMain.py**: Main orchestration and streaming implementation
- **agent_modules/reportsAgent.py**: Reports Agent implementation
- **agent_modules/communityAgent.py**: Community Agent implementation
- **agent_modules/triageAgent.py**: Triage Agent implementation
- **agent_modules/knowledgeBaseAgent.py**: Knowledge Base Agent implementation
- **lambda_function.py**: AWS Lambda entry point
- **helpers/auth_helper.py**: Authentication system implementation
- **helpers/knowledge_base_helper.py**: Knowledge base utilities and schema management
- **helpers/**: Utility functions and shared code
- **local_config.py**: Configuration for local development environment
- **run_local_server.py**: Local WebSocket server for development
- **test/**: Test cases for various components

## Integration Points

- **OpenAI API**: Used by agents for text processing and embedding generation
- **Pinecone**: Vector database for community knowledge and user knowledge base
- **Vector Store**: Storage for expert reports
- **WebSockets**: Real-time streaming of agent responses
- **Supabase Auth**: Authentication and user management
  - Google OAuth integration
  - JWT token validation
  - User profile storage
- **Client Application**: User interface for knowledge base management
  - Knowledge entry creation/editing interface
  - Knowledge search and browsing
  - Schema configuration

## Future Extensions

The modular architecture allows for easy extension with:
- Additional specialized agents for different knowledge domains
- Integration with more knowledge sources
- Enhanced personalization capabilities
- Support for more complex multi-turn conversations

## Knowledge Base Architecture

### Overview

The Knowledge Base is a user-editable repository of structured information that agents can access to answer pricing questions. It's designed to be fully manageable from the client application while providing seamless integration with the agent system.

### Knowledge Base Schema

The knowledge base uses a flexible schema with the following key components:

1. **Core Schema**
   - `id`: Unique identifier for each knowledge item
   - `title`: Short descriptive title
   - `content`: Main text content of the knowledge item
   - `createdAt`: Timestamp of creation
   - `updatedAt`: Timestamp of last update
   - `createdBy`: User ID of creator
   - `tags`: Array of categorization tags
   - `embedding`: Vector embedding of content (generated automatically)

2. **Extended Metadata Schema**
   - `source`: Origin of the information (optional)
   - `confidence`: Reliability rating (1-5 scale, optional)
   - `expiration`: Expiration date for time-sensitive information (optional)
   - `visibility`: Public/private/team setting
   - `schema_version`: Version of the schema used
   - `custom_fields`: JSON object for domain-specific properties

### Storage Implementation

The knowledge base uses Pinecone as the primary storage solution:

1. **Vector Database**
   - Knowledge content is embedded using OpenAI's embedding models
   - Embeddings and metadata are stored in Pinecone
   - Supports semantic search and filtering by metadata fields

2. **Schema Validation**
   - JSON Schema validation ensures data integrity
   - Required fields are enforced before storage
   - Schema versioning allows for future evolution

### Knowledge Base Tools

The Knowledge Base Agent provides the following tools for other agents:

1. **Search Tools**
   - `kb_semantic_search`: Search knowledge base by semantic similarity
   - `kb_metadata_search`: Search knowledge base by metadata filters
   - `kb_hybrid_search`: Combined semantic and metadata search

2. **Management Tools**
   - `kb_create_entry`: Create a new knowledge base entry
   - `kb_update_entry`: Update an existing entry
   - `kb_delete_entry`: Remove an entry
   - `kb_get_entry`: Retrieve a specific entry by ID

### Client Integration

The client application interfaces with the knowledge base through a dedicated API:

1. **API Endpoints**
   - `/api/knowledge-base/entries`: CRUD operations for entries
   - `/api/knowledge-base/search`: Search interface
   - `/api/knowledge-base/schema`: Schema management

2. **User Interface Components**
   - Knowledge entry editor with validation
   - Search interface with filtering options
   - Schema management tools for administrators
   - Tagging and categorization system

3. **Access Control**
   - Permission-based access to knowledge entries
   - Ownership and sharing controls
   - Audit logging for sensitive operations

### Integration with Agent System

The Knowledge Base is fully integrated with the agent system:

1. **Agent Access Pattern**
   - Triage Agent determines when to consult Knowledge Base
   - Knowledge Base Agent mediates access to entries
   - Results from Knowledge Base are properly attributed

2. **Tool Registration**
   - Knowledge Base tools are registered with the Agent Runner
   - All agents can access knowledge through standard tool interfaces
   - Tool schema and documentation is available to agents

3. **Response Integration**
   - Knowledge Base citations are included in agent responses
   - Confidence ratings from the Knowledge Base are reflected in responses
   - Conflicts between knowledge sources are handled appropriately
