"""
Test utilities for PyNews tests.
Contains mock data generators and helper functions for testing.
"""
import json
from unittest.mock import Mock


def create_mock_response(status_code=200, json_data=None):
    """
    Create a mock requests response object with the given status code and JSON data.
    
    Args:
        status_code: HTTP status code for the response
        json_data: Dictionary to return as JSON data
        
    Returns:
        Mock response object
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    
    def mock_json():
        return json_data
        
    mock_response.json = mock_json
    
    return mock_response


def generate_mock_story(story_id=12345):
    """Generate a mock story with the given ID."""
    return {
        "id": story_id,
        "title": f"Test Story {story_id}",
        "by": "test_user",
        "time": 1616513396,  # Example timestamp
        "score": 100,
        "url": f"https://example.com/story/{story_id}",
        "descendants": 2,  # Number of comments
        "kids": [111, 222]  # Comment IDs
    }


def generate_mock_comment(comment_id, parent_id=None, kids=None, deleted=False, dead=False):
    """
    Generate a mock comment with the given ID and properties.
    
    Args:
        comment_id: ID for the comment
        parent_id: ID of the parent (story or comment)
        kids: List of child comment IDs
        deleted: Whether the comment is deleted
        dead: Whether the comment is flagged as dead
        
    Returns:
        Dictionary representing a comment
    """
    if deleted:
        return {
            "id": comment_id,
            "parent": parent_id,
            "deleted": True,
            "time": 1616513396
        }
        
    if dead:
        return {
            "id": comment_id,
            "by": f"user_{comment_id}",
            "parent": parent_id,
            "text": f"This is a dead comment {comment_id}",
            "time": 1616513396,
            "dead": True,
            "kids": kids or []
        }
    
    return {
        "id": comment_id,
        "by": f"user_{comment_id}",
        "parent": parent_id,
        "text": f"This is comment {comment_id}",
        "time": 1616513396,
        "kids": kids or []
    }


def generate_comment_tree_data(story_id=12345, levels=2, width=2):
    """
    Generate a full tree of mock comments for testing.
    
    Args:
        story_id: Story ID that comments belong to
        levels: How many levels of nested comments to generate
        width: How many comments per parent
        
    Returns:
        Tuple of (story, dict_of_comments) where dict_of_comments maps
        comment IDs to comment objects
    """
    story = generate_mock_story(story_id)
    comment_dict = {}
    next_id = 1000
    
    # Create first level comments
    story["kids"] = []
    for i in range(width):
        comment_id = next_id
        next_id += 1
        story["kids"].append(comment_id)
        comment_dict[comment_id] = generate_mock_comment(comment_id, story_id)
        
    # Create additional levels
    current_level_ids = story["kids"].copy()
    for level in range(1, levels):
        next_level_ids = []
        for parent_id in current_level_ids:
            comment_dict[parent_id]["kids"] = []
            for i in range(width):
                child_id = next_id
                next_id += 1
                comment_dict[parent_id]["kids"].append(child_id)
                comment_dict[child_id] = generate_mock_comment(
                    child_id, 
                    parent_id
                )
                next_level_ids.append(child_id)
        current_level_ids = next_level_ids
    
    # Update story descendants count
    story["descendants"] = len(comment_dict)
    
    return story, comment_dict


def simulate_fetch_item(comment_id, comment_dict):
    """
    Simulate fetching an item from the API based on the given comment dictionary.
    
    Args:
        comment_id: ID to fetch
        comment_dict: Dictionary mapping comment IDs to comment objects
        
    Returns:
        Comment data or None if not found
    """
    return comment_dict.get(comment_id)