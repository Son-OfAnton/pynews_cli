"""
Integration tests for the Poll stories functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.poll_view import display_poll_titles, display_poll_details
from pynews.pynews import main
from pynews.constants import URLS
from test_poll_utils import (
    create_mock_response,
    generate_mock_poll_story,
    generate_mock_poll_option,
    generate_mock_poll_with_options,
    generate_poll_ids
)


class TestPollViewIntegration(unittest.TestCase):
    """Integration tests for Poll view with other components."""

    @patch('pynews.utils.req.get')
    def test_poll_api_integration(self, mock_get):
        """Test integration between poll view and the HackerNews API."""
        # Arrange
        # Setup for API call to get story IDs
        story_ids = generate_poll_ids(10)
        story_ids_response = create_mock_response(200, story_ids)
        
        # Create a poll and options
        poll_id = 30000
        poll, options = generate_mock_poll_with_options(poll_id, 100, 20, 3)
        
        # Mock responses for poll and options
        poll_response = create_mock_response(200, poll)
        option_responses = [create_mock_response(200, option) for option in options]
        
        # Configure mock to return different responses for different URLs
        def side_effect(url):
            if url == URLS["top"]:
                return story_ids_response
            elif url == URLS["item"].format(poll_id):
                return poll_response
            
            # Return option responses for option IDs
            for i, option in enumerate(options):
                if url == URLS["item"].format(option["id"]):
                    return option_responses[i]
                    
            # Return a poll for other story IDs (to ensure we find polls)
            for story_id in story_ids:
                if url == URLS["item"].format(story_id):
                    if story_id == poll_id:
                        return poll_response
                    else:
                        new_poll, _ = generate_mock_poll_with_options(story_id, 100, 20, 3)
                        return create_mock_response(200, new_poll)
            
            return create_mock_response(404, None)
            
        mock_get.side_effect = side_effect
        
        # Act - simulate pressing 'q' to quit immediately
        with patch('pynews.poll_view.getch', return_value='q'):
            with patch('pynews.poll_view.clear_screen'):
                with patch('pynews.poll_view.print'):
                    with patch('pynews.poll_view.LoadingIndicator'):
                        display_poll_titles(limit=5)
        
        # Assert - Check that API was called
        mock_get.assert_any_call(URLS["top"])  # Should call for story list
        # Should call for at least one poll
        self.assertTrue(any(call(URLS["item"].format(id)) in mock_get.call_args_list 
                          for id in story_ids))

    @patch('pynews.utils.req.get')
    def test_poll_details_api_integration(self, mock_get):
        """Test API integration when displaying poll details."""
        # Arrange
        poll_id = 30000
        poll, options = generate_mock_poll_with_options(poll_id, 100, 20, 3)
        
        # Configure mock responses
        poll_response = create_mock_response(200, poll)
        option_responses = {
            opt["id"]: create_mock_response(200, opt) for opt in options
        }
        
        def side_effect(url):
            if url == URLS["item"].format(poll_id):
                return poll_response
            
            for opt_id, response in option_responses.items():
                if url == URLS["item"].format(opt_id):
                    return response
            
            return create_mock_response(404, None)
            
        mock_get.side_effect = side_effect
        
        # Act - simulate pressing 'q' to quit
        with patch('pynews.poll_view.getch', return_value='q'):
            with patch('pynews.poll_view.clear_screen'):
                with patch('pynews.poll_view.print'):
                    display_poll_details(poll_id)
        
        # Assert
        mock_get.assert_any_call(URLS["item"].format(poll_id))  # Should call for poll
        # Should call for each option
        for opt_id in poll["parts"]:
            mock_get.assert_any_call(URLS["item"].format(opt_id))

    @patch('pynews.utils.req.get')
    def test_poll_error_handling(self, mock_get):
        """Test error handling during API calls in the poll view."""
        # Arrange - API fails with exception
        mock_get.side_effect = Exception("API Error")
        
        # Act & Assert - Should handle exception without crashing
        with patch('pynews.poll_view.clear_screen'):
            with patch('pynews.poll_view.print'):
                with patch('pynews.poll_view.LoadingIndicator'):
                    with patch('pynews.poll_view.getch', return_value='q'):
                        display_poll_titles()


class TestPyNewsCommandLineIntegration(unittest.TestCase):
    """Test integration with the main PyNews command line parser."""
    
    @patch('pynews.poll_view.display_poll_titles')
    def test_poll_stories_cli_integration(self, mock_display_polls):
        """Test the --poll-stories command line option."""
        # Arrange
        # Act - simulate calling from command line with --poll-stories 5
        with patch('sys.argv', ['pynews', '--poll-stories', '5']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.poll_stories = 5
                options.poll_details = None
                options.poll_recent = None
                options.poll_top = None
                options.poll_discussed = None
                options.poll_keyword = None
                options.sort_by_comments = False
                options.sort_by_time = False
                options.match_all = False
                
                # Set other story types to None
                options.job_stories = None
                options.top_stories = None
                options.news_stories = None
                options.ask_stories = None
                
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_polls.assert_called_once_with(
            limit=5, min_score=0, sort_by_comments=False, sort_by_time=False,
            keywords=None, match_all=False, case_sensitive=False
        )

    @patch('pynews.poll_view.display_poll_details')
    def test_poll_details_cli_integration(self, mock_display_details):
        """Test the --poll-details command line option."""
        # Arrange
        poll_id = 30000
        
        # Act - simulate calling from command line with --poll-details 30000
        with patch('sys.argv', ['pynews', '--poll-details', str(poll_id)]):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.poll_details = poll_id
                options.poll_stories = None
                options.poll_recent = None
                options.poll_top = None
                options.poll_discussed = None
                
                # Set other story types to None
                options.job_stories = None
                options.top_stories = None
                options.news_stories = None
                options.ask_stories = None
                
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_details.assert_called_once_with(poll_id)


if __name__ == '__main__':
    unittest.main()