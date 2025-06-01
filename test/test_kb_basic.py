"""
Tests for the Knowledge Base functionality (basic components only).

This module contains tests for the knowledge base operations,
including schema validation, embedding generation, and CRUD operations.
"""

import unittest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

import pinecone
from openai import OpenAI

from helpers.schema_definitions import (
    KnowledgeBaseEntryCore,
    KnowledgeBaseEntryExtended,
    validate_entry,
    entry_to_metadata,
    metadata_to_entry,
    CURRENT_SCHEMA_VERSION
)
from helpers.knowledge_base_helper import (
    KnowledgeBaseManager,
    generate_embedding,
    get_namespace_for_visibility,
    initialize_pinecone,
    sanitize_metadata
)

# Sample test data
SAMPLE_ENTRY = {
    "id": "test-id-123",
    "title": "Test Knowledge Entry",
    "content": "This is a test knowledge base entry with important pricing information.",
    "created_by": "test-user",
    "tags": ["pricing", "test"],
    "visibility": "private",
    "schema_version": CURRENT_SCHEMA_VERSION
}

SAMPLE_EMBEDDING = [0.1] * 1536  # Dummy embedding for testing

class TestSchemaDefinitions(unittest.TestCase):
    """Test cases for schema definitions."""
    
    def test_entry_validation_valid(self):
        """Test validation with valid entry data."""
        # Valid entry should not raise exception
        self.assertTrue(validate_entry(SAMPLE_ENTRY))
    
    def test_entry_validation_invalid(self):
        """Test validation with invalid entry data."""
        from jsonschema import ValidationError
        
        # Missing required field
        invalid_entry = SAMPLE_ENTRY.copy()
        invalid_entry.pop("title")
        with self.assertRaises(ValidationError):
            validate_entry(invalid_entry)
        
        # Invalid confidence value
        invalid_entry = SAMPLE_ENTRY.copy()
        invalid_entry["confidence"] = 6  # Out of range (1-5)
        with self.assertRaises(ValidationError):
            validate_entry(invalid_entry)
    
    def test_entry_to_metadata(self):
        """Test conversion from entry to Pinecone metadata."""
        entry = KnowledgeBaseEntryExtended(**SAMPLE_ENTRY)
        metadata = entry_to_metadata(entry)
        
        # Check that content is removed (too large for metadata)
        self.assertNotIn("content", metadata)
        
        # Check that tags are preserved as a list
        self.assertIn("tags", metadata)
        self.assertEqual(metadata["tags"], ["pricing", "test"])
    
    def test_metadata_to_entry(self):
        """Test conversion from Pinecone metadata back to entry."""
        # Convert entry to metadata
        entry = KnowledgeBaseEntryExtended(**SAMPLE_ENTRY)
        metadata = entry_to_metadata(entry)
        
        # Convert metadata back to entry
        content = SAMPLE_ENTRY["content"]
        restored_entry = metadata_to_entry(metadata, content)
        
        # Check that entry was properly restored
        self.assertEqual(restored_entry.id, SAMPLE_ENTRY["id"])
        self.assertEqual(restored_entry.title, SAMPLE_ENTRY["title"])
        self.assertEqual(restored_entry.content, SAMPLE_ENTRY["content"])
        self.assertEqual(restored_entry.tags, SAMPLE_ENTRY["tags"])


@patch('helpers.knowledge_base_helper.openai_client')
@patch('helpers.knowledge_base_helper.Pinecone')
class TestKnowledgeBaseHelper(unittest.TestCase):
    """Test cases for knowledge base helper functions."""
    
    def test_generate_embedding(self, mock_pinecone, mock_openai_client):
        """Test embedding generation."""
        # Mock OpenAI embedding response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=SAMPLE_EMBEDDING)]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        # Generate embedding
        embedding = generate_embedding("Test text")
        
        # Check that embedding has correct shape
        self.assertEqual(len(embedding), 1536)
        self.assertEqual(embedding, SAMPLE_EMBEDDING)
    
    def test_get_namespace_for_visibility(self, mock_pinecone, mock_openai_client):
        """Test namespace determination based on visibility."""
        # Public visibility
        namespace = get_namespace_for_visibility("public", "test-user")
        self.assertEqual(namespace, "public-kb")
        
        # Team visibility
        namespace = get_namespace_for_visibility("team", "test-user")
        self.assertEqual(namespace, "team-kb")
        
        # Private visibility
        namespace = get_namespace_for_visibility("private", "test-user")
        self.assertEqual(namespace, "user-test-user")
    
    def test_sanitize_metadata(self, mock_pinecone, mock_openai_client):
        """Test metadata sanitization for Pinecone compatibility."""
        # Test with various data types
        metadata = {
            "string": "text",
            "integer": 123,
            "float": 3.14,
            "boolean": True,
            "null_value": None,
            "list": ["item1", "item2"],
            "nested": {"key": "value"}
        }
        
        sanitized = sanitize_metadata(metadata)
        
        # Check that primitive types pass through
        self.assertEqual(sanitized["string"], "text")
        self.assertEqual(sanitized["integer"], 123)
        self.assertEqual(sanitized["float"], 3.14)
        self.assertEqual(sanitized["boolean"], True)
        
        # Check that null values are skipped
        self.assertNotIn("null_value", sanitized)
        
        # Check that lists are preserved with string conversion
        self.assertEqual(sanitized["list"], ["item1", "item2"])
        
        # Check that nested dicts are flattened
        self.assertEqual(sanitized["nested.key"], "value")
        self.assertNotIn("nested", sanitized)

if __name__ == '__main__':
    unittest.main()
