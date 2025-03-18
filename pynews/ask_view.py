"""
Module for displaying detailed views of Ask HN stories.
"""
import textwrap
import sys
import os
import html
import datetime
from webbrowser import open as url_open

from .colors import Colors, ColorScheme, colorize, supports_color
from .getch import getch
from .utils import get_story, format_comment_count, format_time_ago

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

def format_time_detailed(unix_time):
    """Format time in a detailed way with both absolute and relative time."""
    if not unix_time:
        return "Unknown time"
    
    # Get absolute time (formatted date)
    dt = datetime.datetime.fromtimestamp(unix_time)
    abs_time = dt.strftime("%b %d, %Y at %I:%M %p")
    
    # Get relative time (time ago)
    rel_time = format_time_ago(unix_time)
    
    # Combine them
    time_str = f"{abs_time} ({rel_time})"
    
    if USE_COLORS:
        return colorize(time_str, ColorScheme.TIME)
    return time_str

def clean_text(text):
    """Clean HTML from text and convert to plain text."""
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Replace some HTML tags with plain text alternatives
    text = text.replace('<p>', '\n\n')
    text = text.replace('<i>', '_').replace('</i>', '_')
    text = text.replace('<b>', '*').replace('</b>', '*')
    text = text.replace('<code>', '`').replace('</code>', '`')
    text = text.replace('<pre>', '\n```\n').replace('</pre>', '\n```\n')
    
    # Remove other HTML tags
    while '<' in text and '>' in text:
        start = text.find('<')
        end = text.find('>', start)
        if start != -1 and end != -1:
            text = text[:start] + text[end+1:]
        else:
            break
    
    return text.strip()

def format_score(score):
    """Format score with visual indicators based on value."""
    if USE_COLORS:
        if score >= 300:
            return colorize(f"★★★ {score} points ★★★", Colors.BRIGHT_YELLOW + Colors.BOLD)
        elif score >= 100:
            return colorize(f"★★ {score} points ★★", Colors.BRIGHT_GREEN + Colors.BOLD)
        elif score >= 50:
            return colorize(f"★ {score} points ★", Colors.GREEN + Colors.BOLD)
        else:
            return colorize(f"{score} points", ColorScheme.POINTS)
    else:
        if score >= 300:
            return f"*** {score} points ***"
        elif score >= 100:
            return f"** {score} points **"
        elif score >= 50:
            return f"* {score} points *"
        else:
            return f"{score} points"

def format_comment_count_detailed(count):
    """Format comment count with descriptive text based on activity level."""
    if USE_COLORS:
        if count >= 100:
            return colorize(f"💬 {count} comments (Very active discussion)", Colors.BRIGHT_GREEN + Colors.BOLD)
        elif count >= 50:
            return colorize(f"💬 {count} comments (Active discussion)", Colors.GREEN + Colors.BOLD)
        elif count >= 10:
            return colorize(f"💬 {count} comments", ColorScheme.COUNT)
        elif count > 0:
            return colorize(f"💬 {count} comments", ColorScheme.COUNT)
        else:
            return colorize("💬 No comments yet", Colors.FAINT)
    else:
        if count >= 100:
            return f"*** {count} comments (Very active discussion) ***"
        elif count >= 50:
            return f"** {count} comments (Active discussion) **"
        elif count >= 10:
            return f"{count} comments"
        elif count > 0:
            return f"{count} comments"
        else:
            return "No comments yet"

def display_ask_story_details(story_id):
    """
    Display detailed information about an Ask HN story, 
    highlighting the author information, score, comment count, and submission time.
    """
    # Fetch the story details
    story = get_story(story_id)
    if not story:
        error = "Error: Could not fetch story details"
        if USE_COLORS:
            error = colorize(error, ColorScheme.ERROR)
        print(error)
        return
    
    clear_screen()
    
    # Get story information
    title = story.get('title', 'Untitled')
    author = story.get('by', 'Anonymous')
    created_time = story.get('time', 0)
    points = story.get('score', 0)
    comment_count = len(story.get('kids', []))
    text = story.get('text', '')
    
    # Display the header with title
    if USE_COLORS:
        print(colorize("\n" + "=" * 80, ColorScheme.HEADER))
        print(colorize(title, ColorScheme.TITLE))
    else:
        print("\n" + "=" * 80)
        print(title)
    
    # Display time prominently
    time_display = f"🕒 Posted: {format_time_detailed(created_time)}"
    print(f"\n{time_display}")
    
    # Display score with visual indicators
    formatted_score = format_score(points)
    print(formatted_score)
    
    # Display comment count
    formatted_comments = format_comment_count_detailed(comment_count)
    print(formatted_comments)
    
    # Display author information
    if USE_COLORS:
        author_line = f"By: {colorize(author, ColorScheme.AUTHOR)}"
    else:
        author_line = f"By: {author}"
        
    print(f"\n{author_line}")
    
    # Display the story content if available
    if text:
        if USE_COLORS:
            print(colorize("\nContent:", ColorScheme.SUBHEADER))
            # Wrap and colorize text content
            wrapper = textwrap.TextWrapper(width=80, initial_indent='  ', subsequent_indent='  ')
            wrapped_text = wrapper.fill(clean_text(text))
            print(colorize(wrapped_text, ColorScheme.COMMENT_TEXT))
        else:
            print("\nContent:")
            wrapper = textwrap.TextWrapper(width=80, initial_indent='  ', subsequent_indent='  ')
            print(wrapper.fill(clean_text(text)))
    
    # Show options
    if USE_COLORS:
        print(colorize("\n" + "=" * 80, ColorScheme.HEADER))
        print(colorize("Options:", ColorScheme.NAV_HEADER))
    else:
        print("\n" + "=" * 80)
        print("Options:")
        
    print("[v] View author profile")
    print("[c] View comments")
    print("[u] Upvote this story (opens in browser)")
    print("[q] Return to menu")
    
    # Get user input
    while True:
        key = getch().lower()
        if key == 'v':
            # Open author profile in browser
            url_open(f"https://news.ycombinator.com/user?id={author}")
            break
        elif key == 'c':
            # Return a signal to view comments
            return {'action': 'view_comments', 'id': story_id}
        elif key == 'u':
            # Open the story page in browser to allow upvoting
            url_open(f"https://news.ycombinator.com/item?id={story_id}")
            break
        elif key == 'q':
            # Return to menu
            break
        else:
            # Invalid key, show error
            if USE_COLORS:
                print(colorize("\nInvalid option. Please try again.", ColorScheme.ERROR))
            else:
                print("\nInvalid option. Please try again.")
    
    return {'action': 'return_to_menu'}

