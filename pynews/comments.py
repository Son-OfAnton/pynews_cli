"""
Functions for retrieving and displaying comments from HackerNews.
"""
import datetime
import html
import textwrap
import requests
import time
import sys
import os
import select
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from .constants import URLS
from .loading import with_loading, LoadingIndicator
from .colors import ColorScheme, colorize, supports_color
from .getch import getch

# Check for color support
USE_COLORS = supports_color()

class CommentSortOrder(Enum):
    """Enum for different comment sorting orders."""
    NEWEST_FIRST = "newest"
    OLDEST_FIRST = "oldest"
    DEFAULT = "default"  # Maintains the original API order/structure

def fetch_item(item_id):
    """Fetch a single item (story or comment) from the HackerNews API."""
    url = URLS["item"].format(item_id)
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except requests.RequestException:
        return None

def _fetch_comment_tree_no_loading(comment_ids, max_threads=10):
    """
    Fetch all comments for the given comment IDs, including child comments.
    Returns a list of comment dictionaries with a 'children' field.
    """
    if not comment_ids:
        return []
    
    comments = []
    id_to_comment = {}
    
    # Queue to track comment IDs to fetch
    queue = list(comment_ids)
    processed_ids = set()
    
    while queue:
        batch = [item_id for item_id in queue[:max_threads] if item_id not in processed_ids]
        queue = queue[len(batch):]
        
        if not batch:
            continue
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(fetch_item, item_id): item_id for item_id in batch}
            
            for future in as_completed(futures):
                item_id = futures[future]
                processed_ids.add(item_id)
                
                try:
                    comment = future.result()
                    if not comment or comment.get('deleted', False) or comment.get('dead', False):
                        continue
                    
                    # Initialize children list
                    comment['children'] = []
                    id_to_comment[item_id] = comment
                    
                    # Add any child comments to the queue
                    if 'kids' in comment and comment['kids']:
                        queue.extend(comment['kids'])
                        
                except Exception as e:
                    error_msg = f"Error fetching comment {item_id}: {e}"
                    if USE_COLORS:
                        error_msg = colorize(error_msg, ColorScheme.ERROR)
                    print(error_msg)
    
    # Build the comment tree
    for comment_id, comment in id_to_comment.items():
        # If this is a top-level comment, add it to the result
        parent_id = comment.get('parent')
        if parent_id not in id_to_comment:
            comments.append(comment)
        else:
            # Otherwise, add it as a child to its parent
            parent = id_to_comment[parent_id]
            parent['children'].append(comment)
    
    # Comments come from the API sorted by date (newest first) at each level
    # This maintains the original structure
    return comments

def sort_comment_tree(comment_tree, sort_order=CommentSortOrder.DEFAULT):
    """
    Sort the comment tree according to the given sort order.
    This function recursively sorts all levels of the tree.
    
    Args:
        comment_tree: List of comments to sort
        sort_order: CommentSortOrder enum value
        
    Returns:
        Sorted list of comments
    """
    if not comment_tree:
        return []
    
    # First, sort all children recursively
    for comment in comment_tree:
        if comment.get('children'):
            comment['children'] = sort_comment_tree(comment['children'], sort_order)
    
    # Then sort this level
    if sort_order == CommentSortOrder.NEWEST_FIRST:
        # Sort by timestamp, newest first
        return sorted(comment_tree, key=lambda c: c.get('time', 0), reverse=True)
    elif sort_order == CommentSortOrder.OLDEST_FIRST:
        # Sort by timestamp, oldest first
        return sorted(comment_tree, key=lambda c: c.get('time', 0))
    else:
        # Default: maintain API order
        return comment_tree

@with_loading
def fetch_comment_tree(comment_ids, max_threads=10):
    """
    Fetch all comments for the given comment IDs, including child comments.
    Returns a list of comment dictionaries with a 'children' field.
    
    This version includes a loading indicator while fetching.
    """
    return _fetch_comment_tree_no_loading(comment_ids, max_threads)

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

def clean_comment_text(text):
    """Clean and format comment text for display."""
    if not text:
        return "[No content]"
    
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

