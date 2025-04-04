"""
Test script for the updated annotation format.
"""

import json

def test_annotation_processing():
    """Test the annotation processing logic."""
    
    # Sample community annotation
    community_annotation = {
        "topic_id": "12345",
        "post_id": "67890",
        "title": "How to price your SaaS product",
        "discourse_url": "https://community.example.com/t/12345"
    }
    
    # Sample reports annotation
    reports_annotation = {
        "file_citation": {
            "file_id": "doc-123",
            "title": "SaaS Pricing Guide 2023"
        }
    }
    
    # Process community annotation
    processed_community = process_community_annotation(community_annotation)
    print("Processed Community Annotation:")
    print(json.dumps(processed_community, indent=2))
    
    # Process reports annotation
    processed_reports = process_reports_annotation(reports_annotation)
    print("\nProcessed Reports Annotation:")
    print(json.dumps(processed_reports, indent=2))

def process_community_annotation(annotation):
    """Process a community annotation into the new format."""
    post_citation = {
        "type": "post_citation",
        "post_citation": {
            "post_id": "",
            "topic_id": "",
            "title": "",
            "url": "",
            "source": "community"
        }
    }
    
    # Extract data from the annotation
    for field in ["post_id", "topic_id", "url"]:
        if field in annotation and annotation[field]:
            post_citation["post_citation"][field] = annotation[field]
    
    # Special case for discourse_url
    if "discourse_url" in annotation and annotation["discourse_url"]:
        post_citation["post_citation"]["url"] = annotation["discourse_url"]
    
    # Extract from nested structure if needed
    if "file_citation" in annotation and isinstance(annotation["file_citation"], dict):
        for field in ["post_id", "topic_id", "url"]:
            if field in annotation["file_citation"] and annotation["file_citation"][field]:
                post_citation["post_citation"][field] = annotation["file_citation"][field]
        
        # Special case for discourse_url
        if "discourse_url" in annotation["file_citation"] and annotation["file_citation"]["discourse_url"]:
            post_citation["post_citation"]["url"] = annotation["file_citation"]["discourse_url"]
    
    # Use file_id as topic_id if available and topic_id is not set
    if not post_citation["post_citation"]["topic_id"]:
        if "file_id" in annotation and annotation["file_id"]:
            post_citation["post_citation"]["topic_id"] = annotation["file_id"]
        elif "file_citation" in annotation and "file_id" in annotation["file_citation"]:
            post_citation["post_citation"]["topic_id"] = annotation["file_citation"]["file_id"]
    
    # Set the title with appropriate prefix
    if "title" in annotation and annotation["title"]:
        post_citation["post_citation"]["title"] = f"[Community] {annotation['title']}"
    elif "file_citation" in annotation and "title" in annotation["file_citation"]:
        post_citation["post_citation"]["title"] = f"[Community] {annotation['file_citation']['title']}"
    elif "filename" in annotation and annotation["filename"]:
        post_citation["post_citation"]["title"] = f"[Community] {annotation['filename']}"
    else:
        post_citation["post_citation"]["title"] = f"[Community] Topic {post_citation['post_citation']['topic_id']}"
    
    return post_citation

def process_reports_annotation(annotation):
    """Process a reports annotation into the new format."""
    file_citation = {
        "type": "file_citation",
        "file_citation": {
            "file_id": "",
            "title": "",
            "source": "report"
        }
    }
    
    # Extract file_id
    if "file_id" in annotation and annotation["file_id"]:
        file_citation["file_citation"]["file_id"] = annotation["file_id"]
    elif "file_citation" in annotation and "file_id" in annotation["file_citation"]:
        file_citation["file_citation"]["file_id"] = annotation["file_citation"]["file_id"]
    
    # Set the title with appropriate prefix
    if "title" in annotation and annotation["title"]:
        file_citation["file_citation"]["title"] = f"[Report] {annotation['title']}"
    elif "file_citation" in annotation and "title" in annotation["file_citation"]:
        file_citation["file_citation"]["title"] = f"[Report] {annotation['file_citation']['title']}"
    elif "filename" in annotation and annotation["filename"]:
        file_citation["file_citation"]["title"] = f"[Report] {annotation['filename']}"
    else:
        file_citation["file_citation"]["title"] = f"[Report] Document {file_citation['file_citation']['file_id']}"
    
    return file_citation

if __name__ == "__main__":
    test_annotation_processing()
