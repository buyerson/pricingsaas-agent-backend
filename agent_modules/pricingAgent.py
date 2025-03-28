"""
Pricing Agent - A specialized agent that combines results from both the Community Agent
and Reports Agent to provide comprehensive pricing answers.
"""

import json
import asyncio
import uuid
from typing import List, Dict, Any, Optional

from pydantic import BaseModel

# Import from the openai-agents package
from agents import (
    Agent,
    ItemHelpers,
    MessageOutputItem,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    trace,
)

# Import the community and reports agents
from agent_modules.communityAgent import community_pricing_agent, PricingAgentContext as CommunityAgentContext
from agent_modules.reportsAgent import create_reports_agent, stream_reports_agent_response


class PricingAgentContext(BaseModel):
    """Context for the Pricing Agent, storing query and combined results from both agents."""
    query: str | None = None
    community_annotations: List[Dict[str, Any]] = []
    reports_annotations: List[Dict[str, Any]] = []
    combined_annotations: List[Dict[str, Any]] = []


# ===== Helper Functions =====

async def run_community_agent(query: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Run the community agent and return its response and annotations.
    
    Args:
        query: The user's pricing question
        
    Returns:
        A tuple of (response_text, annotations)
    """
    try:
        print("Running community agent...")
        community_context = CommunityAgentContext()
        community_result = await Runner.run(
            community_pricing_agent,
            [{"content": query, "role": "user"}],
            context=community_context
        )
        
        # Extract the text response from the community agent
        community_response = ItemHelpers.text_message_outputs(community_result.new_items)
        
        # Extract annotations from community agent
        community_annotations = []
        if hasattr(community_context, 'annotations') and isinstance(community_context.annotations, list):
            community_annotations = community_context.annotations.copy()
            
        return community_response, community_annotations
        
    except Exception as e:
        print(f"Error running community agent: {e}")
        import traceback
        traceback.print_exc()
        return "Error retrieving community knowledge.", []


async def run_reports_agent(query: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Run the reports agent and return its response and annotations.
    
    Args:
        query: The user's pricing question
        
    Returns:
        A tuple of (response_text, annotations)
    """
    try:
        print("Running reports agent...")
        reports_result = await Runner.run(
            create_reports_agent(),
            query
        )
        
        # Extract the text response from the reports agent
        reports_response = ItemHelpers.text_message_outputs(reports_result.new_items)
        
        # Collect annotations from the reports agent
        reports_annotations = []
        
        # Try to extract annotations directly from the result items
        for item in reports_result.new_items:
            # Check if the item has annotations attribute
            if hasattr(item, 'annotations'):
                for annotation in item.annotations:
                    reports_annotations.append(annotation)
            
            # Check if it's a ToolCallOutputItem which might contain annotations
            if isinstance(item, ToolCallOutputItem):
                if hasattr(item, 'output') and isinstance(item.output, dict) and 'annotations' in item.output:
                    for annotation in item.output['annotations']:
                        reports_annotations.append(annotation)
        
        # If we didn't find any annotations, try the streaming approach as a fallback
        if not reports_annotations:
            try:
                print("Trying streaming approach for annotations...")
                async for event in stream_reports_agent_response(query):
                    if event["type"] == "annotation":
                        annotation_dict = {
                            "type": getattr(event["data"], "type", "file_citation"),
                            "file_citation": {
                                "file_id": getattr(event["data"], "file_id", ""),
                                "title": getattr(event["data"], "filename", "")
                            }
                        }
                        reports_annotations.append(annotation_dict)
            except Exception as e:
                print(f"Error collecting reports annotations via streaming: {e}")
        
        return reports_response, reports_annotations
        
    except Exception as e:
        print(f"Error running reports agent: {e}")
        import traceback
        traceback.print_exc()
        return "Error retrieving reports knowledge.", []


def combine_annotations(community_annotations: List[Dict[str, Any]], 
                       reports_annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Combine annotations from both sources with appropriate prefixes.
    
    Args:
        community_annotations: Annotations from the community agent
        reports_annotations: Annotations from the reports agent
        
    Returns:
        Combined list of annotations with source prefixes
    """
    combined_annotations = []
    
    # Add community annotations with a prefix
    for annotation in community_annotations:
        if isinstance(annotation, dict):
            annotation_with_prefix = annotation.copy()
            if 'title' in annotation_with_prefix:
                annotation_with_prefix['title'] = f"[Community] {annotation_with_prefix['title']}"
            combined_annotations.append(annotation_with_prefix)
    
    # Add reports annotations with a prefix
    for annotation in reports_annotations:
        if isinstance(annotation, dict):
            annotation_with_prefix = annotation.copy()
            if 'file_citation' in annotation_with_prefix and isinstance(annotation_with_prefix['file_citation'], dict):
                if 'title' in annotation_with_prefix['file_citation']:
                    annotation_with_prefix['file_citation']['title'] = f"[Report] {annotation_with_prefix['file_citation']['title']}"
            combined_annotations.append(annotation_with_prefix)
    
    return combined_annotations


def create_fallback_response(query: str) -> str:
    """
    Create a fallback response when both agents fail.
    
    Args:
        query: The user's pricing question
        
    Returns:
        A fallback response
    """
    return f"""
# Query
{query}

# Fallback Response
I apologize, but I'm currently experiencing difficulties accessing both the community knowledge and reports databases. 
However, I can still provide some general guidance on your question about {query} based on my training.

Please note that this response is not based on the specialized knowledge from our community or reports, 
but rather on general principles of SaaS pricing.

Would you like me to provide this general guidance, or would you prefer to try your question again later 
when the knowledge sources are available?
"""


def create_combined_input(query: str, community_response: str, reports_response: str, 
                         combined_annotations: List[Dict[str, Any]]) -> str:
    """
    Create a combined input for the pricing agent.
    
    Args:
        query: The user's pricing question
        community_response: Response from the community agent
        reports_response: Response from the reports agent
        combined_annotations: Combined annotations from both sources
        
    Returns:
        A formatted input for the pricing agent
    """
    return f"""
# Query
{query}

# Community Agent Response
{community_response}

# Reports Agent Response
{reports_response}

# Annotations
{json.dumps(combined_annotations, indent=2)}

Please synthesize these responses into a single, coherent answer that combines insights from both sources.
Include all relevant citations and references from both sources.
"""


# ===== Main Function Tool =====

@function_tool("combine_agent_responses")
async def combine_agent_responses(query: str) -> str:
    """
    Run both the community agent and reports agent and combine their results.
    
    Args:
        query: The user's pricing question
        
    Returns:
        A combined response from both agents
    """
    print(f"Processing query: {query}")
    
    # Run both agents to get responses and annotations
    community_response, community_annotations = await run_community_agent(query)
    reports_response, reports_annotations = await run_reports_agent(query)
    
    # Combine annotations from both sources
    combined_annotations = combine_annotations(community_annotations, reports_annotations)
    
    # Check if we got meaningful responses from either agent
    community_has_content = len(community_response) > 50 and "Error retrieving" not in community_response
    reports_has_content = len(reports_response) > 50 and "Error retrieving" not in reports_response
    
    # If both agents failed, return a fallback response
    if not community_has_content and not reports_has_content:
        print("Both agents failed to provide meaningful content. Using fallback response.")
        return create_fallback_response(query)
    
    # Create a combined input for the pricing agent
    return create_combined_input(query, community_response, reports_response, combined_annotations)


# ===== Pricing Agent Definition =====

pricing_agent = Agent(
    name="Pricing Agent",
    instructions="""You are a comprehensive SaaS pricing expert. Your role is to combine insights from community knowledge and expert reports to provide the most complete answers to pricing questions.

    # Routine
    1. When a user asks a pricing question, you'll receive answers from two sources:
       - Community knowledge from Discourse forums
       - Expert reports and documents
    2. Your job is to synthesize these sources into a single, coherent response.
    3. Highlight areas of agreement between the sources.
    4. Note any differences or complementary information.
    5. Include all relevant citations from both sources.
    6. Focus on practical, actionable advice about SaaS pricing strategies, models, and best practices.
    
    # Working with Multiple Sources
    - Community knowledge provides real-world experiences and practical implementations
    - Expert reports provide research-backed strategies and industry best practices
    - When sources disagree, present both perspectives and explain the context
    
    Remember that you are a pricing expert, so frame your responses in a professional, knowledgeable manner.
    """,
    tools=[combine_agent_responses],
)


# ===== Interactive CLI =====

async def main():
    """Main function to run the Pricing Agent interactively."""
    input_items: list[TResponseInputItem] = []

    # Use a random UUID for the conversation ID
    conversation_id = uuid.uuid4().hex[:16]

    print("\nPricing Agent")
    print("=============")
    print("Ask questions about SaaS pricing strategies, models, and best practices.")
    print("This agent combines knowledge from community forums and expert reports.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("Enter your pricing question: ")
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
            
        with trace("Combined pricing consultation", group_id=conversation_id):
            print("\nProcessing your question with both community and reports knowledge...\n")
            
            input_items.append({"content": user_input, "role": "user"})
            
            try:
                result = await Runner.run(pricing_agent, input_items)
                
                for item in result.new_items:
                    agent_name = item.agent.name
                    
                    if isinstance(item, MessageOutputItem):
                        message_text = ItemHelpers.text_message_output(item)
                        print(f"{agent_name}: {message_text}")
                    elif isinstance(item, ToolCallItem):
                        print(f"{agent_name}: Gathering information from community and reports...")
                    elif isinstance(item, ToolCallOutputItem):
                        print(f"{agent_name}: Found relevant information from both sources.")
                
                input_items = result.to_input_list()
                
            except Exception as e:
                print(f"Error running pricing agent: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
