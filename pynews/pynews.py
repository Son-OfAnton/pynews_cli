"""
Script to gather news from HackerNews.
"""
import sys

import requests as req

from .constants import DEFAULT_THREADS_NUMBER
from .parser import get_parser_options
from .utils import create_list_stories, create_menu, get_stories, filter_stories_by_keywords
from .comments import display_comments_for_story
from .ask_view import display_ask_story_details, display_top_scored_ask_stories
from .job_view import display_job_listings

def handle_ask_story(story_id, page_size=10, width=80):
    """Handle detailed view of an Ask HN story with option to view comments."""
    result = display_ask_story_details(story_id)
    
    # Check if user wants to view comments
    if result and result.get('action') == 'view_comments':
        display_comments_for_story(story_id, page_size=page_size, width=width)
    
    # Return to main menu otherwise

def handle_top_ask_stories(limit=10, min_score=0, sort_by_comments=False, sort_by_time=False, 
                           keywords=None, match_all=False, case_sensitive=False,
                           page_size=10, width=80):
    """Handle the display of top Ask HN stories (by score, comments, or time) with keyword filtering."""
    while True:
        result = display_top_scored_ask_stories(
            limit=limit, 
            min_score=min_score, 
            sort_by_comments=sort_by_comments, 
            sort_by_time=sort_by_time,
            keywords=keywords,
            match_all=match_all,
            case_sensitive=case_sensitive
        )
        
        if not result or result.get('action') == 'return_to_menu':
            break
            
        if result.get('action') == 'change_sort':
            # Change the sorting mode
            sort_type = result.get('sort_type', 'score')
            if sort_type == 'comments':
                sort_by_comments = True
                sort_by_time = False
            elif sort_type == 'time':
                sort_by_comments = False
                sort_by_time = True
            else:  # score
                sort_by_comments = False
                sort_by_time = False
            continue
        
        if result.get('action') == 'view_story':
            story_result = display_ask_story_details(result.get('id'))
            
            # Check if user wants to view comments from the story view
            if story_result and story_result.get('action') == 'view_comments':
                display_comments_for_story(result.get('id'), page_size=page_size, width=width)

def handle_job_stories(limit=20, page_size=10):
    """Handle the display of job listings."""
    display_job_listings(limit=limit, page_size=page_size)

def main():
    """Main entry point for the script."""
    options = get_parser_options()
    
    # Handle comment viewing if requested
    if options.comments:
        # The display_comments_for_story function now handles pagination and navigation internally
        try:
            display_comments_for_story(
                options.comments, 
                page_size=options.page_size, 
                page_num=options.page, 
                width=options.width
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    # Handle Ask HN story detailed view if requested
    if options.ask_details:
        try:
            handle_ask_story(
                options.ask_details,
                page_size=options.page_size,
                width=options.width
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    # Handle top-scored Ask HN stories if requested
    if options.ask_top:
        try:
            handle_top_ask_stories(
                limit=options.ask_top,
                min_score=options.min_score,
                sort_by_comments=options.sort_by_comments,
                sort_by_time=options.sort_by_time,
                keywords=options.keyword,
                match_all=options.match_all,
                case_sensitive=options.case_sensitive,
                page_size=options.page_size,
                width=options.width
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    # Handle job stories if requested
    if options.job_stories:
        try:
            handle_job_stories(
                limit=options.job_stories,
                page_size=options.page_size
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    # Default behavior for story listing
    if options.top_stories:
        param = options.top_stories, "top"
    elif options.news_stories:
        param = options.news_stories, "news"
    elif options.ask_stories:
        param = options.ask_stories, "ask"
    else:
        print("Please specify either --top-stories, --news-stories, --ask-stories, --job-stories, --ask-top, --ask-discussed, --ask-recent, --ask-search, or --comments")
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
    
    # For Ask stories, we can sort by score (default), comments, or time
    sort_by_comments = param[1] == "ask" and options.sort_by_comments
    sort_by_time = param[1] == "ask" and options.sort_by_time
    
    # Create the menu with appropriate sorting and keyword filtering
    menu = create_menu(
        list_dict_stories, 
        param[1], 
        sort_by_score=not (sort_by_comments or sort_by_time),
        sort_by_time=sort_by_time,
        keywords=options.keyword,
        highlight_keys=True
    )
    menu.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())