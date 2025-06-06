import argparse

from .constants import DEFAULT_THREADS_NUMBER


def get_parser_options() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="PyNews-CLI",
        description="Your news collector inside your terminal! Tell me, what's\
                          cooler than that?",
        usage="""
            PyNews-CLI - News Collector from HackerNews API
            Usage: pynews [-t/--top-stories number_of_stories]
                          [-n/--news-stories number_of_stories]
                          [-a/--ask-stories number_of_stories]
                          [-j/--job-stories number_of_stories]
                          [--poll-stories number_of_stories]
                          [-c/--comments story_id]
                          [-d/--ask-details story_id]
                          [--ask-top number_of_stories]
                          [--ask-discussed number_of_stories]
                          [--ask-recent number_of_stories]
                          [--poll-top number_of_stories]
                          [--poll-discussed number_of_stories]
                          [--poll-recent number_of_stories]
                          [--user USERNAME]
                          [--list-users]
                          [--user-search]
                          [--keyword "search term"]
                          [--job-keyword "search term"]
                          [--poll-keyword "search term"]

            If the number of stories is not supplied, will be showed a default number from the
            500 stories.

            Examples:
            - Get Top Stories:
                $ pynews -t 10 # or
                $ pynews --top-stories 10
                This will show the 10 first top stories from the list of 500.

            - Get New Stories:
                $ pynews -n 10 # or
                $ pynews --news-stories
                This will show the 10 first new stories from the list of 500.
            
            - Get Ask HN Stories:
                $ pynews -a 10 # or
                $ pynews --ask-stories 10
                This will show the 10 latest Ask HN stories with scores and comment counts.
            
            - Get Job Listings:
                $ pynews -j 20 # or
                $ pynews --job-stories 20
                This will show the 20 latest job listings from Hacker News.
                
            - Get Poll Questions:
                $ pynews --poll-stories 10
                This will show the 10 latest poll questions with options.
                
            - Get Top-Scored Poll Questions:
                $ pynews --poll-top 10
                This will show the 10 highest-scoring poll questions.
                
            - Get Most-Discussed Poll Questions:
                $ pynews --poll-discussed 10
                This will show the 10 poll questions with the most comments.
                
            - Get Most Recent Poll Questions:
                $ pynews --poll-recent 10
                This will show the 10 most recent poll questions.
                
            - Filter Polls by Keyword:
                $ pynews --poll-stories --poll-keyword "python"
                This will show poll questions containing "python".
                
            - View Poll Details:
                $ pynews --poll-details 12345
                This will show details for a poll with ID 12345, including all options.
                
            - Get HackerNews User Profile:
                $ pynews --user "username"
                This will show detailed information about a HackerNews user.
                
            - List Random HackerNews Users:
                $ pynews --list-users
                This will display a list of random HackerNews users to explore.
                
            - Search for a HackerNews User:
                $ pynews --user-search
                This will provide an interactive prompt to search for users.
                
            - Filter Jobs by Keyword:
                $ pynews -j --job-keyword "python"
                This will show job listings containing "python".
                
            - Filter Jobs with Multiple Keywords:
                $ pynews -j --job-keyword "python" "remote"
                This will show job listings containing either "python" OR "remote".
                
            - Filter Jobs Requiring ALL Keywords:
                $ pynews -j --job-keyword "python" "senior" --match-all
                This will show job listings containing BOTH "python" AND "senior".
            
            - Filter Ask HN Stories by keyword:
                $ pynews -a 10 --keyword "python"
                This will show Ask HN stories containing the word "python".
                
            - Filter with multiple keywords (ANY match):
                $ pynews -a 10 --keyword "python" "javascript"
                This will show Ask HN stories containing EITHER "python" OR "javascript".
                
            - Filter with multiple keywords (ALL must match):
                $ pynews -a 10 --keyword "python" "javascript" --match-all
                This will show only stories containing BOTH "python" AND "javascript".
            
            - Get Ask HN Stories sorted by submission time:
                $ pynews -a 10 --sort-by-time
                This will show the 10 Ask HN stories sorted by submission time.
                
            - Get Top-Scored Ask HN Stories:
                $ pynews --ask-top 10
                This will show the 10 highest-scoring Ask HN stories.
                
            - Get Most-Discussed Ask HN Stories:
                $ pynews --ask-discussed 10
                This will show the 10 Ask HN stories with the most comments.
                
            - Get Most Recent Ask HN Stories:
                $ pynews --ask-recent 10
                This will show the 10 most recent Ask HN stories.
                
            - Find Ask HN Stories with keyword:
                $ pynews --ask-search "python" 10
                This will search for Ask HN stories containing "python".
                
            - View Comments for a Story:
                $ pynews -c 12345 # or
                $ pynews --comments 12345
                This will show comments for story with ID 12345.
                
            - View Ask HN Story Details:
                $ pynews -d 12345 # or
                $ pynews --ask-details 12345
                This will show details for an Ask HN story with author, score, and comment count.
                
            - Control Comment Pagination:
                $ pynews -c 12345 --page-size 15 --page 2
                This will show the second page of comments (15 per page).

            Get basic options and Help, use: -h\--help

            """,
    )
    parser.add_argument(
        "-t",
        "--top-stories",
        nargs="?",
        const=200,
        type=int,
        help="Get the top N stories from HackerNews API",
    )

    parser.add_argument(
        "-n",
        "--news-stories",
        nargs="?",
        const=200,
        type=int,
        help="Get the N new stories from HackerNews API",
    )

    parser.add_argument(
        "-a",
        "--ask-stories",
        nargs="?",
        const=200,
        type=int,
        help="Get the N latest Ask HN stories from HackerNews API",
    )

    parser.add_argument(
        "-j",
        "--job-stories",
        nargs="?",
        const=20,
        type=int,
        help="Get the N latest job listings from HackerNews API",
    )

    parser.add_argument(
        "--poll-stories",
        nargs="?",
        const=20,
        type=int,
        help="Get the N latest poll questions from HackerNews API",
    )

    parser.add_argument(
        "--poll-keyword",
        nargs="+",
        metavar="KEYWORD",
        help="Filter poll questions by keyword(s)",
    )

    parser.add_argument(
        "--poll-details",
        type=int,
        help="View details of a poll with the given ID",
    )

    parser.add_argument(
        "--poll-top",
        nargs="?",
        const=10,
        type=int,
        help="Get the N highest-scoring poll questions",
    )

    parser.add_argument(
        "--poll-discussed",
        nargs="?",
        const=10,
        type=int,
        help="Get the N most commented poll questions",
    )

    parser.add_argument(
        "--poll-recent",
        nargs="?",
        const=10,
        type=int,
        help="Get the N most recent poll questions",
    )

    parser.add_argument(
        "--user",
        metavar="USERNAME",
        help="View information about a specific HackerNews user",
    )

    parser.add_argument(
        "--list-users",
        action="store_true",
        help="List random HackerNews users and view their profiles",
    )

    parser.add_argument(
        "--user-search",
        action="store_true",
        help="Search for a specific HackerNews user",
    )

    parser.add_argument(
        "--job-keyword",
        nargs="+",
        metavar="KEYWORD",
        help="Filter job listings by keyword(s)",
    )

    parser.add_argument(
        "--job-sort-by-score",
        action="store_true",
        help="Sort job listings by score instead of date",
    )

    parser.add_argument(
        "--job-oldest-first",
        action="store_true",
        help="Show oldest job listings first (default is newest first)",
    )

    parser.add_argument(
        "--ask-top",
        nargs="?",
        const=10,
        type=int,
        help="Get the N highest-scoring Ask HN stories",
    )

    parser.add_argument(
        "--ask-discussed",
        nargs="?",
        const=10,
        type=int,
        help="Get the N most commented Ask HN stories",
    )

    parser.add_argument(
        "--ask-recent",
        nargs="?",
        const=10,
        type=int,
        help="Get the N most recent Ask HN stories",
    )

    parser.add_argument(
        "--ask-search",
        nargs="+",
        metavar="KEYWORD",
        help="Search for Ask HN stories containing specific keywords",
    )

    parser.add_argument(
        "--keyword",
        nargs="+",
        metavar="KEYWORD",
        help="Filter stories by keyword(s)",
    )

    parser.add_argument(
        "--match-all",
        action="store_true",
        help="When using multiple keywords, require ALL keywords to match (default is ANY)",
    )

    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Make keyword search case-sensitive (default is case-insensitive)",
    )

    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Minimum score threshold for stories",
    )

    parser.add_argument(
        "--min-comments",
        type=int,
        default=0,
        help="Minimum comment threshold for Ask HN stories (used with --ask-discussed)",
    )

    parser.add_argument(
        "--max-age",
        type=int,
        default=0,
        help="Maximum age in hours for Ask HN stories (used with --ask-recent)",
    )

    parser.add_argument(
        "--sort-by-comments",
        action="store_true",
        help="Sort Ask HN stories by comment count instead of score",
    )

    parser.add_argument(
        "--sort-by-time",
        action="store_true",
        help="Sort Ask HN stories by submission time (newest first)",
    )

    parser.add_argument(
        "-s",
        "--shuffle",
        nargs="?",
        const=False,
        type=bool,
        help="Get the N new stories from HackerNews API",
    )

    parser.add_argument(
        "-T",
        "--threads",
        nargs="?",
        const=DEFAULT_THREADS_NUMBER,
        type=int,
        help="Determine the number max of threads",
    )

    parser.add_argument(
        "-c",
        "--comments",
        type=int,
        help="View comments for a story with the given ID",
    )

    parser.add_argument(
        "-d",
        "--ask-details",
        type=int,
        help="View details of an Ask HN story with the given ID, highlighting the author and score",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="Number of items to display per page",
    )

    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Which page of comments to display",
    )

    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=80,
        help="Display width for formatting comments",
    )

    # Comment export options
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export comments to a JSON file",
    )

    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export comments to a CSV file",
    )

    parser.add_argument(
        "--export-path",
        type=str,
        help="Path to save exported comments (default: current directory)",
    )

    parser.add_argument(
        "--export-filename",
        type=str,
        help="Filename for exported comments (without extension, default: hn_story_ID_comments_TIMESTAMP)",
    )

    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Omit timestamp from export filename",
    )

    parser.add_argument(
        "--auto-refresh",
        nargs="?",
        const=5,
        type=int,
        help="Automatically refresh comments at the specified interval in seconds (default: 60)",
    )

    parser.add_argument(
        "--notify-new",
        action="store_true",
        help="Show a notification when new comments are found during auto-refresh",
    )

    parser.add_argument(
        "--ask-auto-refresh",
        action="store_true",
        help="Enable background fetching of new comments for Ask HN stories",
    )

    parser.add_argument(
        "--ask-refresh-interval",
        type=int,
        default=5,
        help="Interval in seconds between comment updates for Ask HN stories (default: 60)",
    )

    parser.add_argument(
        "--ask-dashboard",
        action="store_true",
        help="Launch the Ask HN discussions dashboard with live updates",
    )

    parser.add_argument(
        "--dashboard-stories",
        nargs="+",
        type=int,
        metavar="STORY_ID",
        help="Story IDs to initially include in the dashboard",
    )

    parser.add_argument(
        "--job-auto-refresh",
        action="store_true",
        help="Enable background fetching of new comments for job listings",
    )

    parser.add_argument(
        "--job-refresh-interval",
        type=int,
        default=60,
        help="Interval in seconds between comment updates for job listings (default: 60)",
    )

    parser.add_argument(
        "--job-dashboard",
        action="store_true",
        help="Launch the job listings discussion dashboard with live updates",
    )

    parser.add_argument(
        "--job-dashboard-ids",
        nargs="+",
        type=int,
        metavar="JOB_ID",
        help="Job listing IDs to initially include in the dashboard",
    )


    options = parser.parse_args()

    # If --ask-discussed is used, set sort_by_comments to True
    if options.ask_discussed:
        options.sort_by_comments = True
        options.ask_top = options.ask_discussed

    # If --ask-recent is used, set sort_by_time to True
    if options.ask_recent:
        options.sort_by_time = True
        options.ask_top = options.ask_recent

    # If --ask-search is used, set up keyword search
    if options.ask_search:
        options.keyword = options.ask_search
        options.ask_stories = 200  # Default to a larger set for searching

    # Handle poll-specific options
    if options.poll_discussed:
        options.sort_by_comments = True
        options.poll_stories = options.poll_discussed

    if options.poll_recent:
        options.sort_by_time = True
        options.poll_stories = options.poll_recent

    if options.poll_top:
        options.poll_stories = options.poll_top

    return options
