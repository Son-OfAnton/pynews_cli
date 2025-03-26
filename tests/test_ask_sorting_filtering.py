"""
Tests for sorting and filtering functionality of Ask HN stories.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.utils import filter_stories_by_keywords, sort_stories_by_score, sort_stories_by_comments, sort_stories_by_time
from test_ask_utils import generate_mock_ask_stories


class TestStorySorting(unittest.TestCase):
    """Tests for sorting Ask HN stories by different criteria."""
    
    def test_sort_by_score(self):
        """Test sorting Ask HN stories by score."""
        # Arrange - Create stories with different scores
        stories = []
        for i in range(5):
            stories.append({
                "id": 10000 + i,
                "score": (5 - i) * 10  # Scores: 50, 40, 30, 20, 10
            })
        
        # Shuffle the stories to ensure they're not already sorted
        import random
        random.shuffle(stories)
        
        # Act
        sorted_stories = sort_stories_by_score(stories)
        
        # Assert
        self.assertEqual(sorted_stories[0]["score"], 50)
        self.assertEqual(sorted_stories[1]["score"], 40)
        self.assertEqual(sorted_stories[2]["score"], 30)
        self.assertEqual(sorted_stories[3]["score"], 20)
        self.assertEqual(sorted_stories[4]["score"], 10)
    
    def test_sort_by_comments(self):
        """Test sorting Ask HN stories by comment count."""
        # Arrange - Create stories with different comment counts
        stories = []
        for i in range(5):
            stories.append({
                "id": 10000 + i,
                "descendants": i * 10  # Comment counts: 0, 10, 20, 30, 40
            })
        
        # Shuffle the stories
        import random
        random.shuffle(stories)
        
        # Act
        sorted_stories = sort_stories_by_comments(stories)
        
        # Assert
        self.assertEqual(sorted_stories[0]["descendants"], 40)
        self.assertEqual(sorted_stories[1]["descendants"], 30)
        self.assertEqual(sorted_stories[2]["descendants"], 20)
        self.assertEqual(sorted_stories[3]["descendants"], 10)
        self.assertEqual(sorted_stories[4]["descendants"], 0)
    
    def test_sort_by_time(self):
        """Test sorting Ask HN stories by submission time."""
        # Arrange - Create stories with different timestamps
        stories = []
        base_time = 1616513396
        for i in range(5):
            stories.append({
                "id": 10000 + i,
                "time": base_time + i * 3600  # Each 1 hour newer
            })
        
        # Shuffle the stories
        import random
        random.shuffle(stories)
        
        # Act
        sorted_stories = sort_stories_by_time(stories)
        
        # Assert
        self.assertEqual(sorted_stories[0]["time"], base_time + 4 * 3600)
        self.assertEqual(sorted_stories[1]["time"], base_time + 3 * 3600)
        self.assertEqual(sorted_stories[2]["time"], base_time + 2 * 3600)
        self.assertEqual(sorted_stories[3]["time"], base_time + 1 * 3600)
        self.assertEqual(sorted_stories[4]["time"], base_time)


class TestStoryFiltering(unittest.TestCase):
    """Tests for filtering Ask HN stories by keywords."""
    
    def test_filter_by_single_keyword_in_title(self):
        """Test filtering stories by a single keyword in the title."""
        # Arrange
        stories = [
            {"title": "Ask HN: Python question?", "text": "Need help with code"},
            {"title": "Ask HN: JavaScript question?", "text": "Web development help"},
            {"title": "Ask HN: Career advice?", "text": "Should I learn Python?"}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python"])
        
        # Assert
        self.assertEqual(len(filtered), 2)  # Should match Python in title and text
        self.assertEqual(filtered[0]["title"], "Ask HN: Python question?")
        self.assertEqual(filtered[1]["title"], "Ask HN: Career advice?")
    
    def test_filter_by_single_keyword_in_text(self):
        """Test filtering stories by a single keyword in the text."""
        # Arrange
        stories = [
            {"title": "Ask HN: Programming question?", "text": "Need help with Python"},
            {"title": "Ask HN: Web question?", "text": "JavaScript problem"},
            {"title": "Ask HN: Career advice?", "text": "Should I learn coding?"}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python"])
        
        # Assert
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["title"], "Ask HN: Programming question?")
    
    def test_filter_by_multiple_keywords_match_any(self):
        """Test filtering stories by multiple keywords (matching any)."""
        # Arrange
        stories = [
            {"title": "Ask HN: Python question?", "text": "Need help with code"},
            {"title": "Ask HN: JavaScript question?", "text": "Web development"},
            {"title": "Ask HN: Career advice?", "text": "Should I learn Ruby?"},
            {"title": "Ask HN: Database question?", "text": "SQL or NoSQL?"}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python", "javascript", "ruby"])
        
        # Assert
        self.assertEqual(len(filtered), 3)  # Should match Python, JavaScript, and Ruby
    
    def test_filter_by_multiple_keywords_match_all(self):
        """Test filtering stories by multiple keywords (matching all)."""
        # Arrange
        stories = [
            {"title": "Ask HN: Python and JavaScript?", "text": "Need help with both"},
            {"title": "Ask HN: JavaScript question?", "text": "Web development with Python"},
            {"title": "Ask HN: Python question?", "text": "Machine learning"},
            {"title": "Ask HN: JavaScript frameworks?", "text": "React vs Angular"}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python", "javascript"], match_all=True)
        
        # Assert
        self.assertEqual(len(filtered), 2)  # Should match stories containing both Python and JavaScript
    
    def test_filter_with_case_sensitivity(self):
        """Test filtering with case sensitivity."""
        # Arrange
        stories = [
            {"title": "Ask HN: Python question?", "text": "Need help with code"},
            {"title": "Ask HN: PYTHON question?", "text": "Uppercase Python"},
            {"title": "Ask HN: python question?", "text": "Lowercase python"}
        ]
        
        # Act - Case sensitive filter
        filtered = filter_stories_by_keywords(stories, ["Python"], case_sensitive=True)
        
        # Assert
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["title"], "Ask HN: Python question?")


class TestCombinedSortingAndFiltering(unittest.TestCase):
    """Tests for combined sorting and filtering operations."""
    
    def test_filter_then_sort_by_score(self):
        """Test filtering stories by keyword and then sorting by score."""
        # Arrange
        stories = [
            {"title": "Ask HN: Python basics?", "text": "Learning", "score": 10},
            {"title": "Ask HN: Advanced Python?", "text": "Expert tips", "score": 50},
            {"title": "Ask HN: JavaScript?", "text": "Web dev", "score": 30},
            {"title": "Ask HN: Career with Python?", "text": "Jobs", "score": 20}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python"])
        sorted_stories = sort_stories_by_score(filtered)
        
        # Assert
        self.assertEqual(len(sorted_stories), 3)  # Should match 3 Python stories
        self.assertEqual(sorted_stories[0]["score"], 50)  # Highest score first
        self.assertEqual(sorted_stories[1]["score"], 20)
        self.assertEqual(sorted_stories[2]["score"], 10)
    
    def test_filter_then_sort_by_comments(self):
        """Test filtering stories by keyword and then sorting by comments."""
        # Arrange
        stories = [
            {"title": "Ask HN: Python basics?", "text": "Learning", "descendants": 5},
            {"title": "Ask HN: Advanced Python?", "text": "Expert tips", "descendants": 20},
            {"title": "Ask HN: JavaScript?", "text": "Web dev", "descendants": 15},
            {"title": "Ask HN: Career with Python?", "text": "Jobs", "descendants": 10}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python"])
        sorted_stories = sort_stories_by_comments(filtered)
        
        # Assert
        self.assertEqual(len(sorted_stories), 3)  # Should match 3 Python stories
        self.assertEqual(sorted_stories[0]["descendants"], 20)  # Most comments first
        self.assertEqual(sorted_stories[1]["descendants"], 10)
        self.assertEqual(sorted_stories[2]["descendants"], 5)
    
    def test_filter_then_sort_by_time(self):
        """Test filtering stories by keyword and then sorting by time."""
        # Arrange
        base_time = 1616513396
        stories = [
            {"title": "Ask HN: Python basics?", "text": "Learning", "time": base_time},
            {"title": "Ask HN: Advanced Python?", "text": "Expert tips", "time": base_time + 3600},
            {"title": "Ask HN: JavaScript?", "text": "Web dev", "time": base_time + 7200},
            {"title": "Ask HN: Career with Python?", "text": "Jobs", "time": base_time + 1800}
        ]
        
        # Act
        filtered = filter_stories_by_keywords(stories, ["python"])
        sorted_stories = sort_stories_by_time(filtered)
        
        # Assert
        self.assertEqual(len(sorted_stories), 3)  # Should match 3 Python stories
        self.assertEqual(sorted_stories[0]["time"], base_time + 3600)  # Newest first
        self.assertEqual(sorted_stories[1]["time"], base_time + 1800)
        self.assertEqual(sorted_stories[2]["time"], base_time)


if __name__ == '__main__':
    unittest.main()