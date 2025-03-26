"""
Integration tests for the comment display functionality in PyNews.

These tests focus on the display_comments_for_story function and how it
integrates with other comment-related functionality.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Add the parent directory to the path so we can import the modules
sys.path.append("..")

from pynews.comments import display_comments_for_story
from test_utils import generate_mock_story, generate_mock_comment, generate_comment_tree_data


class TestDisplayCommentsForStory(unittest.TestCase):
    """Tests for the display_comments_for_story function."""

    @patch('pynews.comments.fetch_item')
    @patch('pynews.comments.fetch_comment_tree')
    @patch('pynews.comments.display_page_of_comments')
    @patch('pynews.comments.LoadingIndicator')
    @patch('pynews.comments.clear_screen')
    @patch('pynews.comments.print')
    def test_display_story_with_comments(self, mock_print, mock_clear, mock_loader, 
                                        mock_display_page, mock_fetch_tree, mock_fetch_item):
        """Test displaying a story with comments."""
        # Arrange
        story_id = 12345
        story = generate_mock_story(story_id)
        story['kids'] = [111, 222]
        
        # Mock comment tree
        comment_tree = [
            {'id': 111, 'text': 'Comment 1', 'by': 'user1', 'time': 1616513396, 'children': []},
            {'id': 222, 'text': 'Comment 2', 'by': 'user2', 'time': 1616513496, 'children': []}
        ]
        
        # Configure mocks
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        mock_fetch_item.return_value = story
        mock_fetch_tree.return_value = comment_tree
        
        # Mock getch to simulate pressing 'q' to quit
        with patch('pynews.comments.getch', return_value='q'):
            # Act
            result = display_comments_for_story(story_id)
        
        # Assert
        mock_fetch_item.assert_called_once_with(story_id)
        mock_fetch_tree.assert_called_once_with(story['kids'], 10, mock_loader_instance.update_progress)
        mock_display_page.assert_called_once()
        
        # Verify the result
        self.assertEqual(result, (1, 1, 2))  # (total_pages, current_page, total_comments)

    @patch('pynews.comments.fetch_item')
    @patch('pynews.comments.print')
    def test_display_story_not_found(self, mock_print, mock_fetch_item):
        """Test displaying a story that doesn't exist."""
        # Arrange
        story_id = 99999
        mock_fetch_item.return_value = None
        
        # Act
        result = display_comments_for_story(story_id)
        
        # Assert
        mock_fetch_item.assert_called_once_with(story_id)
        mock_print.assert_called_once()  # Error message printed
        self.assertEqual(result, (0, 0, 0))  # (total_pages, current_page, total_comments)

    @patch('pynews.comments.fetch_item')
    @patch('pynews.comments.fetch_comment_tree')
    @patch('pynews.comments.display_page_of_comments')
    @patch('pynews.comments.LoadingIndicator')
    @patch('pynews.comments.clear_screen')
    @patch('pynews.comments.print')
    def test_display_story_no_comments(self, mock_print, mock_clear, mock_loader, 
                                     mock_display_page, mock_fetch_tree, mock_fetch_item):
        """Test displaying a story with no comments."""
        # Arrange
        story_id = 12345
        story = generate_mock_story(story_id)
        story['kids'] = []  # No comments
        
        # Configure mocks
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        mock_fetch_item.return_value = story
        
        # Mock getch to simulate pressing 'q' to quit
        with patch('pynews.comments.getch', return_value='q'):
            # Act
            result = display_comments_for_story(story_id)
        
        # Assert
        mock_fetch_item.assert_called_once_with(story_id)
        mock_fetch_tree.assert_not_called()  # No comments to fetch
        
        # Verify the result
        self.assertEqual(result, (0, 1, 0))  # (total_pages, current_page, total_comments)

    @patch('pynews.comments.fetch_item')
    @patch('pynews.comments.fetch_comment_tree')
    @patch('pynews.comments.sort_comment_tree')
    @patch('pynews.comments.display_page_of_comments')
    @patch('pynews.comments.LoadingIndicator')
    @patch('pynews.comments.clear_screen')
    @patch('pynews.comments.print')
    def test_comment_sorting(self, mock_print, mock_clear, mock_loader, mock_display_page, 
                           mock_sort, mock_fetch_tree, mock_fetch_item):
        """Test sorting comments in display_comments_for_story."""
        # Arrange
        story_id = 12345
        story = generate_mock_story(story_id)
        story['kids'] = [111, 222]
        
        # Mock comment tree
        comment_tree = [
            {'id': 111, 'text': 'Comment 1', 'by': 'user1', 'time': 1616513396, 'children': []},
            {'id': 222, 'text': 'Comment 2', 'by': 'user2', 'time': 1616513496, 'children': []}
        ]
        
        # Configure mocks
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        mock_fetch_item.return_value = story
        mock_fetch_tree.return_value = comment_tree
        mock_sort.return_value = comment_tree  # Return the same tree for simplicity
        
        # Mock getch to simulate pressing 'n' (sort by newest) and then 'q' to quit
        with patch('pynews.comments.getch', side_effect=['n', 'q']):
            # Act
            result = display_comments_for_story(story_id)
        
        # Assert
        mock_fetch_item.assert_called_once_with(story_id)
        mock_fetch_tree.assert_called_once()
        
        # Verify that sort_comment_tree was called with "newest"
        mock_sort.assert_called_with(comment_tree, "newest", None)

    @patch('pynews.comments.fetch_item')
    @patch('pynews.comments.fetch_comment_tree')
    @patch('pynews.comments.display_page_of_comments')
    @patch('pynews.comments.LoadingIndicator')
    @patch('pynews.comments.clear_screen')
    @patch('pynews.comments.print')
    def test_pagination(self, mock_print, mock_clear, mock_loader, mock_display_page, 
                       mock_fetch_tree, mock_fetch_item):
        """Test pagination in display_comments_for_story."""
        # Arrange
        story_id = 12345
        story = generate_mock_story(story_id)
        
        # Generate 25 comments to fill multiple pages with default page size of 10
        story['kids'] = list(range(1000, 1025))
        
        # Mock comment tree - create 25 comments
        comment_tree = []
        for i in range(1000, 1025):
            comment_tree.append({
                'id': i, 
                'text': f'Comment {i}', 
                'by': f'user{i}', 
                'time': 1616513396 + i, 
                'children': []
            })
        
        # Configure mocks
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        mock_fetch_item.return_value = story
        mock_fetch_tree.return_value = comment_tree
        
        # Mock getch to simulate pressing 'n' (next page), 'p' (prev page) and then 'q' to quit
        with patch('pynews.comments.getch', side_effect=['n', 'p', 'q']):
            # Act
            result = display_comments_for_story(story_id)
        
        # Assert
        mock_fetch_item.assert_called_once_with(story_id)
        mock_fetch_tree.assert_called_once()
        
        # Verify that display_page_of_comments was called once for page 1, once for page 2, 
        # and once for page 1 again after going back
        self.assertEqual(mock_display_page.call_count, 3)
        
        # Expected pages: 3 (25 comments with page size 10)
        self.assertEqual(result[0], 3)  # total_pages


if __name__ == '__main__':
    unittest.main()