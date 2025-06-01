#!/usr/bin/env python3
"""
Knowledge Base Demonstration Script

This script demonstrates how to use the knowledge base functionality
including creating, searching, updating, and deleting entries.
"""

import os
import sys
import json
import uuid
from datetime import datetime
import asyncio

# Add parent directory to path to find our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.knowledge_base_helper import get_kb_manager
from helpers.schema_definitions import KnowledgeBaseEntryCore, KnowledgeBaseEntryExtended
from agent_modules.knowledgeBaseAgent import KnowledgeBaseAgent

async def run_demo():
    """Run a demonstration of knowledge base functionality."""
    print("🔍 PricingSaaS Knowledge Base Demonstration 🔍")
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
    
    entry_id = kb_manager.create_entry(entry_data, user_id)
    print(f"✅ Created entry with ID: {entry_id}")
    
    # Wait a moment for the embedding to be indexed
    print("⏳ Waiting for embedding to be indexed...")
    await asyncio.sleep(2)
    
    # Retrieve the entry
    print("\n📄 Retrieving the entry...")
    retrieved_entry = kb_manager.get_entry(entry_id, user_id)
    print(f"✅ Retrieved entry: {retrieved_entry.title}")
    print(f"📅 Created at: {retrieved_entry.created_at}")
    
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
    search_results = kb_manager.search(search_query, user_id, top_k=3)
    
    print(f"Found {len(search_results)} results:")
    for i, (entry, score) in enumerate(search_results, 1):
        print(f"  {i}. {entry.title} (score: {score:.4f})")
        if i == 1:  # Show more details for the first result
            print(f"     Tags: {', '.join(entry.tags)}")
            print(f"     Content preview: {entry.content[:100]}...")
    
    # Metadata search
    print("\n🔎 Searching by metadata (tags)...")
    metadata_results = kb_manager.metadata_search({"tags": ["updated"]}, user_id)
    print(f"Found {len(metadata_results)} results with 'updated' tag")
    
    # Initialize the Knowledge Base Agent
    print("\n🤖 Initializing Knowledge Base Agent...")
    kb_agent = KnowledgeBaseAgent()
    print(f"✅ Agent initialized with {len(kb_agent.get_tools())} tools")
    
    # Process a query with the agent
    print("\n💬 Processing a query with the Knowledge Base Agent...")
    mock_context = type('obj', (object,), {'state': {'user_id': user_id}})
    query = "What are the best practices for SaaS pricing?"
    
    agent_response = await kb_agent.process_query(query, mock_context)
    print("\n📊 Agent Response:")
    print(f"Results count: {len(agent_response.get('results', []))}")
    print(f"Citations count: {len(agent_response.get('citations', []))}")
    
    # Sample of how the agent response would be used in the main flow
    if agent_response['results']:
        print("\n📋 Sample agent response text:")
        for result in agent_response['results'][:1]:  # Show first result only
            print(f"{result['content']}\n")
            if 'citation_ids' in result:
                citation_ids = result['citation_ids']
                print(f"Citation IDs: {citation_ids}")
                for citation_id in citation_ids:
                    if citation_id in agent_response['citations']:
                        citation = agent_response['citations'][citation_id]
                        print(f"Citation: {citation['title']}")
    
    # Delete the entry
    print("\n🗑️ Cleaning up - deleting the test entry...")
    delete_success = kb_manager.delete_entry(entry_id, user_id)
    print(f"✅ Deletion successful: {delete_success}")
    
    print("\n✨ Knowledge Base demonstration complete!")

if __name__ == "__main__":
    # Check if required environment variables are set
    required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'PINECONE_ENVIRONMENT']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running this script.")
        sys.exit(1)
    
    try:
        asyncio.run(run_demo())
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
