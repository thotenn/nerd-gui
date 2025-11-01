"""
Keyboard output module for typing transcribed text.

Uses xdotool on Linux or PyAutoGUI on macOS to type text directly
into any application, mimicking nerd-dictation's behavior.
"""

import subprocess
import threading
from typing import Optional, Callable
import queue
import platform

from src.core.logging_controller import info, debug, warning, error, critical

# Detect platform
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Try to import PyAutoGUI for macOS
if IS_MACOS:
    try:
        import pyautogui
        PYAUTOGUI_AVAILABLE = True
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = False  # Disable failsafe for dictation use
    except ImportError:
        PYAUTOGUI_AVAILABLE = False
        warning("PyAutoGUI not available - install with: pip install pyautogui")
else:
    PYAUTOGUI_AVAILABLE = False


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
        self.use_pyautogui = False
        self.xdotool_available = False

        # Determine which backend to use
        if IS_MACOS:
            # macOS - use PyAutoGUI
            if PYAUTOGUI_AVAILABLE:
                self.use_pyautogui = True
                self.xdotool_available = True  # Treat as "available" for compatibility
                info("Using PyAutoGUI for keyboard output on macOS")
            else:
                error_msg = "PyAutoGUI not found. Install with: pip install pyautogui"
                error(error_msg)
                if on_error:
                    on_error(error_msg)
        else:
            # Linux - use xdotool
            try:
                subprocess.run(['xdotool', '--version'],
                              capture_output=True, check=True)
                self.xdotool_available = True
                info("xdotool found and working")
            except (subprocess.CalledProcessError, FileNotFoundError):
                error_msg = "xdotool not found. Install with: sudo apt install xdotool"
                error(error_msg)
                if on_error:
                    on_error(error_msg)

        self.output_queue = queue.Queue()
        self.is_running = False
        self.output_thread: Optional[threading.Thread] = None

        # Track previous text for correction support (like nerd-dictation)
        self.previous_text = ""

    def start(self):
        """Start the keyboard output worker."""
        if not self.xdotool_available:
            error("Cannot start keyboard output: xdotool not available")
            return False

        if self.is_running:
            warning("Keyboard output already running")
            return True

        self.is_running = True
        self.output_thread = threading.Thread(target=self._output_loop)
        self.output_thread.daemon = True
        self.output_thread.start()

        info("Started keyboard output worker")
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

        # Reset previous text on stop
        self.previous_text = ""

        info("Stopped keyboard output worker")

    def type_text(self, text: str, enable_correction: bool = True):
        """
        Queue text to be typed with optional correction support.

        If enable_correction is True, this will compare with previous text
        and delete/rewrite changed portions (like nerd-dictation).

        Args:
            text: Text to type
            enable_correction: Enable correction by comparing with previous text
        """
        if not self.xdotool_available:
            error("Cannot type text: xdotool not available")
            return

        if self.is_running:
            self.output_queue.put((text, enable_correction))
        else:
            warning("Keyboard output not running, cannot type text")

    def _output_loop(self):
        """Main output loop that runs in background thread."""
        while self.is_running:
            try:
                # Get text from queue with timeout
                item = self.output_queue.get(timeout=0.1)

                # Check for sentinel value
                if item is None:
                    break

                # Handle both old format (string) and new format (tuple)
                if isinstance(item, tuple):
                    text, enable_correction = item
                else:
                    text, enable_correction = item, False

                # Type the text with optional correction
                self._type_text_with_correction(text, enable_correction)

            except queue.Empty:
                continue
            except Exception as e:
                error(f"Output loop error: {e}")
                if self.on_error:
                    self.on_error(f"Output error: {e}")

    def _type_text_with_correction(self, text: str, enable_correction: bool):
        """
        Type text with optional correction (like nerd-dictation).

        Compares with previous text and deletes/rewrites changed portions.

        Args:
            text: Text to type
            enable_correction: If True, compare with previous text and correct
        """
        if not text.strip():
            return

        if enable_correction and self.previous_text:
            # Find where the texts start to differ (like nerd-dictation does)
            match_index = 0
            min_len = min(len(text), len(self.previous_text))

            for i in range(min_len):
                if text[i] != self.previous_text[i]:
                    match_index = i
                    break
            else:
                # Texts match up to min_len
                match_index = min_len

            # Calculate how many characters to delete
            chars_to_delete = len(self.previous_text) - match_index

            # Only type the new/changed portion
            new_text = text[match_index:]

            if chars_to_delete > 0:
                info(f"Correction: deleting {chars_to_delete} chars, typing '{new_text}'")
                # Send BackSpace keys to delete old text
                self._delete_characters(chars_to_delete)

            if new_text:
                # Type the new text
                self._type_text_immediate(new_text)
        else:
            # No correction, just type the text
            self._type_text_immediate(text)

        # Update previous text
        self.previous_text = text

    def _delete_characters(self, count: int):
        """
        Delete characters by sending BackSpace keys.

        Args:
            count: Number of characters to delete
        """
        if count <= 0:
            return

        try:
            if self.use_pyautogui:
                # macOS - use PyAutoGUI
                for _ in range(count):
                    pyautogui.press('backspace')
                debug(f"Deleted {count} characters (PyAutoGUI)")
            else:
                # Linux - use xdotool
                cmd = ['xdotool', 'key', '--'] + ['BackSpace'] * count
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    error_msg = f"xdotool delete failed: {result.stderr}"
                    error(error_msg)
                    if self.on_error:
                        self.on_error(error_msg)
                else:
                    debug(f"Deleted {count} characters")

        except Exception as e:
            error_msg = f"Failed to delete characters: {e}"
            error(error_msg)
            if self.on_error:
                self.on_error(error_msg)

    def _type_text_immediate(self, text: str):
        """
        Type text immediately using xdotool (Linux) or PyAutoGUI (macOS).

        Args:
            text: Text to type
        """
        if not text.strip():
            return  # Skip empty text

        try:
            # Clear any held modifier keys if enabled
            if self.clear_modifiers:
                self._clear_modifiers()

            if self.use_pyautogui:
                # macOS - use PyAutoGUI
                # PyAutoGUI types slower by default which is actually better for reliability
                pyautogui.write(text, interval=self.typing_delay)
                debug(f"Typed text (PyAutoGUI): '{text}'")
            else:
                # Linux - use xdotool
                # --clearmodifiers ensures no modifier keys interfere
                # -- prevents xdotool from interpreting options in the text
                cmd = ['xdotool', 'type', '--clearmodifiers', '--', text]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    error_msg = f"xdotool failed: {result.stderr}"
                    error(error_msg)
                    if self.on_error:
                        self.on_error(error_msg)
                else:
                    debug(f"Typed text: '{text}'")

        except Exception as e:
            error_msg = f"Failed to type text: {e}"
            error(error_msg)
            if self.on_error:
                self.on_error(error_msg)

    def _clear_modifiers(self):
        """Clear any held modifier keys."""
        try:
            if self.use_pyautogui:
                # PyAutoGUI doesn't need explicit modifier clearing
                # It handles this automatically
                pass
            else:
                # Linux - use xdotool
                modifiers = ['Shift', 'Control', 'Alt', 'Super', 'Meta']
                for modifier in modifiers:
                    subprocess.run(['xdotool', 'keyup', modifier],
                                 capture_output=True, check=False)
        except Exception as e:
            warning(f"Failed to clear modifiers: {e}")

    def type_immediate(self, text: str):
        """
        Type text immediately without queueing.

        Bypasses the queue and types directly. Use sparingly
        as this can block the calling thread.

        Args:
            text: Text to type immediately
        """
        if not self.xdotool_available:
            error("Cannot type text: xdotool not available")
            return

        self._type_text_immediate(text)

    def simulate_key_press(self, key: str):
        """
        Simulate a single key press.

        Args:
            key: Key name (e.g., 'Return', 'Space', 'BackSpace')
                 For PyAutoGUI: 'enter', 'space', 'backspace' (lowercase)
        """
        if not self.xdotool_available:
            error("Cannot press key: keyboard output not available")
            return

        try:
            if self.use_pyautogui:
                # Convert xdotool key names to PyAutoGUI key names
                key_map = {
                    'Return': 'enter',
                    'Space': 'space',
                    'BackSpace': 'backspace',
                    'Tab': 'tab',
                    'Escape': 'esc',
                }
                pyautogui_key = key_map.get(key, key.lower())
                pyautogui.press(pyautogui_key)
                debug(f"Pressed key (PyAutoGUI): {pyautogui_key}")
            else:
                subprocess.run(['xdotool', 'key', key],
                              capture_output=True, check=True)
                debug(f"Pressed key: {key}")
        except Exception as e:
            error(f"Failed to press key {key}: {e}")
            if self.on_error:
                self.on_error(f"Key press error: {e}")

    def reset_correction_state(self):
        """
        Reset the correction state.

        Call this when switching documents or contexts where
        the previous text is no longer relevant.
        """
        self.previous_text = ""
        debug("Reset correction state")

    def check_dependencies(self) -> dict:
        """
        Check if all required dependencies are available.

        Returns:
            Dictionary with dependency status
        """
        status = {
            'xdotool': False,
            'display': False,
            'pyautogui': False,
            'platform': platform.system(),
            'error': None
        }

        if IS_MACOS:
            # macOS - check PyAutoGUI
            status['pyautogui'] = PYAUTOGUI_AVAILABLE
            status['display'] = True  # macOS always has display

            if not PYAUTOGUI_AVAILABLE:
                status['error'] = "PyAutoGUI not found. Install with: pip install pyautogui"
                status['error'] += "\nNote: You'll need to grant Accessibility permissions in System Preferences"
            else:
                status['xdotool'] = True  # Mark as available for compatibility
        else:
            # Linux - check xdotool
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

        debug(f"Text processing - Input: '{text}'")

        # First, normalize punctuation spacing (Whisper often doesn't add spaces)
        processed = self._normalize_punctuation_spacing(text)
        debug(f"Text processing - After normalization: '{processed}'")

        # DON'T convert to lowercase - Whisper's capitalization is usually correct
        # Only apply specific text replacements that need case changes

        # Apply text replacements (case-sensitive)
        for old, new in self.text_replacements.items():
            processed = processed.replace(old, new)

        # Handle punctuation commands (spoken words to actual punctuation)
        # These need to be checked in lowercase
        words = processed.split()
        i = 0
        while i < len(words):
            word_lower = words[i].lower()
            if word_lower in self.punctuation_map:
                # Replace punctuation command with actual punctuation
                # Try to combine with previous word
                if i > 0 and len(words[i-1]) > 0:
                    words[i-1] += self.punctuation_map[word_lower]
                    words.pop(i)
                else:
                    words[i] = self.punctuation_map[word_lower]
                    i += 1
            else:
                i += 1

        processed = ' '.join(words)
        debug(f"Text processing - After replacements: '{processed}'")

        # Clean up extra spaces
        processed = ' '.join(processed.split())

        debug(f"Text processing - Final output: '{processed}'")
        return processed

    def _normalize_punctuation_spacing(self, text: str) -> str:
        """
        Add spaces after punctuation marks where they are missing.
        Whisper often returns text without spaces after punctuation.

        Args:
            text: Text with potentially missing spaces after punctuation

        Returns:
            Text with proper spacing after punctuation
        """
        import re

        original = text

        # Add space after sentence-ending punctuation if followed by any character (including ¿¡)
        # Handles: .Era → . Era, ?Los → ? Los, !Pero → ! Pero, .¿ → . ¿
        before = text
        text = re.sub(r'([.!?])([A-ZÑÁÉÍÓÚÜa-zñáéíóúü¿¡])', r'\1 \2', text)
        if text != before:
            debug(f"Normalization - After punctuation+letter: '{before}' → '{text}'")

        # Add space after commas if followed by a letter
        before = text
        text = re.sub(r'(,)([A-Za-zÑñÁÉÍÓÚÜáéíóúü])', r'\1 \2', text)
        if text != before:
            debug(f"Normalization - After comma+letter: '{before}' → '{text}'")

        # Add space after colons and semicolons if followed by a letter
        before = text
        text = re.sub(r'([;:])([A-Za-zÑñÁÉÍÓÚÜáéíóúü])', r'\1 \2', text)
        if text != before:
            debug(f"Normalization - After colon/semicolon+letter: '{before}' → '{text}'")

        # Handle cases where uppercase letter directly follows lowercase (word boundaries)
        # Handles: listoEra → listo Era, gastrosQue → gastros Que, tantasPuntadas → tantas Puntadas
        before = text
        text = re.sub(r'([a-zñáéíóúü])([A-ZÑÁÉÍÓÚÜ])', r'\1 \2', text)
        if text != before:
            debug(f"Normalization - After lowercase+uppercase: '{before}' → '{text}'")

        if text != original:
            info(f"Punctuation normalization applied: '{original}' → '{text}'")

        return text

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