def format_comment(comment, indent_level=0, width=80):
    """Format a single comment for display with the given indentation."""
    if not comment:
        return ""
    
    indent_str = '  ' * indent_level
    
    # Format the author and timestamp
    username = comment.get('by', 'Anonymous')
    if USE_COLORS:
        username = colorize(username, ColorScheme.AUTHOR)
        border_char = colorize("┌─", ColorScheme.COMMENT_BORDER)
    else:
        border_char = "┌─"
        
    # Basic info line with author and timestamp
    header = f"{indent_str}{border_char} {username} · {format_timestamp(comment.get('time', 0))}"
    
    # Format and wrap the comment text
    text = clean_comment_text(comment.get('text', ''))
    
    if USE_COLORS:
        line_prefix = colorize(indent_str + '│ ', ColorScheme.COMMENT_BORDER)
    else:
        line_prefix = indent_str + '│ '
    
    wrapper = textwrap.TextWrapper(
        initial_indent=line_prefix, 
        subsequent_indent=line_prefix,
        width=width
    )
    
    if text:
        wrapped_text = wrapper.fill(text)
        if USE_COLORS:
            # We need to add color after wrapping to avoid messing up the width calculations
            # but we need to maintain the colored border, so we replace just the text part
            parts = wrapped_text.split(line_prefix)
            colored_parts = [line_prefix + colorize(p, ColorScheme.COMMENT_TEXT) for p in parts[1:]]
            wrapped_text = parts[0] + ''.join(colored_parts)
    else:
        no_content = "[No content]"
        if USE_COLORS:
            no_content = colorize(no_content, ColorScheme.COMMENT_TEXT)
        wrapped_text = line_prefix + no_content
    
    # Add footer
    if USE_COLORS:
        footer = indent_str + colorize("└" + "─" * 30, ColorScheme.COMMENT_BORDER)
    else:
        footer = f"{indent_str}└{'─' * 30}"
    
    return f"{header}\n{wrapped_text}\n{footer}"

def flatten_comment_tree(comments, flat_list=None, indent_levels=None):
    """
    Convert a nested comment tree into a flat list while preserving indent information.
    This is used to enable proper pagination across the entire comment hierarchy.
    
    Returns:
        tuple: (flat_list, indent_levels)
        - flat_list: A single flat list of all comments
        - indent_levels: A parallel list with the indentation level for each comment
    """
    if flat_list is None:
        flat_list = []
        indent_levels = []
    
    for comment in comments:
        # Add this comment to the flat list
        flat_list.append(comment)
        indent_levels.append(0)  # Root level indentation
        
        # Process any children recursively with increased indentation
        if 'children' in comment and comment['children']:
            _flatten_children(comment['children'], flat_list, indent_levels, level=1)
    
    return flat_list, indent_levels

def _flatten_children(children, flat_list, indent_levels, level):
    """Helper function for flatten_comment_tree to process nested children."""
    for child in children:
        flat_list.append(child)
        indent_levels.append(level)
        
        if 'children' in child and child['children']:
            _flatten_children(child['children'], flat_list, indent_levels, level + 1)

def display_page_of_comments(flat_comments, indent_levels, page_size, page_num, width=80):
    """
    Display a single page of comments from the flattened comment list.
    
    Args:
        flat_comments: List of all comments in flat structure
        indent_levels: Parallel list of indent levels for each comment
        page_size: Number of comments per page
        page_num: Which page to display (1-indexed)
        width: Display width
        
    Returns:
        bool: True if page had comments, False if page was empty
    """
    start_idx = (page_num - 1) * page_size
    end_idx = start_idx + page_size
    
    # Check if we have comments in this page range
    if start_idx >= len(flat_comments):
        message = "\nNo more comments to display."
        if USE_COLORS:
            message = colorize(message, ColorScheme.INFO)
        print(message)
        return False
    
    # Get the slice of comments for this page
    page_comments = flat_comments[start_idx:end_idx]
    page_indents = indent_levels[start_idx:end_idx]
    
    if not page_comments:
        message = "\nNo more comments to display."
        if USE_COLORS:
            message = colorize(message, ColorScheme.INFO)
        print(message)
        return False
    
    # Print each comment with its proper indentation
    for i, (comment, indent) in enumerate(zip(page_comments, page_indents)):
        print(format_comment(comment, indent, width))
        
        # Add extra spacing between comments for readability
        if i < len(page_comments) - 1:
            print()
    
    return True

