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
import json
import csv
import threading
import queue

from .constants import URLS
from .loading import with_loading, with_progress, LoadingIndicator, ProgressBar, IndeterminateProgressBar
# Make sure to import Colors
from .colors import ColorScheme, colorize, supports_color, Colors
from .getch import getch
from .exporters import export_comments_to_json, export_comments_to_csv


sys.path.append("..")

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


def fetch_comment_tree(comment_ids, max_threads=10, progress_callback=None):
    """
    Fetch all comments for the given comment IDs, including child comments.
    Returns a list of comment dictionaries with a 'children' field.

    Args:
        comment_ids: List of comment IDs to fetch
        max_threads: Maximum number of concurrent requests
        progress_callback: Callback function to update progress
    """
    if not comment_ids:
        return []

    comments = []
    id_to_comment = {}

    # Queue to track comment IDs to fetch
    queue = list(comment_ids)
    processed_ids = set()

    # Estimate total operations for progress tracking
    if progress_callback:
        # Initial queue + potential child comments (estimate)
        # Rough estimate assuming 50% have children
        estimated_total = len(queue) * 1.5
        current_progress = 0
        progress_callback(0)  # Initialize progress to 0

    while queue:
        batch = [item_id for item_id in queue[:max_threads]
                 if item_id not in processed_ids]
        queue = queue[len(batch):]

        if not batch:
            continue

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(
                fetch_item, item_id): item_id for item_id in batch}

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

                    # Update progress
                    if progress_callback:
                        current_progress += 1
                        progress_percent = min(
                            int((current_progress / estimated_total) * 100), 99)
                        progress_callback(progress_percent)

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

    # Final progress update to 100%
    if progress_callback:
        progress_callback(100)

    # Comments come from the API sorted by date (newest first) at each level
    # This maintains the original structure
    return comments


def sort_comment_tree(comment_tree, sort_order=CommentSortOrder.DEFAULT, progress_callback=None):
    """
    Sort the comment tree according to the given sort order.
    This function recursively sorts all levels of the tree.

    Args:
        comment_tree: List of comments to sort
        sort_order: CommentSortOrder enum value
        progress_callback: Callback function to update progress

    Returns:
        Sorted list of comments
    """
    if not comment_tree:
        return []

    total_comments = count_comment_tree(comment_tree)
    processed = 0

    if progress_callback:
        progress_callback(0)  # Initialize progress

    def sort_level(comments, level=0):
        nonlocal processed

        # First, sort all children recursively
        for i, comment in enumerate(comments):
            if comment.get('children'):
                comment['children'] = sort_level(
                    comment['children'], level + 1)

            # Update progress after processing each comment
            if progress_callback:
                processed += 1
                progress_percent = min(
                    int((processed / total_comments) * 100), 99)
                progress_callback(progress_percent)

        # Then sort this level
        if sort_order == CommentSortOrder.NEWEST_FIRST:
            # Sort by timestamp, newest first
            return sorted(comments, key=lambda c: c.get('time', 0), reverse=True)
        elif sort_order == CommentSortOrder.OLDEST_FIRST:
            # Sort by timestamp, oldest first
            return sorted(comments, key=lambda c: c.get('time', 0))
        else:
            # Default: maintain API order
            return comments

    result = sort_level(comment_tree)

    # Final progress update to 100%
    if progress_callback:
        progress_callback(100)

    return result


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
            colored_parts = [
                line_prefix + colorize(p, ColorScheme.COMMENT_TEXT) for p in parts[1:]]
            wrapped_text = parts[0] + ''.join(colored_parts)
    else:
        no_content = "[No content]"
        if USE_COLORS:
            no_content = colorize(no_content, ColorScheme.COMMENT_TEXT)
        wrapped_text = line_prefix + no_content

    # Add footer
    if USE_COLORS:
        footer = indent_str + \
            colorize("└" + "─" * 30, ColorScheme.COMMENT_BORDER)
    else:
        footer = f"{indent_str}└{'─' * 30}"

    return f"{header}\n{wrapped_text}\n{footer}"


