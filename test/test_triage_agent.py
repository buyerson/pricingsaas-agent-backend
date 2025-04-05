"""
Test script for the triage agent.

This script tests the triage agent's ability to validate and complete user profiles.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_modules.profileAgent import UserInfo
from agent_modules.triageAgent import run_triage_agent

async def test_triage_agent_with_empty_profile():
    """Test the triage agent with an empty profile."""
    # Initialize with empty user info
    user_info = UserInfo()
    
    print("=== Testing Triage Agent with Empty Profile ===")
    print("Initial profile:")
    print(f"- Name: '{user_info.name}'")
    print(f"- Email: '{user_info.email}'")
    print(f"- Company: '{user_info.company}'")
    print(f"- Title: '{user_info.title}'")
    print("\nStarting conversation...\n")
    
    # Run the triage agent with an initial message
    async for event in run_triage_agent(user_info, "Hello, I'd like to set up my profile"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nFirst interaction complete.")
    
    # Simulate user providing their name
    print("\nUser: My name is John Doe")
    user_info.name = "John Doe"
    
    # Continue the conversation
    async for event in run_triage_agent(user_info, "My name is John Doe"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nSecond interaction complete.")
    
    # Simulate user providing their email
    print("\nUser: My email is john.doe@example.com")
    user_info.email = "john.doe@example.com"
    
    # Continue the conversation
    async for event in run_triage_agent(user_info, "My email is john.doe@example.com"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nThird interaction complete.")
    
    # Simulate user providing their company and title at once
    print("\nUser: I work at Acme Corp as a Product Manager")
    user_info.company = "Acme Corp"
    user_info.title = "Product Manager"
    
    # Continue the conversation
    async for event in run_triage_agent(user_info, "I work at Acme Corp as a Product Manager"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nFourth interaction complete.")
    
    # Print the final profile
    print("\nFinal profile:")
    print(f"- Name: '{user_info.name}'")
    print(f"- Email: '{user_info.email}'")
    print(f"- Company: '{user_info.company}'")
    print(f"- Title: '{user_info.title}'")

async def test_triage_agent_with_partial_profile():
    """Test the triage agent with a partially filled profile."""
    # Initialize with partial user info
    user_info = UserInfo(name="Jane Smith", email="jane.smith@example.com")
    
    print("\n=== Testing Triage Agent with Partial Profile ===")
    print("Initial profile:")
    print(f"- Name: '{user_info.name}'")
    print(f"- Email: '{user_info.email}'")
    print(f"- Company: '{user_info.company}'")
    print(f"- Title: '{user_info.title}'")
    print("\nStarting conversation...\n")
    
    # Run the triage agent with an initial message
    async for event in run_triage_agent(user_info, "Hello, I'd like to complete my profile"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nFirst interaction complete.")
    
    # Simulate user providing their company
    print("\nUser: I work at TechCorp")
    user_info.company = "TechCorp"
    
    # Continue the conversation
    async for event in run_triage_agent(user_info, "I work at TechCorp"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nSecond interaction complete.")
    
    # Simulate user providing their title
    print("\nUser: I'm a Software Engineer")
    user_info.title = "Software Engineer"
    
    # Continue the conversation
    async for event in run_triage_agent(user_info, "I'm a Software Engineer"):
        if event["type"] == "text_delta":
            print(event["data"], end="", flush=True)
        elif event["type"] == "completion":
            print("\nThird interaction complete.")
    
    # Print the final profile
    print("\nFinal profile:")
    print(f"- Name: '{user_info.name}'")
    print(f"- Email: '{user_info.email}'")
    print(f"- Company: '{user_info.company}'")
    print(f"- Title: '{user_info.title}'")

async def main():
    """Run all tests."""
    await test_triage_agent_with_empty_profile()
    await test_triage_agent_with_partial_profile()

if __name__ == "__main__":
    asyncio.run(main())
