"""
Module for displaying detailed views of Ask HN stories.
"""
import textwrap
import sys
import os
import html
import datetime
import re
from webbrowser import open as url_open

from .colors import Colors, ColorScheme, colorize, supports_color
from .getch import getch
from .utils import (
    get_story, format_comment_count, format_time_ago,
    filter_stories_by_keywords, sort_stories_by_score,
    sort_stories_by_comments, sort_stories_by_time,
    get_stories
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

def highlight_keywords_in_text(text, keywords, case_sensitive=False):
    """
    Highlight keywords in text by wrapping them in special markers.
    
    Args:
        text: The text to highlight keywords in
        keywords: List of keywords to highlight
        case_sensitive: Whether the search should be case-sensitive
    
    Returns:
        Text with highlighted keywords
    """
    if not text or not keywords:
        return text
    
    # Create a copy of the original text for highlighting
    highlighted = text
    
    for keyword in keywords:
        if not keyword:
            continue
        
        # For case-insensitive, we need a regular expression with the i flag
        if case_sensitive:
            pattern = re.compile(re.escape(keyword))
        else:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        
        # Replace all occurrences with highlighted version
        if USE_COLORS:
            highlighted = pattern.sub(lambda m: colorize(m.group(0), Colors.BRIGHT_YELLOW + Colors.BOLD), highlighted)
        else:
            highlighted = pattern.sub(lambda m: f"*{m.group(0)}*", highlighted)
    
    return highlighted

def display_ask_story_details(story_id, keywords=None, case_sensitive=False):
    """
    Display detailed information about an Ask HN story, 
    highlighting the author information, score, comment count, and submission time.
    
    Args:
        story_id: ID of the story to display
        keywords: List of keywords to highlight in the content
        case_sensitive: Whether keyword highlighting should be case-sensitive
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
    
    # Highlight keywords in title and text if provided
    if keywords and any(keywords) and USE_COLORS:
        title = highlight_keywords_in_text(title, keywords, case_sensitive=case_sensitive)
        
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
        cleaned_text = clean_text(text)
        
        # Highlight keywords in the content if provided
        if keywords and any(keywords) and USE_COLORS:
            cleaned_text = highlight_keywords_in_text(cleaned_text, keywords, case_sensitive=case_sensitive)
            
        if USE_COLORS:
            print(colorize("\nContent:", ColorScheme.SUBHEADER))
            # Wrap text content
            wrapper = textwrap.TextWrapper(width=80, initial_indent='  ', subsequent_indent='  ')
            wrapped_text = wrapper.fill(cleaned_text)
            
            # Print with highlighting (already applied above)
            print(wrapped_text)
        else:
            print("\nContent:")
            wrapper = textwrap.TextWrapper(width=80, initial_indent='  ', subsequent_indent='  ')
            print(wrapper.fill(cleaned_text))
    
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

def display_top_scored_ask_stories(limit=10, min_score=0, sort_by_comments=False, sort_by_time=False,
                                 keywords=None, match_all=False, case_sensitive=False):
    """
    Display a list of Ask HN stories sorted by score, comment count, or time.
    
    Args:
        limit: Maximum number of stories to display
        min_score: Minimum score threshold for stories to include
        sort_by_comments: If True, sort by comment count
        sort_by_time: If True, sort by submission time (newest first)
        keywords: List of keywords to search and highlight
        match_all: If True, all keywords must match; if False, any keyword can match
        case_sensitive: Whether the search should be case-sensitive
    """
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
    
    # Add keyword search info to the header
    if keywords and any(keywords):
        keyword_display = ', '.join(f'"{k}"' for k in keywords)
        match_type = "ALL" if match_all else "ANY"
        header += f" - Filtering for {match_type} of: {keyword_display}"
        
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
    
    # Apply keyword filtering if keywords are provided
    if keywords and any(keywords):
        original_count = len(stories)
        stories = filter_stories_by_keywords(stories, keywords, match_all, case_sensitive)
        filtered_count = len(stories)
        
        if USE_COLORS:
            filter_info = colorize(f"\nFiltered: {filtered_count}/{original_count} stories match your keywords", ColorScheme.INFO)
        else:
            filter_info = f"\nFiltered: {filtered_count}/{original_count} stories match your keywords"
        print(filter_info)
    
    # Sort based on the selected criteria and limit to requested number
    if sort_by_time:
        sorted_stories = sort_stories_by_time(stories)[:limit]
    elif sort_by_comments:
        sorted_stories = sort_stories_by_comments(stories)[:limit]
    else:
        sorted_stories = sort_stories_by_score(stories)[:limit]
    
    if not sorted_stories:
        if keywords and any(keywords):
            if USE_COLORS:
                print(colorize(f"\nNo stories matched your search criteria.", ColorScheme.ERROR))
            else:
                print(f"\nNo stories matched your search criteria.")
        else:
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
        
        #  If keywords were provided and colorization is enabled
        if keywords and any(keywords) and USE_COLORS:
            title = highlight_keywords_in_text(title, keywords, case_sensitive=case_sensitive)
        
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