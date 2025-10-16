"""
Centralized logging controller for Dictation Manager

Provides unified logging with respect to debug_enabled setting in database.
Replaces both print statements and logger.* calls throughout the application.
"""

import logging
import time
import threading
import sys
import os
from typing import Optional, Any
from pathlib import Path


class ALSASuppressor:
    """Suppress ALSA messages that go directly to stderr"""

    def __init__(self):
        self.original_stderr = None
        self.suppressed_patterns = [
            b'ALSA lib pcm_dsnoop.c',
            b'ALSA lib pcm_dmix.c',
            b'ALSA lib pcm.c',
            b'ALSA lib pcm_oss.c',
            b'ALSA lib pcm_a52.c',
            b'ALSA lib confmisc.c',
            b'ALSA lib pcm_usb_stream.c',
            b'Unknown PCM cards.pcm.rear',
            b'Unknown PCM cards.pcm.center_lfe',
            b'Unknown PCM cards.pcm.side',
            b'Cannot open device /dev/dsp',
            b'a52 is only for playback',
            b'Invalid field card',
            b'Invalid card \'card\'',
            b'unable to open slave'
        ]

    def install(self):
        """Install stderr filter"""
        if self.original_stderr is None:
            self.original_stderr = sys.stderr
            sys.stderr = self

    def uninstall(self):
        """Uninstall stderr filter"""
        if self.original_stderr is not None:
            sys.stderr = self.original_stderr
            self.original_stderr = None

    def write(self, data):
        """Override write method to filter ALSA messages"""
        if any(pattern in data for pattern in self.suppressed_patterns):
            # Suppress ALSA messages
            return
        # Pass through other messages
        if self.original_stderr:
            self.original_stderr.write(data)
            self.original_stderr.flush()

    def flush(self):
        """Override flush method"""
        if self.original_stderr:
            self.original_stderr.flush()


