"""
Utilities for testing Ask HN functionality.
"""
import json
from unittest.mock import Mock


def create_mock_response(status_code=200, json_data=None):
    """Create a mock requests response object with the given status code and JSON data."""
    mock_response = Mock()
    mock_response.status_code = status_code
    
    def mock_json():
        return json_data
        
    mock_response.json = mock_json
    
    return mock_response


def generate_mock_ask_story(story_id=12345, score=100, descendants=20, title="Ask HN: Test Question?"):
    """
    Generate a mock Ask HN story.
    
    Args:
        story_id: ID for the story
        score: Story score (points)
        descendants: Number of comments
        title: Story title, should start with "Ask HN:"
    
    Returns:
        Dictionary representing an Ask HN story
    """
    return {
        "id": story_id,
        "title": title,
        "by": "test_user",
        "score": score,
        "descendants": descendants,
        "time": 1616513396,  # Example timestamp
        "text": "This is a test Ask HN post with <b>some</b> <i>formatting</i>.",
        "type": "story",
        "kids": list(range(1000, 1000 + descendants)),  # Generate comment IDs
    }


def generate_mock_ask_stories(num_stories=10, base_id=10000, with_random_scores=True):
    """
    Generate a list of mock Ask HN stories.
    
    Args:
        num_stories: Number of stories to generate
        base_id: Starting ID for the stories
        with_random_scores: If True, vary the scores; otherwise all have score=100
    
    Returns:
        List of story dictionaries
    """
    import random
    stories = []
    
    for i in range(num_stories):
        story_id = base_id + i
        score = random.randint(10, 500) if with_random_scores else 100
        descendants = random.randint(0, 50)
        stories.append(generate_mock_ask_story(
            story_id=story_id,
            score=score,
            descendants=descendants,
            title=f"Ask HN: Test Question {i+1}?"
        ))
    
    return stories


def generate_ask_story_ids(num_stories=100):
    """Generate a list of mock Ask HN story IDs."""
    return list(range(20000, 20000 + num_stories))
