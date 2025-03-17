"""
Loading indicator functionality for PyNews CLI.
"""
import sys
import time
import threading
from itertools import cycle

from .colors import ColorScheme, colorize, supports_color

class LoadingIndicator:
    """
    A simple loading indicator that shows animation while a process is running.
    """
    def __init__(self, message="Loading...", animation=None):
        """
        Initialize the loading indicator.
        
        Args:
            message: The message to display alongside the animation
            animation: The animation sequence to use. If None, a default is used.
        """
        self.message = message
        self.animation = animation or ['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽']
        self._running = False
        self._thread = None
        self.use_colors = supports_color()
    
    def _animate(self):
        """Animation loop that runs in a separate thread."""
        spinner = cycle(self.animation)
        
        # Colorize the message if supported
        display_message = colorize(self.message, ColorScheme.LOADING) if self.use_colors else self.message
        sys.stdout.write(f"\r{display_message} ")
        
        while self._running:
            char = next(spinner)
            # Colorize the spinner character if supported
            display_char = colorize(char, ColorScheme.LOADING) if self.use_colors else char
            sys.stdout.write(f"\r{display_message} {display_char}")
            sys.stdout.flush()
            time.sleep(0.1)
        
        # Clear the line when done
        sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
        sys.stdout.flush()
    
    def start(self):
        """Start the loading animation in a separate thread."""
        if self._thread is not None and self._thread.is_alive():
            # Already running
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._animate)
        self._thread.daemon = True  # Thread will exit when main program exits
        self._thread.start()
        
    def stop(self):
        """Stop the loading animation."""
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
            
def with_loading(func):
    """
    Decorator to run a function with a loading indicator.
    
    Example:
        @with_loading
        def fetch_data():
            # long running operation
            return data
    """
    def wrapper(*args, **kwargs):
        # Get custom message from kwargs if provided, otherwise use default
        message = kwargs.pop('loading_message', 'Loading...')
        
        # Create and start loading indicator
        loader = LoadingIndicator(message=message)
        loader.start()
        
        try:
            # Run the actual function
            result = func(*args, **kwargs)
            return result
        finally:
            # Always stop the loading indicator
            loader.stop()
    
    return wrapper