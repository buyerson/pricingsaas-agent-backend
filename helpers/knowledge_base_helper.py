"""
Knowledge Base Helper module.

This module provides utilities for knowledge base operations, including:
- Pinecone vector database interactions
- OpenAI embedding generation
- Knowledge base entry management
"""

import os
import uuid
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from helpers.schema_definitions import (
    KnowledgeBaseEntryCore,
    KnowledgeBaseEntryExtended,
    validate_entry,
    entry_to_metadata,
    metadata_to_entry,
    CURRENT_SCHEMA_VERSION
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PINECONE_INDEX_NAME = "pricingsaas-kb"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MAX_TOKEN_SIZE = 8000  # Max tokens for embedding model

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def initialize_pinecone():
    """Initialize Pinecone client and ensure index exists with correct dimensions."""
    api_key = os.environ.get("PINECONE_API_KEY")
    
    if not api_key:
        raise ValueError("PINECONE_API_KEY must be set")
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=api_key)
    
    # Get index name from environment or use default
    index_name = os.environ.get("PINECONE_INDEX", PINECONE_INDEX_NAME)
    
    # Check if the index already exists
    index_exists = index_name in [idx['name'] for idx in pc.list_indexes()]
    
    # If it exists, check if we need to recreate it with the correct dimensions
    if index_exists:
        try:
            # Try to create a test vector to verify dimensions
            test_index = pc.Index(index_name)
            test_vector = [0.0] * EMBEDDING_DIMENSIONS
            test_index.upsert(vectors=[("test-vector", test_vector, {})], namespace="test")
            logger.info(f"Pinecone index {index_name} exists with correct dimensions")
            test_index.delete(ids=["test-vector"], namespace="test")
        except Exception as e:
            # If we get a dimension mismatch error, delete and recreate the index
            if "dimension" in str(e).lower():
                logger.warning(f"Dimension mismatch detected in index {index_name}. Deleting and recreating...")
                pc.delete_index(index_name)
                logger.info(f"Deleted index {index_name} due to dimension mismatch")
                index_exists = False
            else:
                # Some other error occurred
                logger.error(f"Error testing Pinecone index: {e}")
    
    # Create the index if it doesn't exist or was deleted
    if not index_exists:
        logger.info(f"Creating Pinecone index: {index_name} with dimension {EMBEDDING_DIMENSIONS}")
        pc.create_index(
            name=index_name,
            dimension=EMBEDDING_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        # Wait a moment for the index to initialize
        import time
        time.sleep(2)
    
    # Get the index
    return pc.Index(index_name)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using OpenAI API.
    
    Args:
        text: Text to embed
        
    Returns:
        List of float values representing the embedding vector
    """
    try:
        response: CreateEmbeddingResponse = openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise

def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize metadata for Pinecone by flattening nested structures and
    ensuring values are of compatible types (string, number, boolean, or list of strings).
    
    Args:
        metadata: Dictionary of metadata
    
    Returns:
        Sanitized metadata dictionary suitable for Pinecone
    """
    sanitized = {}
    
    for key, value in metadata.items():
        # Skip null values
        if value is None:
            continue
            
        # Handle lists specially for tag arrays and other list types
        if isinstance(value, list):
            # For lists, ensure all elements are strings
            sanitized[key] = [str(item) for item in value if item is not None]
        elif isinstance(value, (str, int, float, bool)):
            # Basic types pass through as-is
            sanitized[key] = value
        elif isinstance(value, dict):
            # Flatten nested dictionaries with dot notation
            for nested_key, nested_value in value.items():
                if nested_value is not None:
                    flattened_key = f"{key}.{nested_key}"
                    if isinstance(nested_value, (str, int, float, bool)):
                        sanitized[flattened_key] = nested_value
                    else:
                        # For complex types, convert to string
                        sanitized[flattened_key] = str(nested_value)
        else:
            # For any other types, convert to string
            sanitized[key] = str(value)
    
    return sanitized

def get_namespace_for_visibility(visibility: str, user_id: str) -> str:
    """
    Determine the appropriate Pinecone namespace based on visibility.
    
    Args:
        visibility: Visibility setting ('public', 'private', 'team')
        user_id: ID of the user
        
    Returns:
        Namespace string for Pinecone
    """
    if visibility == "public":
        return "public-kb"
    elif visibility == "team":
        return "team-kb"
    else:  # private
        return f"user-{user_id}"

class KnowledgeBaseManager:
    """Manager class for knowledge base operations."""
    
    def __init__(self):
        """Initialize the knowledge base manager."""
        self.index = initialize_pinecone()
    
    def create_entry(self, entry_data: Dict[str, Any], user_id: str) -> str:
        """
        Create a new knowledge base entry.
        
        Args:
            entry_data: Entry data dictionary
            user_id: ID of the user creating the entry
            
        Returns:
            ID of the created entry
        """
        # Generate a unique ID if not provided
        if "id" not in entry_data:
            entry_data["id"] = str(uuid.uuid4())
        
        # Set timestamps
        now = datetime.now()
        entry_data["created_at"] = now.isoformat()
        entry_data["updated_at"] = now.isoformat()
        
        # Set creator
        entry_data["created_by"] = user_id
        
        # Set schema version
        entry_data["schema_version"] = CURRENT_SCHEMA_VERSION
        
        # Validate entry against schema
        validate_entry(entry_data)
        
        # Create entry object
        entry = KnowledgeBaseEntryExtended(**entry_data)
        
        # Generate embedding for content
        embedding = generate_embedding(entry.content)
        
        # Convert to metadata for Pinecone
        metadata = entry_to_metadata(entry)
        
        # Determine namespace based on visibility
        namespace = get_namespace_for_visibility(entry.visibility, user_id)
        logger.info(f"Creating entry {entry.id} in namespace: {namespace}")
        
        # Upsert vector to Pinecone
        self.index.upsert(
            vectors=[(entry.id, embedding, metadata)],
            namespace=namespace
        )
        
        return entry.id
    
    def get_entry(self, entry_id: str, user_id: str) -> Optional[KnowledgeBaseEntryExtended]:
        """
        Retrieve a knowledge base entry by ID.
        
        Args:
            entry_id: ID of the entry to retrieve
            user_id: ID of the user making the request
            
        Returns:
            KnowledgeBaseEntryExtended object or None if not found
        """
        logger.info(f"Attempting to retrieve entry {entry_id} for user {user_id}")
        namespaces = ["public-kb", "team-kb", f"user-{user_id}"]
        
        for namespace in namespaces:
            try:
                logger.info(f"Checking namespace: {namespace}")
                fetch_response = self.index.fetch(ids=[entry_id], namespace=namespace)
                
                if not hasattr(fetch_response, 'vectors') or not fetch_response.vectors:
                    logger.info(f"No vectors found in namespace {namespace}")
                    continue
                    
                if entry_id not in fetch_response.vectors:
                    logger.info(f"Entry ID {entry_id} not found in namespace {namespace}")
                    continue
                    
                vector_data = fetch_response.vectors[entry_id]
                
                if not hasattr(vector_data, 'metadata') or not vector_data.metadata:
                    logger.info(f"No metadata found for entry {entry_id} in namespace {namespace}")
                    continue
                
                # Extract metadata and add ID if needed
                metadata = vector_data.metadata
                content = metadata.get("content_preview", "[Content would be retrieved from storage]")
                metadata["id"] = entry_id
                
                logger.info(f"Entry {entry_id} found in namespace {namespace}")
                return metadata_to_entry(metadata, content)
                
            except Exception as e:
                logger.error(f"Error fetching entry {entry_id} from namespace {namespace}: {e}")
                import traceback
                traceback.print_exc()
        
        # Not found in any namespace
        logger.warning(f"Entry {entry_id} not found in any accessible namespace for user {user_id}")
        return None
    
    def update_entry(self, entry_id: str, update_data: Dict[str, Any], user_id: str) -> bool:
        """
        Update an existing knowledge base entry.
        
        Args:
            entry_id: ID of the entry to update
            update_data: Dictionary of fields to update
            user_id: ID of the user making the update
            
        Returns:
            True if update successful, False otherwise
        """
        # Get the current entry to ensure visibility
        current_entry = self.get_entry(entry_id, user_id)
        if not current_entry:
            logger.error(f"Could not find entry {entry_id} to update")
            return False
        
        # Make sure updated_at is current
        update_data["updated_at"] = datetime.now().isoformat()
        
        # Determine namespace based on visibility
        namespace = get_namespace_for_visibility(current_entry.visibility, user_id)
        logger.info(f"Updating entry {entry_id} in namespace: {namespace}")
        
        # Prepare metadata for update by starting with the current entry data
        entry_dict = current_entry.model_dump()
        
        # Update with new data
        entry_dict.update(update_data)
        
        # Convert to metadata format for Pinecone
        metadata = entry_to_metadata(KnowledgeBaseEntryExtended(**entry_dict))
        
        # Special handling for tags
        if "tags" in update_data and update_data["tags"] is not None:
            if isinstance(update_data["tags"], str):
                metadata["tags"] = [tag.strip() for tag in update_data["tags"].split(",")]
            else:
                metadata["tags"] = update_data["tags"]
            logger.info(f"Updated tags: {metadata['tags']}")
        
        # Update embeddings if title has changed
        embedding = None
        if "title" in update_data and update_data["title"] and update_data["title"] != current_entry.title:
            logger.info(f"Title changed, generating new embedding")
            embedding = generate_embedding(update_data["title"])
        
        # Sanitize metadata for Pinecone
        metadata = sanitize_metadata(metadata)
        
        # Update in Pinecone
        if embedding:
            # If embedding changed, we need to do a full upsert
            logger.info(f"Upserting entry with new embedding")
            self.index.upsert(
                vectors=[(entry_id, embedding, metadata)],
                namespace=namespace
            )
        else:
            # Just update the metadata
            logger.info(f"Updating entry metadata only")
            self.index.update(
                id=entry_id,
                set_metadata=metadata,
                namespace=namespace
            )
        
        return True
    
    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        """
        Delete a knowledge base entry.
        
        Args:
            entry_id: ID of the entry to delete
            user_id: ID of the user making the deletion
            
        Returns:
            Boolean indicating success
        """
        # First retrieve the entry to check permissions
        current_entry = self.get_entry(entry_id, user_id)
        if not current_entry:
            return False
        
        # Check if user has permission to delete
        if current_entry.created_by != user_id and current_entry.visibility == "private":
            return False
        
        # Determine namespace
        namespace = get_namespace_for_visibility(current_entry.visibility, user_id)
        
        # Delete from Pinecone
        try:
            self.index.delete(ids=[entry_id], namespace=namespace)
            return True
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            return False
    
    def search(
        self, 
        query: str, 
        user_id: str, 
        limit: int = 10, 
        namespaces: Optional[List[str]] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[KnowledgeBaseEntryExtended, float]]:
        """
        Search the knowledge base using semantic similarity.
        
        Args:
            query: Search query text
            user_id: ID of the user making the search
            limit: Maximum number of results to return
            namespaces: Optional list of namespaces to search in
            filter_dict: Optional Pinecone metadata filters
            
        Returns:
            List of (entry, score) tuples sorted by relevance
        """
        # Generate embedding for query
        query_embedding = generate_embedding(query)
        
        # Default namespaces - user can see public, team, and their own private entries
        if not namespaces:
            namespaces = [
                "public-kb",
                "team-kb",
                f"user-{user_id}"
            ]
        
        results = []
        
        # Search each namespace
        for namespace in namespaces:
            try:
                # Query Pinecone
                query_response = self.index.query(
                    vector=query_embedding,
                    top_k=limit,
                    namespace=namespace,
                    filter=filter_dict,
                    include_metadata=True
                )
                
                # Process matches
                for match in query_response.matches:
                    metadata = match.metadata
                    # Extract content from metadata or from separate storage
                    content = metadata.get("content_preview", "")
                    
                    # Convert metadata to entry
                    entry = metadata_to_entry(metadata, content)
                    
                    # Add to results with score
                    results.append((entry, match.score))
            except Exception as e:
                logger.error(f"Error searching namespace {namespace}: {e}")
        
        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def filter_by_metadata(
        self, 
        user_id: str, 
        filter_dict: Dict[str, Any], 
        limit: int = 10,
        namespaces: Optional[List[str]] = None
    ) -> List[KnowledgeBaseEntryExtended]:
        """
        Filter knowledge base entries by metadata.
        
        Args:
            user_id: ID of the user making the request
            filter_dict: Pinecone metadata filters
            limit: Maximum number of results
            namespaces: Optional list of namespaces to search in
            
        Returns:
            List of entries matching the filter
        """
        # Default namespaces
        if not namespaces:
            namespaces = [
                "public-kb",
                "team-kb",
                f"user-{user_id}"
            ]
        
        results = []
        
        # Format filter for Pinecone - handle array fields like 'tags' properly
        pinecone_filter = {}
        for key, value in filter_dict.items():
            # For array values like tags, use the $in operator
            if isinstance(value, list):
                pinecone_filter[key] = {"$in": value}
            else:
                pinecone_filter[key] = value
        
        logger.info(f"Using Pinecone filter: {pinecone_filter}")
        
        # Query each namespace
        for namespace in namespaces:
            try:
                # Since we're just filtering by metadata, we can use a random vector
                # This is a limitation of Pinecone - there's no direct metadata-only query
                # In a production system, you might want to use a more sophisticated approach
                dummy_vector = [0.0] * EMBEDDING_DIMENSIONS
                
                query_response = self.index.query(
                    vector=dummy_vector,
                    top_k=limit,
                    namespace=namespace,
                    filter=pinecone_filter,
                    include_metadata=True
                )
                
                # Process matches
                for match in query_response.matches:
                    metadata = match.metadata
                    content = metadata.get("content_preview", "")
                    entry = metadata_to_entry(metadata, content)
                    results.append(entry)
            except Exception as e:
                logger.error(f"Error filtering in namespace {namespace}: {e}")
        
        return results[:limit]

# We'll create the manager instance on demand to avoid initialization issues
kb_manager = None

def get_kb_manager() -> KnowledgeBaseManager:
    """Get the knowledge base manager instance."""
    global kb_manager
    if kb_manager is None:
        kb_manager = KnowledgeBaseManager()
    return kb_manager
