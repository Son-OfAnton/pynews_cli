"""
Loading indicator functionality for PyNews CLI.
"""
import sys
import time
import threading
import shutil
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


class ProgressBar:
    """
    A horizontal progress bar for displaying loading progress.
    """
    def __init__(self, total=100, prefix='Progress:', suffix='Complete', 
                 length=50, fill='█', print_end='\r'):
        """Initialize the progress bar with customization options."""
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.fill = fill
        self.print_end = print_end
        self._running = False
        self._thread = None
        self._value = 0
        self.use_colors = supports_color()
        
        # Get terminal width for better sizing
        self.term_width = shutil.get_terminal_size().columns
        # Adjust length to fit in terminal if needed
        self.length = min(self.length, self.term_width - len(prefix) - len(suffix) - 15)
    
    def update(self, value):
        """Update the progress bar to the specified value."""
        self._value = value
        
    def _animate(self):
        """Animation loop that runs in a separate thread."""
        last_value = -1
        
        while self._running:
            # Only redraw if value has changed
            if self._value != last_value:
                self._print_progress()
                last_value = self._value
            
            time.sleep(0.1)
            
        # Print a newline when done
        sys.stdout.write('\n')
        sys.stdout.flush()
        
    def _print_progress(self):
        """Print the current progress."""
        percent = self._value / self.total * 100
        filled_length = int(self.length * self._value // self.total)
        bar = self.fill * filled_length + '-' * (self.length - filled_length)
        
        # Colorize if supported
        if self.use_colors:
            prefix = colorize(self.prefix, ColorScheme.LOADING)
            percent_str = colorize(f"{percent:.1f}%", ColorScheme.COUNT)
            bar = colorize(bar, ColorScheme.LOADING)
            suffix = colorize(self.suffix, ColorScheme.LOADING)
            progress_str = f"\r{prefix} |{bar}| {percent_str} {suffix}"
        else:
            progress_str = f"\r{self.prefix} |{bar}| {percent:.1f}% {self.suffix}"
        
        sys.stdout.write(progress_str)
        sys.stdout.flush()
        
    def start(self):
        """Start the progress bar animation in a separate thread."""
        if self._thread is not None and self._thread.is_alive():
            # Already running
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._animate)
        self._thread.daemon = True
        self._thread.start()
        
        # Print initial progress
        self._print_progress()
        
    def stop(self):
        """Stop the progress bar animation."""
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        
        # Clear any partial line
        sys.stdout.write('\n')
        sys.stdout.flush()


class IndeterminateProgressBar(ProgressBar):
    """
    A version of the progress bar that shows ongoing activity when progress
    percentage isn't known.
    """
    def __init__(self, prefix='Loading:', suffix='Please wait', 
                 length=50, fill='█', print_end='\r'):
        """Initialize with default values for an indeterminate state."""
        super().__init__(100, prefix, suffix, length, fill, print_end)
        self._position = 0
        self._direction = 1  # 1 for right, -1 for left
        
    def _print_progress(self):
        """Print the animated indeterminate progress bar."""
        # Create a bar with a moving segment
        bar = ['-'] * self.length
        
        # Calculate the segment width (20% of total)
        segment_width = max(1, int(self.length * 0.2))
        
        # Calculate start and end positions
        start = self._position
        end = min(start + segment_width, self.length)
        
        # Fill the moving segment
        for i in range(start, end):
            bar[i] = self.fill
        
        # Convert to string
        bar_str = ''.join(bar)
        
        # Colorize if supported
        if self.use_colors:
            prefix = colorize(self.prefix, ColorScheme.LOADING)
            bar_str = colorize(bar_str, ColorScheme.LOADING)
            suffix = colorize(self.suffix, ColorScheme.LOADING)
            progress_str = f"\r{prefix} |{bar_str}| {suffix}"
        else:
            progress_str = f"\r{self.prefix} |{bar_str}| {self.suffix}"
        
        sys.stdout.write(progress_str)
        sys.stdout.flush()
        
        # Update position for next animation frame
        if self._direction == 1:  # Moving right
            self._position += 1
            if self._position >= self.length - segment_width:
                self._direction = -1  # Switch direction
        else:  # Moving left
            self._position -= 1
            if self._position <= 0:
                self._direction = 1  # Switch direction
                

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


def with_progress(total):
    """
    Decorator factory to run a function with a progress bar.
    The decorated function should accept a callback parameter,
    which it will call with progress updates.
    
    Example:
        @with_progress(100)
        def process_data(progress_callback=None):
            for i in range(100):
                # do work
                if progress_callback:
                    progress_callback(i+1)
            return result
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get custom message from kwargs
            prefix = kwargs.pop('prefix', 'Progress:')
            suffix = kwargs.pop('suffix', 'Complete')
            
            # Create and start progress bar
            progress = ProgressBar(total=total, prefix=prefix, suffix=suffix)
            progress.start()
            
            def update_progress(value):
                progress.update(value)
            
            # Add the callback to the function arguments
            kwargs['progress_callback'] = update_progress
            
            try:
                # Run the function with the progress callback
                result = func(*args, **kwargs)
                # Ensure progress shows 100% at the end
                progress.update(total)
                return result
            finally:
                # Stop the progress bar
                progress.stop()
                
        return wrapper
    return decorator