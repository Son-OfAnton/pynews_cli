"""
Module for simple display of job listings from Hacker News with arrow key navigation
and keyword filtering.
"""
import html
import os
import datetime
import re
import sys
import time
import tty
import termios
from webbrowser import open as url_open
import threading
import queue
from .comments import BackgroundCommentFetcher, display_comments_for_story, fetch_item, format_timestamp
from concurrent.futures import ThreadPoolExecutor, as_completed
from .colors import Colors, ColorScheme, colorize, supports_color
from .getch import getch
from .utils import get_story, get_stories, format_time_ago
from .loading import LoadingIndicator

USE_COLORS = supports_color()

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_absolute_date(timestamp):
    """
    Format a Unix timestamp as an absolute date string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        String formatted as "Month DD, YYYY" (e.g., "July 10, 2024")
    """
    if not timestamp:
        return "Unknown date"
        
    # Convert to datetime
    dt = datetime.datetime.fromtimestamp(timestamp)
    
    # Format the date
    return dt.strftime("%B %d, %Y")

def format_score(score):
    """Format score with visual indicators based on value."""
    if not score:
        return "No score"
        
    if USE_COLORS:
        if score >= 100:
            return colorize(f"⭐ {score} points", Colors.BRIGHT_YELLOW + Colors.BOLD)
        elif score >= 50:
            return colorize(f"⭐ {score} points", Colors.YELLOW + Colors.BOLD)
        elif score >= 25:
            return colorize(f"⭐ {score} points", Colors.GREEN + Colors.BOLD)
        else:
            return colorize(f"⬆ {score} points", ColorScheme.POINTS)
    else:
        if score >= 100:
            return f"*** {score} points ***"
        elif score >= 50:
            return f"** {score} points **"
        elif score >= 25:
            return f"* {score} points *"
        else:
            return f"{score} points"

def extract_company_name(title):
    """
    Extract the company name from a job listing title.
    
    Args:
        title: Job listing title
        
    Returns:
        Tuple of (company_name, cleaned_title)
    """
    # Pattern 1: "Company Name is hiring..."
    is_hiring_match = re.search(r'^(.*?)\s+is\s+hiring', title, re.IGNORECASE)
    if is_hiring_match:
        company = is_hiring_match.group(1).strip()
        return company, title
        
    # Pattern 2: "Company Name (location) is looking for..."
    location_match = re.search(r'^(.*?)\s+\([^)]+\)\s+is', title, re.IGNORECASE)
    if location_match:
        company = location_match.group(1).strip()
        return company, title
        
    # Pattern 3: "Hiring: Position at Company Name"
    hiring_at_match = re.search(r'hiring:?\s+.*?\s+at\s+(.*?)(\s+\(|$|\.)', title, re.IGNORECASE)
    if hiring_at_match:
        company = hiring_at_match.group(1).strip()
        return company, title
        
    # Pattern 4: "Position at Company Name"
    position_at_match = re.search(r'(.*?\s+at\s+)(.*?)(\s+\(|$|\.)', title, re.IGNORECASE)
    if position_at_match:
        company = position_at_match.group(2).strip()
        return company, title
        
    # Pattern 5: "Job Title | Company Name"
    pipe_match = re.search(r'(.*?)\s+\|\s+(.*)', title)
    if pipe_match:
        company = pipe_match.group(2).strip()
        return company, pipe_match.group(1).strip()
        
    # Pattern 6: "Company Name: Job Title" 
    colon_match = re.search(r'^(.*?):\s+(.*)', title)
    if colon_match:
        company = colon_match.group(1).strip()
        return company, colon_match.group(2).strip()

    # Fallback: Couldn't extract a company
    return None, title

def filter_jobs_by_company(jobs, company_name, case_sensitive=False):
    """
    Filter job listings to show only those from a specific company.
    
    Args:
        jobs: List of job dictionaries
        company_name: Company name to filter by
        case_sensitive: Whether to use case-sensitive matching
        
    Returns:
        Filtered list of jobs from the specified company
    """
    if not company_name:
        return jobs
        
    # Prepare company name for comparison
    if not case_sensitive:
        company_name = company_name.lower()
        
    filtered_jobs = []
    
    for job in jobs:
        job_company = job.get('company')
        if job_company:
            # For case-insensitive, convert to lowercase
            if not case_sensitive:
                job_company = job_company.lower()
                
            # Check if the company contains the search term
            if company_name in job_company:
                filtered_jobs.append(job)
                
    return filtered_jobs

def filter_jobs_by_keywords(jobs, keywords, match_all=False, case_sensitive=False):
    """
    Filter job listings based on keywords in the title or text.
    
    Args:
        jobs: List of job dictionaries
        keywords: List of keywords to search for
        match_all: If True, all keywords must match; if False, any keyword can match
        case_sensitive: Whether to use case-sensitive matching
        
    Returns:
        Filtered list of jobs matching the keywords
    """
    if not keywords or not any(keywords):
        return jobs
    
    filtered_jobs = []
    
    for job in jobs:
        title = job.get('title', '')
        text = job.get('text', '')
        
        # Combine title and text for searching
        content = title + ' ' + text
        
        # For case-insensitive search, convert to lowercase
        if not case_sensitive:
            content = content.lower()
            search_keywords = [k.lower() for k in keywords]
        else:
            search_keywords = keywords
        
        # Check if the keywords are in the content
        matches = []
        for keyword in search_keywords:
            if keyword in content:
                matches.append(True)
            else:
                matches.append(False)
        
        # Determine if the job should be included based on matching strategy
        if match_all and all(matches):
            filtered_jobs.append(job)
        elif not match_all and any(matches):
            filtered_jobs.append(job)
    
    return filtered_jobs

def highlight_keywords(text, keywords, case_sensitive=False):
    """
    Highlight keywords in text by adding formatting or markers.
    
    Args:
        text: Text to highlight keywords in
        keywords: List of keywords to highlight
        case_sensitive: Whether to use case-sensitive matching
        
    Returns:
        Text with highlighted keywords
    """
    if not text or not keywords or not any(keywords):
        return text
    
    # For each keyword, highlight it in the text
    highlighted_text = text
    for keyword in keywords:
        if not keyword:
            continue
            
        # Create regex pattern based on case sensitivity
        if case_sensitive:
            pattern = re.compile(f'({re.escape(keyword)})')
        else:
            pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
            
        # Apply highlighting
        if USE_COLORS:
            highlighted_text = pattern.sub(
                lambda m: colorize(m.group(0), Colors.BRIGHT_YELLOW + Colors.BOLD), 
                highlighted_text
            )
        else:
            highlighted_text = pattern.sub(r'*\1*', highlighted_text)
            
    return highlighted_text

def sort_jobs_by_date(jobs, newest_first=True):
    """
    Sort job listings by their posting date.
    
    Args:
        jobs: List of job dictionaries
        newest_first: If True, sort newest jobs first; otherwise oldest first
        
    Returns:
        List of jobs sorted by date
    """
    return sorted(jobs, key=lambda j: j.get('time', 0), reverse=newest_first)

def sort_jobs_by_score(jobs, highest_first=True):
    """
    Sort job listings by their score.
    
    Args:
        jobs: List of job dictionaries
        highest_first: If True, sort highest score first
        
    Returns:
        List of jobs sorted by score
    """
    return sorted(jobs, key=lambda j: j.get('score', 0), reverse=highest_first)

