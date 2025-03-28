"""
Script to gather news from HackerNews.
"""
import sys

import requests as req

from .constants import DEFAULT_THREADS_NUMBER
from .parser import get_parser_options
from .utils import create_list_stories, create_menu, get_stories, filter_stories_by_keywords
from .comments import display_comments_for_story
from .ask_view import display_ask_discussions_dashboard, display_ask_story_details, display_top_scored_ask_stories
from .job_view import display_job_details_with_live_comments, display_job_listings, display_jobs_discussion_dashboard
from .poll_view import display_poll_titles, display_poll_details
from .user_view import (display_user, search_user, list_users, display_karma, 
                        display_created_date, display_user_stories)

def handle_user_profile(username):
    """Handle displaying a specific user's profile."""
    try:
        result = display_user(username)
        
        # Process any chained actions from the user profile
        if result and result.get('action') == 'view_karma':
            return handle_user_karma(result.get('username'))
        elif result and result.get('action') == 'view_created':
            return handle_user_created_date(result.get('username'))
        elif result and result.get('action') == 'view_stories':
            return handle_user_stories(result.get('username'))
        
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        print(f"\nError displaying user profile: {e}")
        return 1

def handle_user_karma(username):
    """Handle displaying a user's karma."""
    try:
        result = display_karma(username)
        
        # Process any chained actions from the karma view
        if result and result.get('action') == 'view_profile':
            return handle_user_profile(result.get('username'))
        elif result and result.get('action') == 'view_created':
            return handle_user_created_date(result.get('username'))
        elif result and result.get('action') == 'view_stories':
            return handle_user_stories(result.get('username'))
        
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        print(f"\nError displaying user karma: {e}")
        return 1

def handle_user_created_date(username):
    """Handle displaying a user's account creation date."""
    try:
        result = display_created_date(username)
        
        # Process any chained actions from the creation date view
        if result and result.get('action') == 'view_profile':
            return handle_user_profile(result.get('username'))
        elif result and result.get('action') == 'view_karma':
            return handle_user_karma(result.get('username'))
        elif result and result.get('action') == 'view_stories':
            return handle_user_stories(result.get('username'))
        
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        print(f"\nError displaying user creation date: {e}")
        return 1

def handle_user_stories(username):
    """Handle displaying a user's submitted stories."""
    try:
        result = display_user_stories(username)
        
        # Process any chained actions from the stories view
        if result and result.get('action') == 'view_profile':
            return handle_user_profile(result.get('username'))
        elif result and result.get('action') == 'view_karma':
            return handle_user_karma(result.get('username'))
        elif result and result.get('action') == 'view_created':
            return handle_user_created_date(result.get('username'))
        elif result and result.get('action') == 'view_comments':
            display_comments_for_story(result.get('story_id'))
            # After viewing comments, go back to stories
            return handle_user_stories(username)
        
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        print(f"\nError displaying user stories: {e}")
        return 1

def handle_user_search():
    """Handle user search functionality."""
    try:
        result = search_user()
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        print(f"\nError with user search: {e}")
        return 1

def handle_user_list():
    """Handle listing random users."""
    try:
        result = list_users()
        return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        print(f"\nError listing users: {e}")
        return 1

def handle_poll_details(poll_id, page_size=10, width=80):
    """Handle detailed view of a poll with option to view comments."""
    result = display_poll_details(poll_id)
    
    # Check if user wants to view comments
    if result and result.get('action') == 'view_comments':
        display_comments_for_story(poll_id, page_size=page_size, width=width)
    
    # Return to main menu otherwise

