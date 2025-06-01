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
├─────────────────┴─────────────────────────┴─────────────────────┤
│                        Agent Runner                             │
├─────────────────────────────────────────────────────────────────┤
│                     Knowledge Sources                           │
│                                                                 │
│  ┌───────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Expert Reports│    │ Community    │    │ Other Knowledge  │  │
│  │ (Vector Store)│    │ (Pinecone)   │    │ Sources          │  │
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
   - Community forum posts and topics
   - Stored in Pinecone with vector embeddings
   - Optimized query processing for relevant matches

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
- **lambda_function.py**: AWS Lambda entry point
- **helpers/auth_helper.py**: Authentication system implementation
- **helpers/**: Utility functions and shared code
- **local_config.py**: Configuration for local development environment
- **run_local_server.py**: Local WebSocket server for development
- **test/**: Test cases for various components

## Integration Points

- **OpenAI API**: Used by agents for text processing and embedding generation
- **Pinecone**: Vector database for community knowledge
- **Vector Store**: Storage for expert reports
- **WebSockets**: Real-time streaming of agent responses
- **Supabase Auth**: Authentication and user management
  - Google OAuth integration
  - JWT token validation
  - User profile storage

## Future Extensions

The modular architecture allows for easy extension with:
- Additional specialized agents for different knowledge domains
- Integration with more knowledge sources
- Enhanced personalization capabilities
- Support for more complex multi-turn conversations
