# Knowledge Base Technical Implementation Scope

This document outlines the technical implementation details for adding a user-editable knowledge base to the PricingSaaS Agent Backend.

## 1. Files to Be Added/Modified

### New Files

1. **`agent_modules/knowledgeBaseAgent.py`**
   - Implements the Knowledge Base Agent
   - Defines tools for knowledge base operations
   - Manages schema validation and embeddings generation

2. **`helpers/knowledge_base_helper.py`**
   - Utilities for knowledge base operations
   - Schema validation functions
   - Embedding generation wrapper
   - Pinecone interaction helpers

3. **`helpers/schema_definitions.py`**
   - JSON schema definitions for knowledge base entries
   - Schema versioning and migration utilities
   - Validation functions

4. **`test/test_knowledge_base.py`**
   - Unit tests for knowledge base functionality
   - Mock data for testing
   - Test cases for all CRUD operations

5. **`supabase/edge-functions/knowledge-base-api/`**
   - Edge function implementation for client-side API
   - Endpoint handlers for CRUD operations
   - Authentication and permission verification

### Files to Modify

1. **`agentMain.py`**
   - Add Knowledge Base Agent initialization
   - Update agent orchestration to include Knowledge Base Agent
   - Add knowledge base results to response formatting

2. **`requirements.txt`**
   - Add new dependencies for schema validation and vector operations

3. **`lambda_function.py`**
   - Update Lambda handler to support knowledge base operations
   - Add authentication checks for knowledge base access

4. **`helpers/auth_helper.py`**
   - Add permission controls for knowledge base operations
   - Extend user profiles with knowledge base access rights

5. **`run_local_server.py`**
   - Add WebSocket routes for knowledge base operations
   - Add local development endpoints for testing

## 2. Pinecone Configuration

### New Index Creation

1. **Knowledge Base Index**
   - Name: `pricingsaas-kb`
   - Dimensions: 1536 (OpenAI embedding size)
   - Metric: cosine
   - Pod type: p1.x1 (production) or s1 (development)

### Namespaces

1. **`user-kb`**: For user-created knowledge entries
2. **`system-kb`**: For system-provided knowledge entries
3. **`team-kb`**: For team-shared knowledge entries

### Metadata Schema

Configure Pinecone index to support the following metadata fields:

```json
{
  "id": "string",
  "title": "string",
  "createdAt": "number",
  "updatedAt": "number",
  "createdBy": "string",
  "tags": "string[]",
  "source": "string",
  "confidence": "number",
  "expiration": "number",
  "visibility": "string",
  "schema_version": "string"
}
```

## 3. Supabase Edge Functions

### Function 1: Knowledge Base CRUD API

**Path**: `/knowledge-base/entries`

**Endpoints**:
- `GET /knowledge-base/entries` - List entries with pagination and filtering
- `GET /knowledge-base/entries/:id` - Get specific entry
- `POST /knowledge-base/entries` - Create new entry
- `PUT /knowledge-base/entries/:id` - Update entry
- `DELETE /knowledge-base/entries/:id` - Delete entry

**Authentication**: JWT token validation with Supabase Auth

**Function Code Structure**:
- Request validation
- Authentication and permission checks
- Operation execution (via Pinecone API)
- Response formatting

### Function 2: Knowledge Base Search API

**Path**: `/knowledge-base/search`

**Endpoints**:
- `POST /knowledge-base/search/semantic` - Semantic search
- `POST /knowledge-base/search/metadata` - Metadata-based search
- `POST /knowledge-base/search/hybrid` - Combined search

**Parameters**:
- Query text or vector
- Metadata filters
- Pagination and sorting options

### Function 3: Schema Management API

**Path**: `/knowledge-base/schema`

**Endpoints**:
- `GET /knowledge-base/schema` - Get current schema
- `PUT /knowledge-base/schema` - Update schema (admin only)
- `GET /knowledge-base/schema/versions` - List schema versions

## 4. Required Libraries

### Python Dependencies

Add to `requirements.txt`:

```
jsonschema>=4.17.3         # JSON schema validation
openai>=1.0.0              # For embedding generation
pinecone-client>=2.2.1     # Pinecone vector DB client
pydantic>=2.0.0            # Data validation
tenacity>=8.2.2            # Retry mechanisms for API calls
```

