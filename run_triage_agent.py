"""
Interactive script to run the triage agent.

This script provides an interactive command-line interface to test the triage agent.
It simulates a real conversation with the agent, allowing the user to provide profile
information one step at a time.
"""

import asyncio
import sys
import os

from agent_modules.profileAgent import UserInfo
from agent_modules.triageAgent import run_triage_agent

async def interactive_triage():
    """Run the triage agent interactively."""
    # Initialize with empty user info
    user_info = UserInfo()
    
    print("=== Profile Triage Agent ===")
    print("This agent will help you complete your profile by asking for missing information.")
    print("Type 'exit' at any time to quit.\n")
    
    # Start with an initial greeting
    initial_message = "Hello, I'd like to set up my profile"
    print(f"You: {initial_message}")
    
    # Run the initial triage
    async for event in run_triage_agent(user_info, initial_message):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\n")
    
    # Continue the conversation until the user types 'exit'
    while True:
        # Get user input
        user_input = input("You: ")
        
        # Check if the user wants to exit
        if user_input.lower() == 'exit':
            break
        
        # Process the user's response based on what the agent asked for
        if "name" in user_input.lower() and not user_info.name:
            # Extract name (simple extraction for demo purposes)
            name_parts = user_input.split("is ")
            if len(name_parts) > 1:
                user_info.name = name_parts[1].strip()
        
        if "email" in user_input.lower() and not user_info.email:
            # Extract email (simple extraction for demo purposes)
            email_parts = user_input.split("is ")
            if len(email_parts) > 1:
                user_info.email = email_parts[1].strip()
        
        if "company" in user_input.lower() and not user_info.company:
            # Extract company (simple extraction for demo purposes)
            company_parts = user_input.split("at ")
            if len(company_parts) > 1:
                user_info.company = company_parts[1].split(" as ")[0].strip()
        
        if "title" in user_input.lower() or "as a" in user_input.lower() and not user_info.title:
            # Extract title (simple extraction for demo purposes)
            if "as a" in user_input.lower():
                title_parts = user_input.split("as a ")
                if len(title_parts) > 1:
                    user_info.title = title_parts[1].strip()
            elif "title is" in user_input.lower():
                title_parts = user_input.split("title is ")
                if len(title_parts) > 1:
                    user_info.title = title_parts[1].strip()
        
        # Run the triage agent with the user's input
        print("Agent: ", end="")
        async for event in run_triage_agent(user_info, user_input):
            if event["type"] == "text_delta":
                print(event["data"], end="", flush=True)
            elif event["type"] == "completion":
                print("\n")
        
        # Check if the profile is complete
        if user_info.name and user_info.email and user_info.company and user_info.title:
            print("\nYour profile is now complete!")
            print("\nFinal profile:")
            print(f"- Name: {user_info.name}")
            print(f"- Email: {user_info.email}")
            print(f"- Company: {user_info.company}")
            print(f"- Title: {user_info.title}")
            break

if __name__ == "__main__":
    asyncio.run(interactive_triage())
