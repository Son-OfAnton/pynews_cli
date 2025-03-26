"""
Unit tests for Poll stories functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import time

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.poll_view import (
    is_poll,
    get_poll_list,
    display_poll_titles,
    display_poll_details,
    format_timestamp
)
from test_poll_utils import (
    create_mock_response,
    generate_mock_poll_story,
    generate_mock_poll_option,
    generate_mock_poll_with_options,
    generate_mock_poll_list,
    generate_poll_ids
)


class TestPollUtilityFunctions(unittest.TestCase):
    """Tests for utility functions in the poll view module."""
    
    def test_is_poll(self):
        """Test is_poll function for identifying poll posts."""
        # Valid poll
        poll = {
            "type": "poll",
            "parts": [30001, 30002, 30003]
        }
        self.assertTrue(is_poll(poll))
        
        # Not a poll (wrong type)
        not_poll_1 = {
            "type": "story",
            "parts": [30001, 30002]
        }
        self.assertFalse(is_poll(not_poll_1))
        
        # Not a poll (missing parts)
        not_poll_2 = {
            "type": "poll"
        }
        self.assertFalse(is_poll(not_poll_2))
        
        # None input
        self.assertFalse(is_poll(None))
    
    def test_format_timestamp(self):
        """Test timestamp formatting for polls."""
        # Test with valid timestamp
        timestamp = 1616513396  # March 23, 2021
        result = format_timestamp(timestamp)
        self.assertIn("Mar", result)
        self.assertIn("2021", result)
        
        # Test with None
        result = format_timestamp(None)
        self.assertEqual(result, "Unknown time")


class TestGetPollList(unittest.TestCase):
    """Tests for get_poll_list functionality."""
    
    @patch('pynews.poll_view.get_stories')
    @patch('pynews.poll_view.get_story')
    def test_get_poll_list_basic(self, mock_get_story, mock_get_stories):
        """Test basic poll list retrieval."""
        # Arrange
        story_ids = generate_poll_ids(10)
        mock_polls = generate_mock_poll_list(10)
        
        mock_get_stories.return_value = story_ids
        mock_get_story.side_effect = lambda id: next((p for p in mock_polls if p["id"] == id), None)
        
        # Act
        with patch('pynews.poll_view.LoadingIndicator'):
            result = get_poll_list(limit=5)
        
        # Assert
        self.assertEqual(len(result), 5)  # Should limit to 5 polls
        mock_get_stories.assert_called_once_with("top")
        self.assertEqual(mock_get_story.call_count, 10)  # Should try all 10 polls to find valid ones
    
    @patch('pynews.poll_view.get_stories')
    @patch('pynews.poll_view.get_story')
    def test_get_poll_list_min_score(self, mock_get_story, mock_get_stories):
        """Test poll list with minimum score filtering."""
        # Arrange
        story_ids = generate_poll_ids(10)
        
        # Create polls with alternating high/low scores
        mock_polls = []
        for i in range(10):
            poll_id = 30000 + (i * 100)
            score = 200 if i % 2 == 0 else 50  # Alternating high/low scores
            mock_polls.append(generate_mock_poll_story(poll_id, score))
        
        mock_get_stories.return_value = story_ids
        mock_get_story.side_effect = lambda id: next((p for p in mock_polls if p["id"] == id), None)
        
        # Act - filter for polls with score > 100
        with patch('pynews.poll_view.LoadingIndicator'):
            result = get_poll_list(min_score=100)
        
        # Assert
        self.assertEqual(len(result), 5)  # Half the polls should meet the criteria
        for poll in result:
            self.assertGreaterEqual(poll["score"], 100)
    
    @patch('pynews.poll_view.get_stories')
    @patch('pynews.poll_view.get_story')
    def test_get_poll_list_keyword_filter(self, mock_get_story, mock_get_stories):
        """Test poll list with keyword filtering."""
        # Arrange
        story_ids = generate_poll_ids(5)
        
        # Create polls with specific keywords
        mock_polls = [
            {
                "id": 30000,
                "type": "poll",
                "parts": [30001, 30002],
                "title": "Poll: What Python framework do you prefer?",
                "text": "Choose your favorite Python web framework",
                "score": 100
            },
            {
                "id": 30100,
                "type": "poll",
                "parts": [30101, 30102],
                "title": "Poll: Best JavaScript framework?",
                "text": "Vote for your preferred JS framework",
                "score": 150
            },
            {
                "id": 30200,
                "type": "poll",
                "parts": [30201, 30202],
                "title": "Poll: Python vs. JavaScript?",
                "text": "Which language do you prefer for web development",
                "score": 200
            },
            {
                "id": 30300,
                "type": "poll",
                "parts": [30301, 30302],
                "title": "Poll: Favorite database?",
                "text": "SQL or NoSQL?",
                "score": 120
            },
            {
                "id": 30400,
                "type": "poll",
                "parts": [30401, 30402],
                "title": "Poll: Text editor preference?",
                "text": "Which code editor or IDE do you use?",
                "score": 80
            }
        ]
        
        mock_get_stories.return_value = story_ids
        mock_get_story.side_effect = lambda id: next((p for p in mock_polls if p["id"] == id), None)
        
        # Act - filter for polls with Python keyword
        with patch('pynews.poll_view.LoadingIndicator'):
            result = get_poll_list(keywords=["python"])
        
        # Assert
        self.assertEqual(len(result), 2)  # Should find two polls with Python
        for poll in result:
            python_in_title = "Python" in poll["title"] or "python" in poll["title"]
            python_in_text = "Python" in poll["text"] or "python" in poll["text"]
            self.assertTrue(python_in_title or python_in_text)
    
    @patch('pynews.poll_view.get_stories')
    @patch('pynews.poll_view.get_story')
    def test_get_poll_list_sort_by_comments(self, mock_get_story, mock_get_stories):
        """Test poll list sorted by comment count."""
        # Arrange
        story_ids = generate_poll_ids(5)
        
        # Create polls with different comment counts
        mock_polls = []
        for i in range(5):
            poll_id = 30000 + (i * 100)
            descendants = i * 10  # 0, 10, 20, 30, 40 comments
            mock_polls.append(generate_mock_poll_story(poll_id, 100, descendants))
        
        mock_get_stories.return_value = story_ids
        mock_get_story.side_effect = lambda id: next((p for p in mock_polls if p["id"] == id), None)
        
        # Act - sort by comments
        with patch('pynews.poll_view.LoadingIndicator'):
            result = get_poll_list(sort_by_comments=True)
        
        # Assert
        self.assertEqual(len(result), 5)
        # Check descending order by comment count
        for i in range(1, len(result)):
            self.assertGreaterEqual(result[i-1]["descendants"], result[i]["descendants"])
    
    @patch('pynews.poll_view.get_stories')
    @patch('pynews.poll_view.get_story')
    def test_get_poll_list_sort_by_time(self, mock_get_story, mock_get_stories):
        """Test poll list sorted by submission time."""
        # Arrange
        story_ids = generate_poll_ids(5)
        
        # Create polls with different timestamps
        mock_polls = []
        base_time = 1616513396
        for i in range(5):
            poll_id = 30000 + (i * 100)
            timestamp = base_time + (i * 3600)  # Each 1 hour newer
            poll = generate_mock_poll_story(poll_id, 100, 20)
            poll["time"] = timestamp
            mock_polls.append(poll)
        
        mock_get_stories.return_value = story_ids
        mock_get_story.side_effect = lambda id: next((p for p in mock_polls if p["id"] == id), None)
        
        # Act - sort by time (newest first)
        with patch('pynews.poll_view.LoadingIndicator'):
            result = get_poll_list(sort_by_time=True)
        
        # Assert
        self.assertEqual(len(result), 5)
        # Check descending order by timestamp (newest first)
        for i in range(1, len(result)):
            self.assertGreaterEqual(result[i-1]["time"], result[i]["time"])


class TestDisplayPollTitles(unittest.TestCase):
    """Tests for display_poll_titles functionality."""
    
    @patch('pynews.poll_view.get_poll_list')
    @patch('pynews.poll_view.clear_screen')
    @patch('pynews.poll_view.print')
    def test_display_poll_titles_basic(self, mock_print, mock_clear, mock_get_poll_list):
        """Test basic poll titles display."""
        # Arrange
        mock_polls = generate_mock_poll_list(5)
        mock_get_poll_list.return_value = mock_polls
        
        # Act - simulate pressing 'q' to quit
        with patch('pynews.poll_view.getch', return_value='q'):
            display_poll_titles(limit=5)
        
        # Assert
        mock_get_poll_list.assert_called_once_with(
            limit=5, min_score=0, sort_by_comments=False, 
            sort_by_time=False, keywords=None, match_all=False, 
            case_sensitive=False
        )
        mock_clear.assert_called()
        self.assertTrue(mock_print.call_count > 5)  # Should print header and polls
    
    @patch('pynews.poll_view.get_poll_list')
    @patch('pynews.poll_view.clear_screen')
    @patch('pynews.poll_view.print')
    def test_display_poll_titles_empty(self, mock_print, mock_clear, mock_get_poll_list):
        """Test displaying poll titles when no polls found."""
        # Arrange
        mock_get_poll_list.return_value = []  # No polls found
        
        # Act
        with patch('pynews.poll_view.getch', return_value='q'):
            display_poll_titles()
        
        # Assert
        mock_get_poll_list.assert_called_once()
        mock_print.assert_any_call("No poll posts found matching your criteria.")
    
    @patch('pynews.poll_view.get_poll_list')
    @patch('pynews.poll_view.display_poll_details')
    @patch('pynews.poll_view.clear_screen')
    @patch('pynews.poll_view.print')
    def test_display_poll_titles_view_details(self, mock_print, mock_clear, 
                                             mock_display_details, mock_get_poll_list):
        """Test viewing poll details from the poll list."""
        # Arrange
        mock_polls = generate_mock_poll_list(5)
        mock_get_poll_list.return_value = mock_polls
        mock_display_details.return_value = {"action": "return_to_list"}
        
        # Act - simulate pressing Enter to view details, then q to quit
        with patch('pynews.poll_view.getch', side_effect=['\r', 'q']):
            display_poll_titles(limit=5)
        
        # Assert
        mock_get_poll_list.assert_called_once()
        mock_display_details.assert_called_once_with(mock_polls[0]["id"])
    
    @patch('pynews.poll_view.get_poll_list')
    @patch('pynews.poll_view.clear_screen')
    @patch('pynews.poll_view.print')
    def test_display_poll_titles_pagination(self, mock_print, mock_clear, mock_get_poll_list):
        """Test pagination in poll titles display."""
        # Arrange
        mock_polls = generate_mock_poll_list(15)  # 15 polls for multiple pages
        mock_get_poll_list.return_value = mock_polls
        
        # Act - simulate pressing 'n' (next page), 'p' (prev page), then 'q' to quit
        with patch('pynews.poll_view.getch', side_effect=['n', 'p', 'q']):
            display_poll_titles(limit=15, page_size=5)  # 5 polls per page
        
        # Assert
        mock_get_poll_list.assert_called_once()
        # clear_screen should be called multiple times for each page navigation
        self.assertTrue(mock_clear.call_count >= 3)


class TestDisplayPollDetails(unittest.TestCase):
    """Tests for display_poll_details functionality."""
    
    @patch('pynews.poll_view.get_story')
    @patch('pynews.poll_view.clear_screen')
    @patch('pynews.poll_view.print')
    def test_display_poll_details_success(self, mock_print, mock_clear, mock_get_story):
        """Test successful display of poll details."""
        # Arrange
        poll_id = 30000
        poll, options = generate_mock_poll_with_options(poll_id, 100, 20, 3)
        
        # Configure mock to return poll and options
        def side_effect(id):
            if id == poll_id:
                return poll
            return next((opt for opt in options if opt["id"] == id), None)
            
        mock_get_story.side_effect = side_effect
        
        # Act - simulate pressing 'q' to return to list
        with patch('pynews.poll_view.getch', return_value='q'):
            result = display_poll_details(poll_id)
        
        # Assert
        mock_get_story.assert_called_with(poll_id)  # Should fetch poll first
        for option in poll["parts"]:
            mock_get_story.assert_any_call(option)  # Should fetch each option
        
        mock_clear.assert_called()
        self.assertTrue(mock_print.call_count > 5)  # Should print poll and options
        self.assertEqual(result["action"], "return_to_list")
    
    @patch('pynews.poll_view.get_story')
    @patch('pynews.poll_view.print')
    def test_display_poll_details_not_found(self, mock_print, mock_get_story):
        """Test displaying details for a non-existent poll."""
        # Arrange
        poll_id = 99999
        mock_get_story.return_value = None  # Poll not found
        
        # Act - simulate pressing any key to continue
        with patch('pynews.poll_view.getch', return_value='x'):
            result = display_poll_details(poll_id)
        
        # Assert
        mock_get_story.assert_called_once_with(poll_id)
        mock_print.assert_any_call("Poll not found or not a valid poll.")
        self.assertEqual(result, None)
    
    @patch('pynews.poll_view.get_story')
    @patch('pynews.poll_view.print')
    def test_display_poll_details_not_a_poll(self, mock_print, mock_get_story):
        """Test displaying details for a post that's not a poll."""
        # Arrange
        story_id = 30000
        story = {
            "id": story_id,
            "title": "Not a poll",
            "type": "story"  # Not a poll type
        }
        mock_get_story.return_value = story
        
        # Act - simulate pressing any key to continue
        with patch('pynews.poll_view.getch', return_value='x'):
            result = display_poll_details(story_id)
        
        # Assert
        mock_get_story.assert_called_once_with(story_id)
        mock_print.assert_any_call("Poll not found or not a valid poll.")
        self.assertEqual(result, None)
    
    @patch('pynews.poll_view.get_story')
    @patch('pynews.poll_view.clear_screen')
    @patch('pynews.poll_view.print')
    def test_display_poll_details_view_comments(self, mock_print, mock_clear, mock_get_story):
        """Test viewing comments from poll details."""
        # Arrange
        poll_id = 30000
        poll, options = generate_mock_poll_with_options(poll_id, 100, 20, 3)
        
        # Configure mock to return poll and options
        def side_effect(id):
            if id == poll_id:
                return poll
            return next((opt for opt in options if opt["id"] == id), None)
            
        mock_get_story.side_effect = side_effect
        
        # Act - simulate pressing 'c' to view comments
        with patch('pynews.poll_view.getch', return_value='c'):
            result = display_poll_details(poll_id)
        
        # Assert
        mock_get_story.assert_called_with(poll_id)
        self.assertEqual(result["action"], "view_comments")
        self.assertEqual(result["story_id"], poll_id)


if __name__ == '__main__':
    unittest.main()