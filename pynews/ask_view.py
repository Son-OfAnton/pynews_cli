"""
Module for displaying detailed views of Ask HN stories.
"""
import textwrap
import sys
import os
import html
import datetime
import re
import time
from webbrowser import open as url_open
import threading
import queue
from .comments import BackgroundCommentFetcher, display_comments_for_story, fetch_item

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

# Add this new function to handle displaying ask story details with background comment fetching
def display_ask_story_details_with_live_comments(story_id, auto_refresh=False, refresh_interval=60, notify_new_comments=False, page_size=10, width=80):
    """
    Display details of an Ask HN story with option to view comments that update in the background.
    
    Args:
        story_id: ID of the Ask HN story to display
        auto_refresh: Whether to refresh comments in background
        refresh_interval: Seconds between comment refreshes
        notify_new_comments: Whether to show notifications for new comments
        page_size: Number of comments to display per page
        width: Display width for comments
        
    Returns:
        Dict with action and parameters, or None
    """
    # Reuse the existing function for initial display
    result = display_ask_story_details(story_id)
    
    # Check if user wants to view comments
    if result and result.get('action') == 'view_comments':
        # Use the enhanced comments display with background fetching
        display_comments_for_story(
            story_id,
            page_size=page_size,
            width=width,
            auto_refresh=auto_refresh,
            refresh_interval=refresh_interval,
            notify_new_comments=notify_new_comments
        )
    
    return result

