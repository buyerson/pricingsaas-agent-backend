"""
Triage Agent - A specialized agent for validating and completing user profiles.

This agent works with the profileAgent to ensure all required profile information
is collected from the user. It prompts for missing information one attribute at a time
and streams responses to provide a better user experience.
"""

import asyncio
import uuid
import time
from typing import List, Dict, Any, Optional

try:
    from openai.types.responses import ResponseContentPartDoneEvent, ResponseTextDeltaEvent
    from agents import (
        Agent, 
        Runner, 
        RawResponsesStreamEvent, 
        TResponseInputItem, 
        trace,
        RunContextWrapper
    )

    # Import from profileAgent with proper module path
    from agent_modules.profileAgent import (
        UserInfo,
        validate_user_info,
        update_profile,
        fetch_user_info,
        load_profile_to_context  # Import the new profile loading function
    )
    IMPORTS_SUCCESSFUL = True
    
    # Function to create dynamic instructions that include user info if available
    def get_triage_instructions(context: Optional[UserInfo] = None) -> str:
        # Default instructions
        base_instructions = """
        You are a Profile Triage Assistant that helps users complete their profiles.
        
        # Routine
        1. First, validate if the user profile is complete using the validate_user_info tool.
        2. If the profile is incomplete, ask the user for ONE missing attribute at a time.
        3. Update the profile with the provided information using the update_profile tool.
        4. After each update, validate again to check if the profile is now complete.
        5. Continue this process until all required information is collected.
        6. Once the profile is complete, inform the user that their profile is now complete.
        
        # Guidelines
        - Be friendly and conversational when asking for information.
        - Ask for only one piece of information at a time.
        - After receiving information, acknowledge it and update the profile.
        - If the user provides multiple pieces of information at once, update all relevant fields.
        - Always validate the profile after each update to track progress.
        
        # Required Profile Fields
        - First Name
        - Last Name
        - Email
        - Company
        - Title
        
        Always use the tools provided to interact with the user profile data.
        """
        
        # If we have context with profile data, personalize the instructions
        if context and hasattr(context, '_profile_loaded') and context._profile_loaded:
            name = f"{context.first_name} {context.last_name}".strip()
            if name:
                base_instructions = f"""
        You are a Profile Triage Assistant that helps {name} complete their profile.
        """ + base_instructions
                
        return base_instructions
    
    # Create the triage agent that will handle profile completion
    triage_agent = Agent[UserInfo](
        name="Profile Triage Assistant",
        instructions=get_triage_instructions(),
        tools=[validate_user_info, fetch_user_info, update_profile, load_profile_to_context],
    )

    # Create a profile agent for validation only
    profile_validator = Agent[UserInfo](
        name="Profile Validator",
        instructions="""
        You are a Profile Validator that checks if a user profile is complete.
        
        # Routine
        1. Use the validate_user_info tool to check if the profile is complete.
        2. Report which fields are missing, if any.
        3. Do not ask the user for information - just validate what's already there.
        
        Only use the validate_user_info tool.
        """,
        tools=[validate_user_info],
    )
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required packages are installed.")
    print("You can install them with: pip install -r requirements.txt")
    IMPORTS_SUCCESSFUL = False
    # Define placeholder variables to avoid NameError
    triage_agent = None
    profile_validator = None

