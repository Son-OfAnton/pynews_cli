"""
Utilities for testing Poll stories functionality.
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


def generate_mock_poll_story(poll_id=30000, score=100, descendants=20, option_count=3):
    """
    Generate a mock poll story.
    
    Args:
        poll_id: ID for the poll
        score: Poll score (points)
        descendants: Number of comments
        option_count: Number of poll options to generate
        
    Returns:
        Dictionary representing a poll story
    """
    # Generate option IDs
    part_ids = list(range(poll_id + 1, poll_id + 1 + option_count))
    
    return {
        "id": poll_id,
        "title": f"Poll: Test Poll Question {poll_id}?",
        "by": "test_user",
        "score": score,
        "descendants": descendants,
        "time": 1616513396,  # Example timestamp
        "text": "This is a test poll with multiple options.",
        "type": "poll",
        "parts": part_ids,
        "kids": list(range(30500, 30500 + descendants)),  # Comment IDs
    }


def generate_mock_poll_option(option_id, poll_id, score, text):
    """
    Generate a mock poll option.
    
    Args:
        option_id: ID for this option
        poll_id: Parent poll ID
        score: Number of votes for this option
        text: Option text
        
    Returns:
        Dictionary representing a poll option
    """
    return {
        "id": option_id,
        "text": text,
        "by": "test_user",
        "poll": poll_id,
        "score": score,
        "time": 1616513396,  # Example timestamp
        "type": "pollopt"
    }


def generate_mock_poll_with_options(poll_id=30000, score=100, descendants=20, option_count=3):
    """
    Generate a mock poll with its options.
    
    Args:
        poll_id: ID for the poll
        score: Poll score (points)
        descendants: Number of comments
        option_count: Number of poll options to generate
        
    Returns:
        Tuple of (poll, list_of_options)
    """
    poll = generate_mock_poll_story(poll_id, score, descendants, option_count)
    
    options = []
    option_texts = [
        "Option A - First choice",
        "Option B - Second choice",
        "Option C - Third choice",
        "Option D - Fourth choice",
        "Option E - Fifth choice"
    ]
    
    total_votes = 50  # Total votes to distribute
    votes_per_option = total_votes // option_count
    
    for i, part_id in enumerate(poll["parts"]):
        # Distribute votes, giving more to earlier options
        option_score = votes_per_option * (option_count - i)
        option_text = option_texts[i] if i < len(option_texts) else f"Option {i+1}"
        
        options.append(generate_mock_poll_option(
            part_id, poll_id, option_score, option_text
        ))
    
    return poll, options


def generate_mock_poll_list(num_polls=10, base_id=30000, vary_scores=True, vary_comments=True):
    """
    Generate a list of mock polls.
    
    Args:
        num_polls: Number of polls to generate
        base_id: Starting ID for polls
        vary_scores: Whether to generate different scores for each poll
        vary_comments: Whether to generate different comment counts
        
    Returns:
        List of poll dictionaries
    """
    import random
    polls = []
    
    for i in range(num_polls):
        poll_id = base_id + (i * 100)  # Space out IDs to allow for options
        
        # Vary attributes if requested
        score = random.randint(5, 500) if vary_scores else 100
        descendants = random.randint(0, 50) if vary_comments else 20
        option_count = random.randint(2, 5)
        
        poll = generate_mock_poll_story(
            poll_id=poll_id,
            score=score,
            descendants=descendants,
            option_count=option_count
        )
        
        polls.append(poll)
    
    return polls


def generate_poll_ids(num_polls=30):
    """Generate a list of mock poll IDs."""
    return list(range(30000, 30000 + num_polls * 100, 100))