# Special key codes
ARROW_UP = 'A'
ARROW_DOWN = 'B'
ARROW_RIGHT = 'C'
ARROW_LEFT = 'D'
HOME = 'H'
END = 'F'
PAGE_UP = '5~'
PAGE_DOWN = '6~'

def read_key():
    """Read a keypress and return the character or special key code."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # ESC
            # Read the next two characters
            ch1 = sys.stdin.read(1)
            if ch1 == '[':
                ch2 = sys.stdin.read(1)
                if ch2 in ['A', 'B', 'C', 'D', 'H', 'F']:
                    return ch2  # Return just the code character
                elif ch2 == '5' or ch2 == '6':
                    sys.stdin.read(1)  # Read the tilde
                    return ch2 + '~'
                else:
                    return ch + ch1 + ch2
            else:
                return ch + ch1
        else:
            return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def prompt_for_input(prompt_text):
    """
    Display a prompt and get user input, temporarily exiting raw mode.
    
    Args:
        prompt_text: Text to display as prompt
        
    Returns:
        User input string
    """
    # Exit raw mode to get normal input behavior
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if USE_COLORS:
            print(colorize(prompt_text, ColorScheme.PROMPT))
        else:
            print(prompt_text)
        return input("> ").strip()
    finally:
        tty.setraw(fd)

def display_job_listings(limit=20, page_size=10, sort_newest_first=True, sort_by_score=False, 
                        company_filter=None, min_score=None, keywords=None, match_all=False,
                        case_sensitive=False):
    """
    Display a simplified list of job listings from Hacker News with arrow key navigation
    and keyword filtering.
    
    Args:
        limit: Maximum number of jobs to fetch
        page_size: Number of jobs to display per page
        sort_newest_first: Whether to sort jobs with newest first (default: True)
        sort_by_score: Whether to sort by score instead of date
        company_filter: Optional company name to filter job listings by
        min_score: Optional minimum score threshold for jobs to display
        keywords: Optional list of keywords to filter by
        match_all: If True, all keywords must match; if False, any keyword can match
        case_sensitive: Whether keyword matching should be case-sensitive
    """
    from .loading import LoadingIndicator
    
    # Fetch job story IDs
    loader = LoadingIndicator(message="Fetching job listings...")
    loader.start()
    try:
        job_ids = get_stories("job")
        if not job_ids:
            if USE_COLORS:
                print(colorize("\nNo job listings found.", ColorScheme.ERROR))
            else:
                print("\nNo job listings found.")
            return
    finally:
        loader.stop()
    
    # Fetch job details
    loader = LoadingIndicator(message="Loading job details...")
    loader.start()
    try:
        jobs = []
        for job_id in job_ids[:min(limit * 3, len(job_ids))]:  # Fetch more to allow for filtering
            job = get_story(job_id)
            if job:  # Make sure we have a valid job
                # Extract company name and add to job data
                company, position = extract_company_name(job.get('title', ''))
                job['company'] = company
                job['position'] = position
                jobs.append(job)
    finally:
        loader.stop()
    
    # Apply keyword filtering if specified
    if keywords and any(keywords):
        original_count = len(jobs)
        jobs = filter_jobs_by_keywords(jobs, keywords, match_all=match_all, case_sensitive=case_sensitive)
        filtered_count = len(jobs)
        
        if filtered_count == 0:
            if USE_COLORS:
                if match_all:
                    print(colorize(f"\nNo job listings found matching ALL keywords: {', '.join(keywords)}.", 
                                ColorScheme.ERROR))
                else:
                    print(colorize(f"\nNo job listings found matching ANY of: {', '.join(keywords)}.", 
                                ColorScheme.ERROR))
            else:
                if match_all:
                    print(f"\nNo job listings found matching ALL keywords: {', '.join(keywords)}.")
                else:
                    print(f"\nNo job listings found matching ANY of: {', '.join(keywords)}.")
            return
    
    # Apply score filtering if specified
    if min_score is not None and min_score > 0:
        original_count = len(jobs)
        jobs = [j for j in jobs if j.get('score', 0) >= min_score]
        filtered_count = len(jobs)
        
        if filtered_count == 0:
            if USE_COLORS:
                print(colorize(f"\nNo job listings found with score {min_score} or higher.", 
                               ColorScheme.ERROR))
            else:
                print(f"\nNo job listings found with score {min_score} or higher.")
            return
    
    # Apply company filtering if specified
    if company_filter:
        original_count = len(jobs)
        jobs = filter_jobs_by_company(jobs, company_filter, case_sensitive=False)
        filtered_count = len(jobs)
        
        if filtered_count == 0:
            if USE_COLORS:
                print(colorize(f"\nNo job listings found matching company '{company_filter}'.", 
                               ColorScheme.ERROR))
            else:
                print(f"\nNo job listings found matching company '{company_filter}'.")
            return
    
    # Sort jobs by selected criterion
    if sort_by_score:
        jobs = sort_jobs_by_score(jobs, highest_first=True)
    else:
        jobs = sort_jobs_by_date(jobs, newest_first=sort_newest_first)
    
    # Limit to the requested number after filtering
    jobs = jobs[:min(limit, len(jobs))]
    
    # Display jobs in a paginated list
    current_page = 1
    total_pages = max(1, (len(jobs) + page_size - 1) // page_size)
    
    # Keep track of sorting parameters and filters
    newest_first = sort_newest_first
    is_sort_by_score = sort_by_score
    current_company_filter = company_filter
    current_min_score = min_score
    current_keywords = keywords or []
    current_match_all = match_all
    
    # Track the currently selected job
    selected_idx = 0
    
    while True:
        clear_screen()
        
        # Determine sort display text
        if is_sort_by_score:
            sort_info = "by highest score"
        else:
            sort_info = "newest first" if newest_first else "oldest first" 
        
        if USE_COLORS:
            header = colorize(f"Hacker News Jobs (Page {current_page}/{total_pages})", 
                              ColorScheme.TITLE)
            sort_display = colorize(f" - Sorted: {sort_info}", ColorScheme.INFO)
            
            filters = []
            if current_company_filter:
                filters.append(f"company: '{current_company_filter}'")
            if current_min_score is not None and current_min_score > 0:
                filters.append(f"min score: {current_min_score}")
            if current_keywords and any(current_keywords):
                match_type = "ALL" if current_match_all else "ANY"
                keywords_display = f"keywords ({match_type}): {', '.join(current_keywords)}"
                filters.append(keywords_display)
                
            if filters:
                filter_display = colorize(f" - Filtered by {', '.join(filters)}", ColorScheme.INFO)
                print(f"\n{header}{sort_display}{filter_display}")
            else:
                print(f"\n{header}{sort_display}")
                
            print(colorize("=" * 80, ColorScheme.HEADER))
        else:
            header_text = f"\nHacker News Jobs (Page {current_page}/{total_pages}) - Sorted: {sort_info}"
            filters = []
            if current_company_filter:
                filters.append(f"company: '{current_company_filter}'")
            if current_min_score is not None and current_min_score > 0:
                filters.append(f"min score: {current_min_score}")
            if current_keywords and any(current_keywords):
                match_type = "ALL" if current_match_all else "ANY"
                keywords_display = f"keywords ({match_type}): {', '.join(current_keywords)}"
                filters.append(keywords_display)
            
            if filters:
                header_text += f" - Filtered by {', '.join(filters)}"
            print(header_text)
            print("=" * 80)
        
        # Calculate slice for current page
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        current_jobs = jobs[start_idx:end_idx]
        
        # Display jobs
        for i, job in enumerate(current_jobs):
            # Determine if this job is selected
            is_selected = i == selected_idx
            
            # Get job information
            title = job.get('title', 'Untitled Job Listing')
            url = job.get('url', '')
            text = job.get('text', '')
            timestamp = job.get('time', 0)
            time_ago = format_time_ago(timestamp)
            absolute_date = format_absolute_date(timestamp)
            company = job.get('company')
            score = job.get('score', 0)
            
            # Apply keyword highlighting if applicable
            if current_keywords and any(current_keywords):
                title = highlight_keywords(title, current_keywords, case_sensitive)
            
            # If no external URL, use the HN link
            if not url:
                url = f"https://news.ycombinator.com/item?id={job.get('id')}"
            
            # Format job listing with selection highlighting
            if USE_COLORS:
                job_num = colorize(f"{start_idx + i + 1}.", ColorScheme.COUNT)
                
                # Use different formatting based on selection state
                if is_selected:
                    # Format the selected job with a distinct highlight
                    # Note: We don't apply BG_BLUE to the title if it has keywords highlighted
                    if current_keywords and any(current_keywords):
                        job_title = colorize(f"➤ ", Colors.BRIGHT_WHITE + Colors.BOLD + Colors.BG_BLUE) + title
                    else:
                        job_title = colorize(f"➤ {title}", Colors.BRIGHT_WHITE + Colors.BOLD + Colors.BG_BLUE)
                    
                    job_score = colorize(format_score(score), Colors.BOLD)
                    job_date = colorize(f"📅 Posted on: {absolute_date} ({time_ago})", ColorScheme.TIME + Colors.BOLD)
                    
                    # Display job info with score and company if available
                    print(f"\n{job_num} {job_title}")
                    print(f"   {job_score}")
                    
                    # Display company info if available
                    if company:
                        company_info = colorize(f"🏢 Company: {company}", ColorScheme.AUTHOR + Colors.BOLD)
                        print(f"   {company_info}")
                        
                    print(f"   {job_date}")
                    print(f"   URL: {colorize(url, ColorScheme.URL + Colors.BOLD)}")
                else:
                    # Format non-selected jobs normally
                    if current_keywords and any(current_keywords):
                        job_title = title  # Already has highlighting applied
                    else:
                        job_title = colorize(title, ColorScheme.HEADER)
                        
                    job_score = format_score(score)
                    job_date = colorize(f"📅 Posted on: {absolute_date}  ({time_ago})", ColorScheme.TIME)
                    
                    # Display job info with score and company if available
                    print(f"\n{job_num} {job_title}")
                    print(f"   {job_score}")
                    
                    # Display company info if available
                    if company:
                        company_info = colorize(f"🏢 Company: {company}", ColorScheme.AUTHOR)
                        print(f"   {company_info}")
                        
                    print(f"   {job_date}")
                    print(f"   URL: {colorize(url, ColorScheme.URL)}")
            else:
                # Non-color formatting with selection indicator
                if is_selected:
                    print(f"\n{start_idx + i + 1}. ➤ {title}")
                else:
                    print(f"\n{start_idx + i + 1}. {title}")
                
                print(f"   {format_score(score)}")
                
                if company:
                    print(f"   🏢 Company: {company}")
                    
                print(f"   📅 Posted on: {absolute_date} ({time_ago})")
                print(f"   URL: {url}")
            
            # Display a snippet of the job description text if available
            if text and is_selected:
                # Clean up the text (remove HTML)
                cleaned_text = re.sub(r'<[^>]+>', ' ', text)
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                
                # Truncate to a reasonable length
                if len(cleaned_text) > 200:
                    cleaned_text = cleaned_text[:197] + "..."
                
                # Highlight keywords in the text if applicable
                if current_keywords and any(current_keywords):
                    cleaned_text = highlight_keywords(cleaned_text, current_keywords, case_sensitive)
                
                if USE_COLORS:
                    print(f"   {colorize('Description: ', ColorScheme.SUBHEADER)}{cleaned_text}")
                else:
                    print(f"   Description: {cleaned_text}")
        
        # Display navigation instructions
        if USE_COLORS:
            print(colorize("\n" + "=" * 80, ColorScheme.HEADER))
            print(colorize("Navigation:", ColorScheme.NAV_HEADER))
        else:
            print("\n" + "=" * 80)
            print("Navigation:")
        
        # Navigation options
        if USE_COLORS:
            print(colorize("Arrow Keys: ↑/↓ Navigate jobs, ←/→ Change page", ColorScheme.NAV_ACTIVE))
            print(colorize("Enter: Open selected job in browser", ColorScheme.NAV_ACTIVE))
            print(colorize("Home/End: Jump to first/last job on page", ColorScheme.NAV_ACTIVE))
            print(colorize("PgUp/PgDn: Go to previous/next page", ColorScheme.NAV_ACTIVE))
        else:
            print("Arrow Keys: ↑/↓ Navigate jobs, ←/→ Change page")
            print("Enter: Open selected job in browser")
            print("Home/End: Jump to first/last job on page") 
            print("PgUp/PgDn: Go to previous/next page")
            
        # Sort and filter options
        if USE_COLORS:
            print(colorize("\nSort and Filter:", ColorScheme.NAV_HEADER))
            
            sort_toggle = colorize(f"[t] Toggle sort: {'by score' if not is_sort_by_score else 'by date'}", 
                                 ColorScheme.NAV_ACTIVE)
            print(sort_toggle)
            
            # Date sort order toggle (only available when sorting by date)
            if not is_sort_by_score:
                sort_option = colorize(f"[d] Sort by date: {'newest first' if newest_first else 'oldest first'}", 
                                      ColorScheme.NAV_ACTIVE)
                print(sort_option)
            
            # Filter by keywords
            keyword_option = "[k] Filter by keywords"
            if current_keywords and any(current_keywords):
                match_type = "ALL" if current_match_all else "ANY"
                keyword_option += f" (current: {match_type} of {', '.join(current_keywords)})"
            print(colorize(keyword_option, ColorScheme.NAV_ACTIVE))
            
            # Toggle keyword match type
            if current_keywords and any(current_keywords):
                match_toggle = f"[m] Toggle match type: currently {('ALL' if current_match_all else 'ANY')}"
                print(colorize(match_toggle, ColorScheme.NAV_ACTIVE))
            
            # Filter by company
            filter_option = "[f] Filter by company" 
            if current_company_filter:
                filter_option += f" (current: '{current_company_filter}')"
            print(colorize(filter_option, ColorScheme.NAV_ACTIVE))
            
            # Filter by minimum score
            score_option = "[s] Set minimum score"
            if current_min_score is not None and current_min_score > 0:
                score_option += f" (current: {current_min_score})"
            print(colorize(score_option, ColorScheme.NAV_ACTIVE))
            
            # Clear filters option (if any active)
            has_filters = (current_company_filter or (current_min_score is not None and current_min_score > 0) or 
                          (current_keywords and any(current_keywords)))
            if has_filters:
                clear_filter = "[c] Clear all filters"
                print(colorize(clear_filter, ColorScheme.NAV_ACTIVE))
            
            # Exit option
            print(colorize("\n[q] Return to main menu", ColorScheme.NAV_ACTIVE))
            
        else:
            print("\nSort and Filter:")
            print(f"[t] Toggle sort: {'by score' if not is_sort_by_score else 'by date'}")
            
            if not is_sort_by_score:
                print(f"[d] Sort by date: {'newest first' if newest_first else 'oldest first'}")
            
            # Filter by keywords
            keyword_option = "[k] Filter by keywords"
            if current_keywords and any(current_keywords):
                match_type = "ALL" if current_match_all else "ANY"
                keyword_option += f" (current: {match_type} of {', '.join(current_keywords)})"
            print(keyword_option)
            
            # Toggle keyword match type
            if current_keywords and any(current_keywords):
                match_toggle = f"[m] Toggle match type: currently {('ALL' if current_match_all else 'ANY')}"
                print(match_toggle)
            
            filter_option = "[f] Filter by company" 
            if current_company_filter:
                filter_option += f" (current: '{current_company_filter}')"
            print(filter_option)
            
            score_option = "[s] Set minimum score"
            if current_min_score is not None and current_min_score > 0:
                score_option += f" (current: {current_min_score})"
            print(score_option)
            
            has_filters = (current_company_filter or (current_min_score is not None and current_min_score > 0) or 
                         (current_keywords and any(current_keywords)))
            if has_filters:
                print("[c] Clear all filters")
                
            print("\n[q] Return to main menu")
        
        # Get user input using arrow keys
        key = read_key()
        
        # Handle navigation
        if key == 'q':
            return {'action': 'return_to_menu'}
        elif key == ARROW_UP:  # Up arrow
            selected_idx = max(0, selected_idx - 1)
        elif key == ARROW_DOWN:  # Down arrow
            selected_idx = min(len(current_jobs) - 1, selected_idx + 1)
        elif key == ARROW_LEFT or key == PAGE_UP:  # Left arrow or Page Up
            if current_page > 1:
                current_page -= 1
                selected_idx = 0  # Reset selection for new page
        elif key == ARROW_RIGHT or key == PAGE_DOWN:  # Right arrow or Page Down
            if current_page < total_pages:
                current_page += 1
                selected_idx = 0  # Reset selection for new page
        elif key == HOME:  # Home key
            selected_idx = 0
        elif key == END:  # End key
            selected_idx = len(current_jobs) - 1
        elif key == '\r' or key == '\n':  # Enter key
            # Open the selected job in browser
            if 0 <= selected_idx < len(current_jobs):
                job = current_jobs[selected_idx]
                url = job.get('url', '')
                if not url:
                    url = f"https://news.ycombinator.com/item?id={job.get('id')}"
                url_open(url)
        elif key == 'k':
            # Prompt for keyword filtering
            try:
                keyword_input = prompt_for_input("\nEnter keywords to filter by (space-separated, or press Enter to cancel):")
                if keyword_input:
                    # Convert to list of keywords (split by spaces)
                    new_keywords = [k.strip() for k in keyword_input.split()]
                    if new_keywords:
                        current_keywords = new_keywords
                        
                        # Reload all jobs and apply all filters
                        jobs = []
                        loader = LoadingIndicator(message="Applying keyword filter...")
                        loader.start()
                        try:
                            for job_id in job_ids[:min(limit * 3, len(job_ids))]:
                                job = get_story(job_id)
                                if job:
                                    company, position = extract_company_name(job.get('title', ''))
                                    job['company'] = company
                                    job['position'] = position
                                    jobs.append(job)
                                    
                            #  Apply all active filters
                            jobs = filter_jobs_by_keywords(
                                jobs, 
                                current_keywords, 
                                match_all=current_match_all, 
                                case_sensitive=case_sensitive
                            )
                            
                            if current_min_score is not None and current_min_score > 0:
                                jobs = [j for j in jobs if j.get('score', 0) >= current_min_score]
                                
                            if current_company_filter:
                                jobs = filter_jobs_by_company(jobs, current_company_filter)
                            
                        finally:
                            loader.stop()
                            
                        if not jobs:
                            if USE_COLORS:
                                match_type = "ALL" if current_match_all else "ANY"
                                print(colorize(f"\nNo jobs found matching {match_type} keywords: {', '.join(current_keywords)}",
                                             ColorScheme.ERROR))
                                print(colorize("Press any key to continue...", ColorScheme.PROMPT))
                            else:
                                match_type = "ALL" if current_match_all else "ANY"
                                print(f"\nNo jobs found matching {match_type} keywords: {', '.join(current_keywords)}")
                                print("Press any key to continue...")
                            read_key()  # Wait for keypress
                            
                            # Revert to previous keywords
                            current_keywords = []
                                
                            # Reload all jobs again without keyword filter
                            jobs = []
                            loader = LoadingIndicator(message="Reloading jobs...")
                            loader.start()
                            try:
                                for job_id in job_ids[:min(limit * 3, len(job_ids))]:
                                    job = get_story(job_id)
                                    if job:
                                        company, position = extract_company_name(job.get('title', ''))
                                        job['company'] = company
                                        job['position'] = position
                                        jobs.append(job)
                                        
                                # Apply remaining active filters
                                if current_min_score is not None and current_min_score > 0:
                                    jobs = [j for j in jobs if j.get('score', 0) >= current_min_score]
                                    
                                if current_company_filter:
                                    jobs = filter_jobs_by_company(jobs, current_company_filter)
                            finally:
                                loader.stop()
                        else:
                            # Sort the filtered results
                            if is_sort_by_score:
                                jobs = sort_jobs_by_score(jobs)
                            else:
                                jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
                                
                            # Limit to requested number
                            jobs = jobs[:min(limit, len(jobs))]
                
                        # Reset page and selection
                        current_page = 1
                        selected_idx = 0
                        total_pages = max(1, (len(jobs) + page_size - 1) // page_size)
            except Exception as e:
                if USE_COLORS:
                    print(colorize(f"\nError processing keywords: {e}", ColorScheme.ERROR))
                    print(colorize("Press any key to continue...", ColorScheme.PROMPT))
                else:
                    print(f"\nError processing keywords: {e}")
                    print("Press any key to continue...")
                read_key()  # Wait for keypress
                
        elif key == 'm' and current_keywords and any(current_keywords):
            # Toggle between 'any' and 'all' keyword matching
            current_match_all = not current_match_all
            
            # Reapply keyword filter with new match type
            loader = LoadingIndicator(message=f"Updating to match {('ALL' if current_match_all else 'ANY')} keywords...")
            loader.start()
            try:
                # Reload all jobs
                jobs = []
                for job_id in job_ids[:min(limit * 3, len(job_ids))]:
                    job = get_story(job_id)
                    if job:
                        company, position = extract_company_name(job.get('title', ''))
                        job['company'] = company
                        job['position'] = position
                        jobs.append(job)
                        
                # Apply all filters with new match type
                jobs = filter_jobs_by_keywords(
                    jobs, 
                    current_keywords, 
                    match_all=current_match_all, 
                    case_sensitive=case_sensitive
                )
                
                if current_min_score is not None and current_min_score > 0:
                    jobs = [j for j in jobs if j.get('score', 0) >= current_min_score]
                    
                if current_company_filter:
                    jobs = filter_jobs_by_company(jobs, current_company_filter)
            finally:
                loader.stop()
                
            if not jobs:
                if USE_COLORS:
                    match_type = "ALL" if current_match_all else "ANY"
                    print(colorize(f"\nNo jobs found matching {match_type} keywords: {', '.join(current_keywords)}",
                                 ColorScheme.ERROR))
                    print(colorize("Press any key to continue...", ColorScheme.PROMPT))
                else:
                    match_type = "ALL" if current_match_all else "ANY"
                    print(f"\nNo jobs found matching {match_type} keywords: {', '.join(current_keywords)}")
                    print("Press any key to continue...")
                read_key()  # Wait for keypress
                
                # Revert to previous match type
                current_match_all = not current_match_all
                
                # Reload with previous match type
                loader = LoadingIndicator(message="Reverting to previous filter...")
                loader.start()
                try:
                    jobs = []
                    for job_id in job_ids[:min(limit * 3, len(job_ids))]:
                        job = get_story(job_id)
                        if job:
                            company, position = extract_company_name(job.get('title', ''))
                            job['company'] = company
                            job['position'] = position
                            jobs.append(job)
                            
                    # Re-apply all filters with original match type
                    jobs = filter_jobs_by_keywords(
                        jobs, 
                        current_keywords, 
                        match_all=current_match_all, 
                        case_sensitive=case_sensitive
                    )
                    
                    if current_min_score is not None and current_min_score > 0:
                        jobs = [j for j in jobs if j.get('score', 0) >= current_min_score]
                        
                    if current_company_filter:
                        jobs = filter_jobs_by_company(jobs, current_company_filter)
                finally:
                    loader.stop()
            else:
                # Sort and limit the results
                if is_sort_by_score:
                    jobs = sort_jobs_by_score(jobs)
                else:
                    jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
                    
                # Limit to requested number
                jobs = jobs[:min(limit, len(jobs))]
                
                # Reset page and selection
                current_page = 1
                selected_idx = 0
                total_pages = max(1, (len(jobs) + page_size - 1) // page_size)
                
        elif key == 't':
            # Toggle between sorting by score and by date
            is_sort_by_score = not is_sort_by_score
            
            # Re-sort the jobs
            if is_sort_by_score:
                jobs = sort_jobs_by_score(jobs)
            else:
                jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
                
            # Reset to first page and selection
            current_page = 1
            selected_idx = 0
        elif key == 'd' and not is_sort_by_score:
            # Toggle sort order for dates (only when sorting by date)
            newest_first = not newest_first
            
            # Re-sort the jobs
            jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
            
            # Reset to first page and selection
            current_page = 1
            selected_idx = 0
        elif key == 'f':
            # Prompt for company filter
            try:
                new_filter = prompt_for_input("\nEnter company name to filter by (or press Enter to cancel):")
                if new_filter:
                    current_company_filter = new_filter
                    # Reload all jobs and apply the filter
                    jobs = []
                    loader = LoadingIndicator(message="Reloading job listings...")
                    loader.start()
                    try:
                        for job_id in job_ids[:min(limit * 3, len(job_ids))]:
                            job = get_story(job_id)
                            if job:
                                company, position = extract_company_name(job.get('title', ''))
                                job['company'] = company
                                job['position'] = position
                                jobs.append(job)
                    finally:
                        loader.stop()
                    
                    # Apply all filters
                    if current_keywords and any(current_keywords):
                        jobs = filter_jobs_by_keywords(
                            jobs, 
                            current_keywords, 
                            match_all=current_match_all, 
                            case_sensitive=case_sensitive
                        )
                        
                    if current_min_score is not None and current_min_score > 0:
                        jobs = [j for j in jobs if j.get('score', 0) >= current_min_score]
                        
                    jobs = filter_jobs_by_company(jobs, current_company_filter)
                    
                    # Apply the current sort
                    if is_sort_by_score:
                        jobs = sort_jobs_by_score(jobs)
                    else:
                        jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
                        
                    # Limit to the requested number
                    jobs = jobs[:min(limit, len(jobs))]
                    
                    # Reset page and selection
                    current_page = 1
                    selected_idx = 0
                    total_pages = max(1, (len(jobs) + page_size - 1) // page_size)
            except Exception as e:
                if USE_COLORS:
                    print(colorize(f"\nError reading input: {e}", ColorScheme.ERROR))
                    print(colorize("Press any key to continue...", ColorScheme.PROMPT))
                else:
                    print(f"\nError reading input: {e}")
                    print("Press any key to continue...")
                read_key()  # Wait for keypress
                    
        elif key == 's':
            # Prompt for minimum score
            try:
                score_input = prompt_for_input("\nEnter minimum score (or press Enter to cancel):")
                if score_input:
                    try:
                        new_min_score = int(score_input)
                        if new_min_score > 0:
                            current_min_score = new_min_score
                            
                            # Reload all jobs and apply the filter
                            jobs = []
                            loader = LoadingIndicator(message="Reloading job listings...")
                            loader.start()
                            try:
                                for job_id in job_ids[:min(limit * 3, len(job_ids))]:
                                    job = get_story(job_id)
                                    if job:
                                        company, position = extract_company_name(job.get('title', ''))
                                        job['company'] = company
                                        job['position'] = position
                                        jobs.append(job)
                            finally:
                                loader.stop()
                            
                            # Apply all filters
                            if current_keywords and any(current_keywords):
                                jobs = filter_jobs_by_keywords(
                                    jobs, 
                                    current_keywords, 
                                    match_all=current_match_all, 
                                    case_sensitive=case_sensitive
                                )
                            
                            jobs = [j for j in jobs if j.get('score', 0) >= current_min_score]
                            
                            if current_company_filter:
                                jobs = filter_jobs_by_company(jobs, current_company_filter)
                            
                            # Apply the current sort
                            if is_sort_by_score:
                                jobs = sort_jobs_by_score(jobs)
                            else:
                                jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
                                
                            # Limit to the requested number
                            jobs = jobs[:min(limit, len(jobs))]
                            
                            # Reset page and selection
                            current_page = 1
                            selected_idx = 0
                            total_pages = max(1, (len(jobs) + page_size - 1) // page_size)
                    except ValueError:
                        if USE_COLORS:
                            print(colorize("\nInvalid number. Please enter a positive integer.", ColorScheme.ERROR))
                            print(colorize("Press any key to continue...", ColorScheme.PROMPT))
                        else:
                            print("\nInvalid number. Please enter a positive integer.")
                            print("Press any key to continue...")
                        read_key()  # Wait for keypress
            except Exception as e:
                if USE_COLORS:
                    print(colorize(f"\nError reading input: {e}", ColorScheme.ERROR))
                    print(colorize("Press any key to continue...", ColorScheme.PROMPT))
                else:
                    print(f"\nError reading input: {e}")
                    print("Press any key to continue...")
                read_key()  # Wait for keypress
                    
        elif key == 'c' and (current_company_filter or 
                           (current_min_score is not None and current_min_score > 0) or
                           (current_keywords and any(current_keywords))):
            # Clear all filters
            current_company_filter = None
            current_min_score = None
            current_keywords = []
            
            # Reload all jobs without filtering
            jobs = []
            loader = LoadingIndicator(message="Reloading job listings...")
            loader.start()
            try:
                for job_id in job_ids[:min(limit, len(job_ids))]:
                    job = get_story(job_id)
                    if job:
                        company, position = extract_company_name(job.get('title', ''))
                        job['company'] = company
                        job['position'] = position
                        jobs.append(job)
            finally:
                loader.stop()
            
            # Apply the current sort
            if is_sort_by_score:
                jobs = sort_jobs_by_score(jobs)
            else:
                jobs = sort_jobs_by_date(jobs, newest_first=newest_first)
            
            # Reset page and selection
            current_page = 1
            selected_idx = 0
            total_pages = max(1, (len(jobs) + page_size - 1) // page_size)

# Add a new function to handle job listings with live comments
def display_job_details_with_live_comments(job_id, auto_refresh=False, refresh_interval=60, notify_new_comments=False, page_size=10, width=80):
    """
    Display details for a job listing with comments that update in the background.
    
    Args:
        job_id: ID of the job listing
        auto_refresh: Whether to auto-refresh comments
        refresh_interval: Interval in seconds between updates
        notify_new_comments: Whether to show notifications for new comments
        page_size: Number of comments to show per page
        width: Display width for formatting
        
    Returns:
        Dict with action and parameters, or None
    """
    # Fetch the job data
    job = fetch_item(job_id)
    if not job:
        error_msg = f"Error: Could not retrieve job with ID {job_id}"
        if USE_COLORS:
            error_msg = colorize(error_msg, ColorScheme.ERROR)
        print(error_msg)
        return None
    
    # Display the job details
    clear_screen()
    
    # Format job title
    if USE_COLORS:
        title_text = colorize(f"\n=== {job.get('title', 'Job Listing')} ===", ColorScheme.TITLE)
    else:
        title_text = f"\n=== {job.get('title', 'Job Listing')} ==="
    
    print(title_text)
    
    # Format job information
    if 'by' in job:
        if USE_COLORS:
            author = colorize(job['by'], ColorScheme.AUTHOR)
        else:
            author = job['by']
        print(f"Posted by: {author}")
    
    # Format timestamp
    if 'time' in job:
        print(f"Posted: {format_timestamp(job.get('time', 0))}")
    
    # Format score
    if 'score' in job:
        if USE_COLORS:
            score = colorize(str(job['score']), ColorScheme.POINTS)
        else:
            score = str(job['score'])
        print(f"Score: {score}")
    
    # Format URL
    if 'url' in job:
        if USE_COLORS:
            url = colorize(job['url'], ColorScheme.URL)
        else:
            url = job['url']
        print(f"URL: {url}")
    
    # Format job description/text
    if 'text' in job:
        print("\n" + "-" * 40)
        job_text = clean_html(job['text'])
        print(job_text)
        print("-" * 40)
    
    # Display information about comments
    comment_ids = job.get('kids', [])
    comment_count = len(comment_ids)
    
    comment_info = f"\nThis job listing has {comment_count} " + \
                   ("comment" if comment_count == 1 else "comments")
    if USE_COLORS:
        comment_info = colorize(comment_info, ColorScheme.INFO)
    print(comment_info)
    
    # Show options
    print("\nOptions:")
    print("1. View comments")
    print("2. Return to job listings")
    
    while True:
        choice = getch()
        
        if choice == '1':
            # View comments with background refreshing
            display_comments_for_story(
                job_id,
                page_size=page_size,
                width=width,
                auto_refresh=auto_refresh,
                refresh_interval=refresh_interval,
                notify_new_comments=notify_new_comments
            )
            return {'action': 'view_comments'}
        
        elif choice == '2':
            return {'action': 'return_to_list'}
        
class JobMonitor:
    """
    Class to monitor multiple job listings for new comments in the background.
    Provides a dashboard-like functionality for tracking discussions on job postings.
    """
    
    def __init__(self, job_ids=None, refresh_interval=60):
        """
        Initialize the job listings monitor.
        
        Args:
            job_ids: List of job listing IDs to monitor (can be empty and added later)
            refresh_interval: Refresh interval in seconds
        """
        self.job_ids = set(job_ids or [])
        self.refresh_interval = max(refresh_interval, 10)
        self.running = False
        self.thread = None
        self.job_data_lock = threading.Lock()
        self.job_data = {}  # Dict mapping job_id to job data
        self.new_comments = {}  # Dict mapping job_id to count of new comments
        
    def start(self):
        """Start the background monitoring thread."""
        if self.running:
            return False
            
        # Fetch initial data for all jobs
        self._fetch_initial_data()
        
        # Start background thread
        self.running = True
        self.thread = threading.Thread(target=self._background_monitor, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Stop the background monitoring thread."""
        if not self.running:
            return False
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)  # Wait up to 1 second for thread to exit
            self.thread = None
        return True
    
    def add_job(self, job_id):
        """Add a job listing to the monitor."""
        if job_id in self.job_ids:
            return False
            
        with self.job_data_lock:
            self.job_ids.add(job_id)
            
            # Fetch initial data for this job
            job = fetch_item(job_id)
            if job:
                comment_count = len(job.get('kids', []))
                
                self.job_data[job_id] = {
                    'title': job.get('title', 'Unknown Job'),
                    'by': job.get('by', 'Unknown'),
                    'time': job.get('time', 0),
                    'score': job.get('score', 0),
                    'url': job.get('url', ''),
                    'comment_ids': set(job.get('kids', [])),
                    'last_comment_count': comment_count
                }
                self.new_comments[job_id] = 0
            
        return True
    
    def remove_job(self, job_id):
        """Remove a job listing from the monitor."""
        if job_id not in self.job_ids:
            return False
            
        with self.job_data_lock:
            self.job_ids.remove(job_id)
            if job_id in self.job_data:
                del self.job_data[job_id]
            if job_id in self.new_comments:
                del self.new_comments[job_id]
            
        return True
        
    def get_all_jobs(self):
        """Get all currently monitored jobs with their data."""
        with self.job_data_lock:
            # Create a deep copy to avoid thread safety issues
            result = {}
            for job_id, data in self.job_data.items():
                result[job_id] = dict(data)
                result[job_id]['new_comments'] = self.new_comments.get(job_id, 0)
                
        return result
    
    def get_job(self, job_id):
        """Get data for a specific job including new comment count."""
        with self.job_data_lock:
            if job_id not in self.job_data:
                return None
                
            result = dict(self.job_data[job_id])
            result['new_comments'] = self.new_comments.get(job_id, 0)
            
        return result
    
    def acknowledge_new_comments(self, job_id):
        """Acknowledge and clear new comment notification for a job."""
        with self.job_data_lock:
            if job_id not in self.new_comments:
                return False
                
            self.new_comments[job_id] = 0
            
        return True
    
    def _fetch_initial_data(self):
        """Fetch initial data for all jobs in the monitor."""
        with self.job_data_lock:
            for job_id in list(self.job_ids):
                job = fetch_item(job_id)
                if not job:
                    self.job_ids.remove(job_id)
                    continue
                    
                comment_count = len(job.get('kids', []))
                
                self.job_data[job_id] = {
                    'title': job.get('title', 'Unknown Job'),
                    'by': job.get('by', 'Unknown'),
                    'time': job.get('time', 0),
                    'score': job.get('score', 0),
                    'url': job.get('url', ''),
                    'comment_ids': set(job.get('kids', [])),
                    'last_comment_count': comment_count
                }
                self.new_comments[job_id] = 0
    
    def _background_monitor(self):
        """Background thread function to monitor jobs for new comments."""
        while self.running:
            try:
                # Sleep to avoid excessive API requests
                time.sleep(self.refresh_interval)
                
                if not self.running:  # Check if we should exit
                    break
                    
                # Make a copy of job IDs to avoid thread safety issues
                with self.job_data_lock:
                    job_ids_to_check = list(self.job_ids)
                
                # Check each job for updates
                for job_id in job_ids_to_check:
                    if not self.running:  # Check if we should exit
                        break
                        
                    updated_job = fetch_item(job_id)
                    if not updated_job:
                        continue
                        
                    with self.job_data_lock:
                        # Skip if job was removed while we were checking
                        if job_id not in self.job_data:
                            continue
                            
                        # Get current data
                        current_data = self.job_data[job_id]
                        
                        # Get updated comment IDs
                        updated_comment_ids = set(updated_job.get('kids', []))
                        current_comment_ids = current_data.get('comment_ids', set())
                        
                        # Calculate new comments
                        new_comments = updated_comment_ids - current_comment_ids
                        new_count = len(new_comments)
                        
                        # Update data if there are changes
                        if new_count > 0:
                            # Update stored data
                            current_data['comment_ids'] = updated_comment_ids
                            current_data['last_comment_count'] = len(updated_comment_ids)
                            
                            # Increment the new comments counter
                            self.new_comments[job_id] = self.new_comments.get(job_id, 0) + new_count
            except Exception as e:
                # Log error but continue running
                print(f"Background job listings monitor error: {e}")

