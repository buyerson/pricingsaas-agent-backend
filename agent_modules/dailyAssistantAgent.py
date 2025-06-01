"""
Daily Assistant Agent - A personal assistant agent for day-to-day tasks and questions.

This agent helps users with general day-to-day questions and tasks, providing
personalized assistance based on user profile information.
"""

import json
import asyncio
import uuid
from typing import List, Dict, Any, Optional

# Import from openai-agents package
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent, ResponseContentPartDoneEvent

# Import from profileAgent for user profile functionality
try:
    from agent_modules.profileAgent import UserInfo, load_profile_to_context
    PROFILE_IMPORTS_SUCCESSFUL = True
except ImportError:
    PROFILE_IMPORTS_SUCCESSFUL = False

### CONTEXT

class AssistantContext:
    """Simple context class for the daily assistant agent."""
    def __init__(self):
        self.conversation_history = []
        
    def add_to_history(self, message):
        """Add a message to the conversation history."""
        self.conversation_history.append(message)
        # Limit history to last 10 messages to avoid context overflow
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

### AGENT CREATION

def create_daily_assistant_agent():
    """Create and return the daily assistant agent."""
    return Agent(
        name="Daily Assistant",
        instructions="""You are a helpful daily assistant that helps users with their day-to-day questions and tasks.
        
        # Routine
        1. When a user asks a question, provide a helpful, friendly response.
        2. Be conversational and engaging in your responses.
        3. Reference previous parts of the conversation when relevant.
        
        # Guidelines
        - Be friendly and helpful in all interactions.
        - Provide concise but thorough answers to questions.
        - If asked about something you don't know, be honest about your limitations.
        - If the user asks for personal opinions, clarify that you're an AI without personal preferences.
        
        Remember to be respectful, helpful, and informative in all your responses.
        """,
        tools=[],  # No specific tools for this agent
    )

### STREAM RESPONSES

async def stream_daily_assistant_response(connection_id, message, user_info=None):
    """
    Stream responses from the daily assistant agent.
    
    Args:
        connection_id: WebSocket connection ID
        message: User message
        user_info: Optional user profile information
        
    Returns:
        None
    """
    try:
        # Create the daily assistant agent
        agent = create_daily_assistant_agent()
        
        # Create context
        context = AssistantContext()
        
        # Initialize response
        response_text = ""
        
        # Run the agent
        result = Runner.run_streamed(
            agent,
            input=message,
            context=context
        )
        
        # Stream the response
        async for event in result.stream_events():
            data = getattr(event, 'data', None)
            
            if isinstance(data, ResponseTextDeltaEvent):
                # Append to the response text
                response_text += data.delta
                
                # Stream the delta to the client
                try:
                    # Send the text delta to the client
                    apigateway.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps({'text': data.delta}).encode('utf-8')
                    )
                except Exception as e:
                    print(f"Error sending to connection: {e}")
            
        # Add the message and response to the conversation history
        context.add_to_history({"role": "user", "content": message})
        context.add_to_history({"role": "assistant", "content": response_text})
        
        # Send completion signal
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'done': True}).encode('utf-8')
        )
    except Exception as e:
        print(f"Error during WebSocket streaming: {e}")
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({'error': str(e), 'done': True}).encode('utf-8')
        )

### RUN

async def main():
    """Main function to run the Daily Assistant Agent interactively."""
    # Initialize user info and try to load profile if imports are successful
    user_greeting = ""
    if PROFILE_IMPORTS_SUCCESSFUL:
        try:
            # Use the mock user ID for testing
            user_id = "e03ea766-9ca0-4e60-8299-0ba759318384"
            user_info = UserInfo(user_id=user_id)
            
            # Pre-load profile data
            print(f"Attempting to load profile data for user ID: {user_id}...")
            load_profile_to_context(user_info, user_id)
            
            # Debug the loaded profile state
            print(f"Profile loaded state: {getattr(user_info, '_profile_loaded', False)}")
            if hasattr(user_info, '_profile_loaded') and user_info._profile_loaded:
                print(f"First name: {getattr(user_info, 'first_name', 'Not found')}")
                print(f"Last name: {getattr(user_info, 'last_name', 'Not found')}")
                print(f"Display name: {getattr(user_info, 'display_name', 'Not found')}")
                print(f"Email: {getattr(user_info, 'email', 'Not found')}")
                
                # Create personalized greeting using the best available information
                if user_info.first_name:
                    # If we have a first name, use it
                    user_greeting = f"Welcome, {user_info.first_name}! "
                    print(f"Created greeting using first name: '{user_greeting}'")
                elif hasattr(user_info, 'display_name') and user_info.display_name:
                    # Next, try to use display_name if available
                    user_greeting = f"Welcome, {user_info.display_name}! "
                    print(f"Created greeting using display_name: '{user_greeting}'")
                elif hasattr(user_info, 'email') and user_info.email:
                    # Fall back to using email username if available
                    username = user_info.email.split('@')[0] if '@' in user_info.email else user_info.email
                    user_greeting = f"Welcome, {username}! "
                    print(f"Created greeting using email username: '{user_greeting}'")
                else:
                    print("No personalization information available for greeting")
        except Exception as e:
            print(f"Error loading profile: {e}")
            import traceback
            traceback.print_exc()
    
    # Print welcome message with personalized greeting if available
    print("\nDaily Assistant")
    print("===============")
    print(f"{user_greeting}How can I assist you today?")
    print("Type 'exit' to quit.\n")
    
    # Create the assistant agent
    agent = create_daily_assistant_agent()
    
    # Create context to maintain conversation history
    context = AssistantContext()

    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        # Add user message to history
        context.add_to_history({"role": "user", "content": user_input})
        
        # Run the agent with the user's input
        print("\nAssistant: ", end="")
        response_text = ""
        
        # Run the agent with streaming
        result = Runner.run_streamed(
            agent,
            input=user_input,
            context=context
        )
        
        # Stream the response to the terminal
        async for event in result.stream_events():
            data = getattr(event, 'data', None)
            
            if isinstance(data, ResponseTextDeltaEvent):
                # Stream the text delta to the terminal
                print(data.delta, end="", flush=True)
                response_text += data.delta
        
        # Add assistant response to history
        context.add_to_history({"role": "assistant", "content": response_text})
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
