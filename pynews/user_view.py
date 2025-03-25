"""
Module for fetching and displaying HackerNews user information.
"""
import os
import html
import datetime
import textwrap
import sys
import requests
import time
from webbrowser import open as url_open
from concurrent.futures import ThreadPoolExecutor, as_completed

from .colors import Colors, colorize, supports_color
from .getch import getch
from .constants import URLS
from .loading import LoadingIndicator
from .utils import format_time_ago

USE_COLORS = supports_color()

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_user(username):
    """
    Fetch user data from the HackerNews API.
    
    Args:
        username: The username to fetch
        
    Returns:
        User data dictionary or None if user not found
    """
    try:
        loader = LoadingIndicator(message=f"Fetching user '{username}'...")
        loader.start()
        
        url = URLS["user"].format(username)
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Failed to fetch user '{username}'. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        loader.stop()

def fetch_item(item_id):
    """
    Fetch a single item (story, comment, etc.) from the HackerNews API.
    
    Args:
        item_id: The ID of the item to fetch
        
    Returns:
        Item data dictionary or None if not found
    """
    try:
        url = URLS["item"].format(item_id)
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        return None

def fetch_submissions(username, max_items=100):
    """
    Fetch submissions (stories, comments, etc.) by a HackerNews user.
    
    Args:
        username: The username to fetch submissions for
        max_items: Maximum number of items to fetch
        
    Returns:
        List of submission items or None if user not found
    """
    try:
        loader = LoadingIndicator(message=f"Fetching submission list for '{username}'...")
        loader.start()
        
        # First, get the user data to get their submission IDs
        url = URLS["user"].format(username)
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error: Failed to fetch user '{username}'. Status code: {response.status_code}")
            return None
            
        user_data = response.json()
        submission_ids = user_data.get('submitted', [])
        
        # Limit the number of submissions to fetch
        submission_ids = submission_ids[:min(max_items, len(submission_ids))]
        
        loader.stop()
        
        if not submission_ids:
            return []
            
        # Now fetch the actual submission items in parallel
        submissions = []
        total_ids = len(submission_ids)
        
        print(f"Fetching {total_ids} submissions for user {username}...")
        completed = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all fetch tasks
            future_to_id = {executor.submit(fetch_item, item_id): item_id for item_id in submission_ids}
            
            # Process results as they complete
            for future in as_completed(future_to_id):
                submission = future.result()
                if submission:
                    submissions.append(submission)
                completed += 1
                
                # Print a simple progress message
                sys.stdout.write(f"\rCompleted: {completed}/{total_ids} submissions")
                sys.stdout.flush()
                
        print("\nFinished fetching submissions.")
        return submissions
        
    except Exception as e:
        print(f"Error fetching submissions: {e}")
        return None
    finally:
        if 'loader' in locals() and hasattr(loader, 'stop'):
            loader.stop()

def categorize_submissions(submissions):
    """
    Categorize submissions by type (story, comment, etc.)
    
    Args:
        submissions: List of submission items
        
    Returns:
        Dictionary with categorized submissions
    """
    categories = {
        'story': [],
        'comment': [],
        'poll': [],
        'pollopt': [],
        'job': [],
        'other': []
    }
    
    for item in submissions:
        item_type = item.get('type', 'other')
        if item_type in categories:
            categories[item_type].append(item)
        else:
            categories['other'].append(item)
            
    return categories

def fetch_karma(username, silent=False):
    """
    Fetch and return only the karma for a HackerNews user.
    
    Args:
        username: The username to fetch karma for
        silent: If True, don't display loading messages or errors
        
    Returns:
        Karma value (int) or None if user not found
    """
    try:
        if not silent:
            loader = LoadingIndicator(message=f"Fetching karma for '{username}'...")
            loader.start()
            
        url = URLS["user"].format(username)
        response = requests.get(url)
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('karma', 0)
        else:
            if not silent:
                print(f"Error: Failed to fetch user '{username}'. Status code: {response.status_code}")
            return None
    except Exception as e:
        if not silent:
            print(f"Error fetching karma: {e}")
        return None
    finally:
        if not silent and 'loader' in locals():
            loader.stop()

