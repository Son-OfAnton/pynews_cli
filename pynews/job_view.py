"""
Module for simple display of job listings from Hacker News with arrow key navigation
and keyword filtering.
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