def flatten_comment_tree(comments, flat_list=None, indent_levels=None,
                         progress_callback=None, base_progress=0, total_progress=100):
    """
    Convert a nested comment tree into a flat list while preserving indent information.
    This is used to enable proper pagination across the entire comment hierarchy.

    Args:
        comments: The nested comment tree to flatten
        flat_list: Optional existing flat list to append to
        indent_levels: Optional existing indent levels list to append to
        progress_callback: Optional callback function to update progress
        base_progress: Base progress percentage (0-100) to start from
        total_progress: Total progress percentage range (typically 100)

    Returns:
        tuple: (flat_list, indent_levels)
        - flat_list: A single flat list of all comments
        - indent_levels: A parallel list with the indentation level for each comment
    """
    if flat_list is None:
        flat_list = []
        indent_levels = []

    # Count total comments for progress tracking
    if progress_callback:
        total_comments = count_comment_tree(comments)
        if total_comments == 0:
            # No comments to process
            progress_callback(base_progress + total_progress)
            return flat_list, indent_levels

        processed = 0
        progress_callback(base_progress)  # Initialize progress

    def flatten_with_progress(comments, level=0):
        nonlocal processed

        for comment in comments:
            # Add this comment to the flat list
            flat_list.append(comment)
            indent_levels.append(level)

            # Update progress
            if progress_callback:
                processed += 1
                progress_percent = base_progress + min(
                    int((processed / total_comments) * total_progress),
                    total_progress - 1
                )
                progress_callback(progress_percent)

            # Process any children recursively
            if 'children' in comment and comment['children']:
                flatten_with_progress(comment['children'], level + 1)

    flatten_with_progress(comments)

    # Final progress update
    if progress_callback:
        progress_callback(base_progress + total_progress)

    return flat_list, indent_levels


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


