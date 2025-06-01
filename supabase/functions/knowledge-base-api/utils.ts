// Utility functions for Knowledge Base Edge Function
import { 
  Index, 
  Pinecone, 
  RecordMetadata 
} from 'https://esm.sh/@pinecone-database/pinecone@0.1.6'

// Pinecone index name
const PINECONE_INDEX_NAME = 'knowledge-base'

// OpenAI embedding model
const EMBEDDING_MODEL = 'text-embedding-3-small'

// Schema version
const CURRENT_SCHEMA_VERSION = '1.0.0'

// Knowledge base entry interface
export interface KnowledgeBaseEntry {
  id?: string;
  title: string;
  content: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  tags?: string[];
  visibility?: 'public' | 'team' | 'private';
  source?: string;
  confidence?: number;
  expires_at?: string;
  schema_version?: string;
  custom_fields?: Record<string, any>;
}

// Namespace mapping
export function getNamespaceForVisibility(
  visibility: string,
  userId: string
): string {
  switch (visibility) {
    case 'public':
      return 'public-kb'
    case 'team':
      return 'team-kb'
    case 'private':
    default:
      return `user-${userId}`
  }
}

// Initialize Pinecone client
export function initPinecone(
  apiKey: string,
  environment: string
): Pinecone {
  return new Pinecone({
    apiKey,
    environment
  })
}

// Generate embedding using OpenAI API
export async function generateEmbedding(
  text: string,
  openaiApiKey: string
): Promise<number[]> {
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${openaiApiKey}`
    },
    body: JSON.stringify({
      input: text,
      model: EMBEDDING_MODEL
    })
  })

  if (!response.ok) {
    const error = await response.json()
    console.error('OpenAI API error:', error)
    throw new Error(`OpenAI API error: ${error.error?.message || 'Unknown error'}`)
  }

  const result = await response.json()
  return result.data[0].embedding
}

// Convert entry to Pinecone metadata
export function entryToMetadata(entry: KnowledgeBaseEntry): RecordMetadata {
  // Create a copy without content (too large for metadata)
  const metadata: RecordMetadata = { ...entry } as unknown as RecordMetadata
  
  // Store a preview of content instead of full content
  const contentPreview = entry.content.substring(0, 100) + (entry.content.length > 100 ? '...' : '')
  metadata.content_preview = contentPreview
  
  // Delete content from metadata
  delete metadata.content
  
  // Convert tags array to comma-separated string
  if (entry.tags && Array.isArray(entry.tags)) {
    metadata.tags_csv = entry.tags.join(',')
    delete metadata.tags
  }
  
  // Convert custom fields to JSON string if present
  if (entry.custom_fields) {
    metadata.custom_fields_json = JSON.stringify(entry.custom_fields)
    delete metadata.custom_fields
  }
  
  return metadata
}

// Convert Pinecone metadata back to entry
export function metadataToEntry(metadata: RecordMetadata, content: string): KnowledgeBaseEntry {
  const entry: KnowledgeBaseEntry = { ...metadata as unknown as KnowledgeBaseEntry }
  
  // Restore content
  entry.content = content
  
  // Convert tags_csv back to tags array
  if (metadata.tags_csv) {
    entry.tags = metadata.tags_csv.split(',')
    delete (entry as any).tags_csv
  }
  
  // Convert custom_fields_json back to object
  if (metadata.custom_fields_json) {
    try {
      entry.custom_fields = JSON.parse(metadata.custom_fields_json)
    } catch (error) {
      console.error('Error parsing custom_fields_json:', error)
      entry.custom_fields = {}
    }
    delete (entry as any).custom_fields_json
  }
  
  // Remove content_preview
  delete (entry as any).content_preview
  
  return entry
}

// Validate knowledge base entry
export function validateEntry(entry: KnowledgeBaseEntry): boolean {
  // Required fields
  if (!entry.title || !entry.content) {
    return false
  }
  
  // Title length validation
  if (entry.title.length < 3 || entry.title.length > 200) {
    return false
  }
  
  // Content length validation
  if (entry.content.length < 10) {
    return false
  }
  
  // Visibility validation
  if (entry.visibility && !['public', 'team', 'private'].includes(entry.visibility)) {
    return false
  }
  
  // Confidence validation (1-5 if present)
  if (entry.confidence !== undefined && (entry.confidence < 1 || entry.confidence > 5)) {
    return false
  }
  
  // Tags validation
  if (entry.tags && (!Array.isArray(entry.tags) || entry.tags.some(tag => typeof tag !== 'string'))) {
    return false
  }
  
  return true
}

// Get schema definition for client
export function getSchemaDefinition() {
  return {
    version: CURRENT_SCHEMA_VERSION,
    schema: {
      type: 'object',
      required: ['title', 'content'],
      properties: {
        id: { type: 'string', description: 'Unique identifier of the entry' },
        title: { 
          type: 'string', 
          description: 'Title of the knowledge entry',
          minLength: 3,
          maxLength: 200
        },
        content: { 
          type: 'string', 
          description: 'Main content of the knowledge entry',
          minLength: 10
        },
        created_by: { 
          type: 'string', 
          description: 'User ID of the creator' 
        },
        created_at: { 
          type: 'string', 
          format: 'date-time',
          description: 'Creation timestamp' 
        },
        updated_at: { 
          type: 'string', 
          format: 'date-time',
          description: 'Last update timestamp' 
        },
        tags: { 
          type: 'array',
          items: { type: 'string' },
          description: 'Tags for categorization' 
        },
        visibility: { 
          type: 'string',
          enum: ['public', 'team', 'private'],
          default: 'private',
          description: 'Visibility level of the entry' 
        },
        source: { 
          type: 'string',
          description: 'Source of the information' 
        },
        confidence: { 
          type: 'number',
          minimum: 1,
          maximum: 5,
          description: 'Confidence level (1-5)' 
        },
        expires_at: { 
          type: 'string',
          format: 'date-time',
          description: 'Expiration timestamp' 
        },
        schema_version: { 
          type: 'string',
          default: CURRENT_SCHEMA_VERSION,
          description: 'Schema version' 
        },
        custom_fields: { 
          type: 'object',
          description: 'Custom fields for extensibility' 
        }
      }
    }
  }
}
