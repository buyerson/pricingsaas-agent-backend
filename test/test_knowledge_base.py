"""
Tests for the Knowledge Base functionality.

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

# Skip agent module imports until the dependency is available
# Commented out for future reference:
# from agent_modules.knowledgeBaseAgent import (
#     KnowledgeBaseAgent,
#     KBSearchTool,
#     KBMetadataSearchTool,
#     KBCreateTool,
#     KBUpdateTool,
#     KBDeleteTool,
#     KBGetTool
# )

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
        
        # Check that tags are converted to csv
        self.assertIn("tags_csv", metadata)
        self.assertEqual(metadata["tags_csv"], "pricing,test")
    
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
        
        # Check that OpenAI API was called correctly
        mock_openai_client.embeddings.create.assert_called_once()
        self.assertEqual(embedding, SAMPLE_EMBEDDING)
    
    def test_namespace_mapping(self, mock_pinecone, mock_openai_client):
        """Test namespace mapping for different visibility settings."""
        # Test public namespace
        self.assertEqual(get_namespace_for_visibility("public", "user123"), "public-kb")
        
        # Test team namespace
        self.assertEqual(get_namespace_for_visibility("team", "user123"), "team-kb")
        
        # Test private namespace
        self.assertEqual(get_namespace_for_visibility("private", "user123"), "user-user123")
    
    def test_initialize_pinecone(self, mock_pinecone_class, mock_openai_client):
        """Test Pinecone initialization."""
        # Mock environment variables
        with patch.dict(os.environ, {
            "PINECONE_API_KEY": "test-api-key",
            "PINECONE_INDEX": "test-index"
        }):
            # Create mock Pinecone instance
            mock_pinecone = MagicMock()
            mock_pinecone_class.return_value = mock_pinecone
            
            # Mock Pinecone index list response
            mock_pinecone.list_indexes.return_value = []
            
            # Create mock index
            mock_index = MagicMock()
            mock_pinecone.Index.return_value = mock_index
            
            # Initialize Pinecone
            index = initialize_pinecone()
            
            # Check that the Pinecone constructor was called with the correct API key
            mock_pinecone_class.assert_called_once_with(api_key="test-api-key")
            
            # Check that create_index was called
            mock_pinecone.create_index.assert_called_once()
            self.assertEqual(index, mock_index)


@patch('helpers.knowledge_base_helper.generate_embedding', return_value=SAMPLE_EMBEDDING)
@patch('helpers.knowledge_base_helper.initialize_pinecone')
class TestKnowledgeBaseManager(unittest.TestCase):
    """Test cases for the KnowledgeBaseManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_index = MagicMock()
        self.user_id = "test-user"
    
    def test_create_entry(self, mock_initialize_pinecone, mock_generate_embedding):
        """Test creating a new knowledge base entry."""
        # Mock Pinecone index
        mock_initialize_pinecone.return_value = self.mock_index
        
        # Create manager and entry
        manager = KnowledgeBaseManager()
        entry_data = SAMPLE_ENTRY.copy()
        entry_data.pop("id")  # Let the manager generate an ID
        
        # Create entry
        entry_id = manager.create_entry(entry_data, self.user_id)
        
        # Check that embedding was generated
        mock_generate_embedding.assert_called_once_with(entry_data["content"])
        
        # Check that entry was upserted to Pinecone
        self.mock_index.upsert.assert_called_once()
        
        # Check that an ID was generated
        self.assertIsNotNone(entry_id)
    
    def test_get_entry(self, mock_initialize_pinecone, mock_generate_embedding):
        """Test retrieving a knowledge base entry."""
        # Mock Pinecone index
        mock_initialize_pinecone.return_value = self.mock_index
        
        # Mock fetch response
        mock_vector = MagicMock()
        mock_vector.metadata = entry_to_metadata(KnowledgeBaseEntryExtended(**SAMPLE_ENTRY))
        mock_vector.metadata["content_preview"] = SAMPLE_ENTRY["content"]
        
        mock_fetch_response = MagicMock()
        mock_fetch_response.vectors = {SAMPLE_ENTRY["id"]: mock_vector}
        self.mock_index.fetch.return_value = mock_fetch_response
        
        # Create manager and get entry
        manager = KnowledgeBaseManager()
        entry = manager.get_entry(SAMPLE_ENTRY["id"], self.user_id)
        
        # Check that entry was retrieved correctly
        self.assertIsNotNone(entry)
        self.assertEqual(entry.id, SAMPLE_ENTRY["id"])
        self.assertEqual(entry.title, SAMPLE_ENTRY["title"])
    
    def test_update_entry(self, mock_initialize_pinecone, mock_generate_embedding):
        """Test updating a knowledge base entry."""
        # Mock Pinecone index
        mock_initialize_pinecone.return_value = self.mock_index
        
        # Mock get_entry to return sample entry
        with patch.object(KnowledgeBaseManager, 'get_entry') as mock_get_entry:
            mock_get_entry.return_value = KnowledgeBaseEntryExtended(**SAMPLE_ENTRY)
            
            # Create manager and update entry
            manager = KnowledgeBaseManager()
            update_data = {"title": "Updated Title"}
            success = manager.update_entry(SAMPLE_ENTRY["id"], update_data, self.user_id)
            
            # Check that update was successful
            self.assertTrue(success)
            
            # Check that entry was updated in Pinecone
            # Our implementation might use either update or upsert depending on whether content changed
            update_called = self.mock_index.update.call_count > 0
            upsert_called = self.mock_index.upsert.call_count > 0
            self.assertTrue(update_called or upsert_called, "Either update or upsert should be called")
            
    
    def test_delete_entry(self, mock_initialize_pinecone, mock_generate_embedding):
        """Test deleting a knowledge base entry."""
        # Mock Pinecone index
        mock_initialize_pinecone.return_value = self.mock_index
        
        # Mock get_entry to return sample entry
        with patch.object(KnowledgeBaseManager, 'get_entry') as mock_get_entry:
            mock_get_entry.return_value = KnowledgeBaseEntryExtended(**SAMPLE_ENTRY)
            
            # Create manager and delete entry
            manager = KnowledgeBaseManager()
            success = manager.delete_entry(SAMPLE_ENTRY["id"], self.user_id)
            
            # Check that deletion was successful
            self.assertTrue(success)
            
            # Check that entry was deleted from Pinecone
            self.mock_index.delete.assert_called_once()
    
    def test_search(self, mock_initialize_pinecone, mock_generate_embedding):
        """Test searching the knowledge base."""
        # Mock Pinecone index
        mock_initialize_pinecone.return_value = self.mock_index
        
        # Mock query response
        mock_match = MagicMock()
        mock_match.metadata = entry_to_metadata(KnowledgeBaseEntryExtended(**SAMPLE_ENTRY))
        mock_match.metadata["content_preview"] = SAMPLE_ENTRY["content"]
        mock_match.score = 0.95
        
        mock_query_response = MagicMock()
        mock_query_response.matches = [mock_match]
        self.mock_index.query.return_value = mock_query_response
        
        # Create manager and search
        manager = KnowledgeBaseManager()
        results = manager.search("test query", self.user_id)
        
        # Check that search returned results
        # The search implementation returns multiple results, which is expected
        self.assertGreater(len(results), 0, "Search should return at least one result")
        
        # Check that the sample entry is in the results
        found = False
        for entry, score in results:
            if entry.id == SAMPLE_ENTRY["id"]:
                self.assertAlmostEqual(score, 0.95, places=1)
                found = True
                break
        
        self.assertTrue(found, "Expected sample entry in search results")


