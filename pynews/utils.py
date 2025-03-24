import html
import random
import sys
import datetime
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from webbrowser import open as url_open

import requests as req
from alive_progress import alive_it
from cursesmenu import CursesMenu
from cursesmenu.items import FunctionItem

from .constants import URLS
from .loading import with_loading, LoadingIndicator
from .colors import Colors, colorize, supports_color


def clean_title(title):
    result = title.encode("utf-8")
    if sys.version_info.major == 3:
        result = result.decode()
    return result


def get_stories(type_url):
    """Return a list of ids of the 500 top stories."""
    loader = LoadingIndicator(message=f"Fetching {type_url} story IDs...")
    loader.start()
    try:
        data = req.get(URLS[type_url])
        return data.json()
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return None
    finally:
        loader.stop()


def get_story(new):
    """Return a story of the given ID."""
    url = URLS["item"].format(new)
    try:
        data = req.get(url)
    except req.ConnectionError:
        raise
    except req.Timeout:
        raise req.Timeout("A timeout problem occurred.")
    except req.TooManyRedirects:
        raise req.TooManyRedirects(
            "The request exceeds the configured number\
            of maximum redirections."
        )
    else:
        return data.json()


def _create_list_stories_no_loading(list_id_stories, number_of_stories, shuffle, max_threads):
    """Show in a formatted way the stories for each item of the list."""

    list_stories = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {
            executor.submit(get_story, new)
            for new in list_id_stories[:number_of_stories]
        }

        for future in alive_it(
            as_completed(futures),
            total=len(futures),
            title="Getting news...",
            enrich_print=True,
            ctrl_c=True,
        ):
            list_stories.append(future.result())

    if shuffle:
        random.shuffle(list_stories)
    return list_stories


@with_loading
def create_list_stories(list_id_stories, number_of_stories, shuffle, max_threads):
    """
    Show in a formatted way the stories for each item of the list.
    Now with loading indicator.
    """
    # Replace the alive_it progress bar with our loading indicator
    list_stories = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {
            executor.submit(get_story, new)
            for new in list_id_stories[:number_of_stories]
        }

        for future in as_completed(futures):
            result = future.result()
            if result:  # Make sure we have a valid result
                list_stories.append(result)

    if shuffle:
        random.shuffle(list_stories)
    return list_stories


def filter_stories_by_keyword(stories, keyword, case_sensitive=False):
    """
    Filter stories by a keyword in the title or text.
    
    Args:
        stories: List of story dictionaries
        keyword: String to search for
        case_sensitive: Whether the search should be case-sensitive
    
    Returns:
        List of filtered stories containing the keyword
    """
    if not keyword:
        return stories
    
    filtered_stories = []
    
    # Prepare the keyword for search
    if not case_sensitive:
        keyword = keyword.lower()
        
    for story in stories:
        # Get the title and text content
        title = story.get('title', '')
        text = story.get('text', '')
        
        # If case-insensitive search, convert to lowercase
        if not case_sensitive:
            title = title.lower()
            text = text.lower()
            
        # Check if keyword is in title or text
        if keyword in title or keyword in text:
            filtered_stories.append(story)
            
    return filtered_stories


def filter_stories_by_keywords(stories, keywords, match_all=False, case_sensitive=False):
    """
    Filter stories by multiple keywords in the title or text.
    
    Args:
        stories: List of story dictionaries
        keywords: List of strings to search for
        match_all: If True, all keywords must match; if False, any keyword can match
        case_sensitive: Whether the search should be case-sensitive
    
    Returns:
        List of filtered stories containing the keywords
    """
    if not keywords:
        return stories
    
    filtered_stories = []
    
    # Prepare the keywords for search
    if not case_sensitive:
        keywords = [k.lower() for k in keywords]
    
    for story in stories:
        # Get the title and text content
        title = story.get('title', '')
        text = story.get('text', '')
        
        # For case-insensitive search, convert to lowercase
        if not case_sensitive:
            title = title.lower()
            text = text.lower()
        
        # Check if the keywords are in the title or text
        matches = []
        for keyword in keywords:
            if keyword in title or keyword in text:
                matches.append(True)
            else:
                matches.append(False)
        
        # Determine if the story should be included based on matching strategy
        if match_all and all(matches):
            filtered_stories.append(story)
        elif not match_all and any(matches):
            filtered_stories.append(story)
    
    return filtered_stories


