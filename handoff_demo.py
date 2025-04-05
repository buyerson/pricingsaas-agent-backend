"""
Handoff Demo - Demonstrates the handoff pattern with the triage agent.

This script shows how to implement the handoff pattern where the triage agent
receives the first message and then hands off to the appropriate agent based
on the completeness of the user profile.
"""

import asyncio
import uuid
from typing import List

# Try to import the required modules
try:
    from openai.types.responses import ResponseContentPartDoneEvent, ResponseTextDeltaEvent
    from agents import Agent, RawResponsesStreamEvent, Runner, TResponseInputItem, trace
    from agent_modules.profileAgent import UserInfo, validate_user_info, update_profile, fetch_user_info
    from agent_modules.triageAgent import triage_agent
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required packages are installed.")
    print("You can install them with: pip install -r requirements.txt")
    IMPORTS_SUCCESSFUL = False

# Create a main agent that can handle general queries once the profile is complete
main_agent = Agent[UserInfo](
    name="main_agent",
    instructions="""
    You are a helpful assistant that can answer general questions.
    You have access to the user's profile information and can reference it in your responses.
    
    Always greet the user by name and personalize your responses based on their profile information.
    """,
    tools=[fetch_user_info],
)

# Create a router agent that will decide which agent to use
router_agent = Agent[UserInfo](
    name="router_agent",
    instructions="""
    You are a router agent that decides which agent should handle the user's request.
    
    If the user profile is incomplete (check using validate_user_info tool), hand off to the triage agent.
    If the user profile is complete, hand off to the main agent.
    
    Do not respond to the user directly - just determine which agent should handle the request.
    """,
    tools=[validate_user_info],
    handoffs=[triage_agent, main_agent],
)

async def main():
    # We'll create an ID for this conversation, so we can link each trace
    conversation_id = str(uuid.uuid4().hex[:16])
    
    # Initialize with empty user info
    user_info = UserInfo()
    
    print("=== Agent Handoff Demo ===")
    print("This demo shows how the router agent can hand off to the triage agent or main agent.")
    print("The triage agent will collect profile information if it's incomplete.")
    print("The main agent will answer general questions once the profile is complete.")
    print("Type 'exit' at any time to quit.\n")
    
    msg = input("How can I help you today? ")
    if msg.lower() == 'exit':
        return
    
    # Start with the router agent
    agent = router_agent
    inputs: List[TResponseInputItem] = [{"content": msg, "role": "user"}]
    
    while True:
        # Each conversation turn is a single trace
        with trace("Handoff Demo", group_id=conversation_id):
            # Run the agent with streaming
            print("Agent: ", end="", flush=True)
            result = Runner.run_streamed(
                agent,
                input=inputs,
                context=user_info
            )
            
            # Process the streaming events
            async for event in result.stream_events():
                if not isinstance(event, RawResponsesStreamEvent):
                    continue
                
                data = event.data
                if isinstance(data, ResponseTextDeltaEvent):
                    print(data.delta, end="", flush=True)
                elif isinstance(data, ResponseContentPartDoneEvent):
                    print("\n")
            
            # Prepare for the next turn
            inputs = result.to_input_list()
            print("\n")
            user_msg = input("Enter a message: ")
            
            # Check if the user wants to exit
            if user_msg.lower() == 'exit':
                break
            
            # Process the user's response to update the profile directly
            # This simulates what would happen in a real application
            
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
            
            # Print the current profile status
            print("\nCurrent profile status:")
            print(f"- Name: {user_info.name or 'Not provided'}")
            print(f"- Email: {user_info.email or 'Not provided'}")
            print(f"- Company: {user_info.company or 'Not provided'}")
            print(f"- Title: {user_info.title or 'Not provided'}")
            print()

if __name__ == "__main__":
    if IMPORTS_SUCCESSFUL:
        asyncio.run(main())
    else:
        print("\nCannot run the handoff demo due to missing dependencies.")
        print("Please install the required packages and try again.")
