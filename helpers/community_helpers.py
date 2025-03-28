"""
Helper functions for the Community Agent to interact with Pinecone and Discourse.
"""

import os
import json
import aiohttp
from typing import Dict, Any, List, Optional, Set

from openai import OpenAI

# Configure API keys and endpoints
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "discourse-topics")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "community")
DISCOURSE_URL = os.getenv("DISCOURSE_URL", "https://community.pricingsaas.com")
SCORE_THRESHOLD = 0.8  # Only consider results with 80% or higher score

# Initialize OpenAI client
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")

async def optimize_query_for_embeddings(query):
    """
    Preprocess the user query to optimize it for embedding-based search.
    Uses OpenAI to generate a better query that will return the best matches.
    
    Args:
        query: The original user query
        
    Returns:
        An optimized query for embedding-based search
    """
    if not openai_client:
        raise ValueError("OpenAI client is not initialized")
    
    try:
        system_prompt = """
        You are a query optimization expert. Your task is to rewrite a user's query to make it more effective for 
        embedding-based search in a vector database (Pinecone) that contains community discussions about SaaS pricing.
        
        The optimized query should:
        1. Focus on key concepts and terminology related to SaaS pricing
        2. Remove unnecessary words and phrases
        3. Include relevant synonyms or related terms that might appear in the target documents
        4. Be concise but comprehensive
        5. Maintain the original intent of the query
        
        Return ONLY the optimized query text without any explanations or additional text.
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Original query: {query}\n\nOptimize this query for embedding-based search in a vector database containing SaaS pricing discussions."}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        optimized_query = response.choices[0].message.content.strip()
        print(f"Original query: '{query}'")
        print(f"Optimized query: '{optimized_query}'")
        
        return optimized_query
    except Exception as e:
        print(f"Error optimizing query: {e}")
        print("Falling back to original query")
        return query

def generate_embedding(text):
    """Generate embedding for the given text using OpenAI API"""
    if not openai_client:
        raise ValueError("OpenAI client is not initialized")
    
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002", 
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise

def query_pinecone(index, vector, top_k=5, filter=None):
    """Query Pinecone index with the given vector"""
    if not index:
        raise ValueError("Pinecone index is not initialized")
    
    try:
        query_params = {
            "vector": vector,
            "top_k": top_k,
            "include_values": False,
            "include_metadata": True,
        }
        
        # Add namespace if specified
        if PINECONE_NAMESPACE:
            query_params["namespace"] = PINECONE_NAMESPACE
            
        # Add filter if specified
        if filter:
            query_params["filter"] = filter
            
        return index.query(**query_params)
    except Exception as e:
        print(f"Error querying Pinecone: {e}")
        raise

def extract_text_from_html(html):
    """Simple function to extract plain text from HTML"""
    import re
    text = re.sub(r'<[^>]*>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_topic_content(topic_data: Dict[str, Any]) -> str:
    """
    Format the full topic data into a readable string
    
    Args:
        topic_data: The topic data from Discourse API
        
    Returns:
        A formatted string with the topic content
    """
    if not topic_data:
        return "No topic data available"
    
    formatted_content = f"TOPIC: {topic_data.get('title', 'Untitled')}\n"
    formatted_content += f"URL: {DISCOURSE_URL}/t/{topic_data.get('id')}\n\n"
    
    # Add the posts
    posts = topic_data.get('post_stream', {}).get('posts', [])
    for post in posts:
        username = post.get('username', 'Unknown')
        post_number = post.get('post_number', 0)
        
        # Skip the first post if it's already included in the topic content
        if post_number == 1 and 'content' in topic_data:
            continue
            
        content = extract_text_from_html(post.get('cooked', ''))
        
        formatted_content += f"Post #{post_number} by {username}:\n"
        formatted_content += f"{content}\n\n"
    
    return formatted_content

async def fetch_topic_from_discourse(topic_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a topic from Discourse API
    
    Args:
        topic_id: The ID of the topic to fetch
        
    Returns:
        The topic data as a dictionary, or None if the request failed
    """
    try:
        print(f"Fetching topic {topic_id} from Discourse API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DISCOURSE_URL}/t/{topic_id}.json") as response:
                if not response.ok:
                    print(f"Failed to fetch topic: {response.status} {response.reason}")
                    # If we get a 404, the topic doesn't exist
                    if response.status == 404:
                        print(f"Topic {topic_id} not found. It may have been deleted or is not accessible.")
                    # If we get a 403, we don't have permission to access the topic
                    elif response.status == 403:
                        print(f"Access denied for topic {topic_id}. It may be private or require authentication.")
                    return None
                
                try:
                    topic_data = await response.json()
                    print(f"Successfully fetched topic {topic_id}")
                    return topic_data
                except json.JSONDecodeError:
                    print(f"Error parsing JSON response for topic {topic_id}")
                    return None
    except aiohttp.ClientError as e:
        print(f"Network error fetching topic {topic_id}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching topic {topic_id}: {e}")
        return None