def display_jobs_discussion_dashboard(
    initial_jobs=None, auto_refresh=True, refresh_interval=60, 
    page_size=10, width=80, notify_new_comments=True
):
    """
    Display a dashboard of job listings with discussion activity.
    
    Args:
        initial_jobs: List of job IDs to initially monitor
        auto_refresh: Whether to auto-refresh jobs
        refresh_interval: Refresh interval in seconds
        page_size: Number of jobs to show per page
        width: Display width
        notify_new_comments: Whether to show notifications
        
    Returns:
        int: Return code (0 for success)
    """
    # Initialize the job monitor
    monitor = JobMonitor(
        job_ids=initial_jobs,
        refresh_interval=refresh_interval
    )
    
    # If no initial jobs provided, fetch recent job listings
    if not initial_jobs:
        # Fetch recent job listings
        jobs = get_job_stories(20)  # Get 20 recent jobs
        for job in jobs:
            job_data = fetch_item(job)
            # Only add jobs that have comments
            if job_data and job_data.get('kids'):
                monitor.add_job(job)
    
    # Start the monitor
    monitor.start()
    
    try:
        # Main display loop
        current_page = 1
        selected_idx = 0
        
        while True:
            clear_screen()
            
            # Get the latest job data
            jobs_data = monitor.get_all_jobs()
            jobs_list = list(jobs_data.items())
            
            # Sort by new comments (most active discussions first)
            jobs_list.sort(
                key=lambda x: (x[1]['new_comments'], x[1]['last_comment_count']), 
                reverse=True
            )
            
            # Calculate pagination
            total_jobs = len(jobs_list)
            total_pages = max(1, (total_jobs + page_size - 1) // page_size)
            
            if current_page > total_pages:
                current_page = total_pages
                
            # Get slice for current page
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_jobs)
            page_jobs = jobs_list[start_idx:end_idx]
            
            # Display header
            if USE_COLORS:
                title = colorize("\n===== Job Listings Discussion Dashboard =====", ColorScheme.TITLE)
            else:
                title = "\n===== Job Listings Discussion Dashboard ====="
            
            status = f"Page {current_page}/{total_pages} | " + \
                     f"Monitoring {total_jobs} job listings | " + \
                     f"Auto-refresh: {refresh_interval}s"
                     
            if USE_COLORS:
                status = colorize(status, ColorScheme.INFO)
            
            print(title)
            print(status)
            print("=" * width)
            
            # Display the jobs on current page
            for idx, (job_id, data) in enumerate(page_jobs):
                # Calculate display index
                display_idx = start_idx + idx
                
                # Format the entry
                is_selected = (display_idx == selected_idx)
                prefix = ">" if is_selected else " "
                
                # Format title with new comment indicator
                job_title = data['title']
                if data['new_comments'] > 0:
                    new_indicator = f" [+{data['new_comments']} new]"
                    if USE_COLORS:
                        new_indicator = colorize(new_indicator, Colors.GREEN)
                    job_title += new_indicator
                
                if USE_COLORS:
                    title_text = colorize(job_title, ColorScheme.TITLE if is_selected else ColorScheme.HEADER)
                    if 'by' in data:
                        author = colorize(data['by'], ColorScheme.AUTHOR)
                    else:
                        author = "Unknown"
                else:
                    title_text = job_title
                    author = data.get('by', "Unknown")
                
                # Format timestamp
                timestamp = format_timestamp(data['time'])
                
                # Format comment count
                comment_count = len(data.get('comment_ids', []))
                if USE_COLORS:
                    comments = colorize(str(comment_count), ColorScheme.COUNT)
                else:
                    comments = str(comment_count)
                
                # Print the entry
                print(f"{prefix} {display_idx+1}. {title_text}")
                print(f"   Posted by: {author} | Comments: {comments} | {timestamp}")
                if data.get('url'):
                    url_text = data['url']
                    if USE_COLORS:
                        url_text = colorize(url_text, ColorScheme.URL)
                    print(f"   URL: {url_text}")
                print()
            
            # Display additional info if no jobs are being monitored
            if not jobs_list:
                info_msg = "\nNo job listings with comments are currently being monitored."
                add_msg = "You can add job listings to monitor by pressing [a]."
                if USE_COLORS:
                    info_msg = colorize(info_msg, ColorScheme.INFO)
                    add_msg = colorize(add_msg, ColorScheme.PROMPT)
                print(info_msg)
                print(add_msg)
            
            # Display navigation
            print("=" * width)
            print("Navigation:")
            print("- [up/down] Move selection | [enter] View selected job listing")
            print("- [left/right] Change page | [r] Refresh now")
            print("- [a] Add new job listing to monitor | [d] Remove selected job")
            print("- [n] Browse latest job listings")
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
                # Prompt for job ID to add
                print("\nEnter job listing ID to add to monitor:")
                try:
                    new_id = int(input("> "))
                    monitor.add_job(new_id)
                    print(f"Added job listing {new_id} to monitor.")
                    time.sleep(1)  # Brief pause
                except (ValueError, KeyboardInterrupt):
                    print("Cancelled or invalid input.")
                    time.sleep(1)
            elif key == 'd':
                # Remove selected job
                if jobs_list and 0 <= selected_idx < len(jobs_list):
                    job_id = jobs_list[selected_idx][0]
                    monitor.remove_job(job_id)
                    # Adjust selection to avoid going out of bounds
                    if selected_idx >= len(jobs_list) - 1:
                        selected_idx = max(0, len(jobs_list) - 2)
            elif key == 'n':
                # Browse latest job listings to add
                new_jobs = browse_job_listings_for_dashboard(monitor)
                if new_jobs:
                    for job_id in new_jobs:
                        monitor.add_job(job_id)
            elif key in ('\x1b[A', 'k'):  # Up arrow or 'k'
                selected_idx = max(0, selected_idx - 1)
                # Handle page change if selection moves off current page
                if selected_idx < start_idx:
                    current_page = max(1, current_page - 1)
            elif key in ('\x1b[B', 'j'):  # Down arrow or 'j'
                selected_idx = min(total_jobs - 1, selected_idx + 1)
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
                # View the selected job
                if jobs_list and 0 <= selected_idx < len(jobs_list):
                    job_id = jobs_list[selected_idx][0]
                    
                    # Clear new comments notification for this job
                    monitor.acknowledge_new_comments(job_id)
                    
                    # View the job with comment auto-refresh
                    display_job_details_with_live_comments(
                        job_id,
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

def browse_job_listings_for_dashboard(monitor):
    """
    Browse recent job listings to add to the dashboard.
    
    Args:
        monitor: The JobMonitor instance
        
    Returns:
        list: IDs of jobs that were selected to add
    """
    # Get fresh job stories
    job_ids = get_job_stories(50)  # Get more to filter for ones with comments
    
    # Fetch job details to find ones with comments
    jobs_with_comments = []
    
    loading_indicator = LoadingIndicator("Loading job listings")
    loading_indicator.start()
    
    try:
        # Fetch jobs in batches for better performance
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all fetch operations
            futures = [executor.submit(fetch_item, job_id) for job_id in job_ids]
            
            # Process results as they complete
            for future in as_completed(futures):
                job = future.result()
                if job and job.get('kids'):
                    jobs_with_comments.append(job)
    finally:
        loading_indicator.stop()
    
    # Sort by comment count (most commented first)
    jobs_with_comments.sort(key=lambda j: len(j.get('kids', [])), reverse=True)
    
    # Display paginated list with selection interface
    selected_jobs = []
    page_size = 10
    current_page = 1
    
    # Dict to track selection state
    selections = {}  # job_id -> bool
    
    # Get currently monitored job IDs
    monitored_jobs = set(monitor.get_all_jobs().keys())
    
    while True:
        clear_screen()
        
        # Calculate pagination
        total_jobs = len(jobs_with_comments)
        total_pages = max(1, (total_jobs + page_size - 1) // page_size)
        
        # Get slice for current page
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_jobs)
        page_jobs = jobs_with_comments[start_idx:end_idx]
        
        # Display header
        if USE_COLORS:
            title = colorize("\n===== Select Job Listings to Monitor =====", ColorScheme.TITLE)
        else:
            title = "\n===== Select Job Listings to Monitor ====="
        
        status = f"Page {current_page}/{total_pages} | " + \
                 f"{len(jobs_with_comments)} job listings with comments | " + \
                 f"Selected: {sum(selections.values())}"
                 
        if USE_COLORS:
            status = colorize(status, ColorScheme.INFO)
        
        print(title)
        print(status)
        print("=" * 80)
        
        # Display the jobs on current page
        for i, job in enumerate(page_jobs):
            job_id = job.get('id')
            comment_count = len(job.get('kids', []))
            
            # Check selection state
            is_selected = selections.get(job_id, False)
            is_monitored = job_id in monitored_jobs
            
            # Format checkbox and status
            if is_monitored:
                checkbox = "[M]"  # Already being monitored
                if USE_COLORS:
                    checkbox = colorize(checkbox, Colors.YELLOW)
            elif is_selected:
                checkbox = "[X]"  # Selected
                if USE_COLORS:
                    checkbox = colorize(checkbox, Colors.GREEN)
            else:
                checkbox = "[ ]"  # Not selected
            
            # Format title and other details
            index = start_idx + i + 1
            title = job.get('title', 'Untitled Job')
            
            if USE_COLORS:
                title_text = colorize(title, ColorScheme.HEADER)
                comment_text = colorize(f"{comment_count} comments", ColorScheme.COUNT)
            else:
                title_text = title
                comment_text = f"{comment_count} comments"
            
            # Print entry
            print(f"{index}. {checkbox} {title_text}")
            print(f"   {comment_text} | {format_timestamp(job.get('time', 0))}")
            if 'by' in job:
                poster = job['by']
                if USE_COLORS:
                    poster = colorize(poster, ColorScheme.AUTHOR)
                print(f"   Posted by: {poster}")
            print()
        
        # Display navigation
        print("=" * 80)
        print("Navigation:")
        print("- Enter a number to toggle selection")
        print("- [a] Select all on current page | [n] Select none on current page")
        print("- [p] Previous page | [n] Next page")
        print("- [f] Finish and add selected | [c] Cancel")
        
        # Get user input
        key = getch().lower()
        
        # Handle navigation
        if key == 'c':
            return []  # Cancel, return empty list
        
        elif key == 'f':
            # Finish and return selected jobs
            return [job_id for job_id, selected in selections.items() if selected]
        
        elif key == 'a':
            # Select all on current page
            for job in page_jobs:
                job_id = job.get('id')
                if job_id not in monitored_jobs:
                    selections[job_id] = True
        
        elif key == 'n':
            # Deselect all on current page
            for job in page_jobs:
                job_id = job.get('id')
                selections[job_id] = False
        
        elif key == 'p':
            # Previous page
            current_page = max(1, current_page - 1)
        
        elif key == 'n':
            # Next page
            current_page = min(total_pages, current_page + 1)
        
        elif key.isdigit():
            # Toggle selection of numbered item
            try:
                num = int(key)
                if 1 <= num <= len(page_jobs):
                    job = page_jobs[num-1]
                    job_id = job.get('id')
                    
                    # Can't select already monitored jobs
                    if job_id not in monitored_jobs:
                        selections[job_id] = not selections.get(job_id, False)
            except ValueError:
                pass  # Invalid number, ignore

def clean_html(html_text):
    """Clean HTML text for display."""
    if not html_text: 
        return "[No description]"
    
    # Decode HTML entities
    text = html.unescape(html_text)
    
    # Replace common HTML tags with plain text equivalents
    text = text.replace('<p>', '\n\n').replace('</p>', '')
    text = text.replace('<b>', '*').replace('</b>', '*')
    text = text.replace('<br/>', '\n').replace('<br />', '\n')
    text = text.replace('<li>', '\n• ').replace('</li>', '')
    text = text.replace('<ul>', '\n').replace('</ul>', '')
    text = text.replace('<ol>', '\n').replace('</ol>', '')
    text = text.replace('<i>', '_').replace('</i>', '_')
    text = text.replace('<strong>', '*').replace('</strong>', '*')
    text = text.replace('<em>', '_').replace('</em>', '_')
    
    # Remove other HTML tags
    while '<' in text and '>' in text:
        start = text.find('<')
        end = text.find('>', start)
        if start != -1 and end != -1:
            text = text[:start] + text[end+1:]
        else:
            break
    
    return text.strip()

def format_timestamp(unix_time):
    """Format a Unix timestamp into a human-readable string."""
    if not unix_time:
        return "Unknown time"
    
    try:
        dt = datetime.datetime.fromtimestamp(unix_time)
        # Format: "Mar 17, 2023 at 10:30 AM"
        timestamp = dt.strftime("%b %d, %Y at %I:%M %p")
        if USE_COLORS:
            timestamp = colorize(timestamp, ColorScheme.TIME)
        return timestamp
    except (TypeError, ValueError):
        return colorize("Unknown time", ColorScheme.TIME) if USE_COLORS else "Unknown time"