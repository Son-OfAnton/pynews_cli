"""
Integration tests for the Ask HN functionality in PyNews.
"""
import sys
import unittest
from unittest.mock import patch, MagicMock, call
import json

# Add the parent directory to the path
sys.path.append("..") # Add parent directory to path

from pynews.ask_view import display_ask_story_details, display_top_scored_ask_stories
from pynews.pynews import main
from pynews.constants import URLS
from test_ask_utils import create_mock_response, generate_mock_ask_story, generate_mock_ask_stories


class TestAskViewIntegration(unittest.TestCase):
    """Integration tests for Ask HN view with other components."""

    @patch('pynews.utils.req.get')
    def test_get_story_integration(self, mock_get):
        """Test integration between get_story and display_ask_story_details."""
        # Arrange
        story_id = 12345
        mock_story = generate_mock_ask_story(story_id)
        mock_response = create_mock_response(200, mock_story)
        mock_get.return_value = mock_response
        
        # Act
        with patch('pynews.ask_view.clear_screen'):
            with patch('pynews.ask_view.print'):
                with patch('pynews.ask_view.getch', return_value='q'):
                    display_ask_story_details(story_id)
        
        # Assert
        mock_get.assert_called_with(URLS["item"].format(story_id))

    @patch('pynews.utils.req.get')
    def test_api_error_handling(self, mock_get):
        """Test error handling during API calls."""
        # Arrange - Connection error
        mock_get.side_effect = Exception("API Error")
        
        # Act & Assert - Should handle the exception without crashing
        with patch('pynews.ask_view.print'):
            display_ask_story_details(12345)

    @patch('pynews.utils.req.get')
    def test_ask_stories_list_integration(self, mock_get):
        """Test integration between API and Ask HN stories list display."""
        # Arrange
        # First mock the API call to get the list of Ask HN stories
        story_ids = list(range(20000, 20010))  # 10 story IDs
        mock_get.side_effect = [
            create_mock_response(200, story_ids)  # First call returns story IDs
        ] + [
            create_mock_response(200, generate_mock_ask_story(id))  # Subsequent calls return story details
            for id in story_ids
        ]
        
        # Act
        with patch('pynews.ask_view.clear_screen'):
            with patch('pynews.ask_view.print'):
                with patch('pynews.ask_view.LoadingIndicator'):
                    with patch('pynews.ask_view.getch', return_value='q'):
                        display_top_scored_ask_stories(limit=5)
        
        # Assert
        # Should call the API at least for the Ask HN stories endpoint
        mock_get.assert_any_call(URLS["ask"])


class TestPyNewsCommandLineIntegration(unittest.TestCase):
    """Test integration with the main PyNews command line parser."""
    
    @patch('pynews.utils.get_stories')
    @patch('pynews.utils.create_list_stories')
    @patch('pynews.utils.create_menu')
    def test_ask_stories_cli_integration(self, mock_create_menu, mock_create_list_stories, mock_get_stories):
        """Test the --ask-stories command line option."""
        # Arrange
        mock_get_stories.return_value = list(range(20000, 20010))  # 10 story IDs
        mock_create_list_stories.return_value = [
            generate_mock_ask_story(id) for id in range(20000, 20010)
        ]
        
        mock_menu = MagicMock()
        mock_create_menu.return_value = mock_menu
        
        # Act - simulate calling from command line with --ask-stories 5
        with patch('sys.argv', ['pynews', '--ask-stories', '5']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.ask_stories = 5  # Number of stories to show
                options.shuffle = False
                options.threads = 10
                options.keyword = None
                options.sort_by_comments = False
                options.sort_by_time = False
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_get_stories.assert_called_once_with("ask")
        mock_create_list_stories.assert_called_once()
        mock_menu.show.assert_called_once()
    
    @patch('pynews.utils.get_story')
    @patch('pynews.ask_view.display_ask_story_details')
    def test_ask_details_cli_integration(self, mock_display_details, mock_get_story):
        """Test the --ask-details command line option."""
        # Arrange
        mock_get_story.return_value = generate_mock_ask_story(12345)
        
        # Act - simulate calling from command line with --ask-details 12345
        with patch('sys.argv', ['pynews', '--ask-details', '12345']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.ask_details = 12345  # Story ID to display
                options.ask_stories = None
                options.ask_top = None
                options.ask_discussed = None
                options.ask_recent = None
                options.ask_search = None
                options.keyword = None
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_details.assert_called_once_with(12345, None, False)
    
    @patch('pynews.utils.get_stories')
    @patch('pynews.ask_view.display_top_scored_ask_stories')
    def test_ask_top_cli_integration(self, mock_display_top, mock_get_stories):
        """Test the --ask-top command line option."""
        # Arrange
        mock_get_stories.return_value = list(range(20000, 20100))  # 100 story IDs
        
        # Act - simulate calling from command line with --ask-top 10
        with patch('sys.argv', ['pynews', '--ask-top', '10']):
            with patch('pynews.parser.get_parser_options') as mock_parser:
                # Configure parser to return the expected options
                options = MagicMock()
                options.ask_top = 10  # Number of stories to show
                options.ask_stories = None
                options.ask_details = None
                options.ask_discussed = None
                options.ask_recent = None
                options.ask_search = None
                options.keyword = None
                options.sort_by_comments = False
                options.sort_by_time = False
                mock_parser.return_value = options
                
                main()
        
        # Assert
        mock_display_top.assert_called_once_with(
            limit=10, min_score=0, 
            sort_by_comments=False, sort_by_time=False, 
            keywords=None, match_all=False, case_sensitive=False
        )


if __name__ == '__main__':
    unittest.main()