def extract_topic_ids_from_matches(matches: List[Dict[str, Any]]) -> Set[int]:
    """
    Extract unique topic IDs from Pinecone matches
    
    Args:
        matches: List of matches from Pinecone query
        
    Returns:
        Set of unique topic IDs
    """
    unique_topic_ids = set()
    
    for match in matches:
        metadata = match.get("metadata", {})
        
        # Extract topic ID from metadata directly if available
        topic_id = None
        
        # First check if topic_id is directly available in metadata
        if "topic_id" in metadata:
            try:
                topic_id = int(metadata["topic_id"])
                unique_topic_ids.add(topic_id)
            except (ValueError, TypeError):
                pass
        
        # If not, try to extract from URL
        elif "url" in metadata:
            url = metadata["url"]
            
            # Extract topic ID from URL like https://community.pricingsaas.com/t/topic-slug/123
            # or from URL like https://community.pricingsaas.com/t/123
            parts = url.strip('/').split('/')
            if len(parts) > 0:
                try:
                    # Get the last part of the URL and remove any query parameters
                    last_part = parts[-1].split('?')[0]
                    
                    # Check if it's a valid integer
                    if last_part.isdigit():
                        topic_id = int(last_part)
                        # Only add if it's a reasonable topic ID (avoid very large numbers)
                        if 1 <= topic_id <= 10000:  # Adjust the upper limit as needed
                            unique_topic_ids.add(topic_id)
                    # If the last part is not a digit, check if it's in the path
                    elif '/t/' in url:
                        # Try to find the topic ID after /t/ in the URL
                        t_index = url.find('/t/')
                        if t_index != -1:
                            path_after_t = url[t_index + 3:].strip('/')
                            path_parts = path_after_t.split('/')
                            
                            # If there are at least 2 parts (slug and ID)
                            if len(path_parts) >= 2 and path_parts[1].isdigit():
                                topic_id = int(path_parts[1])
                                if 1 <= topic_id <= 10000:
                                    unique_topic_ids.add(topic_id)
                except ValueError:
                    pass
        
        # If we still don't have a topic_id, check for id field
        elif "id" in metadata:
            try:
                topic_id = int(metadata["id"])
                unique_topic_ids.add(topic_id)
            except (ValueError, TypeError):
                pass
    
    return unique_topic_ids

