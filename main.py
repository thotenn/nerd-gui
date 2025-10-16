#!/usr/bin/env python3
"""
Dictation Manager - Main Application
A GUI application to manage nerd-dictation with multiple language models
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import MainWindow
from src.core.config import Config
from src.core.database import Database
from src.core.logging_controller import configure_logging


def setup_logging(debug_enabled: bool = False):
    """
    Configure logging for the application.

    Args:
        debug_enabled: If True, show all logs in console. If False, only show warnings and errors.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler - level depends on debug_enabled flag
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    if debug_enabled:
        console_handler.setLevel(logging.DEBUG)  # Show all logs
    else:
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors

    # File handler - always log everything for troubleshooting
    file_handler = logging.FileHandler(logs_dir / "dictation.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root logger captures everything
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from pyaudio and other verbose libraries
    logging.getLogger('pyaudio').setLevel(logging.WARNING)
    logging.getLogger('faster_whisper').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Dictation Manager Starting")
    logger.info(f"Debug mode: {'ENABLED' if debug_enabled else 'DISABLED'}")
    logger.info("=" * 60)


def main():
    """Main entry point for the application"""
    # Initialize configuration first (without database to get db_path)
    config = Config()

    # Initialize database
    db = Database(config.db_path)
    db.initialize()

    # Connect config to database
    config.database = db

    # Migrate configuration from .env to database (one-time operation)
    config.migrate_from_env()

    # Reload settings from database
    config.reload_from_db()

    # Setup logging with debug flag from config
    setup_logging(debug_enabled=config.debug_enabled)

    # Configure our centralized logging controller
    configure_logging(database=db)

    # Create and run GUI
    root = tk.Tk()
    app = MainWindow(root, config, db)
    root.mainloop()


if __name__ == "__main__":
    main()