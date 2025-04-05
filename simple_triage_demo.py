"""
Simple Triage Demo - A simplified version of the triage agent that works without dependencies.

This script demonstrates a basic version of the triage agent functionality
without relying on external dependencies like the agents framework.
"""

from dataclasses import dataclass

@dataclass
class UserInfo:
    """User profile information."""
    name: str = ""
    email: str = ""
    company: str = ""
    title: str = ""
    
    def __post_init__(self):
        """Ensure all fields are initialized to empty strings if None."""
        self.name = self.name or ""
        self.email = self.email or ""
        self.company = self.company or ""
        self.title = self.title or ""

def simple_triage_session():
    """Run a simple triage session to collect user profile information."""
    # Initialize with empty user info
    user_info = UserInfo()
    
    print("=== Simple Profile Triage Demo ===")
    print("This demo will help you complete your profile by asking for missing information.")
    print("Type 'exit' at any time to quit.\n")
    
    # Start the conversation
    print("Welcome to the Profile Triage Assistant!")
    print("I'll help you complete your profile by asking for any missing information.")
    
    # Continue until the profile is complete or the user exits
    while True:
        try:
            # Check which fields are missing
            missing_fields = []
            if not user_info.name:
                missing_fields.append("name")
            if not user_info.email:
                missing_fields.append("email")
            if not user_info.company:
                missing_fields.append("company")
            if not user_info.title:
                missing_fields.append("title")
            
            # If no fields are missing, the profile is complete
            if not missing_fields:
                print("\n✅ Your profile is now complete! Thank you for providing all the required information.")
                print("\nFinal profile:")
                print(f"- Name: {user_info.name}")
                print(f"- Email: {user_info.email}")
                print(f"- Company: {user_info.company}")
                print(f"- Title: {user_info.title}")
                break
            
            # Ask for one missing field at a time
            field_to_ask = missing_fields[0]
            
            if field_to_ask == "name":
                print("\nI notice that I don't have your name yet. What is your name?")
            elif field_to_ask == "email":
                print("\nI need your email address to complete your profile. What is your email?")
            elif field_to_ask == "company":
                print("\nWhich company do you work for?")
            elif field_to_ask == "title":
                print("\nWhat is your job title?")
            
            # Get the user's response
            try:
                user_input = input("You: ")
            except (EOFError, KeyboardInterrupt):
                print("\nInput interrupted. Exiting...")
                break
            
            # Check if the user wants to exit
            if user_input.lower() == 'exit':
                print("Thank you for using the Profile Triage Assistant. Goodbye!")
                break
            
            # Update the profile based on the field we asked for
            if field_to_ask == "name":
                user_info.name = user_input
                print(f"Thanks! I've updated your name to: {user_info.name}")
            elif field_to_ask == "email":
                user_info.email = user_input
                print(f"Great! I've updated your email to: {user_info.email}")
            elif field_to_ask == "company":
                user_info.company = user_input
                print(f"Perfect! I've updated your company to: {user_info.company}")
            elif field_to_ask == "title":
                user_info.title = user_input
                print(f"Excellent! I've updated your title to: {user_info.title}")
            
            # Show the current profile status
            print("\nCurrent profile status:")
            print(f"- Name: {user_info.name or 'Not provided'}")
            print(f"- Email: {user_info.email or 'Not provided'}")
            print(f"- Company: {user_info.company or 'Not provided'}")
            print(f"- Title: {user_info.title or 'Not provided'}")
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Let's try again.")

if __name__ == "__main__":
    simple_triage_session()
