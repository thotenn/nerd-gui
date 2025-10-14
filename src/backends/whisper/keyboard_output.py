"""
Keyboard output module for typing transcribed text.

Uses xdotool to type text directly into any application,
mimicking nerd-dictation's behavior.
"""

import subprocess
import time
import threading
import logging
from typing import Optional, Callable
import queue

logger = logging.getLogger(__name__)


class KeyboardOutput:
    """
    Types transcribed text using xdotool.

    Provides the same typing behavior as nerd-dictation,
    with proper timing and special character handling.
    """

    def __init__(self,
                 typing_delay: float = 0.01,
                 clear_modifiers: bool = True,
                 on_error: Optional[Callable[[str], None]] = None):
        """
        Initialize keyboard output.

        Args:
            typing_delay: Delay between keystrokes in seconds
            clear_modifiers: Clear modifier keys before typing
            on_error: Optional error callback
        """
        self.typing_delay = typing_delay
        self.clear_modifiers = clear_modifiers
        self.on_error = on_error

        # Check if xdotool is available
        try:
            subprocess.run(['xdotool', '--version'],
                          capture_output=True, check=True)
            self.xdotool_available = True
            logger.info("xdotool found and working")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.xdotool_available = False
            error_msg = "xdotool not found. Install with: sudo apt install xdotool"
            logger.error(error_msg)
            if on_error:
                on_error(error_msg)

        self.output_queue = queue.Queue()
        self.is_running = False
        self.output_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the keyboard output worker."""
        if not self.xdotool_available:
            logger.error("Cannot start keyboard output: xdotool not available")
            return False

        if self.is_running:
            logger.warning("Keyboard output already running")
            return True

        self.is_running = True
        self.output_thread = threading.Thread(target=self._output_loop)
        self.output_thread.daemon = True
        self.output_thread.start()

        logger.info("Started keyboard output worker")
        return True

    def stop(self):
        """Stop the keyboard output worker."""
        if not self.is_running:
            return

        self.is_running = False

        # Add sentinel value to wake up worker
        self.output_queue.put(None)

        if self.output_thread:
            self.output_thread.join(timeout=1.0)

        logger.info("Stopped keyboard output worker")

    def type_text(self, text: str):
        """
        Queue text to be typed.

        Args:
            text: Text to type
        """
        if not self.xdotool_available:
            logger.error("Cannot type text: xdotool not available")
            return

        if self.is_running:
            self.output_queue.put(text)
        else:
            logger.warning("Keyboard output not running, cannot type text")

    def _output_loop(self):
        """Main output loop that runs in background thread."""
        while self.is_running:
            try:
                # Get text from queue with timeout
                text = self.output_queue.get(timeout=0.1)

                # Check for sentinel value
                if text is None:
                    break

                # Type the text
                self._type_text_immediate(text)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Output loop error: {e}")
                if self.on_error:
                    self.on_error(f"Output error: {e}")

    def _type_text_immediate(self, text: str):
        """
        Type text immediately using xdotool.

        Args:
            text: Text to type
        """
        if not text.strip():
            return  # Skip empty text

        try:
            # Clear any held modifier keys if enabled
            if self.clear_modifiers:
                self._clear_modifiers()

            # Use xdotool to type the text
            # --clearmodifiers ensures no modifier keys interfere
            # -- prevents xdotool from interpreting options in the text
            cmd = ['xdotool', 'type', '--clearmodifiers', '--', text]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                error_msg = f"xdotool failed: {result.stderr}"
                logger.error(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
            else:
                logger.debug(f"Typed text: '{text}'")

        except Exception as e:
            error_msg = f"Failed to type text: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)

    def _clear_modifiers(self):
        """Clear any held modifier keys."""
        try:
            # Release common modifier keys
            modifiers = ['Shift', 'Control', 'Alt', 'Super', 'Meta']
            for modifier in modifiers:
                subprocess.run(['xdotool', 'keyup', modifier],
                             capture_output=True, check=False)
        except Exception as e:
            logger.warning(f"Failed to clear modifiers: {e}")

    def type_immediate(self, text: str):
        """
        Type text immediately without queueing.

        Bypasses the queue and types directly. Use sparingly
        as this can block the calling thread.

        Args:
            text: Text to type immediately
        """
        if not self.xdotool_available:
            logger.error("Cannot type text: xdotool not available")
            return

        self._type_text_immediate(text)

    def simulate_key_press(self, key: str):
        """
        Simulate a single key press.

        Args:
            key: Key name (e.g., 'Return', 'Space', 'BackSpace')
        """
        if not self.xdotool_available:
            logger.error("Cannot press key: xdotool not available")
            return

        try:
            subprocess.run(['xdotool', 'key', key],
                          capture_output=True, check=True)
            logger.debug(f"Pressed key: {key}")
        except Exception as e:
            logger.error(f"Failed to press key {key}: {e}")
            if self.on_error:
                self.on_error(f"Key press error: {e}")

    def check_dependencies(self) -> dict:
        """
        Check if all required dependencies are available.

        Returns:
            Dictionary with dependency status
        """
        status = {
            'xdotool': False,
            'display': False,
            'error': None
        }

        # Check xdotool
        try:
            subprocess.run(['xdotool', '--version'],
                          capture_output=True, check=True)
            status['xdotool'] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            status['error'] = "xdotool not found. Install with: sudo apt install xdotool"

        # Check display
        try:
            subprocess.run(['xdpyinfo'], capture_output=True, check=True)
            status['display'] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            if not status['error']:
                status['error'] = "No display available or xdpyinfo not installed"

        return status


class TextProcessor:
    """
    Processes transcribed text before typing.

    Handles text formatting, capitalization, and special commands.
    """

    def __init__(self):
        """Initialize text processor."""
        # Common text replacements (similar to nerd-dictation)
        self.text_replacements = {
            # Capitalization
            ' i ': ' I ',
            ' i\'': ' I\'',

            # Common tech terms
            'api': 'API',
            'linux': 'Linux',
            'ubuntu': 'Ubuntu',
            'python': 'Python',
            'github': 'GitHub',

            # Remove filler words
            ' um ': ' ',
            ' uh ': ' ',
            ' eh ': ' ',
        }

        # Punctuation commands (spoken words to actual punctuation)
        self.punctuation_map = {
            'period': '.',
            'comma': ',',
            'question mark': '?',
            'exclamation mark': '!',
            'colon': ':',
            'semicolon': ';',
            'new line': '\n',
            'newline': '\n',
            'paragraph': '\n\n',
        }

    def process_text(self, text: str) -> str:
        """
        Process transcribed text before output.

        Args:
            text: Raw transcribed text

        Returns:
            Processed text
        """
        if not text:
            return text

        processed = text.lower()

        # Apply text replacements
        for old, new in self.text_replacements.items():
            processed = processed.replace(old, new)

        # Handle punctuation commands
        words = processed.split()
        i = 0
        while i < len(words):
            word = words[i]
            if word in self.punctuation_map:
                # Replace punctuation command with actual punctuation
                # Try to combine with previous word
                if i > 0 and len(words[i-1]) > 0:
                    words[i-1] += self.punctuation_map[word]
                else:
                    words[i] = self.punctuation_map[word]
                    i += 1
                # Remove the punctuation command
                if i < len(words) and words[i] == word:
                    words.pop(i)
                else:
                    words.pop(i)
            else:
                i += 1

        # Capitalize first letter of sentences
        processed = ' '.join(words)
        processed = self._capitalize_sentences(processed)

        # Clean up extra spaces
        processed = ' '.join(processed.split())

        return processed

    def _capitalize_sentences(self, text: str) -> str:
        """
        Capitalize the first letter of each sentence.

        Args:
            text: Text to capitalize

        Returns:
            Text with proper sentence capitalization
        """
        sentences = text.split('. ')
        capitalized = []

        for sentence in sentences:
            if sentence.strip():
                # Capitalize first letter
                sentence = sentence.strip()
                if sentence:
                    sentence = sentence[0].upper() + sentence[1:]
                capitalized.append(sentence)

        return '. '.join(capitalized)