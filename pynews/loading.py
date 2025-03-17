"""
Loading indicator functionality for PyNews CLI.
"""
import sys
import time
import threading
from itertools import cycle

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
    
    def _animate(self):
        """Animation loop that runs in a separate thread."""
        spinner = cycle(self.animation)
        sys.stdout.write(f"\r{self.message} ")
        
        while self._running:
            char = next(spinner)
            sys.stdout.write(f"\r{self.message} {char}")
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