def handle_poll_list(limit=10, min_score=0, sort_by_comments=False, sort_by_time=False, 
                     keywords=None, match_all=False, case_sensitive=False,
                     page_size=10, width=80):
    """Handle the display of poll questions with navigation options."""
    while True:
        result = display_poll_titles(
            limit=limit,
            min_score=min_score,
            sort_by_comments=sort_by_comments,
            sort_by_time=sort_by_time,
            keywords=keywords,
            match_all=match_all,
            case_sensitive=case_sensitive,
            page_size=page_size
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
        
        if result.get('action') == 'view_poll':
            poll_result = display_poll_details(result.get('id'))
            
            # Check if user wants to view comments from the poll view
            if poll_result and poll_result.get('action') == 'view_comments':
                display_comments_for_story(result.get('id'), page_size=page_size, width=width)
                
            # If the user wants to return to the list, continue the loop
            if poll_result and poll_result.get('action') != 'return_to_menu':
                continue
            # If the user wants to return to the main menu, break the loop
            else:
                break

def handle_ask_story(story_id, page_size=10, width=80, auto_refresh=False, refresh_interval=60, notify_new_comments=False):
    """Handle detailed view of an Ask HN story with option to view comments."""
    result = display_ask_story_details(story_id)
    
    # Check if user wants to view comments
    if result and result.get('action') == 'view_comments':
        display_comments_for_story(
            story_id, 
            page_size=page_size, 
            width=width,
            auto_refresh=auto_refresh,
            refresh_interval=refresh_interval,
            notify_new_comments=notify_new_comments
        )
    # Return to main menu otherwise

def handle_top_ask_stories(limit=10, min_score=0, sort_by_comments=False, sort_by_time=False, 
                           keywords=None, match_all=False, case_sensitive=False,
                           page_size=10, width=80, auto_refresh=False, refresh_interval=60, 
                           notify_new_comments=False):
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
                display_comments_for_story(
                    result.get('id'), 
                    page_size=page_size, 
                    width=width,
                    auto_refresh=auto_refresh,
                    refresh_interval=refresh_interval,
                    notify_new_comments=notify_new_comments
                )

def handle_job_stories(limit=20, page_size=10, keywords=None, match_all=False, case_sensitive=False,
                      sort_by_score=False, newest_first=True, auto_refresh=False, 
                      refresh_interval=60, notify_new_comments=False):
    """
    Handle the display of job listings with filtering and sorting options.
    
    Args:
        limit: Maximum number of jobs to fetch
        page_size: Number of jobs to display per page
        keywords: List of keywords to filter by
        match_all: If True, all keywords must match; if False, any keyword can match
        case_sensitive: Whether keyword search should be case-sensitive
        sort_by_score: Whether to sort by score instead of date
        newest_first: Whether to sort newest first (when sorting by date)
        auto_refresh: Whether to auto-refresh comments
        refresh_interval: Seconds between comment refreshes
        notify_new_comments: Whether to show notifications for new comments
    """
    # Get the job selected by the user, if any
    job_id = display_job_listings(
        limit=limit,
        page_size=page_size,
        sort_newest_first=newest_first,
        sort_by_score=sort_by_score,
        keywords=keywords,
        match_all=match_all,
        case_sensitive=case_sensitive
    )
    
    # If a job was selected to view, display it with comment auto-refresh
    if job_id:
        display_job_details_with_live_comments(
            job_id,
            auto_refresh=auto_refresh,
            refresh_interval=refresh_interval,
            notify_new_comments=notify_new_comments,
            page_size=page_size
        )

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
                width=options.width,
                export_json=options.export_json,
                export_csv=options.export_csv,
                export_path=options.export_path,
                export_filename=options.export_filename,
                include_timestamp=not options.no_timestamp
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            print(f"\nError: {e}")
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
    
    # Handle poll details if requested
    if options.poll_details:
        try:
            handle_poll_details(
                options.poll_details,
                page_size=options.page_size,
                width=options.width
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    # Handle poll stories if requested
    if options.poll_stories:
        try:
            handle_poll_list(
                limit=options.poll_stories,
                min_score=options.min_score,
                sort_by_comments=options.sort_by_comments,
                sort_by_time=options.sort_by_time,
                keywords=options.poll_keyword,
                match_all=options.match_all,
                case_sensitive=options.case_sensitive,
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
                page_size=options.page_size,
                keywords=options.job_keyword,
                match_all=options.match_all,
                case_sensitive=options.case_sensitive,
                sort_by_score=options.job_sort_by_score,
                newest_first=not options.job_oldest_first
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    if options.job_dashboard:
        try:
            display_jobs_discussion_dashboard(
                initial_jobs=options.job_dashboard_ids,
                auto_refresh=options.job_auto_refresh or options.auto_refresh,
                refresh_interval=options.job_refresh_interval if options.job_refresh_interval else options.refresh_interval,
                page_size=options.page_size,
                width=options.width,
                notify_new_comments=options.notify_new_comments
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0

    # Update the job stories handling
    if options.job_stories:
        try:
            handle_job_stories(
                limit=options.job_stories,
                page_size=options.page_size,
                keywords=options.job_keyword,
                match_all=options.match_all,
                case_sensitive=options.case_sensitive,
                sort_by_score=options.job_sort_by_score,
                newest_first=not options.job_oldest_first,
                auto_refresh=options.job_auto_refresh or options.auto_refresh,
                refresh_interval=options.job_refresh_interval if options.job_refresh_interval else options.refresh_interval,
                notify_new_comments=options.notify_new_comments
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    if options.user:
        return handle_user_profile(options.user)
        
    if options.user_search:
        return handle_user_search()
        
    if options.list_users:
        return handle_user_list()
        
    if options.user_karma:
        return handle_user_karma(options.user_karma)
        
    if options.user_created:
        return handle_user_created_date(options.user_created)
        
    if options.user_stories:
        return handle_user_stories(options.user_stories)
    
    if options.ask_details:
        try:
            handle_ask_story(
                options.ask_details,
                page_size=options.page_size,
                width=options.width,
                auto_refresh=options.ask_auto_refresh or options.auto_refresh,
                refresh_interval=options.ask_refresh_interval if options.ask_refresh_interval else options.refresh_interval,
                notify_new_comments=options.notify_new_comments
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
                width=options.width,
                auto_refresh=options.ask_auto_refresh or options.auto_refresh,
                refresh_interval=options.ask_refresh_interval if options.ask_refresh_interval else options.refresh_interval,
                notify_new_comments=options.notify_new_comments
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        return 0
    
    if options.ask_dashboard:
        try:
            display_ask_discussions_dashboard(
                initial_stories=options.dashboard_stories,
                auto_refresh=options.ask_auto_refresh or options.auto_refresh,
                refresh_interval=options.ask_refresh_interval if options.ask_refresh_interval else options.refresh_interval,
                page_size=options.page_size,
                width=options.width,
                notify_new_comments=options.notify_new_comments
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
        print("Please specify either --top-stories, --news-stories, --ask-stories, --job-stories, --poll-stories, --ask-top, --ask-discussed, --ask-recent, --ask-search, --poll-top, --poll-discussed, --poll-recent, --comments, --user, --list-users, --user-search, --user-karma, --user-created, or --user-stories")
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