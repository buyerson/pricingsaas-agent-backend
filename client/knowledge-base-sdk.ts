/**
 * Knowledge Base Client SDK
 * 
 * This SDK provides a simplified interface for frontend applications
 * to interact with the PricingSaaS Knowledge Base API.
 */

// Types for Knowledge Base entries
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

export interface SearchResult {
  entry: KnowledgeBaseEntry;
  score: number;
}

export interface SearchFilter {
  tags?: string[];
  created_by?: string;
  title?: string;
  created_at?: {
    $gte?: string;
    $lte?: string;
  };
  updated_at?: {
    $gte?: string;
    $lte?: string;
  };
  [key: string]: any;
}

export interface CustomFieldDefinition {
  id?: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'array' | 'object';
  description?: string;
  validation_rules?: Record<string, any>;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export type SearchType = 'semantic' | 'metadata' | 'hybrid';
export type VisibilityLevel = 'public' | 'team' | 'private';

// Knowledge Base Client class
export class KnowledgeBaseClient {
  private supabaseUrl: string;
  private supabaseClient: any;

  /**
   * Create a new Knowledge Base client
   * @param supabaseClient A initialized Supabase client with auth
   * @param supabaseUrl Base URL of the Supabase project
   */
  constructor(supabaseClient: any, supabaseUrl: string) {
    this.supabaseClient = supabaseClient;
    this.supabaseUrl = supabaseUrl;
  }

  /**
   * Check if the client is authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    const {
      data: { user },
    } = await this.supabaseClient.auth.getUser();
    return !!user;
  }

  /**
   * Get the current access token
   */
  private async getAccessToken(): Promise<string> {
    const {
      data: { session },
    } = await this.supabaseClient.auth.getSession();
    return session?.access_token || '';
  }

