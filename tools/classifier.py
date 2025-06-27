"""Classifier that reads discounts.csv, uses LLM to classify each discount description into categories,
and outputs results to discounts_classified.json

Categories:
- Annual discount
- Introductory discount
- Multi-year discount
- Multi-product discount
- Volume discount
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any

# Import the discount agent components
try:
    from tools.discount_agent import (
        DiscountInfo, 
        discount_classifier,
        save_classifications_to_json, 
        DISCOUNT_CATEGORIES
    )
    AGENT_AVAILABLE = True
except ImportError:
    print("Warning: Discount agent not available. Falling back to basic classifier.")
    AGENT_AVAILABLE = False
    
    # Define discount categories if agent not available
    DISCOUNT_CATEGORIES = [
        "Annual discount",
        "Introductory discount",
        "Multi-year discount", 
        "Multi-product discount",
        "Volume discount"
    ]


def classify_with_llm(discount_text):
    """Use an LLM to classify the discount text into appropriate categories.
    
    Args:
        discount_text (str): Description of the discount to classify
        
    Returns:
        dict: Dictionary with classification results
    """
    try:
        from openai import OpenAI
        import os
    except ImportError:
        print("OpenAI library not found. Install with: pip install openai")
        raise
    
    # Construct system and user messages for the LLM
    system_prompt = """You are a pricing discount classifier. 
    Your task is to analyze discount descriptions and classify them into categories.
    Only respond with the classification result in the specified format without explanation."""
    
    user_prompt = f"""Classify the following discount description into one or more of these categories:
    - Annual discount: Discounts for annual billing or commitments
    - Introductory discount: Free trials, limited-time introductory offers
    - Multi-year discount: Discounts for multi-year agreements
    - Multi-product discount: Discounts when purchasing multiple products together
    - Volume discount: Discounts based on usage volume, seats, or users

    For each category, respond with TRUE if the description mentions this type of discount, or FALSE if not.

    Discount description: {discount_text}

    Response format:
    Annual discount: [TRUE/FALSE]
    Introductory discount: [TRUE/FALSE]
    Multi-year discount: [TRUE/FALSE]
    Multi-product discount: [TRUE/FALSE]
    Volume discount: [TRUE/FALSE]
    """
    
    # Initialize the OpenAI client
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",  # Use appropriate model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,  # Keep deterministic for classification
            max_tokens=150,  # Limit response size
        )
        
        # Extract the response text
        llm_response = response.choices[0].message.content
        
        # Parse the LLM response into a dictionary
        results = {}
        for line in llm_response.strip().split('\n'):
            if ':' in line:
                category, value = line.split(':', 1)
                category = category.strip()
                value = value.strip()
                # Remove brackets if present
                value = value.replace('[', '').replace(']', '')
                results[category] = value
                
        return results
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        # Fall back to rule-based approach if API call fails
        results = {
            "Annual discount": "TRUE" if ("annual" in discount_text.lower() or "yearly" in discount_text.lower()) else "FALSE",
            "Introductory discount": "TRUE" if ("trial" in discount_text.lower() or "introductory" in discount_text.lower()) else "FALSE",
            "Multi-year discount": "TRUE" if ("multi-year" in discount_text.lower() or "multiyear" in discount_text.lower()) else "FALSE",
            "Multi-product discount": "TRUE" if ("multi-product" in discount_text.lower() or "bundle" in discount_text.lower()) else "FALSE",
            "Volume discount": "TRUE" if ("volume" in discount_text.lower() or "usage" in discount_text.lower() or "tier" in discount_text.lower()) else "FALSE"
        }
        return results


def classify_discounts():
    """Read CSV, classify each discount with LLM using the agent, and save to JSON.
    
    Returns:
        dict: Dictionary with classification results for each company
    """
    # Get the path to the CSV file and output JSON file
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    csv_path = current_dir.parent / 'data' / 'discounts.csv'
    json_output_path = current_dir.parent / 'data' / 'discounts_classified.json'
    
    results = {}
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        print(f"Processing {len(df)} discount entries...")
        
        # Determine whether to use the agent or direct LLM call
        if AGENT_AVAILABLE:
            # Process using the discount_agent module
            from tools.discount_agent import classify_discount, update_json_file
            
            # Create list of DiscountInfo objects to process
            discount_infos = {}
            for _, row in df.iterrows():
                slug = row['slug']
                discount_text = row.get('discount', '')
                
                if not isinstance(discount_text, str) or not discount_text.strip():
                    print(f"Warning: Missing discount text for {slug}. Skipping...")
                    continue
                
                # Create DiscountInfo object
                discount_infos[slug] = DiscountInfo(slug, discount_text)
            
            # Process in batches to avoid rate limits
            batch_size = 10
            all_slugs = list(discount_infos.keys())
            
            for i in range(0, len(all_slugs), batch_size):
                batch_slugs = all_slugs[i:i+batch_size]
                print(f"Processing batch {i//batch_size + 1}: {len(batch_slugs)} items")
                
                for slug in batch_slugs:
                    info = discount_infos[slug]
                    
                    # Directly call the classification function
                    classified_info = classify_discount(info)
                    
                    # Store the results in memory
                    results[slug] = {
                        "discount_text": classified_info.discount_text,
                        "classifications": classified_info.classifications
                    }
                    
                    # Update the JSON file after each company is analyzed
                    update_json_file(slug, classified_info, str(json_output_path))
                    
                    # Add a small delay between API calls to avoid rate limiting
                    import time
                    time.sleep(0.5)
            
            # No need for final save as we've been incrementally updating
        
        else:
            # Process using direct LLM calls if agent not available
            for _, row in df.iterrows():
                # Extract slug and discount text
                slug = row['slug']
                discount_text = row.get('discount', '')
                
                if not isinstance(discount_text, str) or not discount_text.strip():
                    print(f"Warning: Missing discount text for {slug}. Skipping...")
                    continue
                    
                print(f"Classifying discount for: {slug}")
                
                # Classify discount text using LLM
                classification = classify_with_llm(discount_text)
                
                # Store results in memory
                results[slug] = {
                    "discount_text": discount_text,
                    "classifications": classification
                }
                
                # Update the JSON file incrementally
                existing_data = {}
                if os.path.exists(json_output_path):
                    try:
                        with open(json_output_path, 'r') as f:
                            existing_data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse existing JSON file. Creating new file.")
                
                # Update with new data
                existing_data[slug] = {
                    "discount_text": discount_text,
                    "classifications": classification
                }
                
                # Write back to file
                with open(json_output_path, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                
                print(f"Updated classification results in {json_output_path} for {slug}")
                
                # Add a small delay between API calls to avoid rate limiting
                import time
                time.sleep(0.5)
        
        print(f"Classification complete. Results saved to {json_output_path}")
        return results
        
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return {}


def get_classification_stats(results=None):
    """Generate summary statistics from the classification results.
    
    Args:
        results (dict, optional): Classification results from classify_discounts()
                                  If None, loads results from the JSON file
        
    Returns:
        dict: Statistics about the classifications
    """
    # If no results provided, load from file
    if results is None:
        try:
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            json_path = current_dir.parent / 'data' / 'discounts_classified.json'
            
            with open(json_path, 'r') as f:
                results = json.load(f)
                
            print(f"Loaded classification results from {json_path}")
        except Exception as e:
            print(f"Error loading classification results: {e}")
            return {}
    
    stats = {
        "total_companies": len(results),
        "categories": {cat: 0 for cat in DISCOUNT_CATEGORIES}
    }
    
    # Count occurrences of each category
    for company, data in results.items():
        classifications = data.get("classifications", {})
        for category, value in classifications.items():
            if value == "TRUE":
                if category in stats["categories"]:
                    stats["categories"][category] += 1
    
    # Calculate percentages
    if stats["total_companies"] > 0:
        for cat in DISCOUNT_CATEGORIES:
            percentage = (stats["categories"][cat] / stats["total_companies"]) * 100
            stats["categories"][f"{cat}_percentage"] = round(percentage, 2)
    
    return stats


def print_stats(stats):
    """Print formatted statistics to console.
    
    Args:
        stats (dict): Statistics generated by get_classification_stats()
    """
    print("\nDiscount Classification Statistics:")
    print(f"Total companies analyzed: {stats['total_companies']}")
    
    for category in DISCOUNT_CATEGORIES:
        count = stats["categories"][category]
        percentage = stats["categories"].get(f"{category}_percentage", 0)
        print(f"{category}: {count} companies ({percentage}%)")


if __name__ == "__main__":
    # Run classification
    results = classify_discounts()
    
    # Generate and print statistics
    if results:
        stats = get_classification_stats(results)
        print_stats(stats)