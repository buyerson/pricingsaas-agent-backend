"""
Schema definitions for the Knowledge Base.

This module contains JSON schema definitions for knowledge base entries,
validation functions, and schema versioning utilities.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Literal

from jsonschema import validate, ValidationError
from pydantic import BaseModel, Field

# Schema version for tracking and migrations
CURRENT_SCHEMA_VERSION = "1.0.0"

# Visibility options for knowledge base entries
VisibilityType = Literal["public", "private", "team"]

class KnowledgeBaseEntryCore(BaseModel):
    """Core schema for knowledge base entries."""
    id: str
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str
    tags: List[str] = Field(default_factory=list)
    schema_version: str = CURRENT_SCHEMA_VERSION

class KnowledgeBaseEntryExtended(KnowledgeBaseEntryCore):
    """Extended schema with optional metadata fields."""
    source: Optional[str] = None
    confidence: Optional[float] = None
    expiration: Optional[datetime] = None
    visibility: VisibilityType = "private"
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    embedding_id: Optional[str] = None

# JSON Schema for validation
KB_ENTRY_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "content", "created_by", "schema_version"],
    "properties": {
        "id": {
            "type": "string",
            "description": "Unique identifier for the knowledge base entry"
        },
        "title": {
            "type": "string",
            "description": "Short descriptive title for the entry",
            "minLength": 3,
            "maxLength": 200
        },
        "content": {
            "type": "string",
            "description": "Main text content of the knowledge item",
            "minLength": 10
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp when the entry was created"
        },
        "updated_at": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp when the entry was last updated"
        },
        "created_by": {
            "type": "string",
            "description": "User ID of the creator"
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of categorization tags"
        },
        "source": {
            "type": ["string", "null"],
            "description": "Origin of the information (optional)"
        },
        "confidence": {
            "type": ["number", "null"],
            "minimum": 1,
            "maximum": 5,
            "description": "Reliability rating (1-5 scale, optional)"
        },
        "expiration": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "Expiration date for time-sensitive information (optional)"
        },
        "visibility": {
            "type": "string",
            "enum": ["public", "private", "team"],
            "description": "Visibility setting for the entry"
        },
        "schema_version": {
            "type": "string",
            "description": "Version of the schema used for this entry"
        },
        "custom_fields": {
            "type": "object",
            "description": "JSON object for domain-specific properties"
        },
        "embedding_id": {
            "type": ["string", "null"],
            "description": "ID of the vector embedding in Pinecone"
        }
    },
    "additionalProperties": False
}

# Schema versions history for migration support
SCHEMA_VERSIONS = {
    "1.0.0": KB_ENTRY_SCHEMA,
    # Add new versions here as the schema evolves
}

def validate_entry(entry_data: Dict[str, Any]) -> bool:
    """
    Validate a knowledge base entry against the schema.
    
    Args:
        entry_data: Dictionary containing entry data
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    schema_version = entry_data.get("schema_version", CURRENT_SCHEMA_VERSION)
    
    if schema_version not in SCHEMA_VERSIONS:
        raise ValidationError(f"Unknown schema version: {schema_version}")
        
    schema = SCHEMA_VERSIONS[schema_version]
    validate(instance=entry_data, schema=schema)
    return True

def entry_to_metadata(entry: Union[KnowledgeBaseEntryExtended, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert entry to Pinecone metadata format.
    
    Args:
        entry: Knowledge base entry (Pydantic model or dict)
        
    Returns:
        Dict with metadata formatted for Pinecone
    """
    if isinstance(entry, KnowledgeBaseEntryExtended):
        entry_dict = entry.model_dump()
    else:
        entry_dict = entry.copy()
    
    # Convert datetime objects to ISO format strings for Pinecone
    for field in ["created_at", "updated_at", "expiration"]:
        if field in entry_dict and entry_dict[field] is not None:
            if isinstance(entry_dict[field], datetime):
                entry_dict[field] = entry_dict[field].isoformat()
    
    # Remove content field as it's typically too large for metadata
    # The content is embedded in the vector
    if "content" in entry_dict:
        entry_dict.pop("content")
        
    # Keep tags as array for Pinecone filtering and also provide CSV format for backward compatibility
    if "tags" in entry_dict and isinstance(entry_dict["tags"], list):
        # Keep the original array for filtering with $in operator
        entry_dict["tags"] = [tag for tag in entry_dict["tags"] if tag]
        # Also provide tags_csv for backward compatibility
        entry_dict["tags_csv"] = ",".join(entry_dict["tags"])
    
    # Handle custom_fields - Pinecone doesn't accept empty dictionaries or nested objects
    if "custom_fields" in entry_dict:
        # If empty, remove it
        if not entry_dict["custom_fields"]:
            entry_dict.pop("custom_fields")
        else:
            # Convert any nested dictionaries to JSON strings
            custom_fields = {}
            for key, value in entry_dict["custom_fields"].items():
                if isinstance(value, (dict, list)):
                    custom_fields[f"custom_{key}"] = json.dumps(value)
                elif value is not None:  # Skip None values
                    custom_fields[f"custom_{key}"] = value
            # Remove original custom_fields dict and add flattened fields
            entry_dict.pop("custom_fields")
            entry_dict.update(custom_fields)
    
    # Remove any None/null values as Pinecone doesn't accept them
    cleaned_dict = {}
    for key, value in entry_dict.items():
        if value is not None:
            cleaned_dict[key] = value
    
    return cleaned_dict

def metadata_to_entry(metadata: Dict[str, Any], content: str) -> KnowledgeBaseEntryExtended:
    """
    Convert Pinecone metadata back to a knowledge base entry.
    
    Args:
        metadata: Metadata from Pinecone
        content: Content text (typically not stored in metadata)
        
    Returns:
        KnowledgeBaseEntryExtended: Entry as a Pydantic model
    """
    entry_data = metadata.copy()
    
    # Add content back
    entry_data["content"] = content
    
    # Convert tags back to list
    if "tags_csv" in entry_data:
        entry_data["tags"] = entry_data["tags_csv"].split(",") if entry_data["tags_csv"] else []
        entry_data.pop("tags_csv")
    
    # Reconstruct custom_fields from flattened custom_ prefixed fields
    custom_fields = {}
    custom_keys = [k for k in list(entry_data.keys()) if k.startswith("custom_")]
    
    for key in custom_keys:
        # Extract the original field name without the custom_ prefix
        field_name = key[7:]  # Remove 'custom_' prefix
        value = entry_data[key]
        
        # Try to parse JSON strings back to objects
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                # If not valid JSON, keep as string
                pass
                
        custom_fields[field_name] = value
        entry_data.pop(key)  # Remove the flattened field
    
    # Add reconstructed custom_fields dict if not empty
    if custom_fields:
        entry_data["custom_fields"] = custom_fields
    else:
        entry_data["custom_fields"] = {}
    
    # Parse datetime strings
    for field in ["created_at", "updated_at", "expiration"]:
        if field in entry_data and isinstance(entry_data[field], str):
            try:
                entry_data[field] = datetime.fromisoformat(entry_data[field])
            except ValueError:
                # If parsing fails, keep as string
                pass
    
    return KnowledgeBaseEntryExtended(**entry_data)