if IMPORTS_SUCCESSFUL:
    async def stream_agent_response(agent: Agent, inputs: list[TResponseInputItem], context: UserInfo):
        """
        Stream responses from an agent.
        
        Args:
            agent: The agent to run
            inputs: The input messages
            context: The user info context
            
        Yields:
            Events containing text deltas, annotations, or completion signals
        Returns:
            None
        """
        # Run the agent with streaming
        result = Runner.run_streamed(
            agent,
            input=inputs,
            context=context
        )
        
        # Stream the events to the user
        async for event in result.stream_events():
            if not isinstance(event, RawResponsesStreamEvent):
                continue
            
            data = event.data
            if isinstance(data, ResponseTextDeltaEvent):
                # Yield text deltas for streaming
                yield {"type": "text_delta", "data": data.delta}
            elif isinstance(data, ResponseContentPartDoneEvent):
                # Part is done, yield a completion event
                yield {"type": "completion", "data": None}
        
        # Note: We can't return a value from an async generator function
        # The result will need to be obtained separately if needed

    async def run_triage_agent_session():
        """
        Run a complete triage agent session that handles the conversation flow.
        This function demonstrates how to use the triage agent in a real application.
        """
        # We'll create an ID for this conversation, so we can link each trace
        conversation_id = str(uuid.uuid4().hex[:16])
        
        # Initialize with empty user info
        user_info = UserInfo()
        
        print("Welcome to the Profile Triage Assistant!")
        msg = input("How can I help you with your profile today? ")
        
        # Start with the triage agent
        agent = triage_agent
        inputs: list[TResponseInputItem] = [{"content": msg, "role": "user"}]
        
        # Continue the conversation until the profile is complete
        while True:
            try:
                # Each conversation turn is a single trace
                with trace("Profile Triage", group_id=conversation_id):
                    # Run the agent with streaming
                    print("Processing your request...", flush=True)
                    try:
                        result = Runner.run_streamed(
                            agent,
                            input=inputs,
                            context=user_info
                        )
                        
                        # Process and display the streaming events
                        async for event in result.stream_events():
                            if not isinstance(event, RawResponsesStreamEvent):
                                continue
                            
                            data = event.data
                            if isinstance(data, ResponseTextDeltaEvent):
                                print(data.delta, end="", flush=True)
                            elif isinstance(data, ResponseContentPartDoneEvent):
                                print("\n")
                    except Exception as e:
                        print(f"\nError during agent response: {str(e)}")
                        print("Let me try a different approach...")
                        # Create a simple response if the agent fails
                        print("I'm having trouble processing your request through the normal channels.")
                        print("Let me help you directly with your profile information.")
                        print(f"Current profile state:")
                        print(f"- Name: {user_info.name or 'Not provided'}")
                        print(f"- Email: {user_info.email or 'Not provided'}")
                        print(f"- Company: {user_info.company or 'Not provided'}")
                        print(f"- Title: {user_info.title or 'Not provided'}")
                        print("What would you like to update?")
                        
                        # Create a basic result for the next turn
                        class SimpleResult:
                            def __init__(self):
                                self.current_agent = agent
                                self.inputs = inputs
                            
                            def to_input_list(self):
                                return self.inputs
                        
                        result = SimpleResult()
                    
                    # Check if the profile is now complete
                    try:
                        validation_result = await Runner.run(
                            profile_validator,
                            "Is my profile complete?",
                            context=user_info
                        )
                        
                        # If the profile is complete, break the loop
                        if hasattr(validation_result, 'final_output') and "complete and valid" in validation_result.final_output:
                            print("\nYour profile is now complete! Thank you for providing all the required information.")
                            print("\nFinal profile:")
                            print(f"- Name: {user_info.name or 'Not provided'}")
                            print(f"- Email: {user_info.email or 'Not provided'}")
                            print(f"- Company: {user_info.company or 'Not provided'}")
                            print(f"- Title: {user_info.title or 'Not provided'}")
                            break
                    except Exception as e:
                        print(f"\nError checking profile completeness: {str(e)}")
                        print("Let's continue with the conversation.")
                    
                    # Prepare for the next turn
                    if hasattr(result, 'to_input_list'):
                        inputs = result.to_input_list()
                    print("\n")
                    user_msg = input("Enter your response: ")
                    
                    # Check if the user wants to exit
                    if user_msg.lower() == 'exit':
                        print("Thank you for using the Profile Triage Assistant. Goodbye!")
                        break
                    
                    # Process the user's input to update the profile directly
                    if "name" in user_msg.lower() and "is" in user_msg.lower():
                        name_parts = user_msg.lower().split("is")
                        if len(name_parts) > 1:
                            user_info.name = name_parts[1].strip()
                            print(f"Updated name to: {user_info.name}")
                    
                    if "email" in user_msg.lower() and "is" in user_msg.lower():
                        email_parts = user_msg.lower().split("is")
                        if len(email_parts) > 1:
                            user_info.email = email_parts[1].strip()
                            print(f"Updated email to: {user_info.email}")
                    
                    if "company" in user_msg.lower() and "is" in user_msg.lower():
                        company_parts = user_msg.lower().split("is")
                        if len(company_parts) > 1:
                            user_info.company = company_parts[1].strip()
                            print(f"Updated company to: {user_info.company}")
                    
                    if "title" in user_msg.lower() and "is" in user_msg.lower():
                        title_parts = user_msg.lower().split("is")
                        if len(title_parts) > 1:
                            user_info.title = title_parts[1].strip()
                            print(f"Updated title to: {user_info.title}")
                    
                    inputs.append({"content": user_msg, "role": "user"})
                    if hasattr(result, 'current_agent'):
                        agent = result.current_agent
            except Exception as e:
                print(f"\nAn unexpected error occurred: {str(e)}")
                print("Let's try again with a different approach.")
                
                # Ask the user if they want to continue
                continue_response = input("Would you like to continue? (yes/no): ")
                if continue_response.lower() != 'yes':
                    print("Thank you for using the Profile Triage Assistant. Goodbye!")
                    break

    async def run_triage_agent(user_info: UserInfo, initial_message: str):
        """
        Run the triage agent to complete a user profile, streaming responses.
        
        Args:
            user_info: The current user profile information
            initial_message: The initial message from the user
            
        Yields:
            Events containing text deltas or completion signals
        """
        # Create a unique ID for this conversation
        conversation_id = str(uuid.uuid4().hex[:16])
        
        # Pre-load profile data if not already loaded
        if not hasattr(user_info, '_profile_loaded') or not user_info._profile_loaded:
            # If user_id is not set, use the mock ID
            user_id = getattr(user_info, 'user_id', None) or "e03ea766-9ca0-4e60-8299-0ba759318384"
            load_profile_to_context(user_info, user_id)
            yield {"type": "text_delta", "data": "📋 Loading your profile data...\n\n"}

        # Initialize the input list with the user's initial message
        inputs: list[TResponseInputItem] = [{"content": initial_message, "role": "user"}]
        
        # Start with the triage agent - use dynamic instructions with the loaded profile
        if hasattr(user_info, '_profile_loaded') and user_info._profile_loaded:
            # Create the agent with personalized instructions based on profile data
            agent = Agent[UserInfo](
                name="Profile Triage Assistant",
                instructions=get_triage_instructions(user_info),
                tools=[validate_user_info, fetch_user_info, update_profile],
            )
        else:
            # Use the default agent if profile not loaded
            agent = triage_agent
        
        # Continue the conversation until the profile is complete
        with trace("Profile Triage", group_id=conversation_id):
            # First, yield a status message
            yield {"type": "text_delta", "data": "🔍 Checking your profile...\n\n"}
            
            # Run the agent with streaming
            result = Runner.run_streamed(
                agent,
                input=inputs,
                context=user_info
            )
            
            # Stream the events to the user
            async for event in result.stream_events():
                if not isinstance(event, RawResponsesStreamEvent):
                    continue
                
                data = event.data
                if isinstance(data, ResponseTextDeltaEvent):
                    # Yield text deltas for streaming
                    yield {"type": "text_delta", "data": data.delta}
                elif isinstance(data, ResponseContentPartDoneEvent):
                    # Part is done, yield a newline
                    yield {"type": "text_delta", "data": "\n"}
            
            # Check if the profile is now complete
            try:
                validation_result = await Runner.run(
                    profile_validator,
                    "Is my profile complete?",
                    context=user_info
                )
                
                # If the profile is complete, send a completion message
                if validation_result and hasattr(validation_result, 'final_output') and "complete and valid" in validation_result.final_output:
                    yield {"type": "text_delta", "data": "\n\n✅ Your profile is now complete! Thank you for providing all the required information.\n"}
            except Exception as e:
                # Handle validation errors gracefully
                yield {"type": "text_delta", "data": f"\n\n⚠️ There was an issue checking your profile completeness. Let's continue with the conversation.\n"}
            
            # Send completion event
            yield {"type": "completion", "data": None}
