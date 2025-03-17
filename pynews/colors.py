"""
Color utility functions for PyNews CLI.
"""

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

# Color presets for different UI elements
class ColorScheme:
    """Color scheme for PyNews CLI."""
    # Headers and titles
    TITLE = Colors.BOLD + Colors.BRIGHT_CYAN
    HEADER = Colors.BOLD + Colors.BRIGHT_BLUE
    SUBHEADER = Colors.BOLD + Colors.BRIGHT_WHITE
    
    # Info elements
    INFO = Colors.BRIGHT_WHITE
    TIME = Colors.BRIGHT_BLACK
    URL = Colors.BRIGHT_GREEN + Colors.UNDERLINE
    COUNT = Colors.BRIGHT_YELLOW
    POINTS = Colors.BRIGHT_YELLOW
    AUTHOR = Colors.BOLD + Colors.BRIGHT_YELLOW
    
    # Navigation
    NAV_HEADER = Colors.BOLD + Colors.BRIGHT_BLUE
    NAV_ACTIVE = Colors.BRIGHT_GREEN
    NAV_INACTIVE = Colors.BRIGHT_BLACK
    
    # Content
    COMMENT_TEXT = Colors.WHITE
    COMMENT_BORDER = Colors.BRIGHT_BLACK
    
    # Loading
    LOADING = Colors.BRIGHT_MAGENTA
    
    # Errors and warnings
    ERROR = Colors.BRIGHT_RED
    WARNING = Colors.BRIGHT_YELLOW
    
    # Prompts
    PROMPT = Colors.BRIGHT_GREEN
    INPUT = Colors.BRIGHT_CYAN

def colorize(text, color_code):
    """Wrap text with color codes and reset afterwards."""
    return f"{color_code}{text}{Colors.RESET}"

# Function to check if the terminal supports colors
def supports_color():
    """
    Returns True if the running system's terminal supports color,
    and False otherwise.
    """
    import os
    import sys
    
    # Check if NO_COLOR environment variable is set
    if os.environ.get('NO_COLOR', None) is not None:
        return False
    
    # Check if output is a TTY
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    # Windows check
    if sys.platform == 'win32' and not is_a_tty:
        return False
    
    # Check if TERM is set and not 'dumb'
    term = os.environ.get('TERM', None)
    if term == 'dumb' or not term:
        return False
    
    return is_a_tty