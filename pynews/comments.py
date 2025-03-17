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
from concurrent.futures import ThreadPoolExecutor, as_completed

from .constants import URLS

def fetch_item(item_id):
    """Fetch a single item (story or comment) from the HackerNews API."""
    url = URLS["item"].format(item_id)
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except requests.RequestException:
        return None

def fetch_comment_tree(comment_ids, max_threads=10):
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
                    print(f"Error fetching comment {item_id}: {e}")
    
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
            
    # Sort comments by timestamp
    comments.sort(key=lambda c: c.get('time', 0), reverse=True)
    return comments

def format_timestamp(unix_time):
    """Convert Unix timestamp to a human-readable format."""
    try:
        dt = datetime.datetime.fromtimestamp(unix_time)
        # Format: "Mar 17, 2023 at 10:30 AM"
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except (TypeError, ValueError):
        return "Unknown time"

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
    
    # Basic info line with author and timestamp
    header = f"{'  ' * indent_level}┌─ {comment.get('by', 'Anonymous')} · {format_timestamp(comment.get('time', 0))}"
    
    # Format and wrap the comment text
    text = clean_comment_text(comment.get('text', ''))
    wrapper = textwrap.TextWrapper(
        initial_indent='  ' * indent_level + '│ ', 
        subsequent_indent='  ' * indent_level + '│ ',
        width=width
    )
    wrapped_text = wrapper.fill(text) if text else '  ' * indent_level + '│ [No content]'
    
    # Add footer
    footer = f"{'  ' * indent_level}└{'─' * 30}"
    
    return f"{header}\n{wrapped_text}\n{footer}"

def print_comment_tree(comments, page_size=10, indent_level=0, width=80, start_idx=0):
    """
    Print a list of comments with indentation for nested comments.
    Supports pagination with page_size determining comments per page.
    Returns the number of total comments in the tree.
    """
    total_shown = 0
    total_count = 0
    
    for i, comment in enumerate(comments):
        if i < start_idx:
            # Count child comments for skipped comments
            child_count = count_comment_tree(comment.get('children', []))
            total_count += 1 + child_count
            continue
            
        if total_shown >= page_size:
            # We've printed enough comments for this page
            break
            
        # Print this comment
        print(format_comment(comment, indent_level, width))
        total_shown += 1
        total_count += 1
        
        # Print child comments recursively, with increased indentation
        if 'children' in comment and comment['children']:
            children_count = print_comment_tree(
                comment['children'], 
                page_size - total_shown,  # Adjust page size for what's left
                indent_level + 1, 
                width
            )
            total_count += children_count
            total_shown += min(children_count, page_size - total_shown)
    
    return total_count

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

def show_navigation_menu(current_page, total_pages):
    """Display navigation options for pagination."""
    print("\n" + "=" * 40)
    print("Navigation:")
    
    if current_page > 1:
        print("[p] Previous page")
    else:
        print("[ ] Previous page (unavailable)")
        
    if current_page < total_pages:
        print("[n] Next page")
    else:
        print("[ ] Next page (unavailable)")
    
    print("[g] Go to page (enter number)")
    print("[q] Quit")
    print("=" * 40)
    
    choice = input("\nEnter choice: ").strip().lower()
    return choice

def handle_navigation(choice, current_page, total_pages):
    """Process user navigation choice and return the new page number."""
    if choice == 'p' and current_page > 1:
        return current_page - 1
    elif choice == 'n' and current_page < total_pages:
        return current_page + 1
    elif choice == 'g':
        try:
            page_num = int(input(f"Enter page number (1-{total_pages}): "))
            if 1 <= page_num <= total_pages:
                return page_num
            else:
                print(f"Invalid page number. Must be between 1 and {total_pages}.")
                input("Press Enter to continue...")
                return current_page
        except ValueError:
            print("Invalid input. Please enter a number.")
            input("Press Enter to continue...")
            return current_page
    elif choice == 'q':
        return -1  # Signal to quit
    else:
        print("Invalid choice.")
        input("Press Enter to continue...")
        return current_page

def display_comments_for_story(story_id, page_size=10, page_num=1, width=80):
    """
    Display comments for a given story with interactive pagination support.
    
    Args:
        story_id: The ID of the story to show comments for
        page_size: Number of comments to display per page
        page_num: Which page of comments to display (1-indexed)
        width: Display width for wrapping comments
        
    Returns:
        tuple: (total_pages, current_page_num, total_comments)
    """
    # First, fetch the story to get its comments
    story = fetch_item(story_id)
    if not story:
        print(f"Error: Could not fetch story with ID {story_id}")
        return (0, 0, 0)
    
    # Cache for the comment tree to avoid refetching
    comment_tree = None
    total_comments = 0
    total_pages = 0
    current_page = page_num
    
    while True:
        clear_screen()
        
        # Display story information
        print(f"\n=== Comments for: {story.get('title', 'Unknown Story')} ===")
        print(f"By {story.get('by', 'Unknown')} · {format_timestamp(story.get('time', 0))}")
        print(f"Points: {story.get('score', 0)} · URL: {story.get('url', '[No URL]')}\n")
        
        # Check if the story has comments
        comment_ids = story.get('kids', [])
        if not comment_ids:
            print("This story has no comments.")
            input("\nPress Enter to quit...")
            return (0, 0, 0)
        
        # Fetch comments if not already cached
        if comment_tree is None:
            print(f"Fetching comments...")
            comment_tree = fetch_comment_tree(comment_ids)
            total_comments = count_comment_tree(comment_tree)
            total_pages = (total_comments + page_size - 1) // page_size
            
            # Validate page number
            if current_page > total_pages:
                current_page = total_pages
            
        # Calculate pagination information
        start_idx = (current_page - 1) * page_size
        
        # Show pagination info
        print(f"Page {current_page} of {total_pages} (Total comments: {total_comments})")
        print("=" * width)
        
        # Display comments for the current page
        print_comment_tree(comment_tree, page_size, start_idx=start_idx, width=width)
        
        # Display navigation menu
        choice = show_navigation_menu(current_page, total_pages)
        new_page = handle_navigation(choice, current_page, total_pages)
        
        if new_page == -1:  # User chose to quit
            break
            
        current_page = new_page
    
    return (total_pages, current_page, total_comments)