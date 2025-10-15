"""
Main window UI for Dictation Manager
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dictation_controller import DictationController
from ui.settings_window import SettingsWindow


class MainWindow:
    """Main application window"""
    
    def __init__(self, root, config, database):
        self.root = root
        self.config = config
        self.database = database
        self.controller = DictationController(config, database)
        
        # Window configuration
        self.root.title("Dictation Manager")
        self.root.geometry("600x300")
        self.root.resizable(True, True)

        # Set minimum size
        self.root.minsize(500, 250)
        
        # Create UI
        self._create_ui()
        
        # Update status
        self._update_status()
        
        # Auto-refresh status every 2 seconds
        self._schedule_status_update()
    
    def _create_ui(self):
        """Create the user interface"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="🎤 Dictation Manager",
            font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Status frame
        self._create_status_frame(main_frame)

        # Control buttons frame
        self._create_control_buttons(main_frame)
    
    def _create_status_frame(self, parent):
        """Create status display frame"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="15")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        status_frame.columnconfigure(1, weight=1)
        
        # Status indicator
        ttk.Label(status_frame, text="Estado:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_label = ttk.Label(status_frame, text="Detenido", font=("Arial", 10, "bold"))
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        # Current model
        ttk.Label(status_frame, text="Modelo:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.model_label = ttk.Label(status_frame, text="Ninguno")
        self.model_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Language
        ttk.Label(status_frame, text="Idioma:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.language_label = ttk.Label(status_frame, text="Ninguno")
        self.language_label.grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
    
    def _create_control_buttons(self, parent):
        """Create control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, pady=(0, 20))

        # Stop button
        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ STOP",
            command=self._on_stop_clicked,
            width=15
        )
        self.stop_btn.grid(row=0, column=0, padx=5)

        # Spanish button
        self.spanish_btn = ttk.Button(
            button_frame,
            text="🇪🇸 Español",
            command=lambda: self._on_language_clicked("spanish"),
            width=15
        )
        self.spanish_btn.grid(row=0, column=1, padx=5)

        # English button
        self.english_btn = ttk.Button(
            button_frame,
            text="🇬🇧 English",
            command=lambda: self._on_language_clicked("english"),
            width=15
        )
        self.english_btn.grid(row=0, column=2, padx=5)

        # Settings button
        self.settings_btn = ttk.Button(
            button_frame,
            text="⚙ Settings",
            command=self._on_settings_clicked,
            width=15
        )
        self.settings_btn.grid(row=0, column=3, padx=5)

    def _on_stop_clicked(self):
        """Handle stop button click"""
        self.controller.stop()
        self._update_status()
    
    def _on_language_clicked(self, language):
        """Handle language button click"""
        import logging
        logger = logging.getLogger(__name__)

        # Get language code (en, es, etc.)
        lang_code = self.config.languages.get(language, {}).get("code", language)
        logger.info(f"Language button clicked: {language} (code: {lang_code})")

        # Check if using Whisper backend
        if self.config.backend == "whisper":
            # Whisper doesn't need model_path, just language code
            logger.info(f"Starting Whisper backend with language '{lang_code}'")
            success, message = self.controller.start(lang_code, None)
            logger.info(f"Start result: success={success}, message={message}")
        else:
            # Vosk backend - needs model path
            # Get last used model for this language
            last_model = self.database.get_last_used_model(language)

            if last_model:
                # Use last model
                logger.info(f"Starting with last used model: {last_model['path']}")
                self.controller.restart(lang_code, last_model["path"])
            else:
                # Find first available model for this language
                models = self.config.get_available_models()
                matching_models = [m for m in models if m["language"] == language]

                if matching_models:
                    logger.info(f"Starting with first matching model: {matching_models[0]['path']}")
                    self.controller.restart(lang_code, matching_models[0]["path"])
                else:
                    logger.warning(f"No models found for language: {language}")

        self._update_status()

    def _on_settings_clicked(self):
        """Handle Settings button click"""
        # Open settings window
        SettingsWindow(self.root, self.config, self.database)

    def _update_status(self):
        """Update status display"""
        status = self.controller.get_status()
        
        if status["running"]:
            self.status_label.config(text="🟢 Activo", foreground="green")
            self.model_label.config(text=status["model_name"])
            
            lang_name = self.config.languages.get(
                status["language"],
                {"name": "Desconocido"}
            )["name"]
            self.language_label.config(text=lang_name)
        else:
            self.status_label.config(text="🔴 Detenido", foreground="red")
            self.model_label.config(text="Ninguno")
            self.language_label.config(text="Ninguno")
    
    def _schedule_status_update(self):
        """Schedule periodic status updates"""
        self._update_status()
        self.root.after(2000, self._schedule_status_update)