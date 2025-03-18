import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from webbrowser import open as url_open

import requests as req
from alive_progress import alive_it
from cursesmenu import CursesMenu
from cursesmenu.items import FunctionItem

from .constants import URLS
from .loading import with_loading, LoadingIndicator
from .colors import Colors, colorize, supports_color


def clean_title(title):
    result = title.encode("utf-8")
    if sys.version_info.major == 3:
        result = result.decode()
    return result


def get_stories(type_url):
    """Return a list of ids of the 500 top stories."""
    loader = LoadingIndicator(message=f"Fetching {type_url} story IDs...")
    loader.start()
    try:
        data = req.get(URLS[type_url])
        return data.json()
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return None
    finally:
        loader.stop()


def get_story(new):
    """Return a story of the given ID."""
    url = URLS["item"].format(new)
    try:
        data = req.get(url)
    except req.ConnectionError:
        raise
    except req.Timeout:
        raise req.Timeout("A timeout problem occurred.")
    except req.TooManyRedirects:
        raise req.TooManyRedirects(
            "The request exceeds the configured number\
            of maximum redirections."
        )
    else:
        return data.json()


def _create_list_stories_no_loading(list_id_stories, number_of_stories, shuffle, max_threads):
    """Show in a formatted way the stories for each item of the list."""

    list_stories = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {
            executor.submit(get_story, new)
            for new in list_id_stories[:number_of_stories]
        }

        for future in alive_it(
            as_completed(futures),
            total=len(futures),
            title="Getting news...",
            enrich_print=True,
            ctrl_c=True,
        ):
            list_stories.append(future.result())

    if shuffle:
        random.shuffle(list_stories)
    return list_stories


@with_loading
def create_list_stories(list_id_stories, number_of_stories, shuffle, max_threads):
    """
    Show in a formatted way the stories for each item of the list.
    Now with loading indicator.
    """
    # Replace the alive_it progress bar with our loading indicator
    list_stories = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {
            executor.submit(get_story, new)
            for new in list_id_stories[:number_of_stories]
        }

        for future in as_completed(futures):
            result = future.result()
            if result:  # Make sure we have a valid result
                list_stories.append(result)

    if shuffle:
        random.shuffle(list_stories)
    return list_stories


def create_menu(list_dict_stories, type_new):
    """
    Create a menu with the stories to display.
    For Ask HN stories, we'll include the author information.
    """
    title = f"Pynews - {type_new.capitalize()} stories"
    menu = CursesMenu(title, "Select the story and press enter")
    msg = "This story does not have a URL"
    
    for i, story in enumerate(list_dict_stories):
        # Get the basic story information
        story_title = clean_title(story.get("title", "Untitled"))
        author = story.get("by", "Anonymous")
        points = story.get("score", 0)
        
        # Format the display title - For Ask HN stories, add author information
        if type_new == "ask":
            # For Ask HN, format with author info
            display_title = f"[{i+1}] {story_title} [by {author}, {points} points]"
        else:
            # For other story types, just use the title with index
            display_title = f"[{i+1}] {story_title}"
        
        # Create the menu item with appropriate URL
        if "url" in story and story["url"]:
            item = FunctionItem(display_title, url_open, args=[story["url"]])
        else:
            # For self-posts that don't have a URL, use the HN link
            hn_url = f"https://news.ycombinator.com/item?id={story.get('id')}"
            item = FunctionItem(display_title, url_open, args=[hn_url])
        
        menu.append_item(item)
    
    return menu


def show_author_profile(username):
    """Open the Hacker News user profile in a browser."""
    profile_url = f"https://news.ycombinator.com/user?id={username}"
    url_open(profile_url)