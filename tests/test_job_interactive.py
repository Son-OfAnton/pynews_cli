"""
Tests for the interactive and advanced filtering functionality of job listings.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.job_view import display_job_listings, prompt_for_input
from test_job_utils import generate_mock_job_stories, generate_job_story_ids


class TestJobInteractiveFunctions(unittest.TestCase):
    """Tests for interactive functions in the job view module."""
    
    @patch('pynews.job_view.input')
    def test_prompt_for_input(self, mock_input):
        """Test the prompt_for_input function."""
        # Arrange
        mock_input.return_value = "Test input"
        
        # Act
        result = prompt_for_input("Enter text:")
        
        # Assert
        mock_input.assert_called_once()
        self.assertEqual(result, "Test input")


class TestJobInteractiveFiltering(unittest.TestCase):
    """Tests for interactive filtering of job listings."""
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    @patch('pynews.job_view.prompt_for_input')
    def test_company_search_interaction(self, mock_prompt, mock_print, mock_clear, 
                                      mock_get_story, mock_get_stories):
        """Test interactive company search functionality."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = [
            {"id": 20001, "title": "Job: Engineer at Google", "time": 1616513396, "score": 5},
            {"id": 20002, "title": "Job: Designer at Microsoft", "time": 1616513496, "score": 10},
            {"id": 20003, "title": "Job: Developer at Google", "time": 1616513596, "score": 15}
        ]
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Mock the key input sequence:
        # 'c' (search by company) -> input "Google" -> 'q' (quit)
        key_sequence = ['c', 'q']
        prompt_responses = ["Google"]
        
        with patch('pynews.job_view.read_key', side_effect=key_sequence):
            with patch('pynews.job_view.LoadingIndicator'):
                mock_prompt.side_effect = prompt_responses
                display_job_listings()
        
        # Assert
        mock_prompt.assert_called_once()  # Should prompt for company name
        mock_get_stories.assert_called_once()
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    @patch('pynews.job_view.prompt_for_input')
    def test_keyword_search_interaction(self, mock_prompt, mock_print, mock_clear, 
                                      mock_get_story, mock_get_stories):
        """Test interactive keyword search functionality."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = generate_mock_job_stories(10)
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Mock the key input sequence:
        # 'k' (search by keyword) -> input "python" -> 'q' (quit)
        key_sequence = ['k', 'q']
        prompt_responses = ["python"]
        
        with patch('pynews.job_view.read_key', side_effect=key_sequence):
            with patch('pynews.job_view.LoadingIndicator'):
                mock_prompt.side_effect = prompt_responses
                display_job_listings()
        
        # Assert
        mock_prompt.assert_called_once()  # Should prompt for keyword
        mock_get_stories.assert_called_once()


class TestJobListingAdvancedFeatures(unittest.TestCase):
    """Tests for advanced features of job listings."""
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    def test_toggle_sort_order(self, mock_print, mock_clear, mock_get_story, mock_get_stories):
        """Test toggling sort order functionality."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = generate_mock_job_stories(10)
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Mock the key input sequence:
        # 's' (toggle sort) -> 'o' (toggle order) -> 'q' (quit)
        key_sequence = ['s', 'o', 'q']
        
        with patch('pynews.job_view.read_key', side_effect=key_sequence):
            with patch('pynews.job_view.LoadingIndicator'):
                display_job_listings()
        
        # Assert
        mock_get_stories.assert_called_once()
        self.assertTrue(mock_clear.call_count >= 3)  # Should clear screen after each toggle
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    @patch('pynews.job_view.prompt_for_input')
    def test_minimum_score_filter(self, mock_prompt, mock_print, mock_clear, 
                               mock_get_story, mock_get_stories):
        """Test setting minimum score filter."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = generate_mock_job_stories(10, vary_scores=True)
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Mock the key input sequence:
        # 'm' (set min score) -> input "10" -> 'q' (quit)
        key_sequence = ['m', 'q']
        prompt_responses = ["10"]
        
        with patch('pynews.job_view.read_key', side_effect=key_sequence):
            with patch('pynews.job_view.LoadingIndicator'):
                mock_prompt.side_effect = prompt_responses
                display_job_listings()
        
        # Assert
        mock_prompt.assert_called_once()  # Should prompt for minimum score
        mock_get_stories.assert_called_once()
    
    @patch('pynews.job_view.get_stories')
    @patch('pynews.job_view.get_story')
    @patch('pynews.job_view.clear_screen')
    @patch('pynews.job_view.print')
    @patch('pynews.job_view.webbrowser')
    def test_open_url_interaction(self, mock_browser, mock_print, mock_clear, 
                               mock_get_story, mock_get_stories):
        """Test opening job URL functionality."""
        # Arrange
        job_ids = generate_job_story_ids(10)
        mock_jobs = [
            {
                "id": 20001, 
                "title": "Job: Engineer at Google", 
                "time": 1616513396, 
                "score": 5,
                "url": "https://example.com/job1"
            }
        ]
        
        mock_get_stories.return_value = job_ids
        mock_get_story.side_effect = lambda id: next((j for j in mock_jobs if j["id"] == id), None)
        
        # Mock the key input sequence:
        # 'o' (open url) -> 'q' (quit)
        key_sequence = ['u', 'q']
        
        with patch('pynews.job_view.read_key', side_effect=key_sequence):
            with patch('pynews.job_view.LoadingIndicator'):
                display_job_listings()
        
        # Assert
        mock_browser.open.assert_called_once_with("https://example.com/job1")
        mock_get_stories.assert_called_once()


if __name__ == '__main__':
    unittest.main()