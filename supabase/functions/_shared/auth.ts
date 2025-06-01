// Authentication utilities for edge functions
import { SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2.7.1'

// User data interface
interface User {
  id: string;
  email?: string;
  app_metadata?: {
    provider?: string;
    [key: string]: any;
  };
  user_metadata?: {
    [key: string]: any;
  };
  aud?: string;
  role?: string;
}

// Permission levels
export enum Permission {
  READ = 'read',
  WRITE = 'write',
  DELETE = 'delete',
  ADMIN = 'admin'
}

/**
 * Validate a JWT token using Supabase
 */
export async function validateToken(supabaseClient: SupabaseClient, token: string) {
  try {
    // Get user from token
    const { data: { user }, error } = await supabaseClient.auth.getUser(token)
    
    if (error) {
      console.error('Error validating token:', error)
      return { user: null, error }
    }
    
    return { user, error: null }
  } catch (error) {
    console.error('Exception validating token:', error)
    return { user: null, error }
  }
}

/**
 * Get user ID from user object
 */
export function getUserId(user: User | null): string {
  return user?.id || 'anonymous'
}

/**
 * Check if user has permission for the specified action
 */
export async function checkPermissions(
  supabaseClient: SupabaseClient,
  userId: string,
  resourceType: string,
  resourceId: string | null,
  permission: Permission
): Promise<boolean> {
  // If resource type is 'kb-entry' and resource ID is null, 
  // we're checking permission to create a new entry
  
  try {
    // For now, implement a simple permission model:
    // - Users can always read public entries
    // - Users can read, write, delete their own entries
    // - Users with admin role can do anything
    
    // Check if user has admin role
    const { data: roleData } = await supabaseClient
      .from('user_roles')
      .select('role')
      .eq('user_id', userId)
      .single()
      
    if (roleData?.role === 'admin') {
      return true
    }
    
    // For entry creation, all authenticated users can create
    if (resourceType === 'kb-entry' && !resourceId && permission === Permission.WRITE) {
      return true
    }
    
    // For existing resources, check ownership or visibility
    if (resourceType === 'kb-entry' && resourceId) {
      const { data: entryData } = await supabaseClient
        .from('kb_entries_meta')
        .select('created_by, visibility')
        .eq('id', resourceId)
        .single()
        
      if (!entryData) {
        return false
      }
      
      // Public entries can be read by anyone
      if (permission === Permission.READ && entryData.visibility === 'public') {
        return true
      }
      
      // Team entries can be read by team members
      if (permission === Permission.READ && entryData.visibility === 'team') {
        const { data: teamData } = await supabaseClient
          .from('user_teams')
          .select('team_id')
          .eq('user_id', userId)
          
        if (teamData && teamData.length > 0) {
          return true
        }
      }
      
      // Owners can do anything with their own entries
      if (entryData.created_by === userId) {
        return true
      }
    }
    
    // Default: deny access
    return false
    
  } catch (error) {
    console.error('Error checking permissions:', error)
    return false
  }
}

/**
 * Log access attempt for audit purposes
 */
export async function logAccessAttempt(
  supabaseClient: SupabaseClient,
  userId: string,
  resourceType: string,
  resourceId: string | null,
  permission: Permission,
  granted: boolean
): Promise<void> {
  try {
    await supabaseClient
      .from('access_logs')
      .insert({
        user_id: userId,
        resource_type: resourceType,
        resource_id: resourceId || 'new',
        permission: permission,
        granted: granted,
        timestamp: new Date().toISOString()
      })
  } catch (error) {
    console.error('Error logging access attempt:', error)
  }
}
