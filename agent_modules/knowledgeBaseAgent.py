"""
Knowledge Base Agent for the PricingSaaS backend.

This agent provides tools for storing, retrieving, updating, and deleting
knowledge items in the user-editable knowledge base.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from openai import OpenAI
from openai_agents import Tool, AgentContext, State

from helpers.knowledge_base_helper import (
    get_kb_manager,
    KnowledgeBaseEntryExtended,
    CURRENT_SCHEMA_VERSION
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KBSearchTool(Tool):
    """Tool for semantic search in the knowledge base."""
    
    description = "Search for information in the knowledge base using semantic similarity"
    
    def execute(
        self, 
        query: str, 
        limit: int = 5, 
        filter_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a semantic search in the knowledge base.
        
        Args:
            query: The search query text
            limit: Maximum number of results to return
            filter_tags: Optional list of tags to filter by
            
        Returns:
            List of matching knowledge base entries with scores
        """
        user_id = self.context.state.get("user_id", "system")
        
        # Set up filter dict if tags are provided
        filter_dict = None
        if filter_tags:
            filter_dict = {
                "tags_csv": {"$containsAny": filter_tags}
            }
        
        # Get knowledge base manager and search
        kb_manager = get_kb_manager()
        results = kb_manager.search(
            query=query,
            user_id=user_id,
            limit=limit,
            filter_dict=filter_dict
        )
        
        # Format results for return
        formatted_results = []
        for entry, score in results:
            formatted_results.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "tags": entry.tags,
                "source": entry.source,
                "created_by": entry.created_by,
                "created_at": entry.created_at.isoformat(),
                "visibility": entry.visibility,
                "relevance_score": score
            })
        
        return formatted_results

