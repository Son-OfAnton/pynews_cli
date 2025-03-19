# PyNews CLI

A command-line interface for browsing Hacker News stories and comments.

## Features

- Browse top stories from Hacker News
- Browse new stories from Hacker News
- Browse Ask HN stories from Hacker News with author information, scores, comment counts, and submission times
- Sort Ask HN stories by score, comment count, or submission time
- View and navigate comments for any story
- View detailed information for Ask HN stories with prominent author, score, comment count, and time display
- Color-coded terminal output
- Interactive navigation

## Installation

```
pip install -r requirements.txt
```

## Usage

```
# Get top stories
python -m pynews -t 10

# Get new stories
python -m pynews -n 10

# Get Ask HN stories (shows author, score, comments, and time)
python -m pynews -a 10

# Get Ask HN stories sorted by submission time (newest first)
python -m pynews -a 10 --sort-by-time

# Get Ask HN stories sorted by comment count
python -m pynews -a 10 --sort-by-comments

# Get top-scoring Ask HN stories
python -m pynews --ask-top 10

# Get most-discussed Ask HN stories
python -m pynews --ask-discussed 10

# Get most recent Ask HN stories
python -m pynews --ask-recent 10

# Get top-scoring Ask HN stories with minimum score threshold
python -m pynews --ask-top 10 --min-score 50

# Get most-discussed Ask HN stories with minimum comment threshold
python -m pynews --ask-discussed 10 --min-comments 5

# Get recent Ask HN stories with maximum age limit
python -m pynews --ask-recent 10 --max-age 24  # Last 24 hours

# View detailed information for an Ask HN story
python -m pynews -d 12345

# View comments for a story
python -m pynews -c 12345
```

### Command-line Options

```
-t, --top-stories [N]     Get N top stories (default: 200)
-n, --news-stories [N]    Get N new stories (default: 200)
-a, --ask-stories [N]     Get N latest Ask HN stories (default: 200)
--ask-top [N]             Get N highest-scoring Ask HN stories (default: 10)
--ask-discussed [N]       Get N most-commented Ask HN stories (default: 10)
--ask-recent [N]          Get N most recent Ask HN stories (default: 10)
--min-score N             Minimum score threshold for stories (default: 0)
--min-comments N          Minimum comment threshold for stories (default: 0)
--max-age N               Maximum age in hours for stories (default: 0, no limit)
--sort-by-comments        Sort Ask HN stories by comment count instead of score
--sort-by-time            Sort Ask HN stories by submission time (newest first)
-c, --comments ID         View comments for story with ID
-d, --ask-details ID      View detailed info for an Ask HN story
-p, --page-size N         Number of comments per page (default: 10)
--page N                  Which page to display (default: 1)
-w, --width N             Display width (default: 80)
-s, --shuffle             Shuffle the stories
-T, --threads N           Max number of threads (default: CPU count)
```

## Navigation Keys

When viewing comments:
- `n` - Next page
- `p` - Previous page
- `f` - First page
- `l` - Last page
- `s` - Toggle sort order
- `1-9` - Go to specific page
- `q` - Quit

When viewing Ask HN story details:
- `v` - View author profile in browser
- `c` - View comments for the story
- `u` - Open story in browser (to upvote)
- `q` - Return to menu

When viewing top Ask HN stories:
- `1-9` - View details for a specific story
- `s` - Toggle sort by score
- `c` - Toggle sort by comments
- `t` - Toggle sort by time
- `q` - Return to menu

## Visual Indicators

### Score Display

Stories are displayed with scores visualized based on their value:
- `★★★ 300+ points ★★★` - Very high scoring
- `★★ 100+ points ★★` - High scoring
- `★ 50+ points ★` - Notable score
- `N points` - Regular score

### Comment Count Display

Stories are displayed with comment counts indicating discussion activity:
- `💬 100+ comments` - Very active discussion
- `💬 50+ comments` - Active discussion
- `💬 10+ comments` - Some discussion
- `💬 N comments` - Few comments
- `💬 0` - No comments yet

### Time Display

Stories display time information in two formats:
- Relative: `5m ago`, `2h ago`, `3d ago`, etc.
- Absolute: `Mar 18, 2025 at 09:08 AM` (in detailed view)

## Requirements

See requirements.txt for dependencies.