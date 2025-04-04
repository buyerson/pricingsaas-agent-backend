"""
Profile Agent - A specialized agent for answering questions about user profiles.
"""

import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any

from pydantic import BaseModel
from agents import (
    Agent, 
    RunContextWrapper, 
    Runner, 
    function_tool, 
    trace, 
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    TResponseInputItem,
    input_guardrail
)

@dataclass
class UserInfo:
    """User profile information."""
    name: str = ""
    email: str = ""
    company: str = ""
    title: str = ""

class ValidationOutput(BaseModel):
    """Output model for the sensitive information guardrail check."""
    is_valid: bool
    reasoning: str

@function_tool
async def fetch_user_info(wrapper: RunContextWrapper[UserInfo]) -> str:
    """
    Fetches user information and populates the context with dummy data.
    
    Returns:
        A message confirming the user information has been fetched along with the user details.
    """
    # Populate the context with dummy data
    wrapper.context.name = "John Doe"
    wrapper.context.email = "john.doe@example.com"
    wrapper.context.company = "Acme Corporation"
    wrapper.context.title = "Product Manager"
    
    return f"""User information has been successfully fetched:
- Name: {wrapper.context.name}
- Email: {wrapper.context.email}
- Company: {wrapper.context.company}
- Title: {wrapper.context.title}"""

@function_tool
async def validate_user_info(wrapper: RunContextWrapper[UserInfo]) -> str:
    """
    Validates that user information fields are not empty.
    
    Returns:
        A message indicating whether the user information is valid or not.
    """

    fetch_user_info(wrapper)

    # Check if any of the fields are empty
    empty_fields = []
    
    if not wrapper.context.name:
        empty_fields.append("name")
    if not wrapper.context.email:
        empty_fields.append("email")
    if not wrapper.context.company:
        empty_fields.append("company")
    if not wrapper.context.title:
        empty_fields.append("title")
    
    if empty_fields:
        return f"User information is incomplete. Missing fields: {', '.join(empty_fields)}"
    else:
        return "User information is complete and valid."

@function_tool
async def update_profile(wrapper: RunContextWrapper[UserInfo], name: str = None, email: str = None, 
                         company: str = None, title: str = None) -> str:
    """
    Updates the user profile information in the context.
    
    Args:
        name: New name for the user profile (optional)
        email: New email for the user profile (optional)
        company: New company for the user profile (optional)
        title: New title for the user profile (optional)
        
    Returns:
        A message confirming which fields were updated.
    """
    updated_fields = []
    
    if name is not None:
        wrapper.context.name = name
        updated_fields.append("name")
        
    if email is not None:
        wrapper.context.email = email
        updated_fields.append("email")
        
    if company is not None:
        wrapper.context.company = company
        updated_fields.append("company")
        
    if title is not None:
        wrapper.context.title = title
        updated_fields.append("title")
    
    if not updated_fields:
        return "No profile information was updated."
    
    return f"""Profile information updated:
- Updated fields: {', '.join(updated_fields)}
- Current profile:
  - Name: {wrapper.context.name}
  - Email: {wrapper.context.email}
  - Company: {wrapper.context.company}
  - Title: {wrapper.context.title}"""
 

# Create a guardrail agent to check for sensitive information requests
profile_guardrail_agent = Agent(
    name="Sensitive Information Guardrail",
    instructions="""
    You are a guardrail agent that checks if a user request is for something outside the scope of the profile agent.
    
    This agent can fetch user profile information, validate it or update it. Anything outide of this, should be rejected.
    For example, asking 2+2 should be rejected as it has nothing to do with updating or fetching profile info.
    """,
    output_type=ValidationOutput,
)

@input_guardrail
async def profile_info_guardrail(
    ctx: RunContextWrapper[UserInfo], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    """
    Guardrail that checks if the user is request is valid for this agent.
    """
    result = await Runner.run(profile_guardrail_agent, input, context=ctx.context)
    
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_valid,

    )

async def main():
    """Main function to run the Profile Agent interactively."""
    # Initialize with empty user info
    user_info = UserInfo()

    # with trace("Profiles"): 
        # Create the agent with the appropriate tools
    profile_agent = Agent[UserInfo](
        name="Profile Assistant",
        instructions="""
        You are a Profile Assistant that helps answer questions about current user profiles.
        
        # Routine
        1. When asked about user information, first validate if the information is available using the validate_user_info tool.
        2. If information is missing, fetch it using the fetch_user_info tool.
        3. After fetching, validate again to ensure all information is available.
        4. Only answer questions about the user profile if all information is valid.
        5. You can update user profile information using the update_profile tool when requested.
            
        Always validate before answering questions about the user profile.
        """,
        tools=[validate_user_info, fetch_user_info, update_profile],
        input_guardrails=[profile_info_guardrail],
    ) 

    # Example 2: Sensitive information request (should trigger guardrail)
    try:
        result = await Runner.run(
            starting_agent=profile_agent,
            input="What is the name?",
            context=user_info,
        )
        print("Sensitive request result (shouldn't reach here):")
        print(result.final_output)
    except InputGuardrailTripwireTriggered as e:
        print("Guardrail triggered as expected for sensitive request")
        # print(f"Reason: {e.output_info.reasoning}")
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