def filter_stories_by_author(stories, author, case_sensitive=False):
    """
    Filter stories by their author (username).
    
    Args:
        stories: List of story dictionaries
        author: Username to filter by
        case_sensitive: Whether the username comparison should be case-sensitive
    
    Returns:
        List of filtered stories by the specified author
    """
    if not author:
        return stories
    
    filtered_stories = []
    
    # Prepare the author name for comparison
    if not case_sensitive:
        author = author.lower()
    
    for story in stories:
        # Get the author of the story
        story_author = story.get('by', '')
        
        # For case-insensitive search, convert to lowercase
        if not case_sensitive and story_author:
            story_author = story_author.lower()
        
        # Check if the author matches
        if story_author == author:
            filtered_stories.append(story)
    
    return filtered_stories


def sort_stories_by_score(stories, reverse=True):
    """
    Sort stories by their score (points).
    
    Args:
        stories: List of story dictionaries
        reverse: If True, sort in descending order (highest score first)
        
    Returns:
        Sorted list of stories
    """
    return sorted(stories, key=lambda x: x.get('score', 0), reverse=reverse)


def sort_stories_by_comments(stories, reverse=True):
    """
    Sort stories by their comment count.
    
    Args:
        stories: List of story dictionaries
        reverse: If True, sort in descending order (most comments first)
        
    Returns:
        Sorted list of stories
    """
    return sorted(stories, key=lambda x: len(x.get('kids', [])), reverse=reverse)


def sort_stories_by_time(stories, reverse=True):
    """
    Sort stories by their submission time.
    
    Args:
        stories: List of story dictionaries
        reverse: If True, sort in descending order (newest first)
        
    Returns:
        Sorted list of stories
    """
    return sorted(stories, key=lambda x: x.get('time', 0), reverse=reverse)


def format_comment_count(count):
    """Format comment count with visual indicators based on activity level."""
    if count >= 100:
        return f"💬 {count}"  # Very active discussion
    elif count >= 50:
        return f"💬 {count}"  # Active discussion
    elif count >= 10:
        return f"💬 {count}"  # Notable discussion
    elif count > 0:
        return f"💬 {count}"  # Some discussion
    else:
        return f"💬 0"  # No discussion yet


def format_time_ago(timestamp):
    """
    Format a Unix timestamp as a human-readable 'time ago' string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        String like "5 min ago" or "3 days ago"
    """
    if not timestamp:
        return "Unknown time"
        
    # Convert to datetime
    dt = datetime.datetime.fromtimestamp(timestamp)
    now = datetime.datetime.now()
    
    # Calculate the time difference
    diff = now - dt
    
    # Format the time ago string based on the difference
    if diff.days > 365:
        years = diff.days // 365
        return f"{years}y ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months}mo ago"
    elif diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "just now"


def truncate_string(text, max_length, ellipsis="..."):
    """Truncate a string to max_length, adding ellipsis if it was truncated."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length-len(ellipsis)] + ellipsis


def get_terminal_width():
    """Get the current terminal width, or a reasonable default if it can't be determined."""
    try:
        width, _ = shutil.get_terminal_size()
        # If width seems unreasonably small, use a default instead
        return width if width > 40 else 80
    except Exception:
        return 80


