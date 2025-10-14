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


def setup_logging():
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),  # Console output
            logging.FileHandler(logs_dir / "dictation.log")  # File output
        ]
    )

    # Reduce noise from pyaudio and other verbose libraries
    logging.getLogger('pyaudio').setLevel(logging.WARNING)
    logging.getLogger('faster_whisper').setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Dictation Manager Starting")
    logger.info("=" * 60)


def main():
    """Main entry point for the application"""
    # Setup logging first
    setup_logging()

    # Initialize configuration
    config = Config()
    
    # Initialize database
    db = Database(config.db_path)
    db.initialize()
    
    # Create and run GUI
    root = tk.Tk()
    app = MainWindow(root, config, db)
    root.mainloop()


if __name__ == "__main__":
    main()