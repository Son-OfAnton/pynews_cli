"""
Unit tests for the comment fetching functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the modules
# sys.path.append("..")

from pynews.comments import fetch_item, fetch_comment_tree, sort_comment_tree, clean_comment_text, count_comment_tree
from pynews.constants import URLS
from test_utils import create_mock_response, generate_mock_story, generate_mock_comment, generate_comment_tree_data
import os


class TestFetchItem(unittest.TestCase):
    """Tests for the fetch_item function."""

    @patch('pynews.comments.requests.get')
    def test_fetch_item_success(self, mock_get):
        """Test fetch_item with a successful API response."""
        # Arrange
        item_id = 12345
        expected_data = {"id": item_id, "title": "Test Story", "by": "test_user"}
        mock_get.return_value = create_mock_response(200, expected_data)
        
        # Act
        result = fetch_item(item_id)
        
        # Assert
        mock_get.assert_called_once_with(URLS['item'].format(item_id))
        self.assertEqual(result, expected_data)

    @patch('pynews.comments.requests.get')
    def test_fetch_item_not_found(self, mock_get):
        """Test fetch_item with a 404 response."""
        # Arrange
        item_id = 99999
        mock_get.return_value = create_mock_response(404, None)
        
        # Act
        result = fetch_item(item_id)
        
        # Assert
        mock_get.assert_called_once_with(URLS['item'].format(item_id))
        self.assertIsNone(result)

    @patch('pynews.comments.requests.get')
    def test_fetch_item_exception(self, mock_get):
        """Test fetch_item handling a request exception."""
        # Arrange
        item_id = 12345
        mock_get.side_effect = Exception("Network error")
        
        # Act
        result = fetch_item(item_id)
        
        # Assert
        mock_get.assert_called_once_with(URLS['item'].format(item_id))
        self.assertIsNone(result)


class TestFetchCommentTree(unittest.TestCase):
    """Tests for the fetch_comment_tree function."""

    @patch('pynews.comments.fetch_item')
    def test_fetch_comment_tree_empty(self, mock_fetch_item):
        """Test fetch_comment_tree with empty comment IDs."""
        # Act
        result = fetch_comment_tree([])
        
        # Assert
        mock_fetch_item.assert_not_called()
        self.assertEqual(result, [])

    @patch('pynews.comments.fetch_item')
    def test_fetch_comment_tree_simple(self, mock_fetch_item):
        """Test fetch_comment_tree with a simple list of comment IDs."""
        # Arrange
        comment_ids = [111, 222]
        comment1 = generate_mock_comment(111, 12345)
        comment2 = generate_mock_comment(222, 12345)
        
        # Configure mock to return different values based on input
        mock_fetch_item.side_effect = lambda item_id: {
            111: comment1,
            222: comment2,
        }.get(item_id)
        
        # Act
        result = fetch_comment_tree(comment_ids)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 111)
        self.assertEqual(result[1]['id'], 222)
        self.assertEqual(result[0]['children'], [])  # No child comments
        self.assertEqual(result[1]['children'], [])

    @patch('pynews.comments.fetch_item')
    def test_fetch_comment_tree_nested(self, mock_fetch_item):
        """Test fetch_comment_tree with nested comments."""
        # Arrange
        # Comment structure: 111 has children 222 and 333, 222 has child 444
        comment1 = generate_mock_comment(111, 12345, [222, 333])
        comment2 = generate_mock_comment(222, 111, [444])
        comment3 = generate_mock_comment(333, 111)
        comment4 = generate_mock_comment(444, 222)
        
        mock_fetch_item.side_effect = lambda item_id: {
            111: comment1,
            222: comment2,
            333: comment3,
            444: comment4,
        }.get(item_id)
        
        # Act
        result = fetch_comment_tree([111])
        
        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 111)
        
        # Verify the comment tree structure
        children = result[0]['children']
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0]['id'], 222)
        self.assertEqual(children[1]['id'], 333)
        
        # Check grandchild comment
        grandchildren = children[0]['children']
        self.assertEqual(len(grandchildren), 1)
        self.assertEqual(grandchildren[0]['id'], 444)

    @patch('pynews.comments.fetch_item')
    def test_fetch_comment_tree_with_deleted(self, mock_fetch_item):
        """Test fetch_comment_tree properly handles deleted comments."""
        # Arrange
        comment1 = generate_mock_comment(111, 12345, [222, 333])
        comment2 = generate_mock_comment(222, 111, deleted=True)
        comment3 = generate_mock_comment(333, 111)
        
        mock_fetch_item.side_effect = lambda item_id: {
            111: comment1,
            222: comment2,
            333: comment3,
        }.get(item_id)
        
        # Act
        result = fetch_comment_tree([111])
        
        # Assert
        self.assertEqual(len(result), 1)
        children = result[0]['children']
        self.assertEqual(len(children), 2)  # Both children are included
        
        # Check if deleted comment is properly marked
        self.assertTrue(children[0].get('deleted', False))
        self.assertFalse(children[1].get('deleted', False))

    @patch('pynews.comments.fetch_item')
    def test_fetch_comment_tree_with_dead(self, mock_fetch_item):
        """Test fetch_comment_tree properly handles dead comments."""
        # Arrange
        comment1 = generate_mock_comment(111, 12345, [222, 333])
        comment2 = generate_mock_comment(222, 111)
        comment3 = generate_mock_comment(333, 111, dead=True)
        
        mock_fetch_item.side_effect = lambda item_id: {
            111: comment1,
            222: comment2,
            333: comment3,
        }.get(item_id)
        
        # Act
        result = fetch_comment_tree([111])
        
        # Assert
        self.assertEqual(len(result), 1)
        children = result[0]['children']
        self.assertEqual(len(children), 2)  # Both children are included
        
        # Check if dead comment is properly marked
        self.assertFalse(children[0].get('dead', False))
        self.assertTrue(children[1].get('dead', False))

    @patch('pynews.comments.fetch_item')
    def test_fetch_comment_tree_with_none_response(self, mock_fetch_item):
        """Test fetch_comment_tree properly handles None responses from fetch_item."""
        # Arrange
        comment1 = generate_mock_comment(111, 12345, [222, 333])
        # Simulate 222 not being found
        comment3 = generate_mock_comment(333, 111)
        
        mock_fetch_item.side_effect = lambda item_id: {
            111: comment1,
            222: None,
            333: comment3,
        }.get(item_id)
        
        # Act
        result = fetch_comment_tree([111])
        
        # Assert
        self.assertEqual(len(result), 1)
        children = result[0]['children']
        self.assertEqual(len(children), 1)  # Only one child is included
        self.assertEqual(children[0]['id'], 333)


class TestSortCommentTree(unittest.TestCase):
    """Tests for the sort_comment_tree function."""

    def test_sort_comment_tree_by_newest(self):
        """Test sorting a comment tree by newest first."""
        # Arrange - Create comments with different timestamps
        comments = [
            {
                'id': 111,
                'time': 1616513396,  # Oldest
                'children': []
            },
            {
                'id': 222,
                'time': 1616513496,  # Middle
                'children': []
            },
            {
                'id': 333,
                'time': 1616513596,  # Newest
                'children': []
            }
        ]
        
        # Act
        sorted_comments = sort_comment_tree(comments, "newest")
        
        # Assert
        self.assertEqual(sorted_comments[0]['id'], 333)
        self.assertEqual(sorted_comments[1]['id'], 222)
        self.assertEqual(sorted_comments[2]['id'], 111)

    def test_sort_comment_tree_by_oldest(self):
        """Test sorting a comment tree by oldest first."""
        # Arrange - Create comments with different timestamps
        comments = [
            {
                'id': 111,
                'time': 1616513396,  # Oldest
                'children': []
            },
            {
                'id': 222,
                'time': 1616513496,  # Middle
                'children': []
            },
            {
                'id': 333,
                'time': 1616513596,  # Newest
                'children': []
            }
        ]
        
        # Act
        sorted_comments = sort_comment_tree(comments, "oldest")
        
        # Assert
        self.assertEqual(sorted_comments[0]['id'], 111)
        self.assertEqual(sorted_comments[1]['id'], 222)
        self.assertEqual(sorted_comments[2]['id'], 333)

    def test_sort_comment_tree_recursive(self):
        """Test that sorting applies recursively to child comments."""
        # Arrange - Create nested comments with different timestamps
        comments = [
            {
                'id': 111,
                'time': 1616513396,  # Parent
                'children': [
                    {
                        'id': 222,
                        'time': 1616513596,  # Newer child
                        'children': []
                    },
                    {
                        'id': 333,
                        'time': 1616513496,  # Older child
                        'children': []
                    }
                ]
            }
        ]
        
        # Act
        sorted_comments = sort_comment_tree(comments, "newest")
        
        # Assert - Check that children are sorted correctly
        children = sorted_comments[0]['children']
        self.assertEqual(children[0]['id'], 222)
        self.assertEqual(children[1]['id'], 333)


class TestCleanCommentText(unittest.TestCase):
    """Tests for the clean_comment_text function."""

    def test_clean_comment_text_basic_html(self):
        """Test cleaning basic HTML from comment text."""
        # Arrange
        html_text = "<p>This is a <b>test</b> comment.</p>"
        
        # Act
        cleaned = clean_comment_text(html_text)
        
        # Assert
        self.assertEqual(cleaned, "This is a test comment.")

    def test_clean_comment_text_code_blocks(self):
        """Test cleaning HTML code blocks."""
        # Arrange
        html_text = "<p>Check this code:</p><pre><code>def test(): pass</code></pre>"
        
        # Act
        cleaned = clean_comment_text(html_text)
        
        # Assert
        self.assertEqual(cleaned, "Check this code:\n\n    def test(): pass")

    def test_clean_comment_text_entities(self):
        """Test cleaning HTML entities."""
        # Arrange
        html_text = "&lt;script&gt;alert('XSS');&lt;/script&gt; &amp; other text"
        
        # Act
        cleaned = clean_comment_text(html_text)
        
        # Assert
        self.assertEqual(cleaned, "<script>alert('XSS');</script> & other text")

    def test_clean_comment_text_nested_elements(self):
        """Test cleaning nested HTML elements."""
        # Arrange
        html_text = "<div><p>Level 1 <span>Level 2 <i>Level 3</i></span></p></div>"
        
        # Act
        cleaned = clean_comment_text(html_text)
        
        # Assert
        self.assertEqual(cleaned, "Level 1 Level 2 Level 3")


class TestCountCommentTree(unittest.TestCase):
    """Tests for the count_comment_tree function."""

    def test_count_comment_tree_empty(self):
        """Test counting an empty comment tree."""
        # Act
        count = count_comment_tree([])
        
        # Assert
        self.assertEqual(count, 0)

    def test_count_comment_tree_simple(self):
        """Test counting a simple comment tree."""
        # Arrange
        comments = [
            {'id': 111, 'children': []},
            {'id': 222, 'children': []},
            {'id': 333, 'children': []}
        ]
        
        # Act
        count = count_comment_tree(comments)
        
        # Assert
        self.assertEqual(count, 3)

    def test_count_comment_tree_nested(self):
        """Test counting a nested comment tree."""
        # Arrange
        comments = [
            {
                'id': 111,
                'children': [
                    {
                        'id': 222,
                        'children': [
                            {'id': 444, 'children': []}
                        ]
                    },
                    {'id': 333, 'children': []}
                ]
            }
        ]
        
        # Act
        count = count_comment_tree(comments)
        
        # Assert
        self.assertEqual(count, 4)  # 1 parent + 2 children + 1 grandchild


if __name__ == '__main__':
    unittest.main()