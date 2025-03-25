"""
Module for fetching and displaying HackerNews user information.
"""
import os
import html
import datetime
import textwrap
import sys
import requests
from webbrowser import open as url_open

from .colors import Colors, colorize, supports_color
from .getch import getch
from .constants import URLS
from .loading import LoadingIndicator

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
    print("  [o] Open user profile in browser")
    print("  [q] Return to menu")
    
    while True:
        key = getch().lower()
        
        if key == 'o':
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
        print("Navigation: [↑/↓] Move selection   [Enter] View user   [q] Quit   [r] Refresh list")
        
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
                display_user(users[current_index])
                # Redraw the list screen after viewing a user
                continue
        
        # Arrow key navigation (this is simplified - actual arrow key handling may need more work)
        elif key in ('\x1b', '[', 'A', 'B'):  # Arrow key sequences
            if key == 'A':  # Up
                current_index = max(0, current_index - 1)
            elif key == 'B':  # Down
                current_index = min(len(users) - 1, current_index + 1)
        elif key == 'w':  # Alternative to up arrow
            current_index = max(0, current_index - 1)
        elif key == 's':  # Alternative to down arrow
            current_index = min(len(users) - 1, current_index + 1)

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
        username = input("> ").strip()
        
        if username.lower() == 'q':
            return {'action': 'return_to_menu'}
        
        if username:
            result = display_user(username)
            if result and result.get('action') == 'return_to_menu':
                return result
            clear_screen()
            print(f"{padding}{colorize(header, Colors.BOLD + Colors.YELLOW) if USE_COLORS else header}{padding}")
        else:
            print("Please enter a valid username.")