def count_comment_tree(comments):
    """Count the total number of comments in a tree, including all nested children."""
    if not comments:
        return 0
        
    count = len(comments)
    for comment in comments:
        count += count_comment_tree(comment.get('children', []))
    
    return count

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_sort_order_display(sort_order):
    """Get a display string for the current sort order."""
    if sort_order == CommentSortOrder.NEWEST_FIRST:
        return "Newest first"
    elif sort_order == CommentSortOrder.OLDEST_FIRST:
        return "Oldest first"
    else:
        return "Default"

def show_navigation_options(current_page, total_pages, sort_order, digit_buffer=""):
    """
    Display navigation options for pagination.
    Now using single key navigation without pressing Enter.
    
    Args:
        current_page: The current page being displayed
        total_pages: Total number of pages
        sort_order: Current comment sort order
        digit_buffer: Current digit buffer for multi-digit page navigation
    """
    separator = "=" * 40
    if USE_COLORS:
        separator = colorize(separator, ColorScheme.NAV_HEADER)
        nav_header = colorize("Navigation (press a key):", ColorScheme.NAV_HEADER)
    else:
        nav_header = "Navigation (press a key):"
    
    # Display the current sort order
    sort_display = f"Sort: {get_sort_order_display(sort_order)}"
    if USE_COLORS:
        sort_display = colorize(sort_display, ColorScheme.TITLE)
    
    print(f"\n{separator}")
    print(f"{nav_header} {sort_display}")
    
    # Previous page option
    if current_page > 1:
        prev_option = "Press [p] for previous page"
        if USE_COLORS:
            prev_option = colorize(prev_option, ColorScheme.NAV_ACTIVE)
        print(prev_option)
    else:
        prev_option = "Previous page (unavailable)"
        if USE_COLORS:
            prev_option = colorize(prev_option, ColorScheme.NAV_INACTIVE)
        print(prev_option)
    
    # Next page option
    if current_page < total_pages:
        next_option = "Press [n] for next page"
        if USE_COLORS:
            next_option = colorize(next_option, ColorScheme.NAV_ACTIVE)
        print(next_option)
    else:
        next_option = "Next page (unavailable)"
        if USE_COLORS:
            next_option = colorize(next_option, ColorScheme.NAV_INACTIVE)
        print(next_option)
    
    # Direct page navigation
    direct_nav = f"Enter page number (1-{total_pages}) to go directly to that page"
    if USE_COLORS:
        direct_nav = colorize(direct_nav, ColorScheme.NAV_ACTIVE)
    
    # If there's an active buffer, show it
    if digit_buffer:
        buffer_display = f"Current input: {digit_buffer}"
        if USE_COLORS:
            buffer_display = colorize(buffer_display, ColorScheme.TITLE)
        direct_nav += f" - {buffer_display}"
    
    print(direct_nav)
    
    # Sort options
    sort_options = "Press [s] to cycle sort order (newest/oldest/default)"
    if USE_COLORS:
        sort_options = colorize(sort_options, ColorScheme.NAV_ACTIVE)
    print(sort_options)
    
    # First/last page shortcuts
    firstlast_options = "Press [f] for first page, [l] for last page"
    if USE_COLORS:
        firstlast_options = colorize(firstlast_options, ColorScheme.NAV_ACTIVE)
    print(firstlast_options)
    
    # Quit option
    quit_option = "Press [q] to quit"
    if USE_COLORS:
        quit_option = colorize(quit_option, ColorScheme.NAV_ACTIVE)
    print(quit_option)
    
    print(separator)

