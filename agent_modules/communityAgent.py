"""
Community Pricing Agent - A specialized agent for answering pricing questions
using community knowledge from Discourse forums.
"""

from __future__ import annotations as _annotations

import os
import json
import asyncio
import uuid
from typing import List, Dict, Any

from pydantic import BaseModel

# Import from the openai-agents package, not our local agents directory
from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

# Import helper functions
from helpers.community_helpers import (
    process_pinecone_results,
    format_search_results,
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE
)

# Initialize Pinecone client if API key is available
pc = None
index = None

if PINECONE_API_KEY:
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(PINECONE_INDEX_NAME)
        print(f"Successfully connected to Pinecone index: {PINECONE_INDEX_NAME}")
    except Exception as e:
        print(f"Error connecting to Pinecone: {e}")
        print("Community knowledge search will not be available.")


### CONTEXT

class PricingAgentContext(BaseModel):
    """Context for the Pricing Agent, storing query, search results, and annotations."""
    query: str | None = None
    last_search_results: Dict[str, Any] | None = None
    full_topics: Dict[str, Any] = {}
    annotations: List[Dict[str, Any]] = []


### TOOLS

@function_tool(
    name_override="community_knowledge_search", 
    description_override="Search the community knowledge base for information about pricing topics."
)
async def community_knowledge_search(
    context: RunContextWrapper[PricingAgentContext], 
    query: str
) -> str:
    """
    Search the community knowledge base for information about pricing topics.
    
    Args:
        query: The pricing question or topic to search for in the community knowledge base.
    """
    # Store the query in context
    context.context.query = query
    
    # Reset previous results
    context.context.full_topics = {}
    context.context.annotations = []
    
    # Check if required clients are initialized
    if not OPENAI_API_KEY:
        return "Error: OpenAI API key is not set or client initialization failed. Please set the OPENAI_API_KEY environment variable."
            
    if not pc or not index:
        return "Error: Pinecone client is not initialized or connection failed. Please set the PINECONE_API_KEY environment variable and ensure the index exists."
    
    print(f"Processing query: '{query}'")
    print("Optimizing query for embedding-based search...")
    
    # Process search results with query optimization and limited to top 5 matches
    results = await process_pinecone_results(index, query, context.context)
    
    # Store the results in context for future reference
    context.context.last_search_results = results
    
    # Format the results as a readable string
    formatted_results = format_search_results(results, context.context)
    
    return formatted_results


### AGENTS

community_pricing_agent = Agent[PricingAgentContext](
    name="Community Pricing Agent",
    handoff_description="A helpful agent that can answer pricing questions by querying community knowledge.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a SaaS pricing expert. You help users with pricing questions by searching through community knowledge.
    
    # Routine
    1. When a user asks a pricing question, use the community_knowledge_search tool to find relevant information.
    2. The search will optimize the query using AI to get the best possible matches from the vector database.
    3. The search will only return the top 5 high-confidence matches (80% or higher) and will fetch full topic data from Discourse.
    4. Analyze the search results and provide a comprehensive answer based on the community knowledge.
    5. For each unique topic referenced in your answer, include an annotation with [Topic X] where X is the topic number.
    6. Your response should be a single, coherent answer that synthesizes information from all relevant topics.
    7. If the search doesn't return relevant results, acknowledge the limitations and provide general pricing advice based on your knowledge.
    8. Focus on practical, actionable advice about SaaS pricing strategies, models, and best practices.
    
    # Working with Full Topic Data
    - The search tool now uses AI to optimize queries for better embedding-based search results
    - The search is limited to the top 5 most relevant matches to ensure high quality results
    - The tool fetches complete conversations for each relevant topic
    - Use this detailed information to provide more accurate and comprehensive answers
    - When referencing information from a specific topic, use the annotation format [Topic X] where X corresponds to the topic number
    - Make sure to integrate insights from all relevant topics into a cohesive response
    
    Remember that you are a pricing expert, so frame your responses in a professional, knowledgeable manner.
    """,
    tools=[community_knowledge_search],
)


### RUN

async def main():
    """Main function to run the Community Pricing Agent interactively."""
    current_agent = community_pricing_agent
    input_items: list[TResponseInputItem] = []
    context = PricingAgentContext()

    # Use a random UUID for the conversation ID
    conversation_id = uuid.uuid4().hex[:16]

    print("\nCommunity Pricing Agent")
    print("======================")
    print("Ask questions about SaaS pricing strategies, models, and best practices.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("Enter your pricing question: ")
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
            
        with trace("Pricing consultation", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items, context=context)

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    message_text = ItemHelpers.text_message_output(new_item)
                    print(f"{agent_name}: {message_text}")
                    
                    # If we have annotations, display them after the message
                    if context.annotations:
                        print("\nReferences:")
                        for i, annotation in enumerate(context.annotations, 1):
                            print(f"[{i}] {annotation['title']} - {annotation['url']}")
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Searching community knowledge...")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Found relevant information.")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())
