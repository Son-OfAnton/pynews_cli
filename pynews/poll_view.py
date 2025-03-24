"""
Module for displaying poll questions from Hacker News.
"""
import os
import html
import datetime
import sys
import textwrap
from webbrowser import open as url_open

from .colors import Colors, ColorScheme, colorize, supports_color
from .getch import getch
from .utils import (
    get_story, format_comment_count, format_time_ago,
    filter_stories_by_keywords, sort_stories_by_score,
    sort_stories_by_comments, sort_stories_by_time,
    get_stories, clean_text
)

USE_COLORS = supports_color()

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_timestamp(unix_time):
    """Convert Unix timestamp to a human-readable format."""
    try:
        dt = datetime.datetime.fromtimestamp(unix_time)
        # Format: "Mar 17, 2023 at 10:30 AM"
        timestamp = dt.strftime("%b %d, %Y at %I:%M %p")
        if USE_COLORS:
            timestamp = colorize(timestamp, ColorScheme.TIME)
        return timestamp
    except (TypeError, ValueError):
        return colorize("Unknown time", ColorScheme.TIME) if USE_COLORS else "Unknown time"

def is_poll(story):
    """Check if a story is a poll post."""
    return story and story.get('type') == 'poll' and 'parts' in story

def get_poll_list(limit=30, min_score=0, sort_by_comments=False, sort_by_time=False, 
                  keywords=None, match_all=False, case_sensitive=False):
    """
    Get a list of poll stories, filtered and sorted according to parameters.
    
    Args:
        limit: Maximum number of polls to retrieve
        min_score: Minimum score threshold
        sort_by_comments: Whether to sort by comment count instead of score
        sort_by_time: Whether to sort by submission time
        keywords: List of keywords to filter by
        match_all: Whether all keywords must match (AND) or any (OR)
        case_sensitive: Whether keyword matching should be case-sensitive
        
    Returns:
        List of poll story dictionaries
    """
    # Get top stories as a source of polls (since there's no dedicated poll API endpoint)
    poll_ids = get_stories("top")
    if not poll_ids:
        return []
    
    # Collect all polls
    polls = []
    count = 0
    
    # Fetch stories and check if they are polls
    for poll_id in poll_ids[:min(limit * 3, 100)]:  # Look at more stories to find enough polls
        story = get_story(poll_id)
        if story and is_poll(story) and story.get('score', 0) >= min_score:
            polls.append(story)
            count += 1
            if count >= limit:
                break
    
    # Apply keyword filtering if specified
    if keywords and any(keywords):
        polls = filter_stories_by_keywords(
            polls, keywords, match_all=match_all, case_sensitive=case_sensitive
        )
    
    # Sort the polls
    if sort_by_time:
        polls = sort_stories_by_time(polls)
    elif sort_by_comments:
        polls = sort_stories_by_comments(polls)
    else:
        polls = sort_stories_by_score(polls)
    
    return polls