def fetch_created_timestamp(username, silent=False):
    """
    Fetch and return only the creation timestamp for a HackerNews user.
    
    Args:
        username: The username to fetch creation date for
        silent: If True, don't display loading messages or errors
        
    Returns:
        Creation timestamp (int) or None if user not found
    """
    try:
        if not silent:
            loader = LoadingIndicator(message=f"Fetching account creation date for '{username}'...")
            loader.start()
            
        url = URLS["user"].format(username)
        response = requests.get(url)
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('created', None)
        else:
            if not silent:
                print(f"Error: Failed to fetch user '{username}'. Status code: {response.status_code}")
            return None
    except Exception as e:
        if not silent:
            print(f"Error fetching creation date: {e}")
        return None
    finally:
        if not silent and 'loader' in locals():
            loader.stop()

def display_karma(username):
    """
    Display the karma for a HackerNews user.
    
    Args:
        username: The username to display karma for
        
    Returns:
        Dictionary with action results or None if user not found
    """
    karma = fetch_karma(username)
    
    if karma is None:
        print(f"User '{username}' not found.")
        print("\nPress any key to continue...")
        getch()
        return None
    
    clear_screen()
    terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    
    # Header
    header = f" Karma for HackerNews User: {username} "
    padding = "=" * ((terminal_width - len(header)) // 2)
    print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
    
    # Display karma with formatting
    karma_display = colorize(f"{karma:,}", Colors.BOLD + Colors.GREEN) if USE_COLORS else f"{karma:,}"
    print(f"\nKarma: {karma_display}")
    
    # Options
    print(f"\n{'-' * terminal_width}")
    print("\nOptions:")
    print("  [d] View detailed profile")
    print("  [c] View account creation date")
    print("  [s] View user's stories")
    print("  [o] Open user profile in browser")
    print("  [q] Return to menu")
    
    while True:
        key = getch().lower()
        
        if key == 'd':
            return {
                'action': 'view_profile',
                'username': username
            }
        elif key == 'c':
            return {
                'action': 'view_created',
                'username': username
            }
        elif key == 's':
            return {
                'action': 'view_stories',
                'username': username
            }
        elif key == 'o':
            url = f"https://news.ycombinator.com/user?id={username}"
            print(f"\nOpening {url} in your browser...")
            url_open(url)
            # Stay in the karma view after opening browser
            continue
        elif key == 'q' or key == '\n' or key == '\r':
            return {'action': 'return_to_menu'}

def display_created_date(username):
    """
    Display the account creation date for a HackerNews user.
    
    Args:
        username: The username to display creation date for
        
    Returns:
        Dictionary with action results or None if user not found
    """
    created_timestamp = fetch_created_timestamp(username)
    
    if created_timestamp is None:
        print(f"User '{username}' not found.")
        print("\nPress any key to continue...")
        getch()
        return None
    
    clear_screen()
    terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    
    # Header
    header = f" Account Creation for HackerNews User: {username} "
    padding = "=" * ((terminal_width - len(header)) // 2)
    print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
    
    # Format and display dates
    created_date = format_timestamp(created_timestamp)
    account_age = format_account_age(created_timestamp)
    
    created_display = colorize(created_date, Colors.BOLD + Colors.CYAN) if USE_COLORS else created_date
    age_display = colorize(account_age, Colors.BOLD + Colors.GREEN) if USE_COLORS else account_age
    
    print(f"\nCreated: {created_display}")
    print(f"Account age: {age_display}")
    
    # Calculate some interesting facts
    try:
        created_dt = datetime.datetime.fromtimestamp(created_timestamp)
        days_since_hn_launch = (created_dt - datetime.datetime(2007, 2, 19)).days
        
        if days_since_hn_launch >= 0:
            print(f"\nInteresting fact: This account was created {days_since_hn_launch} days after HackerNews launched")
            
            if days_since_hn_launch < 30:
                print("This is one of the earliest HackerNews accounts!")
            elif days_since_hn_launch < 365:
                print("This account was created in the first year of HackerNews!")
    except:
        pass
    
    # Options
    print(f"\n{'-' * terminal_width}")
    print("\nOptions:")
    print("  [d] View detailed profile")
    print("  [k] View karma")
    print("  [s] View user's stories")
    print("  [o] Open user profile in browser")
    print("  [q] Return to menu")
    
    while True:
        key = getch().lower()
        
        if key == 'd':
            return {
                'action': 'view_profile',
                'username': username
            }
        elif key == 'k':
            return {
                'action': 'view_karma',
                'username': username
            }
        elif key == 's':
            return {
                'action': 'view_stories',
                'username': username
            }
        elif key == 'o':
            url = f"https://news.ycombinator.com/user?id={username}"
            print(f"\nOpening {url} in your browser...")
            url_open(url)
            # Stay in the creation date view after opening browser
            continue
        elif key == 'q' or key == '\n' or key == '\r':
            return {'action': 'return_to_menu'}

def display_user_stories(username, max_items=50):
    """
    Display stories submitted by a specific HackerNews user.
    
    Args:
        username: The username to display stories for
        max_items: Maximum number of stories to fetch and display
        
    Returns:
        Dictionary with action results or None if user not found
    """
    # Fetch all submissions (stories, comments, etc.)
    submissions = fetch_submissions(username, max_items=max_items)
    
    if submissions is None:
        print(f"User '{username}' not found.")
        print("\nPress any key to continue...")
        getch()
        return None
        
    if not submissions:
        print(f"No submissions found for user '{username}'.")
        print("\nPress any key to continue...")
        getch()
        return {'action': 'return_to_menu'}
    
    # Categorize submissions and extract just the stories
    categorized = categorize_submissions(submissions)
    stories = categorized['story']
    
    if not stories:
        clear_screen()
        terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        
        # Header
        header = f" Stories by HackerNews User: {username} "
        padding = "=" * ((terminal_width - len(header)) // 2)
        print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
        
        print("\nNo stories found for this user.")
        print(f"User has {len(categorized['comment'])} comments, {len(categorized['poll'])} polls, and {len(categorized['job'])} job postings.")
        
        print(f"\n{'-' * terminal_width}")
        print("\nOptions:")
        print("  [d] View detailed profile")
        print("  [k] View karma")
        print("  [c] View account creation date")
        print("  [o] Open user profile in browser")
        print("  [q] Return to menu")
        
        while True:
            key = getch().lower()
            
            if key == 'd':
                return {
                    'action': 'view_profile',
                    'username': username
                }
            elif key == 'k':
                return {
                    'action': 'view_karma',
                    'username': username
                }
            elif key == 'c':
                return {
                    'action': 'view_created',
                    'username': username
                }
            elif key == 'o':
                url = f"https://news.ycombinator.com/user?id={username}"
                print(f"\nOpening {url} in your browser...")
                url_open(url)
                continue
            elif key == 'q' or key == '\n' or key == '\r':
                return {'action': 'return_to_menu'}
    
    #  Sort stories by timestamp (newest first)
    stories.sort(key=lambda x: x.get('time', 0), reverse=True)
    
    # Display stories with pagination
    current_page = 0
    stories_per_page = min(10, len(stories))
    max_pages = (len(stories) + stories_per_page - 1) // stories_per_page
    selected_index = 0
    
    while True:
        clear_screen()
        terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        
        # Header
        header = f" Stories by HackerNews User: {username} "
        padding = "=" * ((terminal_width - len(header)) // 2)
        print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
        
        # Pagination info
        start_idx = current_page * stories_per_page
        end_idx = min(start_idx + stories_per_page, len(stories))
        
        stats_line = f"Showing {start_idx+1}-{end_idx} of {len(stories)} stories (Page {current_page+1}/{max_pages})"
        print(colorize(stats_line, Colors.FAINT) if USE_COLORS else stats_line)
        print(f"{'-' * terminal_width}")
        
        # Display stories for the current page
        displayed_stories = stories[start_idx:end_idx]
        for i, story in enumerate(displayed_stories):
            story_index = start_idx + i
            is_selected = (story_index % stories_per_page) == selected_index
            
            # Format story information
            title = story.get('title', 'No title')
            score = story.get('score', 0)
            comment_count = len(story.get('kids', []))
            timestamp = story.get('time', 0)
            story_url = story.get('url', '')
            
            # Format time ago
            time_ago = format_time_ago(timestamp) if timestamp else 'Unknown'
            
            # Truncate title if needed
            max_title_length = terminal_width - 30
            if len(title) > max_title_length:
                title = title[:max_title_length-3] + "..."
            
            # Format the story line
            if is_selected:
                prefix = " > "
                suffix = " < "
                if USE_COLORS:
                    title_display = colorize(title, Colors.BOLD + Colors.CYAN)
                    score_display = colorize(f"{score}", Colors.GREEN)
                    comments_display = colorize(f"{comment_count}", Colors.BLUE)
                    time_display = colorize(time_ago, Colors.FAINT)
                    line = f"{prefix}{title_display} ({score_display} pts, {comments_display} comments, {time_display}){suffix}"
                else:
                    line = f"{prefix}{title} ({score} pts, {comment_count} comments, {time_ago}){suffix}"
            else:
                prefix = "   "
                suffix = ""
                if USE_COLORS:
                    score_display = colorize(f"{score}", Colors.GREEN)
                    comments_display = colorize(f"{comment_count}", Colors.BLUE)
                    time_display = colorize(time_ago, Colors.FAINT)
                    line = f"{prefix}{title} ({score_display} pts, {comments_display} comments, {time_display}){suffix}"
                else:
                    line = f"{prefix}{title} ({score} pts, {comment_count} comments, {time_ago}){suffix}"
            
            print(line)
        
        # Navigation instructions
        print(f"\n{'-' * terminal_width}")
        print("Navigation: [↑/↓] Move selection  [←/→] Change page  [Enter] Open in browser  [c] View comments")
        print("           [d] View profile  [k] View karma  [q] Return")
        
        # Get input
        key = getch().lower()
        
        if key == 'q':
            return {'action': 'return_to_menu'}
            
        elif key == 'd':
            return {
                'action': 'view_profile',
                'username': username
            }
            
        elif key == 'k':
            return {
                'action': 'view_karma',
                'username': username
            }
            
        elif key in ('\x1b', '[', 'A', 'B', 'C', 'D'):  # Arrow key sequences
            if key == 'A':  # Up
                selected_index = max(0, selected_index - 1)
            elif key == 'B':  # Down
                selected_index = min(min(stories_per_page, end_idx - start_idx) - 1, selected_index + 1)
            elif key == 'D':  # Left (previous page)
                if current_page > 0:
                    current_page -= 1
                    selected_index = 0
            elif key == 'C':  # Right (next page)
                if current_page < max_pages - 1:
                    current_page += 1
                    selected_index = 0
        
        elif key == 'w':  # Alternative to up
            selected_index = max(0, selected_index - 1)
        elif key == 's':  # Alternative to down
            selected_index = min(min(stories_per_page, end_idx - start_idx) - 1, selected_index + 1)
        elif key == 'a':  # Alternative to left
            if current_page > 0:
                current_page -= 1
                selected_index = 0
        elif key == 'd':  # Alternative to right
            if current_page < max_pages - 1:
                current_page += 1
                selected_index = 0
                
        elif key == '\n' or key == '\r':  # Enter - open story in browser
            story_idx = start_idx + selected_index
            if 0 <= story_idx < len(stories):
                story = stories[story_idx]
                # Try to use the URL, fall back to HackerNews URL
                url = story.get('url', '')
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story.get('id')}"
                
                print(f"\nOpening {url} in your browser...")
                url_open(url)
                time.sleep(0.5)  # Brief pause to see the message
                
        elif key == 'c':  # View comments
            story_idx = start_idx + selected_index
            if 0 <= story_idx < len(stories):
                story = stories[story_idx]
                story_id = story.get('id')
                if story_id:
                    return {
                        'action': 'view_comments',
                        'story_id': story_id
                    }

def format_timestamp(unix_time):
    """Convert Unix timestamp to a human-readable format."""
    try:
        dt = datetime.datetime.fromtimestamp(unix_time)
        # Format: "Mar 17, 2023 at 10:30 AM"
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except:
        return "Unknown"

def format_account_age(created_at):
    """Calculate user account age from creation timestamp."""
    if not created_at:
        return "Unknown"
        
    try:
        created_date = datetime.datetime.fromtimestamp(created_at)
        now = datetime.datetime.now()
        delta = now - created_date
        
        years = delta.days // 365
        months = (delta.days % 365) // 30
        days = (delta.days % 365) % 30
        
        if years > 0:
            return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
        elif months > 0:
            return f"{months} month{'s' if months != 1 else ''}, {days} day{'s' if days != 1 else ''}"
        else:
            return f"{days} day{'s' if days != 1 else ''}"
    except:
        return "Unknown"

def display_user(username):
    """
    Display detailed information about a HackerNews user.
    
    Args:
        username: The username to display
        
    Returns:
        Dictionary with action results or None if user not found
    """
    user_data = fetch_user(username)
    
    if not user_data:
        print(f"User '{username}' not found.")
        print("\nPress any key to return...")
        getch()
        return None
    
    clear_screen()
    terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    
    # Header
    header = f" HackerNews User: {username} "
    padding = "=" * ((terminal_width - len(header)) // 2)
    print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
    
    # Basic info
    karma = user_data.get('karma', 0)
    created_at = user_data.get('created', 0)
    
    karma_display = colorize(f"{karma:,}", Colors.GREEN) if USE_COLORS else f"{karma:,}"
    print(f"Karma: {karma_display}")
    print(f"Account age: {format_account_age(created_at)} (created on {format_timestamp(created_at)})")
    
    # About text (if available)
    about = user_data.get('about', '')
    if about:
        # Clean HTML and format
        about = html.unescape(about)
        # Simple HTML tag removal (could be improved with a proper parser)
        about = about.replace('<p>', '\n').replace('</p>', '')
        
        print("\n" + colorize("About:", Colors.BOLD) if USE_COLORS else "About:")
        # Wrap text to terminal width
        wrapper = textwrap.TextWrapper(width=terminal_width - 4)
        wrapped_text = wrapper.fill(about)
        print("  " + wrapped_text.replace('\n', '\n  '))
    
    # User's submissions
    submitted = user_data.get('submitted', [])
    if submitted:
        count = len(submitted)
        print(f"\n{colorize('Submissions:', Colors.BOLD) if USE_COLORS else 'Submissions:'} {count:,} total")
    
    # Navigation options
    print("\n" + "=" * terminal_width)
    print("\nOptions:")
    print("  [k] View karma only")
    print("  [c] View creation date only")
    print("  [s] View stories")
    print("  [o] Open user profile in browser")
    print("  [q] Return to menu")
    
    while True:
        key = getch().lower()
        
        if key == 'k':
            return {
                'action': 'view_karma',
                'username': username
            }
        elif key == 'c':
            return {
                'action': 'view_created',
                'username': username
            }
        elif key == 's':
            return {
                'action': 'view_stories',
                'username': username
            }
        elif key == 'o':
            url = f"https://news.ycombinator.com/user?id={username}"
            print(f"\nOpening {url} in your browser...")
            url_open(url)
            continue
        
        if key == 'q' or key == '\n' or key == '\r':
            return {'action': 'return_to_menu'}

def fetch_random_users(count=10):
    """
    Fetch a list of random user names from top stories.
    
    This is a helper function since the API doesn't provide a direct way to get users.
    We'll fetch some top stories and extract the submitters' usernames.
    
    Args:
        count: Number of unique usernames to retrieve
        
    Returns:
        List of unique usernames
    """
    try:
        loader = LoadingIndicator(message="Fetching user names...")
        loader.start()
        
        # First get some top stories
        url = URLS["top"]
        response = requests.get(url)
        stories = response.json()
        
        # Now get the submitters from these stories
        users = set()  # Use a set to avoid duplicates
        for story_id in stories[:min(50, len(stories))]:  # Check up to 50 stories
            if len(users) >= count:
                break
                
            story_url = URLS["item"].format(story_id)
            story_data = requests.get(story_url).json()
            
            if story_data and 'by' in story_data:
                users.add(story_data['by'])
        
        return list(users)[:count]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []
    finally:
        loader.stop()

def list_users():
    """
    Display a list of HackerNews users with interactive selection.
    
    Returns:
        Dictionary with action results
    """
    users = fetch_random_users(20)  # Fetch 20 random users
    
    if not users:
        print("Failed to fetch users.")
        input("Press Enter to return...")
        return {'action': 'return_to_menu'}
    
    clear_screen()
    current_index = 0
    
    while True:
        clear_screen()
        terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        
        # Header
        header = " HackerNews Users "
        padding = "=" * ((terminal_width - len(header)) // 2)
        print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
        
        # Display users
        for i, user in enumerate(users):
            if i == current_index:
                line = f" > {user} < "
                print(colorize(line, Colors.BOLD + Colors.CYAN) if USE_COLORS else line)
            else:
                print(f"   {user}")
        
        # Navigation
        print("\n" + "=" * terminal_width)
        print("Navigation: [↑/↓] Move selection   [Enter] View user   [k] View karma   [c] View creation date")
        print("           [s] View stories   [q] Quit   [r] Refresh list")
        
        # Get input
        key = getch().lower()
        
        if key == 'q':
            return {'action': 'return_to_menu'}
        
        elif key == 'r':
            users = fetch_random_users(20)
            current_index = 0
            continue
        
        elif key == '\n' or key == '\r':
            if users and 0 <= current_index < len(users):
                result = display_user(users[current_index])
                handle_user_action_result(result)
                # Redraw the list screen after viewing user info
                continue
                
        elif key == 'k':
            if users and 0 <= current_index < len(users):
                result = display_karma(users[current_index])
                handle_user_action_result(result)
                # Redraw the list screen after viewing karma
                continue
                
        elif key == 'c':
            if users and 0 <= current_index < len(users):
                result = display_created_date(users[current_index])
                handle_user_action_result(result)
                # Redraw the list screen after viewing creation date
                continue
                
        elif key == 's':
            if users and 0 <= current_index < len(users):
                result = display_user_stories(users[current_index])
                handle_user_action_result(result)
                # Redraw the list screen after viewing stories
                continue
        
        # Arrow key navigation (this is simplified - actual arrow key handling may need more work)
        elif key in ('\x1b', '[', 'A', 'B'):  # Arrow key sequences
            if key == 'A':  # Up
                current_index = max(0, current_index - 1)
            elif key == 'B':  # Down
                current_index = min(len(users) - 1, current_index + 1)
        elif key == 'w':  # Alternative to up arrow
            current_index = max(0, current_index - 1)
        elif key == 's' and not (users and 0 <= current_index < len(users)):  # Alternative to down arrow, only if not trying to view stories
            current_index = min(len(users) - 1, current_index + 1)

def handle_user_action_result(result):
    """Helper function to handle nested view transitions."""
    if not result:
        return
        
    if result.get('action') == 'view_profile':
        user_result = display_user(result.get('username'))
        handle_user_action_result(user_result)
    elif result.get('action') == 'view_karma':
        karma_result = display_karma(result.get('username'))
        handle_user_action_result(karma_result)
    elif result.get('action') == 'view_created':
        created_result = display_created_date(result.get('username'))
        handle_user_action_result(created_result)
    elif result.get('action') == 'view_stories':
        stories_result = display_user_stories(result.get('username'))
        handle_user_action_result(stories_result)

def search_user():
    """
    Interactive prompt to search for a specific HackerNews user.
    
    Returns:
        Dictionary with action results
    """
    clear_screen()
    terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    
    # Header
    header = " Search HackerNews Users "
    padding = "=" * ((terminal_width - len(header)) // 2)
    print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
    
    while True:
        print("\nEnter a username to view (or 'q' to return):")
        print("Options: [u]ser profile, [k]arma only, [c]reation date only, [s]tories")
        option = "u"  # Default to user profile
        username = input("> ").strip()
        
        if username.lower() == 'q':
            return {'action': 'return_to_menu'}
            
        if username.lower() == 'k':
            option = 'k'
            print("Enter username to view karma for:")
            username = input("> ").strip()
            if username.lower() == 'q':
                return {'action': 'return_to_menu'}
                
        if username.lower() == 'c':
            option = 'c'
            print("Enter username to view creation date for:")
            username = input("> ").strip()
            if username.lower() == 'q':
                return {'action': 'return_to_menu'}
                
        if username.lower() == 's':
            option = 's'
            print("Enter username to view stories for:")
            username = input("> ").strip()
            if username.lower() == 'q':
                return {'action': 'return_to_menu'}
                
        if username.lower().startswith('k '):
            option = 'k'
            username = username[2:].strip()
            
        if username.lower().startswith('c '):
            option = 'c'
            username = username[2:].strip()
            
        if username.lower().startswith('s '):
            option = 's'
            username = username[2:].strip()
            
        if username.lower().startswith('u '):
            option = 'u'
            username = username[2:].strip()
        
        if username:
            if option == 'k':
                result = display_karma(username)
                handle_user_action_result(result)
            elif option == 'c':
                result = display_created_date(username)
                handle_user_action_result(result)
            elif option == 's':
                result = display_user_stories(username)
                handle_user_action_result(result)
            else:
                result = display_user(username)
                handle_user_action_result(result)
                
            clear_screen()
            print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
        else:
            print("Please enter a valid username.")

def compare_karma(usernames):
    """
    Compare karma scores between multiple users.
    
    Args:
        usernames: List of usernames to compare
        
    Returns:
        Dictionary with action results
    """
    if not usernames:
        print("No usernames provided for comparison.")
        print("\nPress any key to continue...")
        getch()
        return {'action': 'return_to_menu'}
        
    # Fetch karma for all users
    users_karma = {}
    
    # Show loading message
    print("Fetching karma for users...\n")
    
    for username in usernames:
        karma = fetch_karma(username, silent=True)
        if karma is not None:
            users_karma[username] = karma
            
    if not users_karma:
        print("Could not fetch karma for any of the provided users.")
        print("\nPress any key to continue...")
        getch()
        return {'action': 'return_to_menu'}
        
    # Sort users by karma (highest first)
    sorted_users = sorted(users_karma.items(), key=lambda x: x[1], reverse=True)
    
    clear_screen()
    terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    
    # Header
    header = " HackerNews Karma Comparison "
    padding = "=" * ((terminal_width - len(header)) // 2)
    print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
    
    # Display karma comparison
    max_username_length = max(len(username) for username in users_karma.keys())
    
    for username, karma in sorted_users:
        username_padded = username.ljust(max_username_length)
        if USE_COLORS:
            username_display = colorize(username_padded, Colors.CYAN)
            karma_display = colorize(f"{karma:,}", Colors.GREEN)
            print(f"{username_display} : {karma_display}")
        else:
            print(f"{username_padded} : {karma:,}")
    
    print(f"\n{'-' * terminal_width}")
    print("\nPress any key to continue...")
    getch()
    return {'action': 'return_to_menu'}