def show_navigation_options(current_page, total_pages, sort_order, 
                        new_comments=0, auto_refresh=False, 
                        refresh_interval=0, is_refreshing=False,
                        refresh_progress=0, digit_buffer=""):
    """
    Display navigation options for pagination.
    
    Args:
        current_page: The current page being displayed
        total_pages: Total number of pages
        sort_order: Current comment sort order
        new_comments: Count of new comments found
        auto_refresh: Whether auto-refresh is enabled
        refresh_interval: Refresh interval in seconds
        is_refreshing: Whether a refresh is in progress
        refresh_progress: Current refresh progress (0-100)
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
    
    # Auto-refresh status if enabled
    if auto_refresh:
        # Show different status based on whether refresh is in progress
        if is_refreshing:
            # Create a simple progress indicator
            progress_width = 20
            filled_width = int(progress_width * (refresh_progress / 100))
            progress_bar = f"[{'=' * filled_width}{' ' * (progress_width - filled_width)}] {refresh_progress}%"
            refresh_status = f"Refreshing comments: {progress_bar}"
            
            if USE_COLORS:
                refresh_status = colorize(refresh_status, Colors.YELLOW)
        else:
            refresh_status = f"Auto-refresh: {refresh_interval}s"
            if USE_COLORS:
                refresh_status = colorize(refresh_status, ColorScheme.INFO)
                
            # Add new comments notification if any
            if new_comments > 0:
                new_comment_text = f" [{new_comments} new comment" + ("s" if new_comments > 1 else "") + "]"
                if USE_COLORS:
                    new_comment_text = colorize(new_comment_text, Colors.GREEN)
                refresh_status += new_comment_text
                
        print(refresh_status)
        
        # Manual refresh option
        refresh_option = "Press [r] to refresh now"
        if USE_COLORS:
            refresh_option = colorize(refresh_option, ColorScheme.NAV_ACTIVE)
        print(refresh_option)

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


def get_navigation_key(total_pages=0, timeout=None):
    """
    Get a single keystroke from the user for navigation.
    Supports multi-digit page numbers.

    Returns:
        dict: Navigation action information
    """
    digit_buffer = ""
    digit_timeout = 1.5  # seconds to wait for additional digits
    last_digit_time = None

    # Wait for input with optional timeout
    if timeout:
        # Check if input is available within the timeout
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            # Timeout reached with no input
            return {"action": "timeout"}

    while True:
        # Display the current digit buffer if any
        if digit_buffer:
            if USE_COLORS:
                buffer_msg = colorize(
                    f"\rEntering page number: {digit_buffer}", ColorScheme.PROMPT)
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
            # Small pause to catch quick consecutive keypresses
            time.sleep(0.1)

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


def display_comments_for_story(story_id, page_size=10, page_num=1, width=80, 
                               export_json=False, export_csv=False, 
                               export_path=None, export_filename=None, 
                               include_timestamp=True, auto_refresh=False, 
                               refresh_interval=60, notify_new_comments=False):
    """
    Display comments for a given story with interactive pagination support.
    Now using single-keystroke navigation without pressing Enter.
    Supports multi-digit page numbers and comment sorting.
    Also supports exporting comments to JSON or CSV.

    Args:
        story_id: The ID of the story to show comments for
        page_size: Number of comments to display per page
        page_num: Which page of comments to display (1-indexed)
        width: Display width for wrapping comments
        export_json: Whether to export comments to JSON format
        export_csv: Whether to export comments to CSV format
        export_path: Path to save exported files (defaults to current dir)
        export_filename: Custom filename for exports (without extension)
        include_timestamp: Whether to include timestamp in filename

    Returns:
        tuple: (total_pages, current_page_num, total_comments)
    """

    background_fetcher = None
    new_comments_count = 0
    
    # Initialize background fetcher if requested
    if auto_refresh:
        message = f"Initializing background comment fetching (interval: {refresh_interval}s)..."
        if USE_COLORS:
            message = colorize(message, ColorScheme.INFO)
        print(message)
        
        # Define callback function for new comment notification
        def on_new_comments(count):
            nonlocal new_comments_count
            new_comments_count += count
            
        # Create and start background fetcher
        background_fetcher = BackgroundCommentFetcher(
            story_id, 
            interval=refresh_interval, 
            callback=on_new_comments if notify_new_comments else None
        )
        background_fetcher.start()

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

    # Initialize cached data
    comment_tree = None
    flat_comments = None
    indent_levels = None
    total_comments = 0
    total_pages = 0
    current_page = page_num
    sort_order = CommentSortOrder.DEFAULT
    needs_resort = False

    # Process export options
    should_export = export_json or export_csv

    # Fetch comments (needed for both export and viewing)
    message = "Retrieving comments for this story..."
    if should_export:
        message = "Retrieving comments for export and viewing..."

    if USE_COLORS:
        message = colorize(message, ColorScheme.INFO)
    print(message)

    # Create a progress bar for fetching comments
    progress_bar = ProgressBar(
        total=100,
        prefix='Fetching Comments:',
        suffix='Complete',
        length=50
    )
    progress_bar.start()

    try:
        # Fetch comments with progress updates
        comment_tree = fetch_comment_tree(
            comment_ids,
            max_threads=10,
            progress_callback=progress_bar.update
        )
    finally:
        progress_bar.stop()

    # Make sure comment_tree is not None to avoid errors
    if comment_tree is None:
        comment_tree = []

    needs_resort = True

    # Handle exports if requested
    if should_export and comment_tree:  # Only try to export if we have comments
        # Prepare export path
        if export_path is None:
            export_path = os.getcwd()  # Use current directory
        else:
            # Create directory if it doesn't exist
            os.makedirs(export_path, exist_ok=True)

        # Make sure export_path is an absolute path
        export_path = os.path.abspath(export_path)

        # Set base filename
        base_filename = export_filename or f"hn_story_{story_id}_comments"

        # Export to JSON if requested
        if export_json:
            export_msg = "Exporting comments to JSON..."
            if USE_COLORS:
                export_msg = colorize(export_msg, ColorScheme.INFO)
            print(export_msg)

            # Prepare filename
            json_filename = os.path.join(export_path, f"{base_filename}.json")
            if include_timestamp and not export_filename:
                # Include timestamp in the auto-generated filename
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                json_filename = os.path.join(
                    export_path, f"{base_filename}_{timestamp}.json")

            # Export to JSON
            try:
                json_file = export_comments_to_json(
                    comment_tree, story, json_filename)
                success_msg = f"Comments exported to JSON: {json_file}"
                if USE_COLORS:
                    # Use a color that exists in the Colors class
                    success_msg = colorize(success_msg, Colors.GREEN)
                print(success_msg)
            except Exception as e:
                error_msg = f"Error exporting to JSON: {e}"
                if USE_COLORS:
                    error_msg = colorize(error_msg, ColorScheme.ERROR)
                print(error_msg)

        # Export to CSV if requested
        if export_csv:
            export_msg = "Exporting comments to CSV..."
            if USE_COLORS:
                export_msg = colorize(export_msg, ColorScheme.INFO)
            print(export_msg)

            # Prepare filename
            csv_filename = os.path.join(export_path, f"{base_filename}.csv")
            if include_timestamp and not export_filename:
                # Include timestamp in the auto-generated filename
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = os.path.join(
                    export_path, f"{base_filename}_{timestamp}.csv")

            # Export to CSV
            try:
                csv_file = export_comments_to_csv(
                    comment_tree, story, csv_filename)
                success_msg = f"Comments exported to CSV: {csv_file}"
                if USE_COLORS:
                    # Use a color that exists in the Colors class
                    success_msg = colorize(success_msg, Colors.GREEN)
                print(success_msg)
            except Exception as e:
                error_msg = f"Error exporting to CSV: {e}"
                if USE_COLORS:
                    error_msg = colorize(error_msg, ColorScheme.ERROR)
                print(error_msg)

        # Give user a moment to read the export messages
        if export_json or export_csv:
            prompt = "\nPress any key to continue to comment view..."
            if USE_COLORS:
                prompt = colorize(prompt, ColorScheme.PROMPT)
            print(prompt)
            getch()  # Wait for any key

    # Continue with the regular comment viewing loop
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

        # Re-sort if needed
        if needs_resort and comment_tree:
            message = f"Sorting comments ({get_sort_order_display(sort_order)})..."
            if USE_COLORS:
                message = colorize(message, ColorScheme.INFO)
            print(message)

            # Create progress bar for sorting
            sort_progress = ProgressBar(
                total=100,
                prefix=f'Sorting ({get_sort_order_display(sort_order)}):',
                suffix='Complete',
                length=50
            )
            sort_progress.start()

            try:
                # Sort with progress updates
                sorted_tree = sort_comment_tree(
                    comment_tree,
                    sort_order,
                    progress_callback=sort_progress.update
                )
            finally:
                sort_progress.stop()

            # Create progress bar for flattening
            flatten_progress = ProgressBar(
                total=100,
                prefix='Organizing Comments:',
                suffix='Complete',
                length=50
            )
            flatten_progress.start()

            try:
                # Flatten with progress updates
                flat_comments, indent_levels = flatten_comment_tree(
                    sorted_tree,
                    progress_callback=flatten_progress.update
                )
            finally:
                flatten_progress.stop()

            # Update pagination data
            if flat_comments:  # Make sure flat_comments is not None
                total_comments = len(flat_comments)
                total_pages = (total_comments + page_size - 1) // page_size

                # Validate page number
                if current_page > total_pages and total_pages > 0:
                    current_page = total_pages
            else:
                # Handle case where flattening produced no comments
                total_comments = 0
                total_pages = 0
                current_page = 1
                flat_comments = []
                indent_levels = {}

            needs_resort = False

        # Check if we have comments to display
        if not flat_comments or total_comments == 0:
            message = "No comments to display."
            if USE_COLORS:
                message = colorize(message, ColorScheme.INFO)
            print(message)

            prompt = "\nPress any key to quit..."
            if USE_COLORS:
                prompt = colorize(prompt, ColorScheme.PROMPT)
            print(prompt)
            getch()  # Wait for any key
            return (0, 0, 0)

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
        show_navigation_options(
            current_page, 
            total_pages, 
            sort_order,
            new_comments=new_comments_count,
            auto_refresh=auto_refresh,
            refresh_interval=refresh_interval,
            is_refreshing=background_fetcher.is_currently_refreshing() if background_fetcher else False,
            refresh_progress=background_fetcher.get_refresh_progress() if background_fetcher else 0
        )
        
        # Get navigation key with timeout if auto-refresh is enabled
        timeout = 0.5 if auto_refresh else None  # Check every half second with auto-refresh
        nav = get_navigation_key(total_pages, timeout=timeout)


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
                error = colorize(
                    "Invalid key. Press any key to continue...", ColorScheme.ERROR)
            else:
                error = "Invalid key. Press any key to continue..."

            print(f"\n{error}")
            getch()  # Wait for any key before continuing
        elif nav["action"] == "refresh-now" or (auto_refresh and background_fetcher and background_fetcher.has_new_comments()):
            # Get updated comment tree from background fetcher
            if auto_refresh and background_fetcher:
                comment_tree, story_update = background_fetcher.get_comment_tree()
                if story_update:  # Update story if available
                    story = story_update
                    
                # Acknowledge new comments
                new_comments_count = 0
                if background_fetcher.has_new_comments():
                    background_fetcher.acknowledge_new_comments()
                    
                # Force resort and redisplay
                needs_resort = True
           
        elif nav["action"] == "timeout":
            # Check for new comments on timeout
            continue  # Just refresh the screen

    # Clean up background fetcher if it was used
    if auto_refresh and background_fetcher:
        background_fetcher.stop()

    return (total_pages, current_page, total_comments)


def should_view_comments():
    """Ask the user if they want to view the comments after exporting."""
    print("\nDo you want to view the comments? (y/n)")
    choice = getch().lower()
    return choice == 'y'


class BackgroundCommentFetcher:
    """Class to handle background fetching of comments for a story."""
    
    def __init__(self, story_id, interval=60, callback=None):
        """
        Initialize the background fetcher.
        
        Args:
            story_id: ID of the story to fetch comments for
            interval: Interval in seconds between updates
            callback: Function to call when new comments are found
        """
        self.story_id = story_id
        self.interval = max(interval, 10)  # Minimum 10 seconds to prevent excessive API calls
        self.callback = callback
        self.running = False
        self.thread = None
        self.comment_ids = set()  # Track known comment IDs
        self.comment_tree_lock = threading.Lock()  # Lock for thread-safety
        self.comment_tree = []  # Current comment tree
        self.story = None  # Story data
        self.new_comments_queue = queue.Queue()  # Queue for new comments
        self.total_comments = 0
        self.is_refreshing = False  # Flag to indicate active refresh
        self.refresh_progress = 0   # Progress value (0-100)
        self.status_lock = threading.Lock()  # Lock for status updates
        
    def start(self):
        """
        Start the background fetching thread.
        
        Returns:
            bool: True if started, False if already running
        """
        if self.running:
            return False
            
        # Fetch initial comment data
        self._fetch_initial_data()
        
        # Start background thread
        self.running = True
        self.thread = threading.Thread(target=self._background_fetcher, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """
        Stop the background fetching thread.
        
        Returns:
            bool: True if stopped, False if not running
        """
        if not self.running:
            return False
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)  # Wait up to 1 second for thread to exit
            self.thread = None
        return True
    
    def has_new_comments(self):
        """
        Check if there are new comments available.
        
        Returns:
            bool: True if new comments exist, False otherwise
        """
        return not self.new_comments_queue.empty()
    
    def is_currently_refreshing(self):
        """
        Check if the fetcher is currently refreshing comments.
        
        Returns:
            bool: True if actively refreshing, False otherwise
        """
        with self.status_lock:
            return self.is_refreshing
    
    def get_refresh_progress(self):
        """
        Get the current refresh progress as a percentage.
        
        Returns:
            int: Progress value between 0-100
        """
        with self.status_lock:
            return self.refresh_progress
        
    def get_comment_count(self):
        """
        Get the total number of comments in the current tree.
        
        Returns:
            int: Number of comments
        """
        return self.total_comments
    
    def get_comment_tree(self):
        """
        Get the current comment tree.
        
        Returns:
            tuple: (comment_tree, story)
        """
        with self.comment_tree_lock:
            return (list(self.comment_tree), dict(self.story) if self.story else None)
    
    def get_new_comments_count(self):
        """
        Get the number of new comments since last check.
        
        Returns:
            int: Number of new comments
        """
        return self.new_comments_queue.qsize()
    
    def acknowledge_new_comments(self):
        """
        Acknowledge and clear the new comments notification.
        """
        # Clear the queue
        while not self.new_comments_queue.empty():
            try:
                self.new_comments_queue.get_nowait()
            except queue.Empty:
                break
    
    def _update_refresh_status(self, is_refreshing, progress=0):
        """Update the refreshing status with thread safety."""
        with self.status_lock:
            self.is_refreshing = is_refreshing
            self.refresh_progress = progress
    
    def _fetch_initial_data(self):
        """Fetch the initial comment data for the story."""
        self._update_refresh_status(True, 0)
        
        try:
            # Fetch the story first
            self.story = fetch_item(self.story_id)
            self._update_refresh_status(True, 20)
            
            if not self.story:
                return
                
            # Extract comment IDs
            comment_ids = self.story.get("kids", [])
            self._update_refresh_status(True, 40)
            
            if not comment_ids:
                return
                
            # Fetch the initial comment tree
            self.comment_tree = fetch_comment_tree(comment_ids, progress_callback=lambda p: 
                                                  self._update_refresh_status(True, 40 + int(p * 0.5)))
            self.total_comments = count_comment_tree(self.comment_tree)
            self._update_refresh_status(True, 95)
            
            # Record all comment IDs for future comparison
            self.comment_ids = self._collect_comment_ids(self.comment_tree)
        finally:
            self._update_refresh_status(False, 100)
    
    def _collect_comment_ids(self, comments):
        """Collect all comment IDs in the tree."""
        ids = set()
        for comment in comments:
            if "id" in comment:
                ids.add(comment["id"])
            if "children" in comment and comment["children"]:
                ids.update(self._collect_comment_ids(comment["children"]))
        return ids
    
    def _background_fetcher(self):
        """Background fetching thread function."""
        while self.running:
            try:
                # Sleep for the specified interval
                time.sleep(self.interval)
                
                if not self.running:  # Check if we should exit
                    break
                
                # Start refresh and update status
                self._update_refresh_status(True, 0)
                    
                # Fetch the story again to get updated comment IDs
                updated_story = fetch_item(self.story_id)
                self._update_refresh_status(True, 20)
                
                if not updated_story:
                    continue
                    
                # Get the current comment IDs from the story
                current_comment_ids = updated_story.get("kids", [])
                self._update_refresh_status(True, 40)
                
                if not current_comment_ids:
                    continue
                    
                # Fetch the full comment tree with progress updates
                def progress_callback(progress):
                    # Map progress to 40-90% range
                    adjusted_progress = 40 + int(progress * 0.5)
                    self._update_refresh_status(True, adjusted_progress)
                
                updated_tree = fetch_comment_tree(
                    current_comment_ids,
                    progress_callback=progress_callback
                )
                self._update_refresh_status(True, 90)
                
                updated_comment_ids = self._collect_comment_ids(updated_tree)
                self._update_refresh_status(True, 95)
                
                # Find new comments
                new_comment_ids = updated_comment_ids - self.comment_ids
                if new_comment_ids:
                    # Update our stored data
                    with self.comment_tree_lock:
                        self.comment_tree = updated_tree
                        self.story = updated_story
                        self.comment_ids = updated_comment_ids
                        self.total_comments = count_comment_tree(updated_tree)
                    
                    # Put the count in the queue to signal new comments
                    self.new_comments_queue.put(len(new_comment_ids))
                    
                    # Call the callback if provided
                    if self.callback:
                        self.callback(len(new_comment_ids))
            except Exception as e:
                # Log error but continue running
                error_msg = f"Background fetching error: {e}"
                print(error_msg)  # Simple logging
            finally:
                # Always update status when complete
                self._update_refresh_status(False, 100)