"""
Unit tests for the Ask HN functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO
import time

# Add the parent directory to the path so we can import the modules
sys.path.append("..") # Add parent directory to path

from pynews.ask_view import (
    display_ask_story_details,
    display_top_scored_ask_stories,
    format_timestamp,
    format_time_detailed,
    clean_text,
    format_score,
    format_comment_count_detailed,
    highlight_keywords_in_text
)
from test_ask_utils import (
    create_mock_response,
    generate_mock_ask_story,
    generate_mock_ask_stories,
    generate_ask_story_ids
)


class TestAskViewUtilityFunctions(unittest.TestCase):
    """Tests for utility functions in the Ask HN view module."""
    
    def test_clean_text(self):
        """Test the clean_text function for HTML cleaning."""
        # Test basic HTML cleaning
        html_text = "<p>This is a <b>test</b> with <i>formatting</i>.</p>"
        expected = "This is a test with formatting."
        self.assertEqual(clean_text(html_text), expected)
        
        # Test with line breaks
        html_text = "<p>Line 1</p><p>Line 2</p>"
        expected = "Line 1\n\nLine 2"
        self.assertEqual(clean_text(html_text), expected)
        
        # Test with code
        html_text = "Check <pre><code>def test(): pass</code></pre>"
        expected = "Check \n\n    def test(): pass"
        self.assertEqual(clean_text(html_text), expected)
    
    @patch('pynews.ask_view.time')
    def test_format_timestamp(self, mock_time):
        """Test format_timestamp function."""
        # Mock current time
        mock_time.time.return_value = 1616513396
        
        # Test with a valid timestamp
        timestamp = 1616513396 - 3600  # 1 hour ago
        result = format_timestamp(timestamp)
        self.assertIn("2021", result)  # Contains year
        self.assertIn("Mar", result)   # Contains month
        
        # Test with None
        result = format_timestamp(None)
        self.assertIn("Unknown time", result)
    
    @patch('pynews.ask_view.format_time_ago')
    def test_format_time_detailed(self, mock_format_time_ago):
        """Test format_time_detailed function."""
        mock_format_time_ago.return_value = "1 hour ago"
        
        # Test with a valid timestamp
        timestamp = int(time.time()) - 3600  # 1 hour ago
        result = format_time_detailed(timestamp)
        self.assertIn("1 hour ago", result)
        self.assertIn("2023", result) if "2023" in result else self.assertIn("2024", result)
        
        # Test with None
        result = format_time_detailed(None)
        self.assertEqual(result, "Unknown time")
    
    def test_format_score(self):
        """Test format_score function."""
        # Test with various scores
        self.assertTrue("100" in format_score(100))
        self.assertTrue("0" in format_score(0))
        self.assertTrue("1,234" in format_score(1234))
    
    def test_format_comment_count_detailed(self):
        """Test format_comment_count_detailed function."""
        # Test with various comment counts
        self.assertTrue("5 comments" in format_comment_count_detailed(5))
        self.assertTrue("1 comment" in format_comment_count_detailed(1))
        self.assertTrue("No comments" in format_comment_count_detailed(0))
    
    def test_highlight_keywords_in_text(self):
        """Test keyword highlighting in text."""
        # Regular text with keywords
        text = "This is a test with Python and JavaScript"
        keywords = ["python", "javascript"]
        
        # Case insensitive (default)
        result = highlight_keywords_in_text(text, keywords)
        self.assertNotEqual(result, text)  # Result should be different (highlighted)
        
        # Case sensitive
        result = highlight_keywords_in_text(text, keywords, case_sensitive=True)
        self.assertEqual(result, text)  # No match due to case sensitivity
        
        # Case sensitive with exact case
        result = highlight_keywords_in_text(text, ["Python"], case_sensitive=True)
        self.assertNotEqual(result, text)  # Should match


class TestDisplayAskStoryDetails(unittest.TestCase):
    """Tests for the display_ask_story_details function."""
    
    @patch('pynews.ask_view.get_story')
    @patch('pynews.ask_view.clear_screen')
    @patch('pynews.ask_view.print')
    def test_display_ask_story_details_success(self, mock_print, mock_clear, mock_get_story):
        """Test displaying an Ask HN story successfully."""
        # Arrange
        story_id = 12345
        mock_story = generate_mock_ask_story(story_id)
        mock_get_story.return_value = mock_story
        
        # Act
        with patch('pynews.ask_view.getch', return_value='q'):
            display_ask_story_details(story_id)
        
        # Assert
        mock_get_story.assert_called_once_with(story_id)
        mock_clear.assert_called()
        mock_print.assert_called()  # Should print various parts of the story
    
    @patch('pynews.ask_view.get_story')
    @patch('pynews.ask_view.print')
    def test_display_ask_story_details_not_found(self, mock_print, mock_get_story):
        """Test displaying a non-existent Ask HN story."""
        # Arrange
        story_id = 99999
        mock_get_story.return_value = None  # Story not found
        
        # Act
        display_ask_story_details(story_id)
        
        # Assert
        mock_get_story.assert_called_once_with(story_id)
        mock_print.assert_called_once()  # Should print error message
    
    @patch('pynews.ask_view.get_story')
    @patch('pynews.ask_view.clear_screen')
    @patch('pynews.ask_view.print')
    def test_display_ask_story_with_keywords(self, mock_print, mock_clear, mock_get_story):
        """Test displaying an Ask HN story with keyword highlighting."""
        # Arrange
        story_id = 12345
        mock_story = generate_mock_ask_story(story_id)
        mock_story["text"] = "This is a test with Python code"
        mock_get_story.return_value = mock_story
        
        # Act
        with patch('pynews.ask_view.getch', return_value='q'):
            display_ask_story_details(story_id, keywords=["python"])
        
        # Assert
        mock_get_story.assert_called_once_with(story_id)
        mock_clear.assert_called()


class TestDisplayTopScoredAskStories(unittest.TestCase):
    """Tests for the display_top_scored_ask_stories function."""
    
    @patch('pynews.ask_view.get_stories')
    @patch('pynews.ask_view.clear_screen')
    @patch('pynews.ask_view.print')
    def test_display_top_scored_ask_stories_success(self, mock_print, mock_clear, mock_get_stories):
        """Test displaying top scored Ask HN stories."""
        # Arrange
        mock_stories = generate_mock_ask_stories(10)
        mock_get_stories.return_value = generate_ask_story_ids(100)
        
        # Configure mock to return stories
        with patch('pynews.ask_view.get_story', side_effect=lambda id: 
                  next((s for s in mock_stories if s['id'] == id), None)):
            # Act
            with patch('pynews.ask_view.LoadingIndicator'):
                with patch('pynews.ask_view.getch', return_value='q'):
                    display_top_scored_ask_stories(limit=5)
        
        # Assert
        mock_get_stories.assert_called_once()
        mock_clear.assert_called()
        self.assertTrue(mock_print.call_count > 5)  # Should print multiple stories
    
    @patch('pynews.ask_view.get_stories')
    @patch('pynews.ask_view.print')
    def test_display_top_scored_ask_stories_no_results(self, mock_print, mock_get_stories):
        """Test displaying top scored Ask HN stories with no matching results."""
        # Arrange
        mock_get_stories.return_value = []  # No stories
        
        # Act
        with patch('pynews.ask_view.LoadingIndicator'):
            display_top_scored_ask_stories()
        
        # Assert
        mock_get_stories.assert_called_once()
        mock_print.assert_called_with("No Ask HN stories found matching your criteria.")
    
    @patch('pynews.ask_view.get_stories')
    @patch('pynews.ask_view.clear_screen')
    @patch('pynews.ask_view.print')
    def test_display_top_scored_ask_stories_with_min_score(self, mock_print, mock_clear, mock_get_stories):
        """Test displaying Ask HN stories with minimum score filter."""
        # Arrange
        # Create stories with different scores
        mock_stories = []
        for i in range(10):
            mock_stories.append(generate_mock_ask_story(
                story_id=10000 + i,
                score=(i + 1) * 50  # Scores: 50, 100, 150, ..., 500
            ))
        
        mock_get_stories.return_value = [s['id'] for s in mock_stories]
        
        # Configure mock to return stories
        with patch('pynews.ask_view.get_story', side_effect=lambda id: 
                  next((s for s in mock_stories if s['id'] == id), None)):
            # Act - Set min_score to 200
            with patch('pynews.ask_view.LoadingIndicator'):
                with patch('pynews.ask_view.getch', return_value='q'):
                    display_top_scored_ask_stories(min_score=200)
        
        # Assert
        mock_get_stories.assert_called_once()
        mock_clear.assert_called()
    
    @patch('pynews.ask_view.get_stories')
    @patch('pynews.ask_view.clear_screen')
    @patch('pynews.ask_view.print')
    def test_display_top_scored_ask_stories_sorted_by_comments(self, mock_print, mock_clear, mock_get_stories):
        """Test displaying Ask HN stories sorted by comment count."""
        # Arrange
        mock_stories = []
        for i in range(10):
            mock_stories.append(generate_mock_ask_story(
                story_id=10000 + i,
                descendants=i * 5  # Comment counts: 0, 5, 10, ..., 45
            ))
        
        mock_get_stories.return_value = [s['id'] for s in mock_stories]
        
        # Configure mock to return stories
        with patch('pynews.ask_view.get_story', side_effect=lambda id: 
                  next((s for s in mock_stories if s['id'] == id), None)):
            # Act - Sort by comments
            with patch('pynews.ask_view.LoadingIndicator'):
                with patch('pynews.ask_view.getch', return_value='q'):
                    display_top_scored_ask_stories(sort_by_comments=True)
        
        # Assert
        mock_get_stories.assert_called_once()
        mock_clear.assert_called()
    
    @patch('pynews.ask_view.get_stories')
    @patch('pynews.ask_view.clear_screen')
    @patch('pynews.ask_view.print')
    def test_display_top_scored_ask_stories_with_keywords(self, mock_print, mock_clear, mock_get_stories):
        """Test displaying Ask HN stories filtered by keywords."""
        # Arrange
        mock_stories = [
            generate_mock_ask_story(10001, title="Ask HN: Python question?", 
                                 text="Looking for Python advice"),
            generate_mock_ask_story(10002, title="Ask HN: JavaScript question?", 
                                 text="Need help with JavaScript"),
            generate_mock_ask_story(10003, title="Ask HN: Career advice?", 
                                 text="Should I learn Python or JavaScript?")
        ]
        
        mock_get_stories.return_value = [s['id'] for s in mock_stories]
        
        # Configure mock to return stories
        with patch('pynews.ask_view.get_story', side_effect=lambda id: 
                  next((s for s in mock_stories if s['id'] == id), None)):
            # Act - Filter by Python keyword
            with patch('pynews.ask_view.LoadingIndicator'):
                with patch('pynews.ask_view.getch', return_value='q'):
                    display_top_scored_ask_stories(keywords=["python"])
        
        # Assert
        mock_get_stories.assert_called_once()
        mock_clear.assert_called()


if __name__ == '__main__':
    unittest.main()