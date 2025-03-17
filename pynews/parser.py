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
                          [-c/--comments story_id]

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
                
            - View Comments for a Story:
                $ pynews -c 12345 # or
                $ pynews --comments 12345
                This will show comments for story with ID 12345.
                
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
    return options