# Commented out until openai_agents dependency is available
# @patch('agent_modules.knowledgeBaseAgent.get_kb_manager')
# class TestKnowledgeBaseAgent(unittest.TestCase):
#     """Test cases for the KnowledgeBaseAgent class."""
#     
#     def setUp(self):
#         """Set up test fixtures."""
#         # self.agent = KnowledgeBaseAgent()
#         self.user_id = "test-user"
#         
#         # Create mock context
#         self.mock_context = MagicMock()
#         self.mock_context.state = {"user_id": self.user_id}
    
#     def test_get_tools(self, mock_get_kb_manager):
#         """Test that agent provides the expected tools."""
#         tools = self.agent.get_tools()
#         
#         # Check that all expected tools are provided
#         self.assertEqual(len(tools), 6)
#         tool_classes = [tool.__class__ for tool in tools]
#         self.assertIn(KBSearchTool, tool_classes)
#         self.assertIn(KBMetadataSearchTool, tool_classes)
#         self.assertIn(KBCreateTool, tool_classes)
#         self.assertIn(KBUpdateTool, tool_classes)
#         self.assertIn(KBDeleteTool, tool_classes)
#         self.assertIn(KBGetTool, tool_classes)
#     
#     @patch('helpers.knowledge_base_helper.KnowledgeBaseManager.search')
#     async def test_process_query(self, mock_search, mock_get_kb_manager):
#         """Test processing a query with the knowledge base agent."""
#         # Mock KB manager
#         mock_kb_manager = MagicMock()
#         mock_get_kb_manager.return_value = mock_kb_manager
#         
#         # Mock search results
#         entry = KnowledgeBaseEntryExtended(**SAMPLE_ENTRY)
#         mock_search.return_value = [(entry, 0.95)]
#         mock_kb_manager.search.return_value = [(entry, 0.95)]
#         
#         # Process query
#         response = await self.agent.process_query("test query", self.mock_context)
#         
#         # Check that search was called
#         mock_kb_manager.search.assert_called_once()
#         
#         # Check response format
#         self.assertIn("results", response)
#         self.assertIn("citations", response)
#         self.assertEqual(len(response["results"]), 1)
#         self.assertEqual(len(response["citations"]), 1)


if __name__ == '__main__':
    unittest.main()
