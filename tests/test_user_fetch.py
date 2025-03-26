"""
Unit tests for user information fetching in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.user_view import (
    fetch_user, 
    fetch_submissions, 
    fetch_item,
    categorize_submissions,
    fetch_karma,
    fetch_created_timestamp,
    fetch_random_users,
    display_user,
    display_karma,
    display_created_date,
    display_user_stories,
    format_account_age
)
from pynews.constants import URLS
from test_user_utils import (
    create_mock_response,
    generate_mock_user,
    generate_mock_story,
    generate_mock_comment,
    generate_mock_submissions
)


class TestFetchUser(unittest.TestCase):
    """Tests for the fetch_user function."""

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.LoadingIndicator')
    def test_fetch_user_success(self, mock_loader, mock_get):
        """Test fetching a user successfully."""
        # Arrange
        username = "test_user"
        mock_user_data = generate_mock_user(username)
        mock_get.return_value = create_mock_response(200, mock_user_data)
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_user(username)
        
        # Assert
        mock_get.assert_called_once_with(URLS["user"].format(username))
        mock_loader_instance.start.assert_called_once()
        self.assertEqual(result, mock_user_data)

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.LoadingIndicator')
    @patch('pynews.user_view.print')
    def test_fetch_user_not_found(self, mock_print, mock_loader, mock_get):
        """Test fetching a non-existent user."""
        # Arrange
        username = "nonexistent_user"
        mock_get.return_value = create_mock_response(404, None)
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_user(username)
        
        # Assert
        mock_get.assert_called_once_with(URLS["user"].format(username))
        mock_loader_instance.start.assert_called_once()
        mock_print.assert_called_once()  # Should print error
        self.assertIsNone(result)

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.LoadingIndicator')
    @patch('pynews.user_view.print')
    def test_fetch_user_network_error(self, mock_print, mock_loader, mock_get):
        """Test handling network errors when fetching a user."""
        # Arrange
        username = "test_user"
        mock_get.side_effect = Exception("Network error")
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_user(username)
        
        # Assert
        mock_get.assert_called_once_with(URLS["user"].format(username))
        mock_loader_instance.start.assert_called_once()
        mock_print.assert_called_once()  # Should print error
        self.assertIsNone(result)


class TestFetchItem(unittest.TestCase):
    """Tests for the fetch_item function."""

    @patch('pynews.user_view.requests.get')
    def test_fetch_item_success(self, mock_get):
        """Test fetching an item successfully."""
        # Arrange
        item_id = 10000
        mock_story = generate_mock_story(item_id)
        mock_get.return_value = create_mock_response(200, mock_story)
        
        # Act
        result = fetch_item(item_id)
        
        # Assert
        mock_get.assert_called_once_with(URLS["item"].format(item_id))
        self.assertEqual(result, mock_story)

    @patch('pynews.user_view.requests.get')
    def test_fetch_item_not_found(self, mock_get):
        """Test fetching a non-existent item."""
        # Arrange
        item_id = 99999
        mock_get.return_value = create_mock_response(404, None)
        
        # Act
        result = fetch_item(item_id)
        
        # Assert
        mock_get.assert_called_once_with(URLS["item"].format(item_id))
        self.assertIsNone(result)

    @patch('pynews.user_view.requests.get')
    def test_fetch_item_error(self, mock_get):
        """Test handling errors when fetching an item."""
        # Arrange
        item_id = 10000
        mock_get.side_effect = Exception("Network error")
        
        # Act
        result = fetch_item(item_id)
        
        # Assert
        mock_get.assert_called_once_with(URLS["item"].format(item_id))
        self.assertIsNone(result)


class TestFetchSubmissions(unittest.TestCase):
    """Tests for the fetch_submissions function."""

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.fetch_item')
    @patch('pynews.user_view.LoadingIndicator')
    def test_fetch_submissions_success(self, mock_loader, mock_fetch_item, mock_get):
        """Test fetching user submissions successfully."""
        # Arrange
        username = "test_user"
        max_items = 5
        mock_user_data = generate_mock_user(username)
        mock_get.return_value = create_mock_response(200, mock_user_data)
        
        # Generate mock submissions (stories and comments)
        mock_items = generate_mock_submissions(5, username)
        mock_fetch_item.side_effect = lambda item_id: next(
            (item for item in mock_items if item["id"] == item_id), None
        )
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_submissions(username, max_items)
        
        # Assert
        mock_get.assert_called_once_with(URLS["user"].format(username))
        mock_loader_instance.start.assert_called_once()
        self.assertEqual(mock_fetch_item.call_count, max_items)
        self.assertEqual(len(result), max_items)

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.LoadingIndicator')
    @patch('pynews.user_view.print')
    def test_fetch_submissions_user_not_found(self, mock_print, mock_loader, mock_get):
        """Test fetching submissions for a non-existent user."""
        # Arrange
        username = "nonexistent_user"
        mock_get.return_value = create_mock_response(404, None)
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_submissions(username)
        
        # Assert
        mock_get.assert_called_once_with(URLS["user"].format(username))
        mock_loader_instance.start.assert_called_once()
        mock_print.assert_called_once()  # Should print error
        self.assertIsNone(result)

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.fetch_item')
    @patch('pynews.user_view.LoadingIndicator')
    def test_fetch_submissions_with_deleted_items(self, mock_loader, mock_fetch_item, mock_get):
        """Test fetching submissions and handling deleted items."""
        # Arrange
        username = "test_user"
        mock_user_data = generate_mock_user(username)
        mock_get.return_value = create_mock_response(200, mock_user_data)
        
        # Set up some items to be None (deleted)
        def side_effect(item_id):
            if item_id % 2 == 0:  # Even IDs return None to simulate deleted items
                return None
            else:
                return generate_mock_story(item_id, username)
                
        mock_fetch_item.side_effect = side_effect
        
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_submissions(username, max_items=10)
        
        # Assert
        mock_get.assert_called_once_with(URLS["user"].format(username))
        self.assertEqual(mock_fetch_item.call_count, 10)
        # Should filter out deleted items (Nones)
        self.assertEqual(len(result), 5)


class TestCategorizeSubmissions(unittest.TestCase):
    """Tests for the categorize_submissions function."""

    def test_categorize_submissions_mixed(self):
        """Test categorizing a mix of submission types."""
        # Arrange
        username = "test_user"
        submissions = [
            generate_mock_story(10001, username),
            generate_mock_story(10002, username),
            generate_mock_comment(20001, username),
            generate_mock_comment(20002, username),
            generate_mock_comment(20003, username),
        ]
        
        # Act
        result = categorize_submissions(submissions)
        
        # Assert
        self.assertEqual(len(result["stories"]), 2)
        self.assertEqual(len(result["comments"]), 3)

    def test_categorize_submissions_only_stories(self):
        """Test categorizing only stories."""
        # Arrange
        username = "test_user"
        submissions = [
            generate_mock_story(10001, username),
            generate_mock_story(10002, username),
            generate_mock_story(10003, username),
        ]
        
        # Act
        result = categorize_submissions(submissions)
        
        # Assert
        self.assertEqual(len(result["stories"]), 3)
        self.assertEqual(len(result["comments"]), 0)

    def test_categorize_submissions_only_comments(self):
        """Test categorizing only comments."""
        # Arrange
        username = "test_user"
        submissions = [
            generate_mock_comment(20001, username),
            generate_mock_comment(20002, username),
        ]
        
        # Act
        result = categorize_submissions(submissions)
        
        # Assert
        self.assertEqual(len(result["stories"]), 0)
        self.assertEqual(len(result["comments"]), 2)

    def test_categorize_submissions_empty(self):
        """Test categorizing an empty submissions list."""
        # Act
        result = categorize_submissions([])
        
        # Assert
        self.assertEqual(len(result["stories"]), 0)
        self.assertEqual(len(result["comments"]), 0)


class TestFetchUserAttributes(unittest.TestCase):
    """Tests for fetching specific user attributes."""

    @patch('pynews.user_view.fetch_user')
    def test_fetch_karma_success(self, mock_fetch_user):
        """Test fetching a user's karma successfully."""
        # Arrange
        username = "test_user"
        karma = 1000
        mock_fetch_user.return_value = generate_mock_user(username, karma=karma)
        
        # Act
        result = fetch_karma(username)
        
        # Assert
        mock_fetch_user.assert_called_once_with(username)
        self.assertEqual(result, karma)

    @patch('pynews.user_view.fetch_user')
    def test_fetch_karma_user_not_found(self, mock_fetch_user):
        """Test fetching karma for a non-existent user."""
        # Arrange
        username = "nonexistent_user"
        mock_fetch_user.return_value = None
        
        # Act
        result = fetch_karma(username)
        
        # Assert
        mock_fetch_user.assert_called_once_with(username)
        self.assertEqual(result, -1)

    @patch('pynews.user_view.fetch_user')
    def test_fetch_created_timestamp_success(self, mock_fetch_user):
        """Test fetching a user's creation timestamp successfully."""
        # Arrange
        username = "test_user"
        created = 1234567890
        mock_fetch_user.return_value = generate_mock_user(username, created=created)
        
        # Act
        result = fetch_created_timestamp(username)
        
        # Assert
        mock_fetch_user.assert_called_once_with(username)
        self.assertEqual(result, created)

    @patch('pynews.user_view.fetch_user')
    def test_fetch_created_timestamp_user_not_found(self, mock_fetch_user):
        """Test fetching creation timestamp for a non-existent user."""
        # Arrange
        username = "nonexistent_user"
        mock_fetch_user.return_value = None
        
        # Act
        result = fetch_created_timestamp(username)
        
        # Assert
        mock_fetch_user.assert_called_once_with(username)
        self.assertEqual(result, -1)