else:
    # Define placeholder functions when imports fail
    async def stream_agent_response(*args, **kwargs):
        """Placeholder function when imports fail."""
        yield {"type": "text_delta", "data": "Error: Required dependencies not available."}
        yield {"type": "completion", "data": None}
    
    async def run_triage_agent_session():
        """Placeholder function when imports fail."""
        print("Error: Required dependencies not available.")
        print("Please install the required packages with: pip install -r requirements.txt")
    
    async def run_triage_agent(*args, **kwargs):
        """Placeholder function when imports fail."""
        yield {"type": "text_delta", "data": "Error: Required dependencies not available."}
        yield {"type": "completion", "data": None}

async def main():
    """Main function to run the Triage Agent interactively."""
    if IMPORTS_SUCCESSFUL:
        # Initialize with user ID and pre-load profile
        user_id = "e03ea766-9ca0-4e60-8299-0ba759318384"  # Mock user ID
        user_info = UserInfo(user_id=user_id)
        
        # Pre-load profile data before running the agent
        print(f"Pre-loading profile for user ID: {user_id}...")
        load_profile_to_context(user_info, user_id)
        
        if user_info._profile_loaded:
            print(f"Loaded profile: {user_info.first_name} {user_info.last_name}, {user_info.email}")
        else:
            print("No profile found in database, proceeding with empty user info")
            
        await run_triage_agent_session()
    else:
        print("\nCannot run the triage agent due to missing dependencies.")
        print("Please install the required packages and try again.")

if __name__ == "__main__":
    asyncio.run(main())
