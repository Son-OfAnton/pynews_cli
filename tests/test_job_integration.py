"""
Integration tests for the Job listings functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.job_view import display_job_listings
from pynews.pynews import main
from pynews.constants import URLS
from test_job_utils import create_mock_response, generate_mock_job_story, generate_mock_job_stories


class TestJobViewIntegration(unittest.TestCase):
    """Integration tests for job view with other components."""

    @patch('pynews.utils.req.get')
    def test_get_job_listings_api_integration(self, mock_get):
        """Test integration between job listings and the API."""
        # Arrange
        # First mock the API call to get the list of job IDs
        job_ids = list(range(20000, 20010))  # 10 job IDs
        
        # Create mock API responses
        story_ids_response = create_mock_response(200, job_ids)
        job_responses = [create_mock_response(200, generate_mock_job_story(id)) for id in job_ids]
        
        # Configure mock to return different responses for different URLs
        def side_effect(url):
            if url == URLS["job"]:
                return story_ids_response
            for i, job_id in enumerate(job_ids):
                if url == URLS["item"].format(job_id):
                    return job_responses[i]
            return create_mock_response(404, None)
            
        mock_get.side_effect = side_effect
        
        # Act - simulate pressing 'q' to quit immediately
        with patch('pynews.job_view.read_key', return_value='q'):
            with patch('pynews.job_view.clear_screen'):
                with patch('pynews.job_view.print'):
                    with patch('pynews.job_view.LoadingIndicator'):
                        display_job_listings(limit=5)
        
        # Assert - Check API calls
        mock_get.assert_any_call(URLS["job"])  # Should call the job stories endpoint
        mock_get.assert_any_call(URLS["item"].format(20000))  # Should call item endpoint for a job

    @patch('pynews.utils.req.get')
    def test_job_view_error_handling(self, mock_get):
        """Test error handling during API calls in the job view."""
        # Arrange - First call succeeds, rest fail
        job_ids = list(range(20000, 20010))  # 10 job IDs
        
        # Configure mock
        mock_get.side_effect = [
            create_mock_response(200, job_ids),  # First call returns job IDs
            Exception("API Error")  # Subsequent calls fail
        ]
        
        # Act - Should handle API errors gracefully
        with patch('pynews.job_view.read_key', return_value='q'):
            with patch('pynews.job_view.clear_screen'):
                with patch('pynews.job_view.print'):
                    with patch('pynews.job_view.LoadingIndicator'):
                        display_job_listings()
        
        # Assert
        mock_get.assert_called()  # API was called
        
    @patch('pynews.utils.req.get')
    def test_job_navigation(self, mock_get):
        """Test job listing navigation functionality."""
        # Arrange
        job_ids = list(range(20000, 20020))  # 20 job IDs
        
        # Create mock jobs
        mock_jobs = generate_mock_job_stories(20)
        
        # Configure mock
        story_ids_response = create_mock_response(200, job_ids)
        
        def side_effect(url):
            if url == URLS["job"]:
                return story_ids_response
            for job in mock_jobs:
                if url == URLS["item"].format(job["id"]):
                    return create_mock_response(200, job)
            return create_mock_response(404, None)
            
        mock_get.side_effect = side_effect
        
        # Act - Simulate navigation: down, right (next page), up, left (prev page), q (quit)
        key_sequence = ['j', 'n', 'k', 'p', 'q']
        with patch('pynews.job_view.read_key', side_effect=key_sequence):
            with patch('pynews.job_view.clear_screen'):
                with patch('pynews.job_view.print'):
                    with patch('pynews.job_view.LoadingIndicator'):
                        display_job_listings(page_size=5)  # 5 jobs per page for easier testing
        
        # Assert - Hard to fully verify, but at least check API was called multiple times
        self.assertTrue(mock_get.call_count > 5)


class TestPyNewsCommandLineIntegration(unittest.TestCase):
    """Test integration with the main PyNews command line parser."""
    
    @patch('pynews.utils.get_stories')
    @patch('pynews.job_view.display_job_listings')
    def test_job_stories_cli_integration(self, mock_display_jobs, mock_get_stories):
        """Test the --job-stories command line option."""
        # Arrange
        mock_get_stories.return_value = list(range(20000, 20010))  # 10 job IDs
        
        # Act - simulate calling from command line with --job-stories 5
        with patch('sys.argv', ['pynews', '--job-stories', '5']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.job_stories = 5  # Number of jobs to show
                options.top_stories = None
                options.news_stories = None
                options.ask_stories = None
                options.poll_stories = None
                options.job_keyword = None
                options.job_sort_by_score = False
                options.job_oldest_first = False
                options.match_all = False
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_jobs.assert_called_once_with(
            limit=5, sort_by_score=False, sort_newest_first=True,
            keywords=None, match_all=False, company_filter=None
        )

    @patch('pynews.utils.get_stories')
    @patch('pynews.job_view.display_job_listings')
    def test_job_keyword_cli_integration(self, mock_display_jobs, mock_get_stories):
        """Test the --job-keyword command line option."""
        # Arrange
        mock_get_stories.return_value = list(range(20000, 20010))  # 10 job IDs
        
        # Act - simulate calling from command line with --job-stories 5 --job-keyword python
        with patch('sys.argv', ['pynews', '--job-stories', '5', '--job-keyword', 'python']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.job_stories = 5  # Number of jobs to show
                options.job_keyword = ['python']  # Filter by keyword
                options.job_sort_by_score = False
                options.job_oldest_first = False
                options.match_all = False
                
                # Set other story type options to None to ensure they aren't used
                options.top_stories = None
                options.news_stories = None
                options.ask_stories = None
                options.poll_stories = None
                
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_jobs.assert_called_once_with(
            limit=5, sort_by_score=False, sort_newest_first=True,
            keywords=['python'], match_all=False, company_filter=None
        )

    @patch('pynews.utils.get_stories')
    @patch('pynews.job_view.display_job_listings')
    def test_job_sort_cli_integration(self, mock_display_jobs, mock_get_stories):
        """Test the --job-sort-by-score and --job-oldest-first command line options."""
        # Arrange
        mock_get_stories.return_value = list(range(20000, 20010))  # 10 job IDs
        
        # Act - simulate calling from command line with --job-stories --job-sort-by-score --job-oldest-first
        with patch('sys.argv', ['pynews', '--job-stories', '5', '--job-sort-by-score', '--job-oldest-first']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.job_stories = 5
                options.job_sort_by_score = True
                options.job_oldest_first = True
                options.job_keyword = None
                options.match_all = False
                
                # Set other story type options to None
                options.top_stories = None
                options.news_stories = None
                options.ask_stories = None
                options.poll_stories = None
                
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_jobs.assert_called_once_with(
            limit=5, sort_by_score=True, sort_newest_first=False,
            keywords=None, match_all=False, company_filter=None
        )


if __name__ == '__main__':
    unittest.main()