def display_top_scored_ask_stories(limit=10, min_score=0, sort_by_comments=False, sort_by_time=False):
    """
    Display a list of Ask HN stories sorted by score, comment count, or time.
    
    Args:
        limit: Maximum number of stories to display
        min_score: Minimum score threshold for stories to include
        sort_by_comments: If True, sort by comment count
        sort_by_time: If True, sort by submission time (newest first)
    """
    from .utils import get_stories, get_story, sort_stories_by_score, sort_stories_by_comments, sort_stories_by_time
    from .loading import LoadingIndicator
    
    clear_screen()
    
    # Determine sort mode and display header
    if sort_by_time:
        sort_type = "time"
        header = "Most Recent Ask HN Stories"
    elif sort_by_comments:
        sort_type = "comments"
        header = "Most Discussed Ask HN Stories"
    else:
        sort_type = "score"
        header = "Top Scored Ask HN Stories"
        
    if USE_COLORS:
        print(colorize(f"\n=== {header} ===", ColorScheme.TITLE))
    else:
        print(f"\n=== {header} ===")
    
    # Fetch Ask story IDs
    loader = LoadingIndicator(message="Fetching Ask HN stories...")
    loader.start()
    try:
        story_ids = get_stories("ask")
    finally:
        loader.stop()
    
    if not story_ids:
        if USE_COLORS:
            print(colorize("\nNo Ask HN stories found.", ColorScheme.ERROR))
        else:
            print("\nNo Ask HN stories found.")
        return
    
    # Fetch story details with a loading indicator
    loader = LoadingIndicator(message="Fetching story details...")
    loader.start()
    try:
        stories = []
        for story_id in story_ids[:min(limit * 3, 100)]:  # Fetch more than needed for filtering
            story = get_story(story_id)
            if story and story.get('score', 0) >= min_score:
                stories.append(story)
    finally:
        loader.stop()
    
    # Sort based on the selected criteria and limit to requested number
    if sort_by_time:
        sorted_stories = sort_stories_by_time(stories)[:limit]
    elif sort_by_comments:
        sorted_stories = sort_stories_by_comments(stories)[:limit]
    else:
        sorted_stories = sort_stories_by_score(stories)[:limit]
    
    if not sorted_stories:
        if USE_COLORS:
            print(colorize(f"\nNo Ask HN stories found with score >= {min_score}.", ColorScheme.ERROR))
        else:
            print(f"\nNo Ask HN stories found with score >= {min_score}.")
        return
    
    # Display the stories
    for i, story in enumerate(sorted_stories):
        title = story.get('title', 'Untitled')
        author = story.get('by', 'Anonymous')
        score = story.get('score', 0)
        comment_count = len(story.get('kids', []))
        time_ago = format_time_ago(story.get('time', 0))
        
        if USE_COLORS:
            print(f"\n{colorize(f'{i+1}. {title}', ColorScheme.HEADER)}")
            print(f"   {format_score(score)} | {format_comment_count_detailed(comment_count)}")
            print(f"   🕒 {colorize(time_ago, ColorScheme.TIME)} | By: {colorize(author, ColorScheme.AUTHOR)}")
            print(f"   Link: {colorize(f'https://news.ycombinator.com/item?id={story.get('id')}', ColorScheme.URL)}")
        else:
            print(f"\n{i+1}. {title}")
            print(f"   {format_score(score)} | {format_comment_count_detailed(comment_count)}")
            print(f"   🕒 {time_ago} | By: {author}")
            print(f"   Link: https://news.ycombinator.com/item?id={story.get('id')}")
    
    # Prompt for user input
    if USE_COLORS:
        print(colorize("\n" + "=" * 80, ColorScheme.HEADER))
        print(colorize("Options:", ColorScheme.NAV_HEADER))
    else:
        print("\n" + "=" * 80)
        print("Options:")
        
    print("[number] View details for story (enter 1-10)")
    print("[s] Toggle sort by score")
    print("[c] Toggle sort by comments")
    print("[t] Toggle sort by time")
    print("[q] Return to menu")
    
    # Handle user input
    while True:
        key = getch().lower()
        if key == 'q':
            return {'action': 'return_to_menu'}
        elif key == 's':
            # Switch to score sorting
            return {'action': 'change_sort', 'sort_type': 'score'}
        elif key == 'c':
            # Switch to comment sorting
            return {'action': 'change_sort', 'sort_type': 'comments'}
        elif key == 't':
            # Switch to time sorting
            return {'action': 'change_sort', 'sort_type': 'time'}
        elif key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(sorted_stories):
                return {'action': 'view_story', 'id': sorted_stories[idx].get('id')}
        else:
            if USE_COLORS:
                print(colorize("\nInvalid option. Please try again.", ColorScheme.ERROR))
            else:
                print("\nInvalid option. Please try again.")