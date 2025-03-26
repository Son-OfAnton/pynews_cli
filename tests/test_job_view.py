"""
Unit tests for the Job listings functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import time

# Add the parent directory to the path so we can import the modules
sys.path.append("..") # Add parent directory to path

from pynews.job_view import (
    display_job_listings,
    extract_company_name,
    filter_jobs_by_company,
    filter_jobs_by_keywords,
    highlight_keywords,
    sort_jobs_by_date,
    sort_jobs_by_score,
    format_absolute_date,
    format_score
)
from test_job_utils import (
    create_mock_response,
    generate_mock_job_story,
    generate_mock_job_stories,
    generate_job_story_ids
)


class TestJobViewUtilityFunctions(unittest.TestCase):
    """Tests for utility functions in the job view module."""
    
    def test_extract_company_name(self):
        """Test extracting company name from job title."""
        # Test standard job title format
        title = "Job: Software Engineer at Google"
        self.assertEqual(extract_company_name(title), "Google")
        
        # Test with 'remote' suffix
        title = "Job: Frontend Developer at Startup (Remote)"
        self.assertEqual(extract_company_name(title), "Startup")
        
        # Test with multi-word company name
        title = "Job: Data Scientist at Machine Learning Corp"
        self.assertEqual(extract_company_name(title), "Machine Learning Corp")
        
        # Test with no company name
        title = "Job: DevOps Engineer"
        self.assertEqual(extract_company_name(title), "")
        
        # Test with unusual format
        title = "Software Engineer - Google"
        self.assertEqual(extract_company_name(title), "")
    
    def test_format_absolute_date(self):
        """Test formatting timestamp to absolute date."""
        # Test with a valid timestamp
        timestamp = 1616513396  # March 23, 2021
        result = format_absolute_date(timestamp)
        self.assertIn("Mar", result)
        self.assertIn("2021", result)
        
        # Test with None
        result = format_absolute_date(None)
        self.assertEqual(result, "Unknown date")
    
    def test_format_score(self):
        """Test formatting job score."""
        # Test with various scores
        self.assertIn("10", format_score(10))
        self.assertIn("0", format_score(0))
        
        # Test with None
        self.assertIn("Unknown", format_score(None))
    
    def test_highlight_keywords(self):
        """Test highlighting keywords in text."""
        # Test basic highlighting
        text = "This is a Python job with JavaScript requirements"
        keywords = ["python", "javascript"]
        highlighted = highlight_keywords(text, keywords)
        self.assertNotEqual(highlighted, text)  # Should be different (highlighted)
        
        # Test case sensitivity
        text = "This is a Python job"
        keywords = ["python"]
        highlighted = highlight_keywords(text, keywords, case_sensitive=True)
        self.assertEqual(highlighted, text)  # No match due to case sensitivity
        
        # Test with no keywords
        text = "This is a job description"
        highlighted = highlight_keywords(text, None)
        self.assertEqual(highlighted, text)  # Should be unchanged


class TestJobFiltering(unittest.TestCase):
    """Tests for job filtering functionality."""
    
    def test_filter_jobs_by_company(self):
        """Test filtering jobs by company name."""
        # Create test jobs with different companies
        jobs = [
            {"title": "Job: Developer at Google"},
            {"title": "Job: Engineer at Microsoft"},
            {"title": "Job: Designer at Google"},
            {"title": "Job: Manager at Amazon"}
        ]
        
        # Filter by Google
        filtered = filter_jobs_by_company(jobs, "Google")
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["title"], "Job: Developer at Google")
        self.assertEqual(filtered[1]["title"], "Job: Designer at Google")
        
        # Test case sensitivity
        filtered = filter_jobs_by_company(jobs, "google", case_sensitive=True)
        self.assertEqual(len(filtered), 0)  # No matches with case sensitivity
        
        # Test with non-matching company
        filtered = filter_jobs_by_company(jobs, "Facebook")
        self.assertEqual(len(filtered), 0)
    
    def test_filter_jobs_by_keywords(self):
        """Test filtering jobs by keywords."""
        # Create test jobs with different content
        jobs = [
            {
                "title": "Job: Python Developer at Google",
                "text": "Looking for a Python expert with web development skills"
            },
            {
                "title": "Job: Frontend Engineer at Microsoft",
                "text": "JavaScript, React, and CSS skills required"
            },
            {
                "title": "Job: Full Stack Developer at Amazon",
                "text": "Python and JavaScript knowledge needed for this remote position"
            }
        ]
        
        # Filter by single keyword
        filtered = filter_jobs_by_keywords(jobs, ["python"])
        self.assertEqual(len(filtered), 2)  # Two jobs mention Python
        
        # Filter by multiple keywords (any match)
        filtered = filter_jobs_by_keywords(jobs, ["python", "react"])
        self.assertEqual(len(filtered), 3)  # All jobs mention either Python or React
        
        # Filter by multiple keywords (all match)
        filtered = filter_jobs_by_keywords(jobs, ["python", "javascript"], match_all=True)
        self.assertEqual(len(filtered), 1)  # Only the Amazon job mentions both
        
        # Test case sensitivity
        filtered = filter_jobs_by_keywords(jobs, ["Python"], case_sensitive=True)
        self.assertEqual(len(filtered), 2)  # Two jobs mention Python with exact case


class TestJobSorting(unittest.TestCase):
    """Tests for job sorting functionality."""
    
    def test_sort_jobs_by_date(self):
        """Test sorting jobs by timestamp."""
        # Create jobs with different timestamps
        jobs = [
            {"id": 1, "time": 1616513396},  # Oldest
            {"id": 2, "time": 1616513496},  # Middle
            {"id": 3, "time": 1616513596}   # Newest
        ]
        
        # Sort newest first (default)
        sorted_jobs = sort_jobs_by_date(jobs)
        self.assertEqual(sorted_jobs[0]["id"], 3)
        self.assertEqual(sorted_jobs[1]["id"], 2)
        self.assertEqual(sorted_jobs[2]["id"], 1)
        
        # Sort oldest first
        sorted_jobs = sort_jobs_by_date(jobs, newest_first=False)
        self.assertEqual(sorted_jobs[0]["id"], 1)
        self.assertEqual(sorted_jobs[1]["id"], 2)
        self.assertEqual(sorted_jobs[2]["id"], 3)
    
    def test_sort_jobs_by_score(self):
        """Test sorting jobs by score."""
        # Create jobs with different scores
        jobs = [
            {"id": 1, "score": 10},
            {"id": 2, "score": 30},
            {"id": 3, "score": 20}
        ]
        
        # Sort highest first (default)
        sorted_jobs = sort_jobs_by_score(jobs)
        self.assertEqual(sorted_jobs[0]["id"], 2)
        self.assertEqual(sorted_jobs[1]["id"], 3)
        self.assertEqual(sorted_jobs[2]["id"], 1)
        
        # Sort lowest first
        sorted_jobs = sort_jobs_by_score(jobs, highest_first=False)
        self.assertEqual(sorted_jobs[0]["id"], 1)
        self.assertEqual(sorted_jobs[1]["id"], 3)
        self.assertEqual(sorted_jobs[2]["id"], 2)
        
        # Test with missing scores
        jobs = [
            {"id": 1, "score": 10},
            {"id": 2},  # No score
            {"id": 3, "score": 20}
        ]
        
        sorted_jobs = sort_jobs_by_score(jobs)
        self.assertEqual(len(sorted_jobs), 3)  # Should handle missing scores
        self.assertEqual(sorted_jobs[0]["id"], 3)  # Highest score first


class TestDisplayJobListings(unittest.TestCase):
    """Tests for the display_job_listings function."""
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    def test_display_job_listings_success(self, mock_print, mock_clear, mock_get_story, mock_get_stories):
        """Test displaying job listings successfully."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = generate_mock_job_stories(10)
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Act - Simulate pressing 'q' to quit immediately
        with patch('pynews.job_view.read_key', return_value='q'):
            with patch('pynews.job_view.LoadingIndicator'):
                display_job_listings(limit=5)
        
        # Assert
        mock_get_stories.assert_called_once_with("job")
        mock_clear.assert_called()
        self.assertTrue(mock_print.call_count > 5)  # Should print multiple job items
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.print')
    def test_display_job_listings_no_jobs(self, mock_print, mock_get_stories):
        """Test displaying jobs when none are found."""
        # Arrange
        mock_get_stories.return_value = []  # No jobs found
        
        # Act
        with patch('pynews.job_view.LoadingIndicator'):
            display_job_listings()
        
        # Assert
        mock_get_stories.assert_called_once_with("job")
        mock_print.assert_called_with("\nNo job listings found.")
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    def test_display_job_listings_with_company_filter(self, mock_print, mock_clear, mock_get_story, mock_get_stories):
        """Test displaying job listings filtered by company."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = [
            generate_mock_job_story(20001, title="Job: Engineer at Google"),
            generate_mock_job_story(20002, title="Job: Designer at Microsoft"),
            generate_mock_job_story(20003, title="Job: Manager at Google")
        ]
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Act - Filter by Google, simulate pressing 'q' to quit
        with patch('pynews.job_view.read_key', return_value='q'):
            with patch('pynews.job_view.LoadingIndicator'):
                display_job_listings(company_filter="Google")
        
        # Assert
        mock_get_stories.assert_called_once_with("job")
        mock_clear.assert_called()
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    def test_display_job_listings_with_keyword_filter(self, mock_print, mock_clear, mock_get_story, mock_get_stories):
        """Test displaying job listings filtered by keywords."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = [
            {
                "id": 20001,
                "title": "Job: Python Developer",
                "text": "Looking for Python skills",
                "time": 1616513396,
                "score": 5
            },
            {
                "id": 20002,
                "title": "Job: JavaScript Developer",
                "text": "Frontend skills needed",
                "time": 1616513496,
                "score": 10
            },
            {
                "id": 20003,
                "title": "Job: Full Stack Developer",
                "text": "Python and JavaScript experience required",
                "time": 1616513596,
                "score": 15
            }
        ]
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Act - Filter by Python keyword, simulate pressing 'q' to quit
        with patch('pynews.job_view.read_key', return_value='q'):
            with patch('pynews.job_view.LoadingIndicator'):
                display_job_listings(keywords=["python"])
        
        # Assert
        mock_get_stories.assert_called_once_with("job")
        mock_clear.assert_called()


if __name__ == '__main__':
    unittest.main()