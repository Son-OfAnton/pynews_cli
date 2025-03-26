"""
Utilities for testing user information fetching functionality.
"""
import json
from unittest.mock import Mock
import time


def create_mock_response(status_code=200, json_data=None):
    """Create a mock requests response object with the given status code and JSON data."""
    mock_response = Mock()
    mock_response.status_code = status_code
    
    def mock_json():
        return json_data
        
    mock_response.json = mock_json
    
    return mock_response


def generate_mock_user(username="test_user", karma=1000, created=1234567890, about="Test user bio"):
    """
    Generate a mock HackerNews user.
    
    Args:
        username: Username for the user
        karma: User's karma score
        created: User's account creation timestamp
        about: User's bio/about text
        
    Returns:
        Dictionary representing a user
    """
    return {
        "id": username,
        "karma": karma,
        "created": created,
        "about": about,
        "submitted": list(range(10000, 10050))  # 50 submission IDs
    }


def generate_mock_story(story_id=10000, by="test_user", score=100, title="Test Story"):
    """
    Generate a mock story submission.
    
    Args:
        story_id: ID for the story
        by: Username of the author
        score: Story score
        title: Story title
        
    Returns:
        Dictionary representing a story
    """
    return {
        "id": story_id,
        "by": by,
        "score": score,
        "title": title,
        "time": int(time.time()) - 86400,  # 1 day ago
        "type": "story",
        "descendants": 10,  # Number of comments
        "url": f"https://example.com/story/{story_id}"
    }


def generate_mock_comment(comment_id=10000, by="test_user", parent_id=9000):
    """
    Generate a mock comment.
    
    Args:
        comment_id: ID for the comment
        by: Username of the commenter
        parent_id: ID of the parent post
        
    Returns:
        Dictionary representing a comment
    """
    return {
        "id": comment_id,
        "by": by,
        "parent": parent_id,
        "text": f"This is a test comment {comment_id} by {by}",
        "time": int(time.time()) - 3600,  # 1 hour ago
        "type": "comment"
    }


def generate_mock_submissions(count=50, by="test_user", mix_ratio=0.7):
    """
    Generate a mix of mock submissions (stories and comments).
    
    Args:
        count: Total number of submissions to generate
        by: Username of the author
        mix_ratio: Ratio of stories to total (0.7 means 70% stories, 30% comments)
        
    Returns:
        List of submission dictionaries
    """
    submissions = []
    story_count = int(count * mix_ratio)
    comment_count = count - story_count
    
    # Generate stories
    for i in range(story_count):
        story_id = 10000 + i
        score = 50 + i * 2  # Increasing scores
        submissions.append(generate_mock_story(story_id, by, score, f"Test Story {i+1}"))
    
    # Generate comments
    for i in range(comment_count):
        comment_id = 20000 + i
        parent_id = 9000 + i
        submissions.append(generate_mock_comment(comment_id, by, parent_id))
    
    return submissions