"""
Discount Classification Agent - Uses LLM to classify discount descriptions into categories.

This agent wraps the OpenAI API calls and provides a structured interface
for classifying discount descriptions.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from openai import OpenAI
    from agents import Agent, Runner, trace
except ImportError:
    print("Required libraries not found. Install with: pip install openai")
    print("Ensure the 'agents' library is available in your environment")

# Discount categories for classification
DISCOUNT_CATEGORIES = [
    "Annual discount",
    "Introductory discount",
    "Multi-year discount",
    "Multi-product discount",
    "Volume discount"
]

class DiscountInfo:
    """Object representing discount information for classification"""
    def __init__(self, slug: str, discount_text: str):
        self.slug = slug
        self.discount_text = discount_text
        self.classifications = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization"""
        return {
            "slug": self.slug,
            "discount_text": self.discount_text,
            "classifications": self.classifications
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscountInfo':
        """Create instance from dictionary data"""
        instance = cls(data.get("slug", ""), data.get("discount_text", ""))
        instance.classifications = data.get("classifications", {})
        return instance

# Tools for the discount classifier agent
def classify_discount(discount_info: DiscountInfo) -> DiscountInfo:
    """
    Classify a discount description using the LLM.
    
    Args:
        discount_info: DiscountInfo object containing slug and discount text
        
    Returns:
        DiscountInfo: Updated with classification results
    """
    print(f"\n{'=' * 80}")
    print(f"Processing company: {discount_info.slug}")
    
    if not discount_info.discount_text.strip():
        print(f"Warning: Missing discount text for {discount_info.slug}")
        discount_info.classifications = {cat: "FALSE" for cat in DISCOUNT_CATEGORIES}
        return discount_info
    
    # Print the discount text (truncated if too long)
    max_text_length = 100
    display_text = discount_info.discount_text[:max_text_length]
    if len(discount_info.discount_text) > max_text_length:
        display_text += "..."
    print(f"Discount text: \"{display_text}\"")
    print(f"Classifying using LLM...")
    
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # System and user prompts
        system_prompt = """You are a pricing discount classifier specialist.
Your task is to analyze discount descriptions and classify them into categories.
Only respond with the exact classification result in the specified format without any explanation."""

        user_prompt = f"""Classify the following discount description into these categories:
- Annual discount: Discounts for annual billing or commitments
- Introductory discount: Limited-time introductory offers where users pay something at a discounted rate (excludes free trials and freemium models)
- Multi-year discount: Discounts for multi-year agreements
- Multi-product discount: Discounts when purchasing multiple products together
- Volume discount: Discounts based on usage volume, seats, or users

For each category, respond with TRUE if the description mentions this type of discount, or FALSE if not.

Discount description: {discount_info.discount_text}

Response format (exactly like this):
Annual discount: TRUE/FALSE
Introductory discount: TRUE/FALSE
Multi-year discount: TRUE/FALSE
Multi-product discount: TRUE/FALSE
Volume discount: TRUE/FALSE
"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",  # Use appropriate model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,  # Keep deterministic for classification
            max_tokens=150,   # Limit response size
        )

        # Extract and parse the response text
        llm_response = response.choices[0].message.content
        print(f"LLM response received.")
        
        # Parse the LLM response into a dictionary
        classifications = {}
        for line in llm_response.strip().split('\n'):
            if ':' in line:
                category, value = line.split(':', 1)
                category = category.strip()
                value = value.strip()
                # Remove brackets if present
                value = value.replace('[', '').replace(']', '')
                classifications[category] = value
        
        # Update the discount info with classifications
        discount_info.classifications = classifications
        
        # Print the classifications
        print("Classification results:")
        for category, value in classifications.items():
            if value == "TRUE":
                print(f"  {category}")
        
        # If all are FALSE, print a message
        if "TRUE" not in classifications.values():
            print("  No discount categories matched.")
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        print("Falling back to rule-based classification...")
        # Fall back to rule-based approach
        discount_info.classifications = {
            "Annual discount": "TRUE" if ("annual" in discount_info.discount_text.lower() or "yearly" in discount_info.discount_text.lower()) else "FALSE",
            "Introductory discount": "TRUE" if ("introductory" in discount_info.discount_text.lower() and "free" not in discount_info.discount_text.lower() and "trial" not in discount_info.discount_text.lower()) else "FALSE",
            "Multi-year discount": "TRUE" if ("multi-year" in discount_info.discount_text.lower() or "multiyear" in discount_info.discount_text.lower()) else "FALSE",
            "Multi-product discount": "TRUE" if ("multi-product" in discount_info.discount_text.lower() or "bundle" in discount_info.discount_text.lower()) else "FALSE",
            "Volume discount": "TRUE" if ("volume" in discount_info.discount_text.lower() or "usage" in discount_info.discount_text.lower() or "tier" in discount_info.discount_text.lower()) else "FALSE"
        }
        
        # Print the classifications
        print("Classification results (using fallback rules):")
        for category, value in discount_info.classifications.items():
            if value == "TRUE":
                print(f"  {category}")
        
        # If all are FALSE, print a message
        if "TRUE" not in discount_info.classifications.values():
            print("  No discount categories matched.")
    
    return discount_info

def update_json_file(slug: str, discount_info: DiscountInfo, output_path: Optional[str] = None) -> str:
    """
    Update the JSON file with a single company's classification results.
    If the file doesn't exist, it will be created.
    
    Args:
        slug: Company slug
        discount_info: DiscountInfo object containing classification results
        output_path: Optional file path for output, defaults to 'data/discounts_classified.json'
        
    Returns:
        str: Path to the updated JSON file
    """
    # Default path if none provided
    if not output_path:
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        output_path = str(current_dir.parent / 'data' / 'discounts_classified.json')
    
    # Load existing data if file exists
    existing_data = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse existing JSON file at {output_path}. Creating new file.")
    
    # Update with new data
    existing_data[slug] = discount_info.to_dict()
    
    # Write back to file
    with open(output_path, 'w') as f:
        json.dump(existing_data, f, indent=2)
    
    print(f"Updated classification results in {output_path} for {slug}")
    return output_path

def save_classifications_to_json(results: Dict[str, DiscountInfo], output_path: Optional[str] = None) -> str:
    """
    Save all classification results to a JSON file.
    
    Args:
        results: Dictionary of DiscountInfo objects keyed by slug
        output_path: Optional file path for output, defaults to 'data/discounts_classified.json'
        
    Returns:
        str: Path to the saved JSON file
    """
    # Convert DiscountInfo objects to dictionaries
    serializable_results = {slug: info.to_dict() for slug, info in results.items()}
    
    # Default path if none provided
    if not output_path:
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        output_path = str(current_dir.parent / 'data' / 'discounts_classified.json')
    
    # Write to JSON file
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"All classification results saved to {output_path}")
    return output_path

def get_classifier_instructions() -> str:
    """Return the instructions for the discount classifier agent"""
    return """
    You are a Discount Classifier Agent that analyzes discount descriptions and categorizes them.
    For each discount description, classify it into one or more of these categories:
    - Annual discount: Discounts for annual billing or commitments
    - Introductory discount: Limited-time introductory offers where users pay something at a discounted rate (excludes free trials and freemium models)
    - Multi-year discount: Discounts for multi-year agreements
    - Multi-product discount: Discounts when purchasing multiple products together
    - Volume discount: Discounts based on usage volume, seats, or users

    For each category, determine if the discount fits that category (TRUE) or not (FALSE).
    Your responses should be precise and formatted exactly as required.
    """

# Create the discount classifier agent
discount_classifier = Agent[DiscountInfo](
    name="Discount Classifier",
    instructions=get_classifier_instructions(),
    tools=[classify_discount, save_classifications_to_json, update_json_file],
)
