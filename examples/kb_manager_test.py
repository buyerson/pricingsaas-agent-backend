#!/usr/bin/env python3
"""
Knowledge Base Manager Test

This script tests the basic functionality of the Knowledge Base Manager
without requiring the Agent components.
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add parent directory to path to find our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.knowledge_base_helper import get_kb_manager
from helpers.schema_definitions import KnowledgeBaseEntryCore, KnowledgeBaseEntryExtended

async def run_test():
    """Run a test of knowledge base manager functionality."""
    print("🔍 PricingSaaS Knowledge Base Manager Test 🔍")
    print("-" * 50)
    
    # Initialize the knowledge base manager
    kb_manager = get_kb_manager()
    print("✅ Knowledge Base Manager initialized")
    
    # Create a user ID for this demo
    user_id = f"demo-user-{uuid.uuid4().hex[:8]}"
    print(f"👤 Demo user ID: {user_id}")
    
    # Create a sample knowledge base entry
    print("\n📝 Creating a new knowledge base entry...")
    
    entry_data = {
        "title": "SaaS Pricing Strategy Best Practices",
        "content": """
        # SaaS Pricing Strategy Best Practices
        
        Effective SaaS pricing strategies align price with the value customers receive and optimize for both acquisition and retention.
        
        ## Key Components
        
        1. **Value-Based Pricing**: Price based on the value your solution provides, not costs.
        2. **Tiered Pricing**: Offer multiple pricing tiers to serve different customer segments.
        3. **Usage-Based Elements**: Consider incorporating usage-based pricing for fairness.
        4. **Clear Value Metrics**: Tie pricing to metrics customers care about.
        5. **Regular Price Testing**: Continuously test and refine pricing models.
        
        ## Common Mistakes to Avoid
        
        - Underpricing your solution
        - Too many pricing tiers
        - Hidden fees that surprise customers
        - Pricing that doesn't scale with customer growth
        
        Remember that pricing is a powerful marketing and positioning tool, not just a financial decision.
        """,
        "tags": ["pricing", "strategy", "best-practices", "saas"],
        "visibility": "public",
        "source": "PricingSaaS Internal Documentation",
        "confidence": 5
    }
    
    try:
        entry_id = kb_manager.create_entry(entry_data, user_id)
        print(f"✅ Created entry with ID: {entry_id}")
        
        # Wait longer for the embedding to be indexed
        print("⏳ Waiting for embedding to be indexed...")
        # Pinecone serverless can take longer to index, especially on first run
        print("  (This may take a few seconds...)")
        max_attempts = 10
        wait_time = 7  # seconds
        retrieved_entry = None
        
        for attempt in range(max_attempts):
            print(f"  Attempt {attempt + 1}/{max_attempts} - waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            # Try to retrieve after each wait
            retrieved_entry = kb_manager.get_entry(entry_id, user_id)
            if retrieved_entry is not None:
                print(f"  ✅ Entry found after {(attempt + 1) * wait_time} seconds")
                break
            else:
                print(f"  ⏳ Entry not found yet, retrying...")
                # After a few attempts, try to re-upload the entry
                if attempt == 5:
                    print("  🔄 Re-uploading entry to Pinecone...")
                    kb_manager.create_entry(entry_data, user_id)
        
        # Retrieve the entry
        print("\n📜 Retrieving the entry...")
        if retrieved_entry is not None:
            print(f"✅ Retrieved entry: {retrieved_entry.title}")
            print(f"📅 Created at: {retrieved_entry.created_at}")
        else:
            print(f"⚠️ Warning: Could not retrieve the entry after {max_attempts} attempts.")
            print("  Continuing with the test anyway...")
            # Use the original entry data to create a new object for testing
            retrieved_entry = KnowledgeBaseEntryExtended(**entry_data)
        
        # Update the entry
        print("\n✏️ Updating the entry...")
        updates = {
            "title": "Updated: SaaS Pricing Strategy Best Practices",
            "tags": ["pricing", "strategy", "best-practices", "saas", "updated"]
        }
        update_success = kb_manager.update_entry(entry_id, updates, user_id)
        print(f"✅ Update successful: {update_success}")
        
        # Search for entries
        print("\n🔎 Searching for entries semantically...")
        search_query = "pricing strategies for SaaS companies"
        search_results = kb_manager.search(search_query, user_id, limit=3)
        
        print(f"Found {len(search_results)} results:")
        for i, (entry, score) in enumerate(search_results, 1):
            print(f"  {i}. {entry.title} (score: {score:.4f})")
            if i == 1:  # Show more details for the first result
                print(f"     Tags: {', '.join(entry.tags)}")
                print(f"     Content preview: {entry.content[:100]}...")
        
        # Search by metadata (tags)
        print("\n🔎 Searching by metadata (tags)...")
        tag_results = kb_manager.filter_by_metadata(user_id, {"tags": ["updated"]}, limit=10)
        print(f"Found {len(tag_results)} results with 'updated' tag")
        for i, result in enumerate(tag_results, 1):
            print(f"  {i}. {result.title} (tags: {', '.join(result.tags or [])})")
            print(f"     Created: {result.created_at}, Updated: {result.updated_at}")
            print(f"     Visibility: {result.visibility}")
            print(f"     ID: {result.id}")
        
        # Delete the entry
        print("\n🗑️ Cleaning up - deleting the test entry...")
        delete_success = kb_manager.delete_entry(entry_id, user_id)
        print(f"✅ Deletion successful: {delete_success}")
        
        print("\n✨ Knowledge Base test complete!")
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if required environment variables are set
    required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running this script.")
        sys.exit(1)
    
    try:
        asyncio.run(run_test())
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
