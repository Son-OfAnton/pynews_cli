"""
Script to gather news from HackerNews.
"""
import sys

import requests as req

from .constants import DEFAULT_THREADS_NUMBER
from .parser import get_parser_options
from .utils import create_list_stories, create_menu, get_stories
from .comments import display_comments_for_story


def main():
    """Main entry point for the script."""
    options = get_parser_options()
    
    # Handle comment viewing if requested
    if options.comments:
        # The display_comments_for_story function now handles navigation internally
        display_comments_for_story(
            options.comments, 
            page_size=options.page_size, 
            page_num=options.page, 
            width=options.width
        )
        return 0
    
    # Default behavior for story listing
    if options.top_stories:
        param = options.top_stories, "top"
    elif options.news_stories:
        param = options.news_stories, "news"
    else:
        print("Please specify either --top-stories or --news-stories or --comments")
        return 1

    list_data = None

    try:
        list_data = get_stories(param[1])
    except req.ConnectionError:
        print("A connection problem occurred.")
        return 1
    except req.Timeout:
        print("A timeout problem occurred.")
        return 1
    except req.TooManyRedirects:
        print(
            "The request exceeds the configured number\
            of maximum redirections."
        )
        return 1

    if not list_data:
        return 1

    max_threads = (
        options.threads if options.threads or 0 > 0 else DEFAULT_THREADS_NUMBER
    )

    list_dict_stories = create_list_stories(
        list_data, param[0], options.shuffle, max_threads
    )

    menu = create_menu(list_dict_stories, param[1])
    menu.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())