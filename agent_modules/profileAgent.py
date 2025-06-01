"""
Profile Agent - A specialized agent for answering questions about user profiles.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# We import supabase_client dynamically in fetch_profile_from_db function

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
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    company: str = ""
    title: str = ""
    display_name: str = ""  # Adding display_name field
    user_id: str = ""
    _profile_loaded: bool = False  # Track if profile has been loaded from DB
    
    def __post_init__(self):
        """Ensure all fields are initialized to empty strings if None."""
        self.first_name = self.first_name or ""
        self.last_name = self.last_name or ""
        self.email = self.email or ""
        self.company = self.company or ""
        self.title = self.title or ""
        self.display_name = self.display_name or ""
        self.user_id = self.user_id or ""

class ValidationOutput(BaseModel):
    """Output model for the sensitive information guardrail check."""
    is_valid: bool
    reasoning: str

def fetch_profile_from_db(user_id: str) -> Optional[Dict]:
    """
    Fetches user profile from the database.
    
    Args:
        user_id: The ID of the user to fetch
        
    Returns:
        Dictionary with profile data or None if not found
    """
    try:
        # Import supabase_client only when needed
        # This avoids module import issues when running the file directly
        from importlib import import_module
        import sys, os
        # Get the parent directory path
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Add parent directory to path temporarily if not already there
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            # Import the module
            supabase_client = import_module('supabase_client')
            # Remove the path after import to avoid polluting sys.path
            sys.path.remove(parent_dir)
        else:
            # Import the module if parent_dir is already in sys.path
            supabase_client = import_module('supabase_client')
        
        # Get supabase client and fetch profile
        supabase = supabase_client.get_supabase_client()
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching profile from DB: {e}")
        return None

def load_profile_to_context(user_info: UserInfo, user_id: str = "e03ea766-9ca0-4e60-8299-0ba759318384") -> None:
    """
    Loads user profile from database into the UserInfo context object.
    
    Args:
        user_info: The UserInfo object to update with profile data
        user_id: The ID of the user to fetch (defaults to mock ID)
    """
    if user_info._profile_loaded:
        return  # Skip if profile already loaded
        
    # Save user_id to context
    user_info.user_id = user_id
    
    # Fetch profile data
    profile_data = fetch_profile_from_db(user_id)
    
    if profile_data:
        # Update context with profile data
        user_info.first_name = profile_data.get('first_name', '')
        user_info.last_name = profile_data.get('last_name', '')
        user_info.email = profile_data.get('email', '')
        user_info.company = profile_data.get('company', '')
        user_info.title = profile_data.get('title', '')
        user_info.display_name = profile_data.get('display_name', '')
        user_info._profile_loaded = True

@function_tool
async def fetch_user_info(wrapper: RunContextWrapper[UserInfo]) -> str:
    """
    Fetches user information from the context.
    
    Returns:
        A message confirming the user information has been fetched along with the user details.
    """
    try:
        # The profile should already be loaded before the agent runs
        # Get data from context
        first_name = wrapper.context.first_name or "Not provided"
        last_name = wrapper.context.last_name or "Not provided"
        full_name = f"{first_name} {last_name}".strip()
        if full_name == "Not provided Not provided":
            full_name = "Not provided"
            
        email = wrapper.context.email or "Not provided"
        company = wrapper.context.company or "Not provided"
        title = wrapper.context.title or "Not provided"
        
        return f"""User information has been successfully fetched:
- Name: {full_name}
- Email: {email}
- Company: {company}
- Title: {title}"""
    except Exception as e:
        # Handle any errors gracefully
        return f"Could not fetch user information. Error: {str(e)}"

@function_tool
async def validate_user_info(wrapper: RunContextWrapper[UserInfo]) -> str:
    """
    Validates that user information fields are not empty.
    
    Returns:
        A message indicating whether the user information is valid or not.
    """
    try:
        # Don't call fetch_user_info here as it might cause issues
        # Just validate what we already have
        
        # Check if any of the fields are empty
        empty_fields = []
        
        if not wrapper.context.first_name:
            empty_fields.append("first_name")
        if not wrapper.context.last_name:
            empty_fields.append("last_name")
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
    except Exception as e:
        # Handle any errors gracefully
        first_name = wrapper.context.first_name or 'Not provided'
        last_name = wrapper.context.last_name or 'Not provided'
        return f"Could not validate user information. Current profile state: First Name: '{first_name}', Last Name: '{last_name}', Email: '{wrapper.context.email or 'Not provided'}', Company: '{wrapper.context.company or 'Not provided'}', Title: '{wrapper.context.title or 'Not provided'}'."

@function_tool
async def update_profile(wrapper: RunContextWrapper[UserInfo], first_name: str = None, last_name: str = None, 
                         email: str = None, company: str = None, title: str = None) -> str:
    """
    Updates the user profile information in the context.
    
    Args:
        first_name: New first name for the user profile (optional)
        last_name: New last name for the user profile (optional)
        email: New email for the user profile (optional)
        company: New company for the user profile (optional)
        title: New title for the user profile (optional)
        
    Returns:
        A message confirming which fields were updated.
    """
    try:
        updated_fields = []
        
        if first_name is not None:
            wrapper.context.first_name = first_name
            updated_fields.append("first_name")
            
        if last_name is not None:
            wrapper.context.last_name = last_name
            updated_fields.append("last_name")
            
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
        
        # Get current values, handling None values
        current_first_name = wrapper.context.first_name or "Not provided"
        current_last_name = wrapper.context.last_name or "Not provided"
        full_name = f"{current_first_name} {current_last_name}".strip()
        if full_name == "Not provided Not provided":
            full_name = "Not provided"
            
        current_email = wrapper.context.email or "Not provided"
        current_company = wrapper.context.company or "Not provided"
        current_title = wrapper.context.title or "Not provided"
        
        return f"""Profile information updated:
- Updated fields: {', '.join(updated_fields)}
- Current profile:
  - Name: {full_name}
  - Email: {current_email}
  - Company: {current_company}
  - Title: {current_title}"""
    except Exception as e:
        # Handle any errors gracefully
        return f"There was an issue updating the profile. Please try again with specific field values."
 

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
    # Initialize with user ID
    user_id = "e03ea766-9ca0-4e60-8299-0ba759318384"  # Mock user ID
    user_info = UserInfo(user_id=user_id)
    
    # Pre-load profile data before running the agent
    print(f"Pre-loading profile for user ID: {user_id}...")
    load_profile_to_context(user_info)
    
    if user_info._profile_loaded:
        print(f"Loaded profile: {user_info.first_name} {user_info.last_name}, {user_info.email}")
    else:
        print("No profile found in database, proceeding with empty user info")

    # with trace("Profiles"): 
        # Create the agent with the appropriate tools
    # Create a dynamic instructions function that includes user information
    def get_instructions(context: UserInfo) -> str:
        name = f"{context.first_name} {context.last_name}".strip() or "User"
        return f"""
        You are a Profile Assistant that helps answer questions about {name}'s profile.
        
        # Routine
        1. When asked about user information, first validate if the information is available using the validate_user_info tool.
        2. If information is missing, fetch it using the fetch_user_info tool.
        3. After fetching, validate again to ensure all information is available.
        4. Only answer questions about the user profile if all information is valid.
        5. You can update user profile information using the update_profile tool when requested.
            
        Always validate before answering questions about the user profile.
        
        # IMPORTANT
        The user profile has already been loaded from the database before you were started.
        """
    
    profile_agent = Agent[UserInfo](
        name="Profile Assistant",
        instructions=get_instructions(user_info),  # Use dynamic instructions with user context
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
