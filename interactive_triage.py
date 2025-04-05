"""
Interactive Triage Agent Demo

This script demonstrates the full functionality of the triage agent with streaming responses.
It simulates a real conversation with the agent, allowing the user to provide profile
information one step at a time.
"""

import asyncio
import uuid
import sys
import os
from typing import Dict, Any, List

# Try to import the required modules
try:
    from agents import TResponseInputItem, trace
    from agent_modules.profileAgent import UserInfo
    from agent_modules.triageAgent import triage_agent, profile_validator, Runner
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required packages are installed.")
    print("You can install them with: pip install -r requirements.txt")
    IMPORTS_SUCCESSFUL = False

async def interactive_triage_session():
    """
    Run an interactive triage session with streaming responses.
    This demonstrates the full functionality of the triage agent.
    """
    # Create a unique ID for this conversation
    conversation_id = str(uuid.uuid4().hex[:16])
    
    # Initialize with empty user info
    user_info = UserInfo()
    
    print("=== Profile Triage Agent ===")
    print("This agent will help you complete your profile by asking for missing information.")
    print("Type 'exit' at any time to quit.\n")
    
    # Get the initial message from the user
    msg = input("You: ")
    if msg.lower() == 'exit':
        return
    
    # Start with the triage agent
    agent = triage_agent
    inputs: List[TResponseInputItem] = [{"content": msg, "role": "user"}]
    
    # Continue the conversation until the profile is complete or the user exits
    while True:
        try:
            # Each conversation turn is a single trace
            with trace("Profile Triage", group_id=conversation_id):
                # Run the agent and stream the response
                print("Agent: ", end="", flush=True)
                result = Runner.run_streamed(
                    agent,
                    input=inputs,
                    context=user_info
                )
                
                # Process and display the streaming events
                try:
                    async for event in result.stream_events():
                        if hasattr(event, 'type') and event.type == "raw_response_event":
                            if hasattr(event.data, 'delta'):
                                print(event.data.delta, end="", flush=True)
                except Exception as e:
                    print(f"\nError during streaming: {str(e)}")
                
                print("\n")
                
                # Check if the profile is now complete
                try:
                    validation_result = await Runner.run(
                        profile_validator,
                        "Is my profile complete?",
                        context=user_info
                    )
                    
                    # If the profile is complete, break the loop
                    if validation_result and hasattr(validation_result, 'final_output') and "complete and valid" in validation_result.final_output:
                        print("\n✅ Your profile is now complete! Thank you for providing all the required information.")
                        print("\nFinal profile:")
                        print(f"- Name: {user_info.name or 'Not provided'}")
                        print(f"- Email: {user_info.email or 'Not provided'}")
                        print(f"- Company: {user_info.company or 'Not provided'}")
                        print(f"- Title: {user_info.title or 'Not provided'}")
                        break
                except Exception as e:
                    print(f"\nError checking profile completeness: {str(e)}")
                    print("Continuing with the conversation...")
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Let's try again with a different approach.")
            
            # Prepare for the next turn
            inputs = result.to_input_list()
            user_msg = input("You: ")
            
            # Check if the user wants to exit
            if user_msg.lower() == 'exit':
                break
            
            # Process the user's response to update the profile directly
            # This simulates what would happen in a real application where
            # the frontend would extract this information
            
            # Check for name information
            if ("name" in user_msg.lower() or "i am" in user_msg.lower()) and not user_info.name:
                if "name is" in user_msg.lower():
                    name_parts = user_msg.lower().split("name is")
                    if len(name_parts) > 1:
                        user_info.name = name_parts[1].strip()
                elif "i am" in user_msg.lower():
                    name_parts = user_msg.lower().split("i am")
                    if len(name_parts) > 1:
                        user_info.name = name_parts[1].strip()
            
            # Check for email information
            if "email" in user_msg.lower() and not user_info.email:
                if "@" in user_msg:
                    # Simple email extraction
                    words = user_msg.split()
                    for word in words:
                        if "@" in word:
                            user_info.email = word.strip(".,;:")
            
            # Check for company information
            if ("company" in user_msg.lower() or "work at" in user_msg.lower() or "work for" in user_msg.lower()) and not user_info.company:
                if "company is" in user_msg.lower():
                    company_parts = user_msg.lower().split("company is")
                    if len(company_parts) > 1:
                        user_info.company = company_parts[1].strip()
                elif "work at" in user_msg.lower():
                    company_parts = user_msg.lower().split("work at")
                    if len(company_parts) > 1:
                        user_info.company = company_parts[1].split("as")[0].strip()
                elif "work for" in user_msg.lower():
                    company_parts = user_msg.lower().split("work for")
                    if len(company_parts) > 1:
                        user_info.company = company_parts[1].split("as")[0].strip()
            
            # Check for title information
            if ("title" in user_msg.lower() or "position" in user_msg.lower() or "as a" in user_msg.lower()) and not user_info.title:
                if "title is" in user_msg.lower():
                    title_parts = user_msg.lower().split("title is")
                    if len(title_parts) > 1:
                        user_info.title = title_parts[1].strip()
                elif "position is" in user_msg.lower():
                    title_parts = user_msg.lower().split("position is")
                    if len(title_parts) > 1:
                        user_info.title = title_parts[1].strip()
                elif "as a" in user_msg.lower():
                    title_parts = user_msg.lower().split("as a")
                    if len(title_parts) > 1:
                        user_info.title = title_parts[1].strip()
            
            # Add the user's message to the inputs
            inputs.append({"content": user_msg, "role": "user"})
            agent = result.current_agent

if __name__ == "__main__":
    if IMPORTS_SUCCESSFUL:
        asyncio.run(interactive_triage_session())
    else:
        print("\nCannot run the interactive triage session due to missing dependencies.")
        print("Please install the required packages and try again.")