def get_navigation_key(total_pages=0):
    """
    Get a single keystroke from the user for navigation.
    Supports multi-digit page numbers.
    
    Returns:
        dict: Navigation action information
    """
    digit_buffer = ""
    digit_timeout = 1.5  # seconds to wait for additional digits
    last_digit_time = None
    
    while True:
        # Display the current digit buffer if any
        if digit_buffer:
            if USE_COLORS:
                buffer_msg = colorize(f"\rEntering page number: {digit_buffer}", ColorScheme.PROMPT)
            else:
                buffer_msg = f"\rEntering page number: {digit_buffer}"
            sys.stdout.write(buffer_msg)
            sys.stdout.flush()
        
        # Get a single keystroke
        key = getch().lower()
        
        # Process navigation keys
        if key == 'p':
            return {'action': 'prev-page'}
        elif key == 'n':
            return {'action': 'next-page'}
        elif key == 'q':
            return {'action': 'quit'}
        elif key == 's':
            return {'action': 'change-sort'}
        elif key == 'f':
            return {'action': 'first-page'}
        elif key == 'l':
            return {'action': 'last-page'}
        elif key.isdigit():
            # Add to the digit buffer
            current_time = time.time()
            digit_buffer += key
            last_digit_time = current_time
            
            # Check if we've exceeded the page range
            if int(digit_buffer) > total_pages:
                # We've gone beyond valid pages, truncate to max
                digit_buffer = str(total_pages)
            
            # Wait a moment to see if user enters more digits
            time.sleep(0.1)  # Small pause to catch quick consecutive keypresses
            
            # Check if there's more input available (non-blocking)
            if select.select([sys.stdin], [], [], 0.0)[0]:
                # More input is available, continue collecting
                continue
            elif time.time() - last_digit_time >= digit_timeout:
                # Timeout expired, process current buffer
                if digit_buffer:
                    page = int(digit_buffer)
                    return {'action': 'goto', 'page': page}
            
            # Continue collecting digits
            continue
        elif digit_buffer:
            # Non-digit key pressed after digits, process the buffer
            page = int(digit_buffer)
            return {'action': 'goto', 'page': page}
        else:
            # Invalid key
            return {'action': 'invalid'}

