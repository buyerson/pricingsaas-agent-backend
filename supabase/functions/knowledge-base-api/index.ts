// Knowledge Base API Edge Function
import { serve } from 'https://deno.land/std@0.131.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.7.1'
import { corsHeaders } from '../_shared/cors.ts'
import { 
  validateToken,
  getUserId,
  checkPermissions
} from '../_shared/auth.ts'
import { 
  entriesHandler,
  searchHandler,
  schemaHandler
} from './handlers.ts'

// Create a Supabase client
const supabaseClient = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_ANON_KEY') ?? ''
)

const pineconeApiKey = Deno.env.get('PINECONE_API_KEY') ?? ''
const pineconeEnv = Deno.env.get('PINECONE_ENVIRONMENT') ?? ''
const openaiApiKey = Deno.env.get('OPENAI_API_KEY') ?? ''

// Router for handling different API paths
const router = {
  // CRUD operations for knowledge base entries
  '/knowledge-base/entries': entriesHandler,
  // Search operations for knowledge base
  '/knowledge-base/search': searchHandler,
  // Schema management operations
  '/knowledge-base/schema': schemaHandler
}

serve(async (req: Request) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Get URL and path
    const url = new URL(req.url)
    const path = url.pathname
    
    // Validate JWT token from authorization header
    const token = req.headers.get('Authorization')?.replace('Bearer ', '')
    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized - No token provided' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }
    
    // Verify token using Supabase Auth
    const { user, error } = await validateToken(supabaseClient, token)
    if (error || !user) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized - Invalid token' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }
    
    const userId = getUserId(user)
    
    // Find the appropriate handler based on the path
    const handler = Object.keys(router).find(route => path.includes(route))
    if (!handler) {
      return new Response(
        JSON.stringify({ error: 'Not Found - Invalid endpoint' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }
    
    // Execute the handler with the necessary context
    const context = {
      req,
      supabaseClient,
      user,
      userId,
      pineconeApiKey,
      pineconeEnv,
      openaiApiKey
    }
    
    return await router[handler as keyof typeof router](context)
    
  } catch (error) {
    console.error('Error processing request:', error)
    return new Response(
      JSON.stringify({ error: 'Internal Server Error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