def create_menu(list_dict_stories, type_new, sort_by_score=True, sort_by_time=False, 
                keywords=None, highlight_keys=False, author_filter=None, highlight_author_name=False):
    """
    Create a menu with the stories to display.
    
    Args:
        list_dict_stories: List of story dictionaries
        type_new: Type of stories ('ask', 'top', 'news')
        sort_by_score: Whether to sort Ask HN stories by score
        sort_by_time: Whether to sort Ask HN stories by submission time
        keywords: List of keywords to highlight in titles (if None, no highlighting)
        highlight_keys: Whether to highlight keywords in the titles (DISABLED - causes display issues)
        author_filter: Username to filter stories by (only show stories from this author)
        highlight_author_name: Whether to highlight the author name (DISABLED - causes display issues)
    """
    title = f"Pynews - {type_new.capitalize()} stories"
    
    # Apply author filtering if specified
    if author_filter and type_new == "ask":
        original_count = len(list_dict_stories)
        list_dict_stories = filter_stories_by_author(list_dict_stories, author_filter, case_sensitive=False)
        filtered_count = len(list_dict_stories)
        title = f"Pynews - {type_new.capitalize()} stories by '{author_filter}' ({filtered_count}/{original_count})"
    
    # Apply keyword filtering if keywords are provided
    if keywords and any(keywords) and type_new == "ask":
        original_count = len(list_dict_stories)
        list_dict_stories = filter_stories_by_keywords(list_dict_stories, keywords)
        filtered_count = len(list_dict_stories)
        if author_filter:
            title = f"Pynews - {type_new.capitalize()} stories by '{author_filter}' with keywords ({filtered_count}/{original_count})"
        else:
            title = f"Pynews - {type_new.capitalize()} stories (filtered: {filtered_count}/{original_count})"
    
    # For Ask stories, sort based on the specified criteria
    if type_new == "ask":
        if sort_by_time:
            list_dict_stories = sort_stories_by_time(list_dict_stories)
            title += " (sorted by time)"
        elif sort_by_score:
            list_dict_stories = sort_stories_by_score(list_dict_stories)
            title += " (sorted by score)"
        else:  # Sort by comments
            list_dict_stories = sort_stories_by_comments(list_dict_stories)
            title += " (sorted by comments)"
    
    # Create the menu
    menu = CursesMenu(title, "Select the story and press enter")

    # Get terminal width for proper formatting
    term_width = get_terminal_width()
    
    # Calculate reasonable title width - allow space for metadata
    title_width = term_width - 35  # Reserve space for metadata
    if title_width < 30:  # Minimum reasonable title width
        title_width = term_width - 20
    
    # Process each story
    for story in list_dict_stories:
        # Get the basic story information
        story_title = clean_title(story.get("title", "Untitled"))
        author = story.get("by", "Anonymous")
        points = story.get("score", 0)
        comment_count = len(story.get('kids', []))
        time_ago = format_time_ago(story.get('time', 0))
        
        # Format the display title - FIXED: Use single line format with truncated title
        # Removed all ANSI color codes and highlighting to fix encoding issues
        if type_new == "ask":
            # Truncate title if needed to fit in the available width
            truncated_title = truncate_string(story_title, title_width)
            
            # For Ask HN, format everything on one line to prevent display issues
            # Fixed the author display by removing all color/highlighting
            display_title = f"{truncated_title} - {points} pts, {comment_count} cmts, {time_ago}, by {author}"
        else:
            # For other story types, just use the title with reasonable truncation
            display_title = truncate_string(story_title, term_width - 5)
        
        # Create the menu item with appropriate URL
        if "url" in story and story["url"]:
            item = FunctionItem(display_title, url_open, args=[story["url"]])
        else:
            # For self-posts that don't have a URL, use the HN link
            hn_url = f"https://news.ycombinator.com/item?id={story.get('id')}"
            item = FunctionItem(display_title, url_open, args=[hn_url])
        
        menu.append_item(item)
    
    return menu


def show_author_profile(username):
    """Open the Hacker News user profile in a browser."""
    profile_url = f"https://news.ycombinator.com/user?id={username}"
    url_open(profile_url)


def get_user_stories(username, story_type='submitted'):
    """
    Fetch a list of stories submitted by a specific user.
    
    Args:
        username: HackerNews username to fetch stories for
        story_type: Type of stories ('submitted', 'favorites', 'comments')
        
    Returns:
        List of story IDs submitted by the user
    """
    if not username:
        return []
    
    # Fetch the user profile
    user_url = f"https://hacker-news.firebaseio.com/v0/user/{username}.json"
    try:
        response = req.get(user_url)
        if response.status_code != 200:
            return []
        
        user_data = response.json()
        if not user_data or not isinstance(user_data, dict):
            return []
        
        # Get the list of submitted items
        submitted = user_data.get(story_type, [])
        return submitted
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return []
    
def clean_text(text):
    """
    Clean HTML from text and convert to plain text.
    
    Args:
        text: HTML text to clean
        
    Returns:
        Cleaned plain text
    """
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