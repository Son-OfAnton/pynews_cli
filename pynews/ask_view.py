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
from .utils import get_story

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

def display_ask_story_details(story_id):
    """
    Display detailed information about an Ask HN story, 
    highlighting the author information.
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
    
    # Display author information prominently
    if USE_COLORS:
        author_line = f"Posted by: {colorize(author, ColorScheme.AUTHOR)} on {format_timestamp(created_time)}"
        points_text = colorize(str(points), ColorScheme.POINTS)
        comments_text = colorize(str(comment_count), ColorScheme.COUNT)
    else:
        author_line = f"Posted by: {author} on {format_timestamp(created_time)}"
        points_text = str(points)
        comments_text = str(comment_count)
        
    print(f"\n{author_line}")
    print(f"Points: {points_text} | Comments: {comments_text}")
    
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