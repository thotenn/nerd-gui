#!/usr/bin/python3
"""
Dictation Manager - Main Application
A GUI application to manage nerd-dictation with multiple language models
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import MainWindow
from src.core.config import Config
from src.core.database import Database


def main():
    """Main entry point for the application"""
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