// Handler for knowledge base entries CRUD operations
import { corsHeaders } from '../_shared/cors.ts'
import { Permission, checkPermissions, logAccessAttempt } from '../_shared/auth.ts'
import {
  KnowledgeBaseEntry,
  initPinecone,
  generateEmbedding,
  entryToMetadata,
  metadataToEntry,
  validateEntry,
  getNamespaceForVisibility
} from './utils.ts'

const PINECONE_INDEX_NAME = 'knowledge-base'

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
 * Handle CRUD operations for knowledge base entries
 */
export async function entriesHandler(context: HandlerContext): Promise<Response> {
  const { req, supabaseClient, userId, pineconeApiKey, pineconeEnv, openaiApiKey } = context
  
  // Parse URL to get entry ID if present
  const url = new URL(req.url)
  const entryId = url.searchParams.get('id')
  
  // Initialize Pinecone client
  const pinecone = initPinecone(pineconeApiKey, pineconeEnv)
  const index = pinecone.Index(PINECONE_INDEX_NAME)
  
  try {
    switch (req.method) {
      // Get a specific entry or list entries
      case 'GET': {
        // Check if getting a specific entry or listing entries
        if (entryId) {
          // Check permission
          const hasPermission = await checkPermissions(
            supabaseClient,
            userId,
            'kb-entry',
            entryId,
            Permission.READ
          )
          
          await logAccessAttempt(
            supabaseClient,
            userId,
            'kb-entry',
            entryId,
            Permission.READ,
            hasPermission
          )
          
          if (!hasPermission) {
            return new Response(
              JSON.stringify({ error: 'Permission denied' }),
              { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
          }
          
          // Get entry from Pinecone
          // We need to check all possible namespaces
          const namespaces = [
            'public-kb',
            'team-kb',
            `user-${userId}`
          ]
          
          let entry = null
          
          for (const namespace of namespaces) {
            try {
              const response = await index.fetch({
                ids: [entryId],
                namespace
              })
              
              if (response.vectors && response.vectors[entryId]) {
                const vector = response.vectors[entryId]
                const metadata = vector.metadata
                
                // Get content from separate storage if not in metadata
                let content = ''
                
                // Try to get content from Supabase storage first
                const { data, error } = await supabaseClient
                  .storage
                  .from('kb-content')
                  .download(`${entryId}.txt`)
                
                if (data && !error) {
                  content = await data.text()
                } else {
                  // Fall back to content preview in metadata
                  content = metadata.content_preview || ''
                }
                
                entry = metadataToEntry(metadata, content)
                break
              }
            } catch (error) {
              console.error(`Error fetching from namespace ${namespace}:`, error)
            }
          }
          
          if (!entry) {
            return new Response(
              JSON.stringify({ error: 'Entry not found' }),
              { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
          }
          
          return new Response(
            JSON.stringify({ entry }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
          
        } else {
          // List entries based on filters
          const visibility = url.searchParams.get('visibility') || 'all'
          const tag = url.searchParams.get('tag')
          const limit = parseInt(url.searchParams.get('limit') || '50')
          
          // Define namespaces to search in based on visibility
          let namespaces = []
          
          if (visibility === 'all' || visibility === 'public') {
            namespaces.push('public-kb')
          }
          if (visibility === 'all' || visibility === 'team') {
            namespaces.push('team-kb')
          }
          if (visibility === 'all' || visibility === 'private') {
            namespaces.push(`user-${userId}`)
          }
          
          // Build filter based on tags if specified
          let filter = {}
          if (tag) {
            filter = {
              tags_csv: { $contains: tag }
            }
          }
          
          // Get entries from each namespace
          const entries: KnowledgeBaseEntry[] = []
          
          for (const namespace of namespaces) {
            try {
              // List entries using Pinecone query with zero vector (returns all entries)
              const zeroVector = new Array(1536).fill(0)
              
              const response = await index.query({
                vector: zeroVector,
                topK: limit,
                namespace,
                filter,
                includeMetadata: true
              })
              
              for (const match of response.matches || []) {
                const metadata = match.metadata!
                
                // Convert metadata to entry
                const entry = metadataToEntry(metadata, metadata.content_preview || '')
                entries.push(entry)
                
                // Only collect up to limit entries
                if (entries.length >= limit) {
                  break
                }
              }
              
              if (entries.length >= limit) {
                break
              }
              
            } catch (error) {
              console.error(`Error listing from namespace ${namespace}:`, error)
            }
          }
          
          return new Response(
            JSON.stringify({ entries }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
      }
      
      // Create a new entry
      case 'POST': {
        // Check permission
        const hasPermission = await checkPermissions(
          supabaseClient,
          userId,
          'kb-entry',
          null,
          Permission.WRITE
        )
        
        await logAccessAttempt(
          supabaseClient,
          userId,
          'kb-entry',
          null,
          Permission.WRITE,
          hasPermission
        )
        
        if (!hasPermission) {
          return new Response(
            JSON.stringify({ error: 'Permission denied' }),
            { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Parse request body
        const requestData = await req.json()
        const entryData: KnowledgeBaseEntry = requestData.entry
        
        // Validate entry data
        if (!validateEntry(entryData)) {
          return new Response(
            JSON.stringify({ error: 'Invalid entry data' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Set created_by to current user
        entryData.created_by = userId
        
        // Set timestamps
        const now = new Date().toISOString()
        entryData.created_at = now
        entryData.updated_at = now
        
        // Generate ID if not provided
        const id = entryData.id || crypto.randomUUID()
        entryData.id = id
        
        // Default visibility to private if not specified
        entryData.visibility = entryData.visibility || 'private'
        
        // Generate embedding
        const embedding = await generateEmbedding(entryData.content, openaiApiKey)
        
        // Get namespace based on visibility
        const namespace = getNamespaceForVisibility(entryData.visibility, userId)
        
        // Convert to metadata
        const metadata = entryToMetadata(entryData)
        
        // Store content in Supabase Storage
        try {
          await supabaseClient
            .storage
            .from('kb-content')
            .upload(`${id}.txt`, entryData.content, {
              contentType: 'text/plain',
              upsert: true
            })
        } catch (error) {
          console.error('Error storing content in Supabase:', error)
          // Continue anyway - we'll fall back to content_preview if needed
        }
        
        // Store metadata and embedding in Pinecone
        await index.upsert({
          vectors: [{
            id,
            values: embedding,
            metadata
          }],
          namespace
        })
        
        // Store entry metadata in Supabase for easier querying
        await supabaseClient
          .from('kb_entries_meta')
          .upsert({
            id,
            title: entryData.title,
            visibility: entryData.visibility,
            created_by: userId,
            created_at: now,
            updated_at: now,
            tags: entryData.tags || []
          })
        
        return new Response(
          JSON.stringify({ success: true, id }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Update an existing entry
      case 'PUT': {
        if (!entryId) {
          return new Response(
            JSON.stringify({ error: 'Entry ID is required' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Check permission
        const hasPermission = await checkPermissions(
          supabaseClient,
          userId,
          'kb-entry',
          entryId,
          Permission.WRITE
        )
        
        await logAccessAttempt(
          supabaseClient,
          userId,
          'kb-entry',
          entryId,
          Permission.WRITE,
          hasPermission
        )
        
        if (!hasPermission) {
          return new Response(
            JSON.stringify({ error: 'Permission denied' }),
            { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Parse request body
        const requestData = await req.json()
        const updateData = requestData.entry
        
        // Ensure ID is not changed
        updateData.id = entryId
        
        // Set updated_at timestamp
        const now = new Date().toISOString()
        updateData.updated_at = now
        
        // Find the current entry to get its namespace
        const { data: entryMeta } = await supabaseClient
          .from('kb_entries_meta')
          .select('visibility, created_by')
          .eq('id', entryId)
          .single()
          
        if (!entryMeta) {
          return new Response(
            JSON.stringify({ error: 'Entry not found' }),
            { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Keep the same creator
        updateData.created_by = entryMeta.created_by
        
        // Get current and new namespaces
        const currentNamespace = getNamespaceForVisibility(entryMeta.visibility, entryMeta.created_by)
        const newNamespace = getNamespaceForVisibility(updateData.visibility || entryMeta.visibility, entryMeta.created_by)
        
        // Generate new embedding if content changed
        let embedding: number[] | null = null
        if (updateData.content) {
          embedding = await generateEmbedding(updateData.content, openaiApiKey)
        }
        
        // Convert to metadata
        const metadata = entryToMetadata(updateData)
        
        // If content updated, store in Supabase Storage
        if (updateData.content) {
          try {
            await supabaseClient
              .storage
              .from('kb-content')
              .upload(`${entryId}.txt`, updateData.content, {
                contentType: 'text/plain',
                upsert: true
              })
          } catch (error) {
            console.error('Error storing content in Supabase:', error)
            // Continue anyway - we'll fall back to content_preview if needed
          }
        }
        
        // Update entry in Pinecone
        // If visibility changed, need to delete from old namespace and insert in new one
        if (currentNamespace !== newNamespace) {
          // Delete from old namespace
          await index.delete({
            ids: [entryId],
            namespace: currentNamespace
          })
          
          // Insert into new namespace with full vector
          if (!embedding) {
            // Need to get current content to generate embedding
            let content = ''
            try {
              const { data, error } = await supabaseClient
                .storage
                .from('kb-content')
                .download(`${entryId}.txt`)
              
              if (data && !error) {
                content = await data.text()
                embedding = await generateEmbedding(content, openaiApiKey)
              }
            } catch (error) {
              console.error('Error getting content for embedding:', error)
              return new Response(
                JSON.stringify({ error: 'Failed to update entry due to content access error' }),
                { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
              )
            }
          }
          
          await index.upsert({
            vectors: [{
              id: entryId,
              values: embedding,
              metadata
            }],
            namespace: newNamespace
          })
          
        } else if (embedding) {
          // Just update in the same namespace with new vector
          await index.upsert({
            vectors: [{
              id: entryId,
              values: embedding,
              metadata
            }],
            namespace: currentNamespace
          })
        } else {
          // Just update metadata in the same namespace
          await index.update({
            id: entryId,
            metadata,
            namespace: currentNamespace
          })
        }
        
        // Update entry metadata in Supabase
        const updateFields: any = {
          updated_at: now
        }
        
        if (updateData.title) updateFields.title = updateData.title
        if (updateData.visibility) updateFields.visibility = updateData.visibility
        if (updateData.tags) updateFields.tags = updateData.tags
        
        await supabaseClient
          .from('kb_entries_meta')
          .update(updateFields)
          .eq('id', entryId)
        
        return new Response(
          JSON.stringify({ success: true }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Delete an entry
      case 'DELETE': {
        if (!entryId) {
          return new Response(
            JSON.stringify({ error: 'Entry ID is required' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Check permission
        const hasPermission = await checkPermissions(
          supabaseClient,
          userId,
          'kb-entry',
          entryId,
          Permission.DELETE
        )
        
        await logAccessAttempt(
          supabaseClient,
          userId,
          'kb-entry',
          entryId,
          Permission.DELETE,
          hasPermission
        )
        
        if (!hasPermission) {
          return new Response(
            JSON.stringify({ error: 'Permission denied' }),
            { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Get entry's current namespace
        const { data: entryMeta } = await supabaseClient
          .from('kb_entries_meta')
          .select('visibility, created_by')
          .eq('id', entryId)
          .single()
          
        if (!entryMeta) {
          return new Response(
            JSON.stringify({ error: 'Entry not found' }),
            { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        const namespace = getNamespaceForVisibility(entryMeta.visibility, entryMeta.created_by)
        
        // Delete from Pinecone
        await index.delete({
          ids: [entryId],
          namespace
        })
        
        // Delete content from Supabase Storage
        try {
          await supabaseClient
            .storage
            .from('kb-content')
            .remove([`${entryId}.txt`])
        } catch (error) {
          console.error('Error removing content from Supabase:', error)
          // Continue anyway
        }
        
        // Delete metadata from Supabase
        await supabaseClient
          .from('kb_entries_meta')
          .delete()
          .eq('id', entryId)
        
        return new Response(
          JSON.stringify({ success: true }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      default:
        return new Response(
          JSON.stringify({ error: 'Method not allowed' }),
          { status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }
    
  } catch (error) {
    console.error('Error in entries handler:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}
