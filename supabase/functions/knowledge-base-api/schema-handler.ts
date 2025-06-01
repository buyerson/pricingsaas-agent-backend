// Handler for knowledge base schema operations
import { corsHeaders } from '../_shared/cors.ts'
import { Permission, checkPermissions, logAccessAttempt } from '../_shared/auth.ts'
import { getSchemaDefinition } from './utils.ts'

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
 * Handle schema operations for knowledge base
 */
export async function schemaHandler(context: HandlerContext): Promise<Response> {
  const { req, supabaseClient, userId } = context
  
  try {
    switch (req.method) {
      // Get schema definition
      case 'GET': {
        // No special permissions required for getting schema
        const schema = getSchemaDefinition()
        
        return new Response(
          JSON.stringify({ schema }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Add custom field definition (admin only)
      case 'POST': {
        // Check for admin permission
        const hasPermission = await checkPermissions(
          supabaseClient,
          userId,
          'kb-schema',
          null,
          Permission.ADMIN
        )
        
        await logAccessAttempt(
          supabaseClient,
          userId,
          'kb-schema',
          null,
          Permission.ADMIN,
          hasPermission
        )
        
        if (!hasPermission) {
          return new Response(
            JSON.stringify({ error: 'Permission denied - requires admin role' }),
            { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Parse request body
        const requestData = await req.json()
        const fieldDefinition = requestData.fieldDefinition
        
        if (!fieldDefinition || !fieldDefinition.name || !fieldDefinition.type) {
          return new Response(
            JSON.stringify({ error: 'Invalid field definition' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Get existing custom field definitions
        const { data: customFieldsData, error } = await supabaseClient
          .from('kb_schema_custom_fields')
          .select('*')
        
        if (error) {
          console.error('Error getting custom fields:', error)
          return new Response(
            JSON.stringify({ error: 'Failed to retrieve custom fields' }),
            { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Check if field with same name already exists
        if (customFieldsData.some((field: any) => field.name === fieldDefinition.name)) {
          return new Response(
            JSON.stringify({ error: 'Field with this name already exists' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Add new field definition
        const { data: insertData, error: insertError } = await supabaseClient
          .from('kb_schema_custom_fields')
          .insert({
            name: fieldDefinition.name,
            type: fieldDefinition.type,
            description: fieldDefinition.description || '',
            validation_rules: fieldDefinition.validation_rules || {},
            created_by: userId,
            created_at: new Date().toISOString()
          })
          .select()
        
        if (insertError) {
          console.error('Error adding custom field:', insertError)
          return new Response(
            JSON.stringify({ error: 'Failed to add custom field' }),
            { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        return new Response(
          JSON.stringify({ success: true, field: insertData[0] }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Update custom field definition (admin only)
      case 'PUT': {
        // Check for admin permission
        const hasPermission = await checkPermissions(
          supabaseClient,
          userId,
          'kb-schema',
          null,
          Permission.ADMIN
        )
        
        await logAccessAttempt(
          supabaseClient,
          userId,
          'kb-schema',
          null,
          Permission.ADMIN,
          hasPermission
        )
        
        if (!hasPermission) {
          return new Response(
            JSON.stringify({ error: 'Permission denied - requires admin role' }),
            { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Parse request body
        const requestData = await req.json()
        const fieldDefinition = requestData.fieldDefinition
        
        if (!fieldDefinition || !fieldDefinition.id) {
          return new Response(
            JSON.stringify({ error: 'Invalid field definition or missing ID' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Update field definition
        const { data: updateData, error: updateError } = await supabaseClient
          .from('kb_schema_custom_fields')
          .update({
            name: fieldDefinition.name,
            type: fieldDefinition.type,
            description: fieldDefinition.description || '',
            validation_rules: fieldDefinition.validation_rules || {},
            updated_at: new Date().toISOString()
          })
          .eq('id', fieldDefinition.id)
          .select()
        
        if (updateError) {
          console.error('Error updating custom field:', updateError)
          return new Response(
            JSON.stringify({ error: 'Failed to update custom field' }),
            { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        return new Response(
          JSON.stringify({ success: true, field: updateData[0] }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      
      // Delete custom field definition (admin only)
      case 'DELETE': {
        // Check for admin permission
        const hasPermission = await checkPermissions(
          supabaseClient,
          userId,
          'kb-schema',
          null,
          Permission.ADMIN
        )
        
        await logAccessAttempt(
          supabaseClient,
          userId,
          'kb-schema',
          null,
          Permission.ADMIN,
          hasPermission
        )
        
        if (!hasPermission) {
          return new Response(
            JSON.stringify({ error: 'Permission denied - requires admin role' }),
            { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Get field ID from URL params
        const url = new URL(req.url)
        const fieldId = url.searchParams.get('id')
        
        if (!fieldId) {
          return new Response(
            JSON.stringify({ error: 'Field ID is required' }),
            { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
        // Delete field definition
        const { error: deleteError } = await supabaseClient
          .from('kb_schema_custom_fields')
          .delete()
          .eq('id', fieldId)
        
        if (deleteError) {
          console.error('Error deleting custom field:', deleteError)
          return new Response(
            JSON.stringify({ error: 'Failed to delete custom field' }),
            { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }
        
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
    console.error('Error in schema handler:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}