  /**
   * Make an authenticated API request to the Knowledge Base API
   */
  private async apiRequest(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    body?: any
  ): Promise<any> {
    const token = await this.getAccessToken();
    
    if (!token) {
      throw new Error('Not authenticated');
    }

    const response = await fetch(`${this.supabaseUrl}/functions/v1${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: body ? JSON.stringify(body) : undefined
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { error: 'Unknown error' };
      }
      throw new Error(errorData.error || `API request failed with status ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Create a new knowledge base entry
   * @param entry The entry to create
   * @returns ID of the created entry
   */
  async createEntry(entry: KnowledgeBaseEntry): Promise<string> {
    const response = await this.apiRequest(
      '/knowledge-base/entries',
      'POST',
      { entry }
    );
    return response.id;
  }

  /**
   * Get a knowledge base entry by ID
   * @param id Entry ID
   * @returns The entry
   */
  async getEntry(id: string): Promise<KnowledgeBaseEntry> {
    const response = await this.apiRequest(
      `/knowledge-base/entries?id=${id}`,
      'GET'
    );
    return response.entry;
  }

  /**
   * Update a knowledge base entry
   * @param id Entry ID
   * @param updates The updates to apply
   * @returns Success status
   */
  async updateEntry(id: string, updates: Partial<KnowledgeBaseEntry>): Promise<boolean> {
    const response = await this.apiRequest(
      `/knowledge-base/entries?id=${id}`,
      'PUT',
      { entry: { id, ...updates } }
    );
    return response.success === true;
  }

  /**
   * Delete a knowledge base entry
   * @param id Entry ID
   * @returns Success status
   */
  async deleteEntry(id: string): Promise<boolean> {
    const response = await this.apiRequest(
      `/knowledge-base/entries?id=${id}`,
      'DELETE'
    );
    return response.success === true;
  }

  /**
   * List knowledge base entries
   * @param options List options
   * @returns List of entries
   */
  async listEntries(options: {
    visibility?: VisibilityLevel | 'all';
    tag?: string;
    limit?: number;
  } = {}): Promise<KnowledgeBaseEntry[]> {
    const params = new URLSearchParams();
    if (options.visibility) params.append('visibility', options.visibility);
    if (options.tag) params.append('tag', options.tag);
    if (options.limit) params.append('limit', options.limit.toString());

    const response = await this.apiRequest(
      `/knowledge-base/entries?${params.toString()}`,
      'GET'
    );
    return response.entries;
  }

  /**
   * Search the knowledge base
   * @param options Search options
   * @returns Search results
   */
  async search(options: {
    query?: string;
    searchType?: SearchType;
    filters?: SearchFilter;
    topK?: number;
    visibility?: VisibilityLevel[];
  }): Promise<SearchResult[]> {
    const {
      query = '',
      searchType = 'semantic',
      filters = {},
      topK = 5,
      visibility = ['public', 'team', 'private']
    } = options;

    // Validate options
    if ((searchType === 'semantic' || searchType === 'hybrid') && !query) {
      throw new Error('Query is required for semantic or hybrid search');
    }

    const response = await this.apiRequest(
      '/knowledge-base/search',
      'POST',
      {
        query,
        searchType,
        filters,
        topK,
        visibility
      }
    );
    return response.results;
  }

  /**
   * Perform a semantic search
   * @param query Search query
   * @param topK Number of results
   * @param visibility Visibility levels to search
   * @returns Search results
   */
  async semanticSearch(
    query: string,
    topK: number = 5,
    visibility: VisibilityLevel[] = ['public', 'team', 'private']
  ): Promise<SearchResult[]> {
    return this.search({
      query,
      searchType: 'semantic',
      topK,
      visibility
    });
  }

  /**
   * Perform a metadata search
   * @param filters Metadata filters
   * @param topK Number of results
   * @param visibility Visibility levels to search
   * @returns Search results
   */
  async metadataSearch(
    filters: SearchFilter,
    topK: number = 5,
    visibility: VisibilityLevel[] = ['public', 'team', 'private']
  ): Promise<SearchResult[]> {
    return this.search({
      searchType: 'metadata',
      filters,
      topK,
      visibility
    });
  }

  /**
   * Perform a hybrid search (semantic + metadata)
   * @param query Search query
   * @param filters Metadata filters
   * @param topK Number of results
   * @param visibility Visibility levels to search
   * @returns Search results
   */
  async hybridSearch(
    query: string,
    filters: SearchFilter,
    topK: number = 5,
    visibility: VisibilityLevel[] = ['public', 'team', 'private']
  ): Promise<SearchResult[]> {
    return this.search({
      query,
      searchType: 'hybrid',
      filters,
      topK,
      visibility
    });
  }

  /**
   * Get the knowledge base schema
   * @returns Schema definition
   */
  async getSchema(): Promise<any> {
    const response = await this.apiRequest(
      '/knowledge-base/schema',
      'GET'
    );
    return response.schema;
  }

  /**
   * Add a custom field definition (admin only)
   * @param fieldDef Custom field definition
   * @returns Success status and created field
   */
  async addCustomField(fieldDef: CustomFieldDefinition): Promise<{ success: boolean, field: CustomFieldDefinition }> {
    const response = await this.apiRequest(
      '/knowledge-base/schema',
      'POST',
      { fieldDefinition: fieldDef }
    );
    return {
      success: response.success === true,
      field: response.field
    };
  }

  /**
   * Update a custom field definition (admin only)
   * @param fieldDef Custom field definition with ID
   * @returns Success status and updated field
   */
  async updateCustomField(fieldDef: CustomFieldDefinition): Promise<{ success: boolean, field: CustomFieldDefinition }> {
    if (!fieldDef.id) {
      throw new Error('Field ID is required for updates');
    }

    const response = await this.apiRequest(
      '/knowledge-base/schema',
      'PUT',
      { fieldDefinition: fieldDef }
    );
    return {
      success: response.success === true,
      field: response.field
    };
  }

  /**
   * Delete a custom field definition (admin only)
   * @param fieldId Field ID
   * @returns Success status
   */
  async deleteCustomField(fieldId: string): Promise<boolean> {
    const response = await this.apiRequest(
      `/knowledge-base/schema?id=${fieldId}`,
      'DELETE'
    );
    return response.success === true;
  }
}

/**
 * Create a Knowledge Base client
 * @param supabaseClient Initialized Supabase client
 * @param supabaseUrl Supabase project URL
 * @returns Knowledge Base client
 */
export function createKnowledgeBaseClient(supabaseClient: any, supabaseUrl: string): KnowledgeBaseClient {
  return new KnowledgeBaseClient(supabaseClient, supabaseUrl);
}