async def process_pinecone_results(index, query, context):
    """
    Process Pinecone search results and fetch full topic data
    
    Args:
        index: Pinecone index
        query: User query
        context: Agent context
        
    Returns:
        Dictionary with search results and formatted output
    """
    results = {}
    
    try:
        # Optimize the query for embedding-based search
        optimized_query = await optimize_query_for_embeddings(query)
        
        # Generate embedding for the optimized query
        query_vector = generate_embedding(optimized_query)
        
        # First, try to find matching posts - limit to top 5
        post_results = query_pinecone(index, query_vector, 5, {"type": "post"})
        
        if post_results["matches"] and len(post_results["matches"]) > 0:
            # Filter results to only include those with 80% or higher score
            high_score_matches = [match for match in post_results["matches"] if match.get("score", 0) >= SCORE_THRESHOLD]
            
            if high_score_matches:
                results["posts"] = []
                
                # Extract unique topic IDs from matches
                unique_topic_ids = extract_topic_ids_from_matches(high_score_matches)
                
                # Process each match
                for match in high_score_matches:
                    metadata = match.get("metadata", {})
                    score = match.get("score", 0)
                    
                    post_data = {
                        "title": metadata.get("topic_title", "Untitled"),
                        "post_number": metadata.get("post_number", "N/A"),
                        "score": f"{score * 100:.2f}%",
                        "author": metadata.get("username", "Unknown"),
                        "url": metadata.get("url", "No URL"),
                        "content": metadata.get("content_preview", "No content preview available")
                    }
                    
                    results["posts"].append(post_data)
                
                # Fetch full conversations for each unique topic
                for topic_id in unique_topic_ids:
                    if topic_id:
                        try:
                            topic_data = await fetch_topic_from_discourse(topic_id)
                            if topic_data:
                                context.full_topics[str(topic_id)] = topic_data
                                
                                # Create annotation for this topic
                                annotation = {
                                    "type": "topic_citation",
                                    "topic_id": str(topic_id),
                                    "title": topic_data.get("title", f"Topic {topic_id}"),
                                    "url": f"{DISCOURSE_URL}/t/{topic_id}"
                                }
                                context.annotations.append(annotation)
                        except Exception as e:
                            print(f"Error processing topic {topic_id}: {e}")
            else:
                results["message"] = "No high-confidence matches found (threshold: 80%)."
        
        if not results.get("posts") or len(results["posts"]) == 0:
            # If no posts found or no high-confidence matches, try to find matching topics - limit to top 5
            topic_results = query_pinecone(index, query_vector, 5, {"type": "topic"})
            
            if topic_results["matches"] and len(topic_results["matches"]) > 0:
                # Filter results to only include those with 80% or higher score
                high_score_matches = [match for match in topic_results["matches"] if match.get("score", 0) >= SCORE_THRESHOLD]
                
                if high_score_matches:
                    results["topics"] = []
                    
                    # Extract unique topic IDs from matches
                    unique_topic_ids = extract_topic_ids_from_matches(high_score_matches)
                    
                    # Process each match
                    for match in high_score_matches:
                        metadata = match.get("metadata", {})
                        score = match.get("score", 0)
                        
                        content = ""
                        if metadata.get("content"):
                            # Extract plain text from HTML content
                            content = extract_text_from_html(metadata["content"])
                        elif metadata.get("content_preview"):
                            content = metadata["content_preview"]
                        
                        topic_data = {
                            "title": metadata.get("title", "Untitled"),
                            "score": f"{score * 100:.2f}%",
                            "url": metadata.get("url", "No URL"),
                            "content": content
                        }
                        
                        results["topics"].append(topic_data)
                    
                    # Fetch full conversations for each unique topic
                    for topic_id in unique_topic_ids:
                        if topic_id:
                            try:
                                topic_data = await fetch_topic_from_discourse(topic_id)
                                if topic_data:
                                    context.full_topics[str(topic_id)] = topic_data
                                    
                                    # Create annotation for this topic
                                    annotation = {
                                        "type": "topic_citation",
                                        "topic_id": str(topic_id),
                                        "title": topic_data.get("title", f"Topic {topic_id}"),
                                        "url": f"{DISCOURSE_URL}/t/{topic_id}"
                                    }
                                    context.annotations.append(annotation)
                            except Exception as e:
                                print(f"Error processing topic {topic_id}: {e}")
                else:
                    results["message"] = "No high-confidence matches found (threshold: 80%)."
            else:
                results["message"] = "No relevant content found for your query."
    
    except Exception as e:
        results["error"] = str(e)
    
    return results

def format_search_results(results, context):
    """
    Format search results as a readable string
    
    Args:
        results: Dictionary with search results
        context: Agent context
        
    Returns:
        Formatted string with search results
    """
    formatted_results = "Here are the search results from the community knowledge base:\n\n"
    formatted_results += "Query was optimized for embedding-based search to find the most relevant content.\n"
    formatted_results += "Results are limited to the top 5 most relevant matches with 80%+ confidence.\n\n"
    
    if "error" in results:
        formatted_results += f"Error: {results['error']}\n"
    elif "message" in results:
        formatted_results += f"{results['message']}\n"
    else:
        if "posts" in results:
            formatted_results += "RELEVANT POSTS (80%+ confidence):\n"
            for i, post in enumerate(results["posts"], 1):
                formatted_results += f"{i}. {post['title']} (by {post['author']}, relevance: {post['score']})\n"
                formatted_results += f"   URL: {post['url']}\n"
                formatted_results += f"   Content: {post['content']}\n\n"
        
        if "topics" in results:
            formatted_results += "RELEVANT TOPICS (80%+ confidence):\n"
            for i, topic in enumerate(results["topics"], 1):
                formatted_results += f"{i}. {topic['title']} (relevance: {topic['score']})\n"
                formatted_results += f"   URL: {topic['url']}\n"
                formatted_results += f"   Content: {topic['content']}\n\n"
        
        # Add information about full topics fetched
        if context.full_topics:
            formatted_results += f"\nFetched {len(context.full_topics)} full topic(s) for detailed analysis.\n"
            formatted_results += "These will be referenced in the response with annotations.\n\n"
            
            # Include the full topic content for each topic
            formatted_results += "FULL TOPIC CONTENT:\n"
            formatted_results += "===================\n\n"
            
            for i, (topic_id, topic_data) in enumerate(context.full_topics.items(), 1):
                formatted_results += f"[Topic {i}] {topic_data.get('title', f'Topic {topic_id}')}\n"
                formatted_results += "-------------------\n"
                formatted_results += format_topic_content(topic_data)
                formatted_results += "\n\n"
    
    return formatted_results
