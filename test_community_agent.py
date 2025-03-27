import asyncio
import os
import sys

# Add the project root to the Python path to ensure imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Set the Discourse URL if not already set
    if not os.getenv("DISCOURSE_URL"):
        os.environ["DISCOURSE_URL"] = "https://community.pricingsaas.com"
    
    print("Starting Community Agent test...")
    print("Using Discourse URL:", os.getenv("DISCOURSE_URL"))
    
    try:
        # Import the main function from the communityAgent module
        from agent_modules.communityAgent import main
        
        # Run the main function
        asyncio.run(main())
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Make sure all required packages are installed:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"Error running the Community Agent: {e}")
