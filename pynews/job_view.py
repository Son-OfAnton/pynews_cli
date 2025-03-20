"""
Module for simple display of job listings from Hacker News with arrow key navigation.
"""
import os
import datetime
import re
import sys
import tty
import termios
from webbrowser import open as url_open

from .colors import Colors, ColorScheme, colorize, supports_color
from .getch import getch
from .utils import get_story, get_stories, format_time_ago

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

def display_job_listings(limit=20, page_size=10, sort_newest_first=True, sort_by_score=False, company_filter=None, min_score=None):
    """
    Display a simplified list of job listings from Hacker News with arrow key navigation.
    
    Args:
        limit: Maximum number of jobs to fetch
        page_size: Number of jobs to display per page
        sort_newest_first: Whether to sort jobs with newest first (default: True)
        sort_by_score: Whether to sort by score instead of date
        company_filter: Optional company name to filter job listings by
        min_score: Optional minimum score threshold for jobs to display
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
        for job_id in job_ids[:min(limit * 2, len(job_ids))]:  # Fetch more to allow for filtering
            job = get_story(job_id)
            if job:  # Make sure we have a valid job
                # Extract company name and add to job data
                company, position = extract_company_name(job.get('title', ''))
                job['company'] = company
                job['position'] = position
                jobs.append(job)
    finally:
        loader.stop()
    
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
        jobs = sort_jobs_by_score(jobs)
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
            timestamp = job.get('time', 0)
            time_ago = format_time_ago(timestamp)
            absolute_date = format_absolute_date(timestamp)
            company = job.get('company')
            score = job.get('score', 0)
            
            # If no external URL, use the HN link
            if not url:
                url = f"https://news.ycombinator.com/item?id={job.get('id')}"
            
            # Format job listing with selection highlighting
            if USE_COLORS:
                job_num = colorize(f"{start_idx + i + 1}.", ColorScheme.COUNT)
                
                # Use different formatting based on selection state
                if is_selected:
                    # Format the selected job with a distinct highlight
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
            if current_company_filter or (current_min_score is not None and current_min_score > 0):
                clear_filter = "[c] Clear all filters"
                print(colorize(clear_filter, ColorScheme.NAV_ACTIVE))
            
            # Exit option
            print(colorize("\n[q] Return to main menu", ColorScheme.NAV_ACTIVE))
            
        else:
            print("\nSort and Filter:")
            print(f"[t] Toggle sort: {'by score' if not is_sort_by_score else 'by date'}")
            
            if not is_sort_by_score:
                print(f"[d] Sort by date: {'newest first' if newest_first else 'oldest first'}")
            
            filter_option = "[f] Filter by company" 
            if current_company_filter:
                filter_option += f" (current: '{current_company_filter}')"
            print(filter_option)
            
            score_option = "[s] Set minimum score"
            if current_min_score is not None and current_min_score > 0:
                score_option += f" (current: {current_min_score})"
            print(score_option)
            
            if current_company_filter or (current_min_score is not None and current_min_score > 0):
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
            if USE_COLORS:
                print(colorize("\nEnter company name to filter by (or press Enter to cancel):", ColorScheme.PROMPT))
            else:
                print("\nEnter company name to filter by (or press Enter to cancel):")
                
            # Get user input for company name
            try:
                # Exit raw mode to get normal input behavior
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    new_filter = input("> ").strip()
                finally:
                    tty.setraw(fd)
                    
                if new_filter:
                    current_company_filter = new_filter
                    # Reload all jobs and apply the filter
                    jobs = []
                    loader = LoadingIndicator(message="Reloading job listings...")
                    loader.start()
                    try:
                        for job_id in job_ids[:min(limit * 2, len(job_ids))]:
                            job = get_story(job_id)
                            if job:
                                company, position = extract_company_name(job.get('title', ''))
                                job['company'] = company
                                job['position'] = position
                                jobs.append(job)
                    finally:
                        loader.stop()
                    
                    # Apply all filters
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
                else:
                    print(f"\nError reading input: {e}")
                    
        elif key == 's':
            # Prompt for minimum score
            if USE_COLORS:
                print(colorize("\nEnter minimum score (or press Enter to cancel):", ColorScheme.PROMPT))
            else:
                print("\nEnter minimum score (or press Enter to cancel):")
                
            # Get user input for score
            try:
                # Exit raw mode to get normal input behavior
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    score_input = input("> ").strip()
                finally:
                    tty.setraw(fd)
                    
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
                                for job_id in job_ids[:min(limit * 2, len(job_ids))]:
                                    job = get_story(job_id)
                                    if job:
                                        company, position = extract_company_name(job.get('title', ''))
                                        job['company'] = company
                                        job['position'] = position
                                        jobs.append(job)
                            finally:
                                loader.stop()
                            
                            # Apply all filters
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
                        else:
                            print("\nInvalid number. Please enter a positive integer.")
            except Exception as e:
                if USE_COLORS:
                    print(colorize(f"\nError reading input: {e}", ColorScheme.ERROR))
                else:
                    print(f"\nError reading input: {e}")
                    
        elif key == 'c' and (current_company_filter or (current_min_score is not None and current_min_score > 0)):
            # Clear all filters
            current_company_filter = None
            current_min_score = None
            
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