class TestFormatAccountAge(unittest.TestCase):
    """Tests for formatting account age."""

    def test_format_account_age_years(self):
        """Test formatting account age in years."""
        # Arrange - Set creation time to 3 years ago
        now = int(time.time())
        created = now - (3 * 365 * 24 * 60 * 60)  # 3 years ago
        
        # Act
        result = format_account_age(created)
        
        # Assert
        self.assertIn("3 years", result.lower())

    def test_format_account_age_months(self):
        """Test formatting account age in months."""
        # Arrange - Set creation time to 5 months ago
        now = int(time.time())
        created = now - (5 * 30 * 24 * 60 * 60)  # ~5 months ago
        
        # Act
        result = format_account_age(created)
        
        # Assert
        self.assertIn("5 months", result.lower())

    def test_format_account_age_days(self):
        """Test formatting account age in days."""
        # Arrange - Set creation time to 12 days ago
        now = int(time.time())
        created = now - (12 * 24 * 60 * 60)  # 12 days ago
        
        # Act
        result = format_account_age(created)
        
        # Assert
        self.assertIn("12 days", result.lower())

    def test_format_account_age_invalid(self):
        """Test formatting an invalid account age."""
        # Arrange
        created = -1  # Invalid timestamp
        
        # Act
        result = format_account_age(created)
        
        # Assert
        self.assertEqual(result, "Unknown")


