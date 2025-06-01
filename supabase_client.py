import os
from supabase import create_client, Client
from dotenv import load_dotenv

def get_supabase_client() -> Client:
    """
    Returns a valid Supabase client using environment variables for authentication.
    
    Returns:
        Client: A configured Supabase client instance
    """
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(url, key)


if __name__ == "__main__":
    # Test connection to Supabase and retrieve profile record
    try:
        supabase = get_supabase_client()
        print("Connected to Supabase successfully!")
        
        # Test query to profiles table for specific id
        profile_id = 'e03ea766-9ca0-4e60-8299-0ba759318384'
        
        # Query the profiles table
        response = supabase.table('profiles').select('*').eq('id', profile_id).execute()
        
        # Check if we got any data
        if response.data:
            print(f"Found profile record for ID: {profile_id}")
            print("Profile data:", response.data[0])
        else:
            print(f"No profile found with ID: {profile_id}")
            
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
