// Handler for knowledge base search operations
import { corsHeaders } from '../_shared/cors.ts'
import { Permission, checkPermissions, logAccessAttempt } from '../_shared/auth.ts'
import {
  initPinecone,
  generateEmbedding,
  metadataToEntry,
  getNamespaceForVisibility
} from './utils.ts'

const PINECONE_INDEX_NAME = 'knowledge-base'
const DEFAULT_TOP_K = 5

// Types for handler context
export type HandlerContext = {
  req: Request,
  supabaseClient: any,
  user: any,
  userId: string,
  pineconeApiKey: string,
  pineconeEnv: string,
  openaiApiKey: string
}

/**
 * Handle semantic search and metadata search for knowledge base
 */
export async function searchHandler(context: HandlerContext): Promise<Response> {
  const { req, supabaseClient, userId, pineconeApiKey, pineconeEnv, openaiApiKey } = context
  
  // Only allow POST method for search (to handle search query in body)
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Parse request body
  const requestData = await req.json()
  const searchType = requestData.searchType || 'semantic'
  
  // Initialize Pinecone client
  const pinecone = initPinecone(pineconeApiKey, pineconeEnv)
  const index = pinecone.Index(PINECONE_INDEX_NAME)
  
  try {
    // Define namespaces to search based on requested visibility levels
    const visibilityLevels = requestData.visibility || ['public', 'team', 'private']
    const namespaces = []
    
    if (visibilityLevels.includes('public')) {
      namespaces.push('public-kb')
    }
    if (visibilityLevels.includes('team')) {
      namespaces.push('team-kb')
    }
    if (visibilityLevels.includes('private')) {
      namespaces.push(`user-${userId}`)
    }
    
    // If no namespaces, return empty results
    if (namespaces.length === 0) {
      return new Response(
        JSON.stringify({ results: [] }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }
    
    // Handle different search types
    switch (searchType) {
      // Semantic search based on vector similarity
      case 'semantic': {
        const query = requestData.query
        const topK = requestData.topK || DEFAULT_TOP_K
        
        if (!query) {
          return new Response(
            JSON.stringify({ error: 'Query is required for semantic search' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Generate embedding for query
        const embedding = await generateEmbedding(query, openaiApiKey)
        
        // Collect results from all namespaces
        const allResults = []
        
        for (const namespace of namespaces) {
          try {
            // Query Pinecone
            const response = await index.query({
              vector: embedding,
              topK,
              namespace,
              includeMetadata: true
            })
            
            // Process matches
            const matches = response.matches || []
            
            for (const match of matches) {
              const metadata = match.metadata!
              
              // Get content from Supabase Storage if possible
              let content = ''
              try {
                const { data, error } = await supabaseClient
                  .storage
                  .from('kb-content')
                  .download(`${match.id}.txt`)
                
                if (data && !error) {
                  content = await data.text()
                } else {
                  // Fall back to content preview in metadata
                  content = metadata.content_preview || ''
                }
              } catch (error) {
                console.error('Error getting content:', error)
                content = metadata.content_preview || ''
              }
              
              // Convert metadata to entry
              const entry = metadataToEntry(metadata, content)
              
              allResults.push({
                entry,
                score: match.score
              })
            }
          } catch (error) {
            console.error(`Error searching in namespace ${namespace}:`, error)
          }
        }
        
        // Sort by score (descending) and limit to topK results
        allResults.sort((a, b) => b.score - a.score)
        const results = allResults.slice(0, topK)
        
        return new Response(
          JSON.stringify({ results }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Metadata search based on filters
      case 'metadata': {
        const filters = requestData.filters || {}
        const topK = requestData.topK || DEFAULT_TOP_K
        
        // Convert filters to Pinecone filter format
        const pineconeFilter = convertToPineconeFilter(filters)
        
        // Collect results from all namespaces
        const allResults = []
        
        for (const namespace of namespaces) {
          try {
            // List entries using Pinecone query with zero vector and filters
            const zeroVector = new Array(1536).fill(0)
            
            const response = await index.query({
              vector: zeroVector,
              topK,
              namespace,
              filter: pineconeFilter,
              includeMetadata: true
            })
            
            // Process matches
            const matches = response.matches || []
            
            for (const match of matches) {
              const metadata = match.metadata!
              
              // Get content from Supabase Storage if possible
              let content = ''
              try {
                const { data, error } = await supabaseClient
                  .storage
                  .from('kb-content')
                  .download(`${match.id}.txt`)
                
                if (data && !error) {
                  content = await data.text()
                } else {
                  // Fall back to content preview in metadata
                  content = metadata.content_preview || ''
                }
              } catch (error) {
                console.error('Error getting content:', error)
                content = metadata.content_preview || ''
              }
              
              // Convert metadata to entry
              const entry = metadataToEntry(metadata, content)
              
              allResults.push({
                entry,
                score: 1.0  // No actual score for metadata search
              })
            }
          } catch (error) {
            console.error(`Error searching in namespace ${namespace}:`, error)
          }
        }
        
        // Limit to topK results
        const results = allResults.slice(0, topK)
        
        return new Response(
          JSON.stringify({ results }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Hybrid search (semantic + metadata)
      case 'hybrid': {
        const query = requestData.query
        const filters = requestData.filters || {}
        const topK = requestData.topK || DEFAULT_TOP_K
        
        if (!query) {
          return new Response(
            JSON.stringify({ error: 'Query is required for hybrid search' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Convert filters to Pinecone filter format
        const pineconeFilter = convertToPineconeFilter(filters)
        
        // Generate embedding for query
        const embedding = await generateEmbedding(query, openaiApiKey)
        
        // Collect results from all namespaces
        const allResults = []
        
        for (const namespace of namespaces) {
          try {
            // Query Pinecone with both embedding and filters
            const response = await index.query({
              vector: embedding,
              topK,
              namespace,
              filter: pineconeFilter,
              includeMetadata: true
            })
            
            // Process matches
            const matches = response.matches || []
            
            for (const match of matches) {
              const metadata = match.metadata!
              
              // Get content from Supabase Storage if possible
              let content = ''
              try {
                const { data, error } = await supabaseClient
                  .storage
                  .from('kb-content')
                  .download(`${match.id}.txt`)
                
                if (data && !error) {
                  content = await data.text()
                } else {
                  // Fall back to content preview in metadata
                  content = metadata.content_preview || ''
                }
              } catch (error) {
                console.error('Error getting content:', error)
                content = metadata.content_preview || ''
              }
              
              // Convert metadata to entry
              const entry = metadataToEntry(metadata, content)
              
              allResults.push({
                entry,
                score: match.score
              })
            }
          } catch (error) {
            console.error(`Error searching in namespace ${namespace}:`, error)
          }
        }
        
        // Sort by score (descending) and limit to topK results
        allResults.sort((a, b) => b.score - a.score)
        const results = allResults.slice(0, topK)
        
        return new Response(
          JSON.stringify({ results }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid search type' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }
    
  } catch (error) {
    console.error('Error in search handler:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

/**
 * Convert client filter format to Pinecone filter format
 */
function convertToPineconeFilter(filters: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {}
  
  // Handle special case for tags (convert from array to tags_csv contains)
  if (filters.tags && Array.isArray(filters.tags)) {
    result.tags_csv = { $containsAny: filters.tags.map(tag => tag) }
    delete filters.tags
  }
  
  // Handle date ranges
  if (filters.created_at) {
    if (filters.created_at.$gte) {
      result.created_at = result.created_at || {}
      result.created_at.$gte = filters.created_at.$gte
    }
    if (filters.created_at.$lte) {
      result.created_at = result.created_at || {}
      result.created_at.$lte = filters.created_at.$lte
    }
    delete filters.created_at
  }
  
  if (filters.updated_at) {
    if (filters.updated_at.$gte) {
      result.updated_at = result.updated_at || {}
      result.updated_at.$gte = filters.updated_at.$gte
    }
    if (filters.updated_at.$lte) {
      result.updated_at = result.updated_at || {}
      result.updated_at.$lte = filters.updated_at.$lte
    }
    delete filters.updated_at
  }
  
  // Handle string equals
  if (filters.created_by) {
    result.created_by = filters.created_by
    delete filters.created_by
  }
  
  if (filters.title) {
    // If it looks like a regex or contains wildcard, treat as contains
    if (typeof filters.title === 'string' && 
        (filters.title.includes('*') || filters.title.startsWith('/') && filters.title.endsWith('/'))) {
      result.title = { $contains: filters.title.replace(/^\//,'').replace(/\/$/,'') }
    } else {
      result.title = filters.title
    }
    delete filters.title
  }
  
  // Handle any remaining filters directly
  Object.entries(filters).forEach(([key, value]) => {
    result[key] = value
  })
  
  return result
}