class LogController:
    """
    Centralized logging controller that respects debug_enabled database setting.

    This class provides a unified interface for all logging operations in the
    application, replacing both print statements and logger.* calls.

    Rules:
    - ERROR, WARNING, CRITICAL: Always shown
    - INFO: Always shown (important system messages)
    - DEBUG: Only shown if debug_enabled = True in database
    """

    _instance: Optional['LogController'] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the logging controller."""
        self._database = None
        self._debug_enabled = False
        self._last_debug_check = 0.0
        self._cache_ttl = 5.0  # Cache debug setting for 5 seconds

        # Add caching for log filters
        self._log_filters_cache = {}
        self._last_filters_check = 0.0

        # Initialize ALSA suppressor
        self._alsa_suppressor = ALSASuppressor()

        # Setup standard Python logging
        self._setup_logging()

        # Create module-specific loggers
        self._loggers = {}

    @classmethod
    def get_instance(cls) -> 'LogController':
        """Get singleton instance of LogController."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def configure(self, database) -> None:
        """
        Configure the log controller with database connection.

        Args:
            database: Database connection object for querying debug_enabled
        """
        self._database = database
        # Initial load of debug setting
        self._update_debug_setting()

    def _setup_logging(self) -> None:
        """Setup standard Python logging configuration."""
        # Create logs directory if it doesn't exist
        log_dir = Path.home() / ".dictation" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure root logger with INFO level initially (will be updated dynamically)
        logging.basicConfig(
            level=logging.INFO,  # Default to INFO level
            format='[%(levelname)s] [%(name)s] [%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),  # Console output
                logging.FileHandler(log_dir / 'dictation.log', encoding='utf-8')
            ]
        )

        # Suppress verbose external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('faster_whisper').setLevel(logging.WARNING)
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
        logging.getLogger('datasets').setLevel(logging.WARNING)

        # Suppress audio-related logs (ALSA, PyAudio, etc.)
        logging.getLogger('pyaudio').setLevel(logging.ERROR)
        logging.getLogger('sounddevice').setLevel(logging.ERROR)
        logging.getLogger('alsa').setLevel(logging.ERROR)

        # Install ALSA stderr suppressor
        self._alsa_suppressor.install()

    def _get_logger(self, module_name: str) -> logging.Logger:
        """Get or create logger for specific module."""
        if module_name not in self._loggers:
            self._loggers[module_name] = logging.getLogger(module_name)
        return self._loggers[module_name]

    def _update_debug_setting(self) -> None:
        """Update debug_enabled setting from database with caching."""
        current_time = time.time()
        old_debug_enabled = self._debug_enabled

        # Use cached value if within TTL
        if current_time - self._last_debug_check < self._cache_ttl:
            return

        self._last_debug_check = current_time

        # Try to get setting from database
        if self._database:
            try:
                debug_str = self._database.get_setting('debug_enabled', 'false')
                self._debug_enabled = debug_str.lower() in ('true', '1', 'yes')
            except Exception as e:
                # If database fails, assume debug enabled for safety
                self._debug_enabled = True
                self._fallback_print(f"Warning: Could not read debug setting from database: {e}")
        else:
            # No database available, use debug mode for development
            self._debug_enabled = True

        # Update global logging level if debug setting changed
        if old_debug_enabled != self._debug_enabled:
            self._update_global_logging_level()

    def _update_global_logging_level(self) -> None:
        """Update the global logging level based on debug_enabled setting."""
        if self._debug_enabled:
            # Enable debug logging globally
            logging.getLogger().setLevel(logging.DEBUG)
            # Set specific external libraries to WARNING to avoid spam
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('requests').setLevel(logging.WARNING)
            logging.getLogger('faster_whisper').setLevel(logging.WARNING)
            logging.getLogger('transformers').setLevel(logging.WARNING)
            logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
            logging.getLogger('datasets').setLevel(logging.WARNING)
        else:
            # Disable debug logging globally
            logging.getLogger().setLevel(logging.INFO)
            # External libraries remain at WARNING level (already set in _setup_logging)

    def _fallback_print(self, message: str) -> None:
        """Fallback print method if logging system fails."""
        print(f"[FALLBACK] {message}")

    def _should_log(self, level: str) -> bool:
        """
        Check if message should be logged based on level, debug setting, and user filters.

        Args:
            level: Log level (debug, info, warning, error, critical)

        Returns:
            True if message should be logged
        """
        # Always show debug if enabled (debug setting takes precedence)
        if level == 'debug':
            self._update_debug_setting()
            if self._debug_enabled:
                return True
            return False

        # For other levels, check user filters if available
        return self._check_log_filter(level)

    def _update_log_filters_cache(self) -> None:
        """Update log filters cache from database with same TTL as debug setting."""
        current_time = time.time()

        # Use cached value if within TTL (same TTL as debug setting)
        if current_time - self._last_filters_check < self._cache_ttl:
            return

        self._last_filters_check = current_time

        # Try to get filters from database
        if self._database:
            try:
                self._log_filters_cache = self._database.get_log_filters()
            except Exception as e:
                # If database fails, assume all filters enabled for safety
                self._log_filters_cache = {
                    'INFO': True,
                    'WARNING': True,
                    'ERROR': True,
                    'CRITICAL': True
                }
                self._fallback_print(f"Warning: Could not read log filters from database: {e}")
        else:
            # No database available, use all enabled for development
            self._log_filters_cache = {
                'INFO': True,
                'WARNING': True,
                'ERROR': True,
                'CRITICAL': True
            }

    def _check_log_filter(self, level: str) -> bool:
        """
        Check if a log level is enabled in user filters.

        Args:
            level: Log level to check

        Returns:
            True if level is enabled in filters, True if no filters exist (default behavior)
        """
        if not self._database:
            # No database available, assume all levels are enabled
            return True

        # Update cache if needed
        self._update_log_filters_cache()

        level_upper = level.upper()
        # Return True if filter is enabled or if filter doesn't exist (default to True)
        return self._log_filters_cache.get(level_upper, True)

    def _get_caller_module(self) -> str:
        """Extract module name from call stack."""
        import inspect

        # Get the calling frame (skip _log, _should_log, and the public method)
        frame = inspect.currentframe()
        try:
            # Go up the call stack to find the actual caller
            # 0: _get_caller_module, 1: _log, 2: should_log, 3: public method, 4: actual caller
            caller_frame = frame.f_back.f_back.f_back.f_back
            if caller_frame:
                module_name = caller_frame.f_globals.get('__name__', 'unknown')
                # Extract just the module part (e.g., 'dictation_controller' from 'src.core.dictation_controller')
                return module_name.split('.')[-1] if '.' in module_name else module_name
        except (AttributeError, IndexError):
            pass
        finally:
            del frame

        return 'unknown'

    def _log(self, level: str, message: str, *args, **kwargs) -> None:
        """
        Internal logging method with level checking and database integration.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional keyword arguments
        """
        try:
            # Check if we should log this message
            if not self._should_log(level):
                return

            # Get module logger
            module_name = self._get_caller_module()
            logger = self._get_logger(module_name)

            # Format message if arguments provided
            if args:
                formatted_message = message % args
            else:
                formatted_message = message

            # Add extra context if provided
            extra = kwargs.get('extra', {})

            # Log to appropriate logger method
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(formatted_message, extra=extra)

        except Exception as e:
            # Fallback to print if logging fails
            self._fallback_print(f"Logging failed: {e} - Original message: [{level.upper()}] {message}")

    def debug(self, message: str, *args, **kwargs) -> None:
        """
        Log debug message (only if debug_enabled = True).

        Args:
            message: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional keyword arguments
        """
        self._log('debug', message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """
        Log info message (always shown).

        Args:
            message: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional keyword arguments
        """
        self._log('info', message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """
        Log warning message (always shown).

        Args:
            message: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional keyword arguments
        """
        self._log('warning', message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """
        Log error message (always shown).

        Args:
            message: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional keyword arguments
        """
        self._log('error', message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """
        Log critical message (always shown).

        Args:
            message: Message to log
            *args: Arguments for message formatting
            **kwargs: Additional keyword arguments
        """
        self._log('critical', message, *args, **kwargs)

    def is_debug_enabled(self) -> bool:
        """
        Check if debug logging is currently enabled.

        Returns:
            True if debug logging is enabled
        """
        self._update_debug_setting()
        return self._debug_enabled

    def force_debug_update(self) -> None:
        """Force immediate update of debug setting from database."""
        self._last_debug_check = 0.0  # Reset cache to force update
        self._update_debug_setting()

    def get_cache_info(self) -> dict:
        """
        Get information about debug setting cache.

        Returns:
            Dictionary with cache information
        """
        return {
            'debug_enabled': self._debug_enabled,
            'last_update': self._last_debug_check,
            'cache_ttl': self._cache_ttl,
            'cache_age': time.time() - self._last_debug_check
        }

    def get_log_filters(self) -> dict:
        """
        Get current log filter settings.

        Returns:
            Dictionary with current filter settings
        """
        if not self._database:
            return {
                'INFO': True,
                'WARNING': True,
                'ERROR': True,
                'CRITICAL': True
            }

        try:
            return self._database.get_log_filters()
        except Exception as e:
            self._fallback_print(f"Warning: Could not get log filters, returning defaults: {e}")
            return {
                'INFO': True,
                'WARNING': True,
                'ERROR': True,
                'CRITICAL': True
            }

    def update_log_filters(self, filters: dict) -> bool:
        """
        Update log filter settings.

        Args:
            filters: Dictionary with filter settings
                    {'INFO': bool, 'WARNING': bool, 'ERROR': bool, 'CRITICAL': bool}

        Returns:
            True if successful
        """
        if not self._database:
            self._fallback_print("Warning: No database available, cannot save log filters")
            return False

        try:
            success = self._database.save_log_filters(filters)
            if success:
                # Force cache update next time to ensure filters take effect immediately
                self._last_debug_check = 0.0
                self._last_filters_check = 0.0
                self._log_filters_cache = {}  # Clear cache
            return success
        except Exception as e:
            self._fallback_print(f"Error saving log filters: {e}")
            return False

    def is_log_level_enabled(self, level: str) -> bool:
        """
        Check if a specific log level is currently enabled.

        Args:
            level: Log level to check (info, warning, error, critical, debug)

        Returns:
            True if the level is enabled
        """
        return self._should_log(level)


# Global instance for easy access throughout the application
log = LogController.get_instance()


def configure_logging(database) -> None:
    """
    Configure the global logging controller.

    This function should be called once during application startup.

    Args:
        database: Database connection object
    """
    log.configure(database)


def get_log_controller() -> LogController:
    """
    Get the global logging controller instance.

    Returns:
        LogController instance
    """
    return log


# Convenience functions for direct access
def debug(message: str, *args, **kwargs) -> None:
    """Log debug message."""
    log.debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs) -> None:
    """Log info message."""
    log.info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs) -> None:
    """Log warning message."""
    log.warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs) -> None:
    """Log error message."""
    log.error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs) -> None:
    """Log critical message."""
    log.critical(message, *args, **kwargs)


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled."""
    return log.is_debug_enabled()


def force_debug_update() -> None:
    """Force update of debug setting from database."""
    log.force_debug_update()