def display_comments_for_story(story_id, page_size=10, page_num=1, width=80):
    """
    Display comments for a given story with interactive pagination support.
    Now using single-keystroke navigation without pressing Enter.
    Supports multi-digit page numbers and comment sorting.
    
    Args:
        story_id: The ID of the story to show comments for
        page_size: Number of comments to display per page
        page_num: Which page of comments to display (1-indexed)
        width: Display width for wrapping comments
        
    Returns:
        tuple: (total_pages, current_page_num, total_comments)
    """
    # First, fetch the story to get its comments
    loader = LoadingIndicator(message="Fetching story details...")
    loader.start()
    try:
        story = fetch_item(story_id)
    finally:
        loader.stop()
        
    if not story:
        error_msg = f"Error: Could not fetch story with ID {story_id}"
        if USE_COLORS:
            error_msg = colorize(error_msg, ColorScheme.ERROR)
        print(error_msg)
        return (0, 0, 0)
    
    # Initialize cached data
    comment_tree = None
    flat_comments = None
    indent_levels = None
    total_comments = 0
    total_pages = 0
    current_page = page_num
    sort_order = CommentSortOrder.DEFAULT
    needs_resort = False
    
    while True:
        clear_screen()
        
        # Display story information
        if USE_COLORS:
            title = colorize(f"\n=== Comments for: {story.get('title', 'Unknown Story')} ===", 
                           ColorScheme.TITLE)
            author_line = f"By {colorize(story.get('by', 'Unknown'), ColorScheme.AUTHOR)} · {format_timestamp(story.get('time', 0))}"
            points = colorize(str(story.get('score', 0)), ColorScheme.POINTS)
            url = story.get('url', '[No URL]')
            if url != '[No URL]':
                url = colorize(url, ColorScheme.URL)
            info_line = f"Points: {points} · URL: {url}\n"
        else:
            title = f"\n=== Comments for: {story.get('title', 'Unknown Story')} ==="
            author_line = f"By {story.get('by', 'Unknown')} · {format_timestamp(story.get('time', 0))}"
            info_line = f"Points: {story.get('score', 0)} · URL: {story.get('url', '[No URL]')}\n"
        
        print(title)
        print(author_line)
        print(info_line)
        
        # Check if the story has comments
        comment_ids = story.get('kids', [])
        if not comment_ids:
            message = "This story has no comments."
            if USE_COLORS:
                message = colorize(message, ColorScheme.INFO)
            print(message)
            
            prompt = "\nPress any key to quit..."
            if USE_COLORS:
                prompt = colorize(prompt, ColorScheme.PROMPT)
            print(prompt)
            getch()  # Wait for any key
            return (0, 0, 0)
        
        # Fetch and process comments if not already cached
        if comment_tree is None:
            message = f"Retrieving comments for this story..."
            if USE_COLORS:
                message = colorize(message, ColorScheme.INFO)
            print(message)
            
            # This now automatically shows a loading indicator during fetch
            comment_tree = fetch_comment_tree(comment_ids, loading_message="Fetching comments...")
            needs_resort = True
            
        # Re-sort if needed
        if needs_resort:
            message = f"Sorting comments ({get_sort_order_display(sort_order)})..."
            if USE_COLORS:
                message = colorize(message, ColorScheme.INFO)
            print(message)
            
            # Sort comments according to current sort order
            loader = LoadingIndicator(message=f"Sorting comments ({get_sort_order_display(sort_order)})...")
            loader.start()
            try:
                sorted_tree = sort_comment_tree(comment_tree, sort_order)
                
                # Flatten the comment tree for easier pagination
                flat_comments, indent_levels = flatten_comment_tree(sorted_tree)
                
                total_comments = len(flat_comments)
                total_pages = (total_comments + page_size - 1) // page_size
                
                # Validate page number
                if current_page > total_pages and total_pages > 0:
                    current_page = total_pages
                
                needs_resort = False
            finally:
                loader.stop()
            
        # Show pagination info
        if USE_COLORS:
            page_info = f"Page {colorize(str(current_page), ColorScheme.COUNT)} of " + \
                       f"{colorize(str(total_pages), ColorScheme.COUNT)} " + \
                       f"(Total comments: {colorize(str(total_comments), ColorScheme.COUNT)})"
            separator = colorize("=" * width, ColorScheme.HEADER)
        else:
            page_info = f"Page {current_page} of {total_pages} (Total comments: {total_comments})"
            separator = "=" * width
        
        print(page_info)
        print(separator)
        
        # Display comments for the current page
        has_comments = display_page_of_comments(
            flat_comments, indent_levels, page_size, current_page, width
        )
        
        # Display navigation options
        show_navigation_options(current_page, total_pages, sort_order)
        
        # Get navigation key and process
        nav = get_navigation_key(total_pages)
        
        if nav['action'] == 'prev-page' and current_page > 1:
            current_page -= 1
        elif nav['action'] == 'next-page' and current_page < total_pages:
            current_page += 1
        elif nav['action'] == 'first-page':
            current_page = 1
        elif nav['action'] == 'last-page':
            current_page = total_pages
        elif nav['action'] == 'goto':
            page = nav['page']
            if 1 <= page <= total_pages:
                current_page = page
        elif nav['action'] == 'change-sort':
            # Cycle through sort orders
            if sort_order == CommentSortOrder.DEFAULT:
                sort_order = CommentSortOrder.NEWEST_FIRST
            elif sort_order == CommentSortOrder.NEWEST_FIRST:
                sort_order = CommentSortOrder.OLDEST_FIRST
            else:
                sort_order = CommentSortOrder.DEFAULT
            
            needs_resort = True
        elif nav['action'] == 'quit':
            break
        elif nav['action'] == 'invalid':
            # Invalid key, show a brief error message
            if USE_COLORS:
                error = colorize("Invalid key. Press any key to continue...", ColorScheme.ERROR)
            else:
                error = "Invalid key. Press any key to continue..."
            
            print(f"\n{error}")
            getch()  # Wait for any key before continuing
    
    return (total_pages, current_page, total_comments)