### Agent Tools Implementation

The Knowledge Base Agent will implement the following tool classes:

1. **`KBSearchTool`**: 
   - Semantic search in knowledge base
   - Parameters: query, limit, filters
   - Returns: matching entries with relevance scores

2. **`KBMetadataSearchTool`**:
   - Search by metadata fields
   - Parameters: metadata filters, limit, sort
   - Returns: matching entries

3. **`KBCreateTool`**:
   - Create new knowledge base entry
   - Parameters: title, content, tags, metadata
   - Returns: created entry ID

4. **`KBUpdateTool`**:
   - Update existing entry
   - Parameters: id, fields to update
   - Returns: success status

5. **`KBDeleteTool`**:
   - Delete knowledge base entry
   - Parameters: id
   - Returns: success status

6. **`KBGetTool`**:
   - Retrieve specific entry
   - Parameters: id
   - Returns: full entry with metadata

## 5. Embedding Generation

### Implementation Details

1. **Embedding Model**: OpenAI text-embedding-3-small
   - Dimensions: 1536
   - Consistent with existing vector storage

2. **Chunking Strategy**:
   - Single embedding per knowledge base entry
   - Max token size: 8,000 tokens
   - Truncation for longer entries with warning

3. **Embedding Storage**:
   - Primary storage in Pinecone
   - Caching mechanism for frequent lookups
   - Background refresh for updated entries

## 6. Client Integration Points

While the client application is a separate project, the backend will provide these integration points:

1. **API Gateway Routes**:
   - Map Supabase edge functions to API Gateway
   - Set up CORS for client access
   - Configure rate limiting and caching

2. **WebSocket Notifications**:
   - Real-time updates when knowledge base changes
   - Subscription mechanism for client applications

3. **Client-Side SDK**:
   - Helper functions for client integration
   - TypeScript definitions for knowledge base operations
   - Example usage documentation

## 7. Implementation Phases

### Phase 1: Core Infrastructure

1. Set up Pinecone index and schema
2. Implement knowledge_base_helper.py and schema_definitions.py
3. Create basic Knowledge Base Agent with search capabilities
4. Add unit tests for core functionality

### Phase 2: Agent Integration

1. Integrate Knowledge Base Agent with Agent Runner
2. Update agentMain.py to include knowledge base in query processing
3. Add citation handling for knowledge base entries
4. Implement knowledge base tools for other agents

### Phase 3: API and Client Integration

1. Develop Supabase edge functions
2. Set up API Gateway routes
3. Create WebSocket notification system
4. Build client-side SDK and example usage

### Phase 4: Advanced Features

1. Implement schema versioning and migration
2. Add advanced search capabilities (hybrid search)
3. Develop permission models and access controls
4. Create admin tools for knowledge base management

## 8. Security Considerations

1. **Access Control**:
   - Row-level security based on user ID and visibility setting
   - Audit logging for sensitive operations
   - Validation to prevent injection attacks

2. **Data Protection**:
   - Encryption for sensitive knowledge base entries
   - Regular backup procedures
   - Data retention and purging policies

3. **Authentication**:
   - JWT validation for all operations
   - Scope-based permissions for different operations
   - API key rotation for automated access

## 9. Testing Strategy

1. **Unit Tests**:
   - Test each knowledge base operation in isolation
   - Mock Pinecone responses for predictable testing
   - Schema validation tests with various inputs

2. **Integration Tests**:
   - Test knowledge base integration with agent system
   - Verify proper citation and attribution
   - Test search relevance and accuracy

3. **Load Testing**:
   - Benchmark performance with large knowledge bases
   - Test concurrent operations
   - Identify and address bottlenecks

## 10. Monitoring and Maintenance

1. **Metrics Collection**:
   - Usage statistics for knowledge base operations
   - Query performance monitoring
   - Error rates and types

2. **Alerting**:
   - Notifications for high error rates
   - Warnings for large knowledge base growth
   - API usage limits approaching

3. **Maintenance Procedures**:
   - Index optimization schedule
   - Schema migration procedures
   - Backup and restore documentation
