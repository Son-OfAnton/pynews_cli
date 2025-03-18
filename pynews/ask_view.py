"""
Module for displaying detailed views of Ask HN stories.
"""
import textwrap
import sys
import os
import html
from webbrowser import open as url_open

from .colors import Colors, ColorScheme, colorize, supports_color
from .getch import getch
from .utils import get_story, format_score

USE_COLORS = supports_color()

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_timestamp(unix_time):
    """Convert Unix timestamp to a human-readable format."""
    import datetime
    try:
        dt = datetime.datetime.fromtimestamp(unix_time)
        # Format: "Mar 17, 2023 at 10:30 AM"
        timestamp = dt.strftime("%b %d, %Y at %I:%M %p")
        if USE_COLORS:
            timestamp = colorize(timestamp, ColorScheme.TIME)
        return timestamp
    except (TypeError, ValueError):
        return colorize("Unknown time", ColorScheme.TIME) if USE_COLORS else "Unknown time"

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

def create_score_bar(score, max_width=40):
    """Create a visual bar representing the score."""
    # Scale: ▁▂▃▄▅▆▇█
    # Determine the number of blocks based on score
    if score <= 0:
        return "▁" * 5  # Minimum bar for non-positive scores
    
    # Scale logarithmically since HN scores can vary widely
    import math
    log_score = math.log10(score + 1)  # +1 to handle score=0
    max_log = math.log10(1001)  # Scale against a score of 1000
    ratio = min(log_score / max_log, 1.0)  # Cap at 1.0
    
    # Map to bar width
    bar_width = int(max_width * ratio)
    bar_width = max(5, bar_width)  # Ensure minimum width
    
    # Create the bar with gradient characters based on score
    if score < 10:
        bar = "▁" * bar_width
    elif score < 25:
        bar = "▂" * bar_width
    elif score < 50:
        bar = "▃" * bar_width
    elif score < 100:
        bar = "▄" * bar_width
    elif score < 200:
        bar = "▅" * bar_width
    elif score < 500:
        bar = "▆" * bar_width
    elif score < 1000:
        bar = "▇" * bar_width
    else:
        bar = "█" * bar_width
    
    return bar

def display_ask_story_details(story_id):
    """
    Display detailed information about an Ask HN story, 
    highlighting the author information and score.
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
    
    # Display score prominently with a visual indicator
    score_display = format_score(points)
    score_bar = create_score_bar(points)
    
    if USE_COLORS:
        print(f"\n{colorize('SCORE:', ColorScheme.SUBHEADER)} {colorize(score_display, ColorScheme.POINTS)}")
        print(colorize(score_bar, ColorScheme.POINTS))
    else:
        print(f"\nSCORE: {score_display}")
        print(score_bar)
    
    # Display author information prominently
    if USE_COLORS:
        author_line = f"Posted by: {colorize(author, ColorScheme.AUTHOR)} on {format_timestamp(created_time)}"
        comments_text = colorize(str(comment_count), ColorScheme.COUNT)
    else:
        author_line = f"Posted by: {author} on {format_timestamp(created_time)}"
        comments_text = str(comment_count)
        
    print(f"\n{author_line}")
    print(f"Comments: {comments_text}")
    
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
    print("[u] Upvote story (opens in browser)")
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
            # Open story in browser to upvote
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