class TestFetchRandomUsers(unittest.TestCase):
    """Tests for the fetch_random_users function."""

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.LoadingIndicator')
    @patch('pynews.user_view.fetch_user')
    def test_fetch_random_users_success(self, mock_fetch_user, mock_loader, mock_get):
        """Test fetching random users successfully."""
        # Arrange
        story_ids = [10001, 10002, 10003, 10004, 10005]
        mock_get.return_value = create_mock_response(200, story_ids)
        
        # Set up mock stories with different authors
        mock_stories = [
            {"by": f"user{i}", "id": story_id} 
            for i, story_id in enumerate(story_ids)
        ]
        
        # Mock fetch_item to return a story with a username
        def mock_fetch_item_side_effect(item_id):
            for story in mock_stories:
                if story["id"] == item_id:
                    return story
            return None
            
        with patch('pynews.user_view.fetch_item', side_effect=mock_fetch_item_side_effect):
            # Mock fetch_user to return a user for each username
            mock_fetch_user.side_effect = lambda username: generate_mock_user(username)
            
            mock_loader_instance = MagicMock()
            mock_loader.return_value = mock_loader_instance
            
            # Act
            result = fetch_random_users(count=3)
            
            # Assert
            mock_get.assert_called_once()
            self.assertEqual(len(result), 3)
            for user in result:
                self.assertTrue(isinstance(user, dict))
                self.assertIn("id", user)
                self.assertIn("karma", user)

    @patch('pynews.user_view.requests.get')
    @patch('pynews.user_view.LoadingIndicator')
    def test_fetch_random_users_api_failure(self, mock_loader, mock_get):
        """Test handling API failures when fetching random users."""
        # Arrange
        mock_get.return_value = create_mock_response(500, None)
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        # Act
        result = fetch_random_users(count=3)
        
        # Assert
        mock_get.assert_called_once()
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()