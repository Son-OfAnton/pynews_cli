import multiprocessing

DEFAULT_THREADS_NUMBER = multiprocessing.cpu_count()

URL_NEWS_STORIES = "https://hacker-news.firebaseio.com/v0/newstories.json"

URL_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"

URL_ASK_STORIES = "https://hacker-news.firebaseio.com/v0/askstories.json"

URL_JOB_STORIES = "https://hacker-news.firebaseio.com/v0/jobstories.json"

URL_POLL_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"  # Using topstories as a source for polls

URL_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

URL_USER = "https://hacker-news.firebaseio.com/v0/user/{}.json"

URLS = {
    "top": URL_TOP_STORIES, 
    "news": URL_NEWS_STORIES, 
    "ask": URL_ASK_STORIES, 
    "job": URL_JOB_STORIES, 
    "poll": URL_POLL_STORIES, 
    "item": URL_ITEM,
    "user": URL_USER
}