class AskStoryMonitor:
    """
    Class to monitor multiple Ask HN stories for new comments in the background.
    This provides a dashboard-like functionality for tracking active discussions.
    """
    
    def __init__(self, story_ids=None, refresh_interval=60):
        """
        Initialize the Ask HN story monitor.
        
        Args:
            story_ids: List of story IDs to monitor (can be empty and added later)
            refresh_interval: Refresh interval in seconds
        """
        self.story_ids = set(story_ids or [])
        self.refresh_interval = max(refresh_interval, 10)
        self.running = False
        self.thread = None
        self.story_data_lock = threading.Lock()
        self.story_data = {}  # Dict mapping story_id to story data
        self.new_comments = {}  # Dict mapping story_id to count of new comments
        
    def start(self):
        """
        Start the background monitoring thread.
        
        Returns:
            bool: True if started, False if already running
        """
        if self.running:
            return False
            
        # Fetch initial data for all stories
        self._fetch_initial_data()
        
        # Start background thread
        self.running = True
        self.thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """
        Stop the background monitoring thread.
        
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
    
    def add_story(self, story_id):
        """
        Add a story to the monitor.
        
        Args:
            story_id: ID of story to add
            
        Returns:
            bool: True if added, False if already being monitored
        """
        if story_id in self.story_ids:
            return False
            
        with self.story_data_lock:
            self.story_ids.add(story_id)
            
            # Fetch initial data for this story
            story = fetch_item(story_id)
            if story:
                comment_count = len(story.get('kids', []))
                
                self.story_data[story_id] = {
                    'title': story.get('title', 'Unknown'),
                    'by': story.get('by', 'Unknown'),
                    'time': story.get('time', 0),
                    'score': story.get('score', 0),
                    'descendants': story.get('descendants', 0),
                    'comment_ids': set(story.get('kids', [])),
                    'last_comment_count': comment_count
                }
                self.new_comments[story_id] = 0
            
        return True
    
    def remove_story(self, story_id):
        """
        Remove a story from the monitor.
        
        Args:
            story_id: ID of story to remove
            
        Returns:
            bool: True if removed, False if not being monitored
        """
        if story_id not in self.story_ids:
            return False
            
        with self.story_data_lock:
            self.story_ids.remove(story_id)
            if story_id in self.story_data:
                del self.story_data[story_id]
            if story_id in self.new_comments:
                del self.new_comments[story_id]
            
        return True
        
    def get_all_stories(self):
        """
        Get all currently monitored stories with their data.
        
        Returns:
            dict: Mapping of story_id to story data including new comment counts
        """
        with self.story_data_lock:
            # Create a deep copy to avoid thread safety issues
            result = {}
            for story_id, data in self.story_data.items():
                result[story_id] = dict(data)
                result[story_id]['new_comments'] = self.new_comments.get(story_id, 0)
                
        return result
    
    def get_story(self, story_id):
        """
        Get data for a specific story including new comment count.
        
        Args:
            story_id: ID of the story to get data for
            
        Returns:
            dict: Story data with new comment count, or None if not found
        """
        with self.story_data_lock:
            if story_id not in self.story_data:
                return None
                
            result = dict(self.story_data[story_id])
            result['new_comments'] = self.new_comments.get(story_id, 0)
            
        return result
    
    def acknowledge_new_comments(self, story_id):
        """
        Acknowledge and clear new comment notification for a story.
        
        Args:
            story_id: ID of the story to acknowledge
            
        Returns:
            bool: True if successful, False if story not found
        """
        with self.story_data_lock:
            if story_id not in self.new_comments:
                return False
                
            self.new_comments[story_id] = 0
            
        return True
    
    def _fetch_initial_data(self):
        """Fetch initial data for all stories in the monitor."""
        with self.story_data_lock:
            for story_id in list(self.story_ids):
                story = fetch_item(story_id)
                if not story:
                    self.story_ids.remove(story_id)
                    continue
                    
                comment_count = len(story.get('kids', []))
                
                self.story_data[story_id] = {
                    'title': story.get('title', 'Unknown'),
                    'by': story.get('by', 'Unknown'),
                    'time': story.get('time', 0),
                    'score': story.get('score', 0),
                    'descendants': story.get('descendants', 0),
                    'comment_ids': set(story.get('kids', [])),
                    'last_comment_count': comment_count
                }
                self.new_comments[story_id] = 0
    
    def _background_monitor(self):
        """Background thread function to monitor stories for new comments."""
        while self.running:
            try:
                # Sleep to avoid excessive API requests
                time.sleep(self.refresh_interval)
                
                if not self.running:  # Check if we should exit
                    break
                    
                # Make a copy of story IDs to avoid thread safety issues
                with self.story_data_lock:
                    story_ids_to_check = list(self.story_ids)
                
                # Check each story for updates
                for story_id in story_ids_to_check:
                    if not self.running:  # Check if we should exit
                        break
                        
                    updated_story = fetch_item(story_id)
                    if not updated_story:
                        continue
                        
                    with self.story_data_lock:
                        # Skip if story was removed while we were checking
                        if story_id not in self.story_data:
                            continue
                            
                        # Get current data
                        current_data = self.story_data[story_id]
                        
                        # Get updated comment IDs
                        updated_comment_ids = set(updated_story.get('kids', []))
                        current_comment_ids = current_data.get('comment_ids', set())
                        
                        # Calculate new comments
                        new_comments = updated_comment_ids - current_comment_ids
                        new_count = len(new_comments)
                        
                        # Update data if there are changes
                        if new_count > 0:
                            # Update stored data
                            current_data['comment_ids'] = updated_comment_ids
                            current_data['descendants'] = updated_story.get('descendants', 0)
                            current_data['last_comment_count'] = len(updated_comment_ids)
                            
                            # Increment the new comments counter
                            self.new_comments[story_id] = self.new_comments.get(story_id, 0) + new_count
            except Exception as e:
                # Log error but continue running
                print(f"Background Ask stories monitor error: {e}")

def display_ask_discussions_dashboard(
    initial_stories=None, auto_refresh=True, refresh_interval=60, 
    page_size=10, width=80, notify_new_comments=True
):
    """
    Display a dashboard of active Ask HN discussions with live updates.
    
    Args:
        initial_stories: List of story IDs to initially monitor
        auto_refresh: Whether to auto-refresh stories
        refresh_interval: Refresh interval in seconds
        page_size: Number of discussion items to show per page
        width: Display width
        notify_new_comments: Whether to show notifications
        
    Returns:
        int: Return code (0 for success)
    """
    # Initialize the story monitor
    monitor = AskStoryMonitor(
        story_ids=initial_stories,
        refresh_interval=refresh_interval
    )
    
    # If no initial stories provided, fetch top Ask stories
    if not initial_stories:
        # Fetch top Ask stories
        ask_stories = get_top_ask_stories(20)  # Get top 20
        for story in ask_stories:
            monitor.add_story(story['id'])
    
    # Start the monitor
    monitor.start()
    
    try:
        # Main display loop
        current_page = 1
        selected_idx = 0
        
        while True:
            clear_screen()
            
            # Get the latest story data
            stories_data = monitor.get_all_stories()
            stories_list = list(stories_data.items())
            
            # Sort by new comments (most active discussions first)
            stories_list.sort(
                key=lambda x: (x[1]['new_comments'], x[1]['descendants']), 
                reverse=True
            )
            
            # Calculate pagination
            total_stories = len(stories_list)
            total_pages = max(1, (total_stories + page_size - 1) // page_size)
            
            if current_page > total_pages:
                current_page = total_pages
                
            # Get slice for current page
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_stories)
            page_stories = stories_list[start_idx:end_idx]
            
            # Display header
            if USE_COLORS:
                title = colorize("\n===== Active Ask HN Discussions Dashboard =====", ColorScheme.TITLE)
            else:
                title = "\n===== Active Ask HN Discussions Dashboard ====="
            
            status = f"Page {current_page}/{total_pages} | " + \
                     f"Monitoring {total_stories} discussions | " + \
                     f"Auto-refresh: {refresh_interval}s"
                     
            if USE_COLORS:
                status = colorize(status, ColorScheme.INFO)
            
            print(title)
            print(status)
            print("=" * width)
            
            # Display the stories on current page
            for idx, (story_id, data) in enumerate(page_stories):
                # Calculate display index
                display_idx = start_idx + idx
                
                # Format the entry
                is_selected = (display_idx == selected_idx)
                prefix = ">" if is_selected else " "
                
                # Format title with new comment indicator
                story_title = data['title']
                if data['new_comments'] > 0:
                    new_indicator = f" [+{data['new_comments']} new]"
                    if USE_COLORS:
                        new_indicator = colorize(new_indicator, Colors.GREEN)
                    story_title += new_indicator
                
                if USE_COLORS:
                    title_text = colorize(story_title, ColorScheme.TITLE if is_selected else ColorScheme.HEADER)
                    author = colorize(data['by'], ColorScheme.AUTHOR)
                    score = colorize(str(data['score']), ColorScheme.POINTS)
                    comments = colorize(str(data['descendants']), ColorScheme.COUNT)
                else:
                    title_text = story_title
                    author = data['by']
                    score = str(data['score'])
                    comments = str(data['descendants'])
                
                # Format timestamp
                timestamp = format_timestamp(data['time'])
                
                # Print the entry
                print(f"{prefix} {display_idx+1}. {title_text}")
                print(f"   By {author} | Score: {score} | Comments: {comments} | {timestamp}")
                print()
            
            # Display navigation
            print("=" * width)
            print("Navigation:")
            print("- [up/down] Move selection | [enter] View selected discussion")
            print("- [left/right] Change page | [r] Refresh now")
            print("- [a] Add new story to monitor | [d] Remove selected story")
            print("- [q] Quit dashboard")
            
            # Get user input
            key = getch().lower()
            
            # Handle navigation
            if key == 'q':
                break
            elif key == 'r':
                # Just continue to refresh
                continue
            elif key == 'a':
                # Prompt for story ID to add
                print("\nEnter story ID to add to monitor:")
                try:
                    new_id = int(input("> "))
                    monitor.add_story(new_id)
                    print(f"Added story {new_id} to monitor.")
                    time.sleep(1)  # Brief pause
                except (ValueError, KeyboardInterrupt):
                    print("Cancelled or invalid input.")
                    time.sleep(1)
            elif key == 'd':
                # Remove selected story
                if stories_list and 0 <= selected_idx < len(stories_list):
                    story_id = stories_list[selected_idx][0]
                    monitor.remove_story(story_id)
                    # Adjust selection to avoid going out of bounds
                    if selected_idx >= len(stories_list) - 1:
                        selected_idx = max(0, len(stories_list) - 2)
            elif key in ('\x1b[A', 'k'):  # Up arrow or 'k'
                selected_idx = max(0, selected_idx - 1)
                # Handle page change if selection moves off current page
                if selected_idx < start_idx:
                    current_page = max(1, current_page - 1)
            elif key in ('\x1b[B', 'j'):  # Down arrow or 'j'
                selected_idx = min(total_stories - 1, selected_idx + 1)
                # Handle page change if selection moves off current page
                if selected_idx >= end_idx:
                    current_page = min(total_pages, current_page + 1)
            elif key in ('\x1b[D', 'h'):  # Left arrow or 'h'
                current_page = max(1, current_page - 1)
                # Adjust selection to be on the new page
                selected_idx = (current_page - 1) * page_size
            elif key in ('\x1b[C', 'l'):  # Right arrow or 'l'
                current_page = min(total_pages, current_page + 1)
                # Adjust selection to be on the new page
                selected_idx = (current_page - 1) * page_size
            elif key in ('\r', '\n', ' '):  # Enter or Space
                # View the selected story
                if stories_list and 0 <= selected_idx < len(stories_list):
                    story_id = stories_list[selected_idx][0]
                    
                    # Clear new comments notification for this story
                    monitor.acknowledge_new_comments(story_id)
                    
                    # View the story with comment auto-refresh
                    display_ask_story_details_with_live_comments(
                        story_id,
                        auto_refresh=auto_refresh,
                        refresh_interval=refresh_interval,
                        notify_new_comments=notify_new_comments,
                        page_size=page_size,
                        width=width
                    )
    finally:
        # Clean up
        monitor.stop()
        
    return 0