def display_poll_titles(limit=30, min_score=0, sort_by_comments=False, sort_by_time=False,
                         keywords=None, match_all=False, case_sensitive=False,
                         page_size=10):
    """
    Display a list of poll titles with navigation options.
    
    Args:
        limit: Maximum number of polls to display
        min_score: Minimum score threshold
        sort_by_comments: Whether to sort by comment count
        sort_by_time: Whether to sort by submission time
        keywords: List of keywords to filter by
        match_all: Whether all keywords must match (AND) or any (OR)
        case_sensitive: Whether keyword matching should be case-sensitive
        page_size: Number of items to display per page
        
    Returns:
        Dictionary with action and possible poll ID if a poll was selected
    """
    # Get the list of polls
    polls = get_poll_list(
        limit=limit,
        min_score=min_score,
        sort_by_comments=sort_by_comments,
        sort_by_time=sort_by_time,
        keywords=keywords,
        match_all=match_all,
        case_sensitive=case_sensitive
    )
    
    if not polls:
        print(f"No polls found with score >= {min_score}.")
        print("Press any key to return...")
        getch()
        return {'action': 'return_to_menu'}
    
    # Display the list of polls with pagination
    current_page = 0
    total_pages = (len(polls) - 1) // page_size + 1
    
    while True:
        clear_screen()
        
        # Display header
        if sort_by_comments:
            header = "Poll Questions (Sorted by Comment Count)"
        elif sort_by_time:
            header = "Poll Questions (Sorted by Time)"
        else:
            header = "Poll Questions (Sorted by Score)"
            
        if keywords and any(keywords):
            keyword_str = ', '.join(keywords)
            header += f" - Filtered by: {keyword_str}"
        
        print(f"\n{'=' * len(header)}")
        print(header)
        print(f"{'=' * len(header)}")
        
        # Display the current page of polls
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(polls))
        
        for i, poll in enumerate(polls[start_idx:end_idx], start=1):
            title = poll.get('title', 'Untitled Poll')
            score = poll.get('score', 0)
            author = poll.get('by', 'Anonymous')
            comment_count = len(poll.get('kids', []))
            time_ago = format_time_ago(poll.get('time', 0))
            
            # Format the display
            if USE_COLORS:
                idx_str = colorize(f"{start_idx + i}.", ColorScheme.INFO)
                title_str = colorize(title, ColorScheme.TITLE)
                score_str = colorize(f"{score} points", ColorScheme.POINTS)
                author_str = colorize(f"by {author}", ColorScheme.AUTHOR)
                comments_str = colorize(f"{comment_count} comments", ColorScheme.COUNT)
                time_str = colorize(time_ago, ColorScheme.TIME)
            else:
                idx_str = f"{start_idx + i}."
                title_str = title
                score_str = f"{score} points"
                author_str = f"by {author}"
                comments_str = f"{comment_count} comments"
                time_str = time_ago
            
            print(f"{idx_str} {title_str}")
            print(f"   {score_str} | {comments_str} | {time_str} | {author_str}")
            print()
        
        # Display navigation options
        print("\nNavigation:")
        print("[n] Next page" if current_page < total_pages - 1 else "[n] -")
        print("[p] Previous page" if current_page > 0 else "[p] -")
        print("[number] View poll details")
        print("[s] Sort by score")
        print("[c] Sort by comments")
        print("[t] Sort by time")
        print("[q] Return to main menu")
        
        print(f"\nPage {current_page + 1} of {total_pages}")
        
        # Get user input
        choice = getch()
        
        if choice == 'q':
            return {'action': 'return_to_menu'}
        elif choice == 'n' and current_page < total_pages - 1:
            current_page += 1
        elif choice == 'p' and current_page > 0:
            current_page -= 1
        elif choice == 's':
            return {'action': 'change_sort', 'sort_type': 'score'}
        elif choice == 'c':
            return {'action': 'change_sort', 'sort_type': 'comments'}
        elif choice == 't':
            return {'action': 'change_sort', 'sort_type': 'time'}
        elif choice.isdigit():
            # Try to view poll details
            idx = int(choice) - 1
            if start_idx <= idx < end_idx:
                poll_id = polls[idx].get('id')
                return {'action': 'view_poll', 'id': poll_id}

def display_poll_details(poll_id):
    """
    Display detailed information about a specific poll, including the question and options.
    
    Args:
        poll_id: The ID of the poll to display
        
    Returns:
        Dictionary with action (view_comments/return_to_list)
    """
    # Fetch the poll
    poll = get_story(poll_id)
    if not poll or not is_poll(poll):
        print("Poll not found or not a valid poll.")
        print("Press any key to return...")
        getch()
        return {'action': 'return_to_list'}
    
    # Get the poll parts (options)
    parts = poll.get('parts', [])
    
    # Display the poll details
    while True:
        clear_screen()
        
        # Display poll title and info
        title = poll.get('title', 'Untitled Poll')
        score = poll.get('score', 0)
        author = poll.get('by', 'Anonymous')
        comment_count = len(poll.get('kids', []))
        timestamp = format_timestamp(poll.get('time', 0))
        
        if USE_COLORS:
            print(colorize("=" * 40, Colors.BRIGHT_BLUE))
            print(colorize(title, Colors.BRIGHT_GREEN + Colors.BOLD))
            print(colorize("=" * 40, Colors.BRIGHT_BLUE))
            print(colorize(f"Posted by: {author}", ColorScheme.AUTHOR))
            print(colorize(f"Score: {score} points", ColorScheme.POINTS))
            print(colorize(f"Comments: {comment_count}", ColorScheme.COUNT))
            print(colorize(f"Posted on: {timestamp}", ColorScheme.TIME))
        else:
            print("=" * 40)
            print(title)
            print("=" * 40)
            print(f"Posted by: {author}")
            print(f"Score: {score} points")
            print(f"Comments: {comment_count}")
            print(f"Posted on: {timestamp}")
        
        print("\nPoll Options:")
        
        # Display poll options
        if parts:
            for i, part_id in enumerate(parts, 1):
                option = get_story(part_id)
                if option:
                    option_text = option.get('text', 'Unknown option')
                    option_score = option.get('score', 0)
                    
                    # Clean HTML from option text
                    option_text = clean_text(option_text)
                    
                    if USE_COLORS:
                        print(colorize(f"{i}. {option_text} - {option_score} votes", ColorScheme.INFO))
                    else:
                        print(f"{i}. {option_text} - {option_score} votes")
        else:
            print("No poll options found.")
        
        # Display navigation options
        print("\nOptions:")
        print("[c] View comments")
        print("[b] Back to poll list")
        print("[o] Open in browser")
        print("[q] Return to main menu")
        
        # Get user input
        choice = getch()
        
        if choice == 'q':
            return {'action': 'return_to_menu'}
        elif choice == 'b':
            return {'action': 'return_to_list'}
        elif choice == 'c':
            return {'action': 'view_comments'}
        elif choice == 'o':
            # Open in browser
            url = f"https://news.ycombinator.com/item?id={poll_id}"
            url_open(url)