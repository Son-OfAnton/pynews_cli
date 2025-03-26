"""
Unit tests for comment display and formatting functions in PyNews.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import time

# Add the parent directory to the path so we can import the modules
sys.path.append("..")

from pynews.comments import (
    clean_comment_text,
    format_timestamp,
    format_comment,
    display_page_of_comments,
    flatten_comment_tree
)
from test_utils import generate_mock_comment, generate_comment_tree_data


class TestFormatTimestamp(unittest.TestCase):
    """Tests for the format_timestamp function."""

    @patch('pynews.comments.time.time')
    def test_format_timestamp_now(self, mock_time):
        """Test formatting a timestamp for the current time."""
        # Arrange
        mock_time.return_value = 1616513496
        timestamp = 1616513496  # Same time (now)
        
        # Act
        result = format_timestamp(timestamp)
        
        # Assert
        self.assertEqual(result, "just now")

    @patch('pynews.comments.time.time')
    def test_format_timestamp_minutes_ago(self, mock_time):
        """Test formatting a timestamp for a few minutes ago."""
        # Arrange
        mock_time.return_value = 1616513496
        timestamp = 1616513496 - (5 * 60)  # 5 minutes ago
        
        # Act
        result = format_timestamp(timestamp)
        
        # Assert
        self.assertEqual(result, "5 minutes ago")

    @patch('pynews.comments.time.time')
    def test_format_timestamp_hours_ago(self, mock_time):
        """Test formatting a timestamp for a few hours ago."""
        # Arrange
        mock_time.return_value = 1616513496
        timestamp = 1616513496 - (3 * 60 * 60)  # 3 hours ago
        
        # Act
        result = format_timestamp(timestamp)
        
        # Assert
        self.assertEqual(result, "3 hours ago")

    @patch('pynews.comments.time.time')
    def test_format_timestamp_days_ago(self, mock_time):
        """Test formatting a timestamp for a few days ago."""
        # Arrange
        mock_time.return_value = 1616513496
        timestamp = 1616513496 - (2 * 24 * 60 * 60)  # 2 days ago
        
        # Act
        result = format_timestamp(timestamp)
        
        # Assert
        self.assertEqual(result, "2 days ago")


class TestFormatComment(unittest.TestCase):
    """Tests for the format_comment function."""

    def test_format_comment_basic(self):
        """Test basic comment formatting."""
        # Arrange
        comment = {
            'id': 123,
            'by': 'testuser',
            'text': 'This is a test comment',
            'time': int(time.time()) - 3600,  # 1 hour ago
            'children': []
        }
        level = 0
        width = 80
        
        # Act
        header, body = format_comment(comment, level, width, None)
        
        # Assert
        self.assertIn('testuser', header)
        self.assertIn('hour ago', header)
        self.assertEqual(body, 'This is a test comment')

    def test_format_comment_with_indentation(self):
        """Test comment formatting with indentation for replies."""
        # Arrange
        comment = {
            'id': 123,
            'by': 'testuser',
            'text': 'This is a nested comment',
            'time': int(time.time()) - 3600,  # 1 hour ago
            'children': []
        }
        level = 2  # Indent level 2
        width = 80
        
        # Act
        header, body = format_comment(comment, level, width, None)
        
        # Assert
        # Check that the body is indented
        self.assertTrue(body.startswith('    '))  # 4 spaces for level 2

    def test_format_comment_with_deleted(self):
        """Test formatting for a deleted comment."""
        # Arrange
        comment = {
            'id': 123,
            'deleted': True,
            'time': int(time.time()) - 3600,  # 1 hour ago
        }
        level = 0
        width = 80
        
        # Act
        header, body = format_comment(comment, level, width, None)
        
        # Assert
        self.assertIn('[deleted]', header)
        self.assertEqual(body, '[Comment deleted]')

    def test_format_comment_with_dead(self):
        """Test formatting for a dead (flagged) comment."""
        # Arrange
        comment = {
            'id': 123,
            'by': 'testuser',
            'text': 'This is a flagged comment',
            'time': int(time.time()) - 3600,  # 1 hour ago
            'dead': True,
            'children': []
        }
        level = 0
        width = 80
        
        # Act
        header, body = format_comment(comment, level, width, None)
        
        # Assert
        self.assertIn('[flagged]', header)


class TestFlattenCommentTree(unittest.TestCase):
    """Tests for the flatten_comment_tree function."""

    def test_flatten_empty_tree(self):
        """Test flattening an empty comment tree."""
        # Arrange
        comments = []
        flat_list = []
        indent_levels = {}
        parent_index = {}
        
        # Act
        flatten_comment_tree(comments, flat_list, indent_levels, parent_index, 0, 0)
        
        # Assert
        self.assertEqual(flat_list, [])
        self.assertEqual(indent_levels, {})
        self.assertEqual(parent_index, {})

    def test_flatten_simple_tree(self):
        """Test flattening a simple comment tree without nesting."""
        # Arrange
        comments = [
            {'id': 111, 'children': []},
            {'id': 222, 'children': []},
            {'id': 333, 'children': []}
        ]
        flat_list = []
        indent_levels = {}
        parent_index = {}
        
        # Act
        flatten_comment_tree(comments, flat_list, indent_levels, parent_index, 0, 0)
        
        # Assert
        self.assertEqual(len(flat_list), 3)
        self.assertEqual(flat_list[0]['id'], 111)
        self.assertEqual(flat_list[1]['id'], 222)
        self.assertEqual(flat_list[2]['id'], 333)
        
        # All should be at level 0
        self.assertEqual(indent_levels[111], 0)
        self.assertEqual(indent_levels[222], 0)
        self.assertEqual(indent_levels[333], 0)

    def test_flatten_nested_tree(self):
        """Test flattening a nested comment tree."""
        # Arrange
        comments = [
            {
                'id': 111,
                'children': [
                    {'id': 222, 'children': []},
                    {'id': 333, 'children': []}
                ]
            },
            {'id': 444, 'children': []}
        ]
        flat_list = []
        indent_levels = {}
        parent_index = {}
        
        # Act
        flatten_comment_tree(comments, flat_list, indent_levels, parent_index, 0, 0)
        
        # Assert
        self.assertEqual(len(flat_list), 4)
        self.assertEqual(flat_list[0]['id'], 111)
        self.assertEqual(flat_list[1]['id'], 222)
        self.assertEqual(flat_list[2]['id'], 333)
        self.assertEqual(flat_list[3]['id'], 444)
        
        # Check indentation levels
        self.assertEqual(indent_levels[111], 0)  # Root comment
        self.assertEqual(indent_levels[222], 1)  # Child of 111
        self.assertEqual(indent_levels[333], 1)  # Child of 111
        self.assertEqual(indent_levels[444], 0)  # Root comment
        
        # Check parent indices
        self.assertEqual(parent_index[222], 0)  # Parent is at index 0
        self.assertEqual(parent_index[333], 0)  # Parent is at index 0


class TestDisplayPageOfComments(unittest.TestCase):
    """Tests for the display_page_of_comments function."""

    @patch('pynews.comments.format_comment')
    @patch('pynews.comments.print')
    def test_display_page_of_comments_empty(self, mock_print, mock_format_comment):
        """Test displaying a page of comments when there are no comments."""
        # Arrange
        flat_comments = []
        indent_levels = {}
        
        # Act
        display_page_of_comments(flat_comments, indent_levels, 1, 10, 80)
        
        # Assert
        mock_format_comment.assert_not_called()
        mock_print.assert_called_once_with("No comments found for this story.")

    @patch('pynews.comments.format_comment')
    @patch('pynews.comments.print')
    def test_display_page_of_comments_first_page(self, mock_print, mock_format_comment):
        """Test displaying the first page of comments."""
        # Arrange
        # Create 15 comments to span multiple pages
        flat_comments = []
        indent_levels = {}
        
        for i in range(15):
            comment = {
                'id': 1000 + i,
                'text': f'Comment {i}',
                'by': f'user{i}',
                'time': int(time.time()) - i*3600
            }
            flat_comments.append(comment)
            indent_levels[1000 + i] = 0
        
        # Mock format_comment to return tuple for header and body
        mock_format_comment.side_effect = lambda c, l, w, hl: (
            f"Header for comment {c['id']}", 
            f"Body for comment {c['id']}"
        )
        
        # Act - Display first page with 10 comments per page
        display_page_of_comments(flat_comments, indent_levels, 1, 10, 80)
        
        # Assert
        # Should format first 10 comments only
        self.assertEqual(mock_format_comment.call_count, 10)
        
        # Check that the 10 comments were printed (2 print calls each - header and body)
        # Plus 2 for pagination info
        self.assertEqual(mock_print.call_count, 22)

    @patch('pynews.comments.format_comment')
    @patch('pynews.comments.print')
    def test_display_page_of_comments_second_page(self, mock_print, mock_format_comment):
        """Test displaying the second page of comments."""
        # Arrange
        # Create 15 comments to span multiple pages
        flat_comments = []
        indent_levels = {}
        
        for i in range(15):
            comment = {
                'id': 1000 + i,
                'text': f'Comment {i}',
                'by': f'user{i}',
                'time': int(time.time()) - i*3600
            }
            flat_comments.append(comment)
            indent_levels[1000 + i] = 0
        
        # Mock format_comment to return tuple for header and body
        mock_format_comment.side_effect = lambda c, l, w, hl: (
            f"Header for comment {c['id']}", 
            f"Body for comment {c['id']}"
        )
        
        # Act - Display second page with 10 comments per page
        display_page_of_comments(flat_comments, indent_levels, 2, 10, 80)
        
        # Assert
        # Should format the remaining 5 comments
        self.assertEqual(mock_format_comment.call_count, 5)
        
        # Check that all 5 comments were printed (2 print calls each - header and body)
        # Plus 2 for pagination info
        self.assertEqual(mock_print.call_count, 12)


if __name__ == '__main__':
    unittest.main()