class KBMetadataSearchTool(Tool):
    """Tool for searching the knowledge base by metadata."""
    
    description = "Search for information in the knowledge base by metadata fields"
    
    def execute(
        self, 
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        visibility: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Execute a metadata search in the knowledge base.
        
        Args:
            tags: Optional list of tags to filter by
            created_by: Optional creator ID to filter by
            visibility: Optional visibility setting to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of matching knowledge base entries
        """
        user_id = self.context.state.get("user_id", "system")
        
        # Set up filter dict
        filter_dict = {}
        if tags:
            filter_dict["tags_csv"] = {"$containsAny": tags}
        if created_by:
            filter_dict["created_by"] = created_by
        if visibility:
            filter_dict["visibility"] = visibility
        
        # Get knowledge base manager and search
        kb_manager = get_kb_manager()
        results = kb_manager.filter_by_metadata(
            user_id=user_id,
            filter_dict=filter_dict,
            limit=limit
        )
        
        # Format results for return
        formatted_results = []
        for entry in results:
            formatted_results.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "tags": entry.tags,
                "source": entry.source,
                "created_by": entry.created_by,
                "created_at": entry.created_at.isoformat(),
                "visibility": entry.visibility
            })
        
        return formatted_results

class KBCreateTool(Tool):
    """Tool for creating a new knowledge base entry."""
    
    description = "Create a new entry in the knowledge base"
    
    def execute(
        self, 
        title: str, 
        content: str, 
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        visibility: str = "private",
        confidence: Optional[float] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new knowledge base entry.
        
        Args:
            title: Short descriptive title for the entry
            content: Main text content
            tags: Optional list of categorization tags
            source: Optional source of the information
            visibility: Visibility setting ('public', 'private', 'team')
            confidence: Optional reliability rating (1-5)
            custom_fields: Optional custom fields for domain-specific properties
            
        Returns:
            Dictionary with the ID of the created entry
        """
        user_id = self.context.state.get("user_id", "system")
        
        # Prepare entry data
        entry_data = {
            "title": title,
            "content": content,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "visibility": visibility
        }
        
        if tags:
            entry_data["tags"] = tags
        if source:
            entry_data["source"] = source
        if confidence is not None:
            entry_data["confidence"] = confidence
        if custom_fields:
            entry_data["custom_fields"] = custom_fields
        
        # Get knowledge base manager and create entry
        kb_manager = get_kb_manager()
        entry_id = kb_manager.create_entry(entry_data, user_id)
        
        return {"id": entry_id, "status": "created"}

class KBUpdateTool(Tool):
    """Tool for updating an existing knowledge base entry."""
    
    description = "Update an existing entry in the knowledge base"
    
    def execute(
        self, 
        entry_id: str, 
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        visibility: Optional[str] = None,
        confidence: Optional[float] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing knowledge base entry.
        
        Args:
            entry_id: ID of the entry to update
            title: Optional new title
            content: Optional new content
            tags: Optional new tags
            source: Optional new source
            visibility: Optional new visibility setting
            confidence: Optional new confidence rating
            custom_fields: Optional new custom fields
            
        Returns:
            Dictionary with the status of the update
        """
        user_id = self.context.state.get("user_id", "system")
        
        # Prepare update data
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
        if tags is not None:
            update_data["tags"] = tags
        if source is not None:
            update_data["source"] = source
        if visibility is not None:
            update_data["visibility"] = visibility
        if confidence is not None:
            update_data["confidence"] = confidence
        if custom_fields is not None:
            update_data["custom_fields"] = custom_fields
        
        # Get knowledge base manager and update entry
        kb_manager = get_kb_manager()
        success = kb_manager.update_entry(entry_id, update_data, user_id)
        
        return {"id": entry_id, "status": "updated" if success else "failed"}

class KBDeleteTool(Tool):
    """Tool for deleting a knowledge base entry."""
    
    description = "Delete an entry from the knowledge base"
    
    def execute(self, entry_id: str) -> Dict[str, Any]:
        """
        Delete a knowledge base entry.
        
        Args:
            entry_id: ID of the entry to delete
            
        Returns:
            Dictionary with the status of the deletion
        """
        user_id = self.context.state.get("user_id", "system")
        
        # Get knowledge base manager and delete entry
        kb_manager = get_kb_manager()
        success = kb_manager.delete_entry(entry_id, user_id)
        
        return {"id": entry_id, "status": "deleted" if success else "failed"}

class KBGetTool(Tool):
    """Tool for retrieving a specific knowledge base entry."""
    
    description = "Retrieve a specific entry from the knowledge base by ID"
    
    def execute(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific knowledge base entry.
        
        Args:
            entry_id: ID of the entry to retrieve
            
        Returns:
            Dictionary containing the entry data or None if not found
        """
        user_id = self.context.state.get("user_id", "system")
        
        # Get knowledge base manager and retrieve entry
        kb_manager = get_kb_manager()
        entry = kb_manager.get_entry(entry_id, user_id)
        
        if not entry:
            return None
        
        # Format entry for return
        return {
            "id": entry.id,
            "title": entry.title,
            "content": entry.content,
            "tags": entry.tags,
            "source": entry.source,
            "created_by": entry.created_by,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "visibility": entry.visibility,
            "confidence": entry.confidence,
            "custom_fields": entry.custom_fields
        }

class KnowledgeBaseAgent:
    """
    Agent for managing the knowledge base.
    
    This agent provides tools for storing, retrieving, updating, and
    deleting knowledge items in the user-editable knowledge base.
    """
    
    def __init__(self):
        """Initialize the Knowledge Base Agent."""
        self.tools = [
            KBSearchTool(),
            KBMetadataSearchTool(),
            KBCreateTool(),
            KBUpdateTool(),
            KBDeleteTool(),
            KBGetTool()
        ]
        
        # Make sure Pinecone is initialized
        get_kb_manager()
    
    def get_tools(self) -> List[Tool]:
        """Get the tools provided by this agent."""
        return self.tools
    
    async def process_query(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """
        Process a query using the knowledge base.
        
        Args:
            query: The user's query
            context: The agent context
            
        Returns:
            Response dictionary with results and citations
        """
        # Get user ID from context
        user_id = context.state.get("user_id", "system")
        
        # Search the knowledge base
        kb_manager = get_kb_manager()
        search_results = kb_manager.search(
            query=query,
            user_id=user_id,
            limit=5
        )
        
        # Format results for response
        results = []
        citations = []
        
        for i, (entry, score) in enumerate(search_results):
            # Only include results with a good relevance score
            if score < 0.7:
                continue
                
            # Add citation
            citation_id = f"kb{i+1}"
            citations.append({
                "id": citation_id,
                "title": entry.title,
                "source": entry.source or "Knowledge Base",
                "url": f"kb://{entry.id}"
            })
            
            # Add result with citation
            results.append({
                "content": entry.content,
                "citation": citation_id,
                "relevance": score
            })
        
        return {
            "results": results,
            "citations": citations
        }
