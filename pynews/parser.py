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
                          [-c/--comments story_id]
                          [-d/--ask-details story_id]
                          [--ask-top number_of_stories]
                          [--ask-discussed number_of_stories]

            If the number of stories is not supplied, will be showed 200 from the
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
                
            - Get Top-Scored Ask HN Stories:
                $ pynews --ask-top 10
                This will show the 10 highest-scoring Ask HN stories.
                
            - Get Most-Discussed Ask HN Stories:
                $ pynews --ask-discussed 10
                This will show the 10 Ask HN stories with the most comments.
                
            - View Comments for a Story:
                $ pynews -c 12345 # or
                $ pynews --comments 12345
                This will show comments for story with ID 12345.
                
            - View Ask HN Story Details:
                $ pynews -d 12345 # or
                $ pynews --ask-details 12345
                This will show details for an Ask HN story with author, score, and comment count.
                
            - Control Comment Pagination:
                $ pynews -c 12345 -p 15 --page 2
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
        "--min-score",
        type=int,
        default=0,
        help="Minimum score threshold for Ask HN stories (used with --ask-top)",
    )
    
    parser.add_argument(
        "--min-comments",
        type=int,
        default=0,
        help="Minimum comment threshold for Ask HN stories (used with --ask-discussed)",
    )
    
    parser.add_argument(
        "--sort-by-comments",
        action="store_true",
        help="Sort Ask HN stories by comment count instead of score",
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
        "-p",
        "--page-size",
        type=int,
        default=10,
        help="Number of comments to display per page",
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

    options = parser.parse_args()
    
    # If --ask-discussed is used, set sort_by_comments to True
    if options.ask_discussed:
        options.sort_by_comments = True
        options.ask_top = options.ask_discussed
        
    return options