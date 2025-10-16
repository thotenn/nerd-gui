"""
Main window UI for Dictation Manager
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys
import threading

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dictation_controller import DictationController


class MainWindow:
    """Main application window"""

    def __init__(self, root, config, database):
        self.root = root
        self.config = config
        self.database = database
        self.controller = DictationController(config, database)

        # Window configuration
        self.root.title("Dictation Manager")
        # Start with main view size since we show main view initially
        self.root.geometry("600x350")
        self.root.resizable(True, True)

        # Set minimum size for main view
        self.root.minsize(500, 300)

        # Center window on screen initially
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 350) // 2
        self.root.geometry(f"600x350+{x}+{y}")

        # Create main container
        self.container = ttk.Frame(self.root)
        self.container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        # Create both views
        self._create_main_view()
        self._create_settings_view()

        # Show main view initially
        self.show_main_view()

        # Update UI with current config values
        self._update_ui_from_config()

        # Ensure controller has the correct backend from config
        self.controller.reload_backend_from_config()

        # Update status
        self._update_status()

        # Auto-refresh status every 2 seconds
        self._schedule_status_update()

    def _create_main_view(self):
        """Create the main view with status and controls"""
        self.main_frame = ttk.Frame(self.container, padding="20")

        # Configure grid
        self.main_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(
            self.main_frame,
            text="🎤 Dictation Manager",
            font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Status frame
        self._create_status_frame(self.main_frame)

        # Control buttons frame
        self._create_control_buttons(self.main_frame)

        # Download progress frame (hidden by default)
        self._create_progress_frame(self.main_frame)

    def _create_settings_view(self):
        """Create the settings view"""
        self.settings_frame = ttk.Frame(self.container, padding="20")

        # Configure grid
        self.settings_frame.columnconfigure(0, weight=1)
        self.settings_frame.rowconfigure(1, weight=1)

        # Settings title
        settings_title = ttk.Label(
            self.settings_frame,
            text="⚙ Settings",
            font=("Arial", 16, "bold")
        )
        settings_title.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)

        # Content frame
        content_frame = ttk.Frame(self.settings_frame)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)

        # Backend selection
        self._create_backend_section(content_frame)

        # Debug settings
        self._create_debug_section(content_frame)

        # Settings buttons
        self._create_settings_buttons(self.settings_frame)

    def _create_backend_section(self, parent):
        """Create backend selection section"""
        backend_frame = ttk.LabelFrame(parent, text="Backend Selection", padding="15")
        backend_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        backend_frame.columnconfigure(0, weight=1)

        # Info label
        info_label = ttk.Label(
            backend_frame,
            text="Select the speech recognition backend:",
            font=("Arial", 10)
        )
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Backend radio buttons
        self.backend_var = tk.StringVar(value="vosk")

        vosk_radio = ttk.Radiobutton(
            backend_frame,
            text="Vosk (CPU-based, fast startup)",
            variable=self.backend_var,
            value="vosk",
            command=self._on_backend_changed
        )
        vosk_radio.grid(row=1, column=0, sticky=tk.W, pady=5)

        whisper_radio = ttk.Radiobutton(
            backend_frame,
            text="Whisper (GPU-accelerated, higher accuracy)",
            variable=self.backend_var,
            value="whisper",
            command=self._on_backend_changed
        )
        whisper_radio.grid(row=2, column=0, sticky=tk.W, pady=5)

        # Backend-specific settings frames
        self._create_vosk_settings(backend_frame)
        self._create_whisper_settings(backend_frame)

    def _create_vosk_settings(self, parent):
        """Create Vosk backend configuration UI"""
        self.vosk_frame = ttk.LabelFrame(parent, text="Vosk Models", padding="15")
        self.vosk_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        self.vosk_frame.columnconfigure(1, weight=1)

        # Get available Vosk models
        all_models = self.config.get_available_models()
        spanish_models = [m["name"] for m in all_models if m["language"] == "spanish"]
        english_models = [m["name"] for m in all_models if m["language"] == "english"]

        # Spanish model selection
        ttk.Label(
            self.vosk_frame,
            text="Spanish Model:",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.vosk_spanish_var = tk.StringVar()
        self.vosk_spanish_combo = ttk.Combobox(
            self.vosk_frame,
            textvariable=self.vosk_spanish_var,
            values=spanish_models,
            state="readonly",
            width=50
        )
        self.vosk_spanish_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))

        if spanish_models:
            self.vosk_spanish_combo.set(spanish_models[0])

        # Warning for Spanish if no models
        if not spanish_models:
            ttk.Label(
                self.vosk_frame,
                text="⚠ No Spanish models found in models directory",
                foreground="orange"
            ).grid(row=1, column=1, sticky=tk.W, pady=(0, 10))

        # English model selection
        ttk.Label(
            self.vosk_frame,
            text="English Model:",
            font=("Arial", 10, "bold")
        ).grid(row=2, column=0, sticky=tk.W, pady=(10, 5))

        self.vosk_english_var = tk.StringVar()
        self.vosk_english_combo = ttk.Combobox(
            self.vosk_frame,
            textvariable=self.vosk_english_var,
            values=english_models,
            state="readonly",
            width=50
        )
        self.vosk_english_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 5))

        if english_models:
            self.vosk_english_combo.set(english_models[0])

        # Warning for English if no models
        if not english_models:
            ttk.Label(
                self.vosk_frame,
                text="⚠ No English models found in models directory",
                foreground="orange"
            ).grid(row=3, column=1, sticky=tk.W)

        # Info about models location
        models_path = str(self.config.models_dir)
        ttk.Label(
            self.vosk_frame,
            text=f"Models directory: {models_path}",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(15, 0))

    def _create_whisper_settings(self, parent):
        """Create Whisper backend configuration UI"""
        self.whisper_frame = ttk.LabelFrame(parent, text="Whisper Configuration", padding="15")
        self.whisper_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        self.whisper_frame.columnconfigure(1, weight=1)

        # Info about Whisper models being multilingual
        info_label = ttk.Label(
            self.whisper_frame,
            text="ℹ️ Whisper models are multilingual - one model works for all languages",
            font=("Arial", 9, "italic"),
            foreground="#0066cc"
        )
        info_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        # Whisper model sizes - using official Systran faster-whisper model names
        model_options = [
            ("Tiny (~75MB, fastest)", "Systran/faster-whisper-tiny"),
            ("Base (~145MB)", "Systran/faster-whisper-base"),
            ("Small (~466MB)", "Systran/faster-whisper-small"),
            ("Medium (~1.5GB)", "Systran/faster-whisper-medium"),
            ("Large-v3 (~3.09GB, most accurate)", "Systran/faster-whisper-large-v3")
        ]

        # Extract display names and actual model IDs
        self.model_display_names = [display for display, _ in model_options]
        self.model_ids = {display: model_id for display, model_id in model_options}
        self.model_id_to_display = {model_id: display for display, model_id in model_options}

        # Model selection
        ttk.Label(
            self.whisper_frame,
            text="Model Size:",
            font=("Arial", 10, "bold")
        ).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        self.whisper_model_var = tk.StringVar(value="Medium (~1.5GB)")
        self.whisper_model_combo = ttk.Combobox(
            self.whisper_frame,
            textvariable=self.whisper_model_var,
            values=self.model_display_names,
            state="readonly",
            width=35
        )
        self.whisper_model_combo.grid(row=1, column=1, sticky=tk.W, pady=(0, 5), columnspan=2)

        # Download info
        ttk.Label(
            self.whisper_frame,
            text="✓ Downloaded automatically on first use from: huggingface.co/Systran\n"
                 "✓ Saved to: ~/.cache/huggingface/hub/\n"
                 "✓ Larger models = better accuracy but slower and more VRAM",
            font=("Arial", 9),
            foreground="gray"
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # Separator
        ttk.Separator(self.whisper_frame, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 20)
        )

        # Advanced settings
        self._create_whisper_advanced_settings()

    def _create_whisper_advanced_settings(self):
        """Create Whisper advanced parameters section"""
        # Advanced settings label
        ttk.Label(
            self.whisper_frame,
            text="Advanced Settings",
            font=("Arial", 11, "bold")
        ).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Device selection
        ttk.Label(self.whisper_frame, text="Device:", font=("Arial", 9)).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.whisper_device_var = tk.StringVar(value="cuda")
        device_combo = ttk.Combobox(
            self.whisper_frame,
            textvariable=self.whisper_device_var,
            values=["cuda", "cpu"],
            state="readonly",
            width=15
        )
        device_combo.grid(row=6, column=1, sticky=tk.W, pady=5)

        # Compute Type selection
        ttk.Label(self.whisper_frame, text="Compute Type:", font=("Arial", 9)).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.whisper_compute_type_var = tk.StringVar(value="float16")
        compute_combo = ttk.Combobox(
            self.whisper_frame,
            textvariable=self.whisper_compute_type_var,
            values=["float16", "float32"],
            state="readonly",
            width=15
        )
        compute_combo.grid(row=7, column=1, sticky=tk.W, pady=5)

        # Device Index
        ttk.Label(self.whisper_frame, text="Device Index:", font=("Arial", 9)).grid(row=8, column=0, sticky=tk.W, pady=5)
        self.whisper_device_index_var = tk.StringVar(value="")
        device_index_entry = ttk.Entry(self.whisper_frame, textvariable=self.whisper_device_index_var, width=18)
        device_index_entry.grid(row=8, column=1, sticky=tk.W, pady=5)

        # Silence Duration
        ttk.Label(self.whisper_frame, text="Silence Duration:", font=("Arial", 9)).grid(row=9, column=0, sticky=tk.W, pady=5)
        self.whisper_silence_var = tk.DoubleVar(value=1.0)
        silence_spinbox = ttk.Spinbox(
            self.whisper_frame,
            from_=0.5, to=2.0, increment=0.1,
            textvariable=self.whisper_silence_var,
            width=16
        )
        silence_spinbox.grid(row=9, column=1, sticky=tk.W, pady=5)

        # Energy Threshold
        ttk.Label(self.whisper_frame, text="Energy Threshold:", font=("Arial", 9)).grid(row=10, column=0, sticky=tk.W, pady=5)
        self.whisper_energy_var = tk.DoubleVar(value=0.008)
        energy_spinbox = ttk.Spinbox(
            self.whisper_frame,
            from_=0.0001, to=0.01, increment=0.0001,
            textvariable=self.whisper_energy_var,
            width=16
        )
        energy_spinbox.grid(row=10, column=1, sticky=tk.W, pady=5)

        # Min Audio Length
        ttk.Label(self.whisper_frame, text="Min Audio Length:", font=("Arial", 9)).grid(row=11, column=0, sticky=tk.W, pady=5)
        self.whisper_min_audio_var = tk.DoubleVar(value=0.3)
        min_audio_spinbox = ttk.Spinbox(
            self.whisper_frame,
            from_=0.3, to=1.0, increment=0.1,
            textvariable=self.whisper_min_audio_var,
            width=16
        )
        min_audio_spinbox.grid(row=11, column=1, sticky=tk.W, pady=5)

    def _create_debug_section(self, parent):
        """Create debug settings section"""
        debug_frame = ttk.LabelFrame(parent, text="Debug Settings", padding="15")
        debug_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        debug_frame.columnconfigure(0, weight=1)

        # Debug checkbox
        self.debug_var = tk.BooleanVar(value=False)
        debug_check = ttk.Checkbutton(
            debug_frame,
            text="Enable Debug Logging",
            variable=self.debug_var
        )
        debug_check.grid(row=0, column=0, sticky=tk.W, pady=5)

        # Info label
        ttk.Label(
            debug_frame,
            text="When enabled, detailed debug logs will be shown in the console and log file.\n"
                 "Disable this for a cleaner console output (errors and warnings will still be shown).",
            font=("Arial", 9),
            foreground="gray",
            wraplength=700,
            justify=tk.LEFT
        ).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

    def _create_settings_buttons(self, parent):
        """Create settings view buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, pady=(20, 0))

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_settings_cancel,
            width=15
        )
        cancel_btn.grid(row=0, column=0, padx=5)

        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="💾 Save",
            command=self._on_settings_save,
            width=15
        )
        save_btn.grid(row=0, column=1, padx=5)

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

    def _create_progress_frame(self, parent):
        """Create download progress frame (hidden by default)"""
        self.progress_frame = ttk.Frame(parent)
        self.progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        self.progress_frame.columnconfigure(0, weight=1)

        # Progress label
        self.progress_label = ttk.Label(
            self.progress_frame,
            text="Descargando modelo...",
            font=("Arial", 10)
        )
        self.progress_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='indeterminate',
            length=400
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Hide by default
        self.progress_frame.grid_remove()

    def show_main_view(self):
        """Show the main view"""
        self.settings_frame.grid_remove()
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Get current window position
        self.root.update_idletasks()
        x = self.root.winfo_x()
        y = self.root.winfo_y()

        # Compact size for main view, maintaining position
        self.root.geometry(f"600x350+{x}+{y}")
        self.root.minsize(500, 300)
        # No max size restriction for main view (allow free resizing)

    def show_settings_view(self):
        """Show the settings view"""
        self.main_frame.grid_remove()
        self.settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Get current window position
        self.root.update_idletasks()
        x = self.root.winfo_x()
        y = self.root.winfo_y()

        # Larger size for settings to show all content, maintaining position
        # Increased height to accommodate all Whisper settings and debug options
        self.root.geometry(f"850x900+{x}+{y}")
        self.root.minsize(800, 850)    # Minimum to ensure all content is visible
        # No max size restriction (allow free resizing)

        # Load current settings
        self._load_settings()

        # Update the window to ensure proper layout
        self.root.update_idletasks()

    def _load_settings(self):
        """Load current settings from database or config"""
        # Load backend
        backend = self.database.get_setting('backend', self.config.backend)
        self.backend_var.set(backend)

        # Load Vosk settings
        vosk_es = self.database.get_setting('vosk_model_es', '')
        if vosk_es and vosk_es in self.vosk_spanish_combo['values']:
            self.vosk_spanish_var.set(vosk_es)

        vosk_en = self.database.get_setting('vosk_model_en', '')
        if vosk_en and vosk_en in self.vosk_english_combo['values']:
            self.vosk_english_var.set(vosk_en)

        # Load Whisper settings
        model_id = self.database.get_setting('whisper_model', self.config.whisper_model)
        display_name = self.model_id_to_display.get(model_id, "Medium (~1.5GB)")
        self.whisper_model_var.set(display_name)

        self.whisper_device_var.set(
            self.database.get_setting('whisper_device', self.config.whisper_device)
        )
        self.whisper_compute_type_var.set(
            self.database.get_setting('whisper_compute_type', self.config.whisper_compute_type)
        )
        self.whisper_device_index_var.set(
            self.database.get_setting('whisper_device_index', '')
        )

        # Load numeric settings
        try:
            self.whisper_silence_var.set(
                float(self.database.get_setting('whisper_silence_duration',
                      str(self.config.whisper_silence_duration)))
            )
        except ValueError:
            self.whisper_silence_var.set(1.0)

        try:
            self.whisper_energy_var.set(
                float(self.database.get_setting('whisper_energy_threshold',
                      str(self.config.whisper_energy_threshold)))
            )
        except ValueError:
            self.whisper_energy_var.set(0.008)

        try:
            self.whisper_min_audio_var.set(
                float(self.database.get_setting('whisper_min_audio_length',
                      str(self.config.whisper_min_audio_length)))
            )
        except ValueError:
            self.whisper_min_audio_var.set(0.3)

        # Load debug flag
        debug_str = self.database.get_setting('debug_enabled', 'false')
        self.debug_var.set(debug_str.lower() in ('true', '1', 'yes'))

        # Update frame visibility
        self._on_backend_changed()

    def _on_backend_changed(self):
        """Handle backend selection change"""
        backend = self.backend_var.get()

        # Hide both frames first
        self.vosk_frame.grid_remove()
        self.whisper_frame.grid_remove()

        # Show the appropriate frame
        if backend == "vosk":
            self.vosk_frame.grid()
        elif backend == "whisper":
            self.whisper_frame.grid()

    def _validate_inputs(self):
        """Validate all input fields"""
        # Validate device index
        device_index = self.whisper_device_index_var.get().strip()
        if device_index:
            try:
                int(device_index)
            except ValueError:
                messagebox.showerror(
                    "Validation Error",
                    "Device Index must be a number or empty for auto-detect"
                )
                return False

        # Validate numeric ranges
        silence = self.whisper_silence_var.get()
        if not (0.5 <= silence <= 2.0):
            messagebox.showerror(
                "Validation Error",
                "Silence Duration must be between 0.5 and 2.0 seconds"
            )
            return False

        energy = self.whisper_energy_var.get()
        if not (0.0001 <= energy <= 0.01):
            messagebox.showerror(
                "Validation Error",
                "Energy Threshold must be between 0.0001 and 0.01"
            )
            return False

        min_audio = self.whisper_min_audio_var.get()
        if not (0.3 <= min_audio <= 1.0):
            messagebox.showerror(
                "Validation Error",
                "Min Audio Length must be between 0.3 and 1.0 seconds"
            )
            return False

        return True

    def _on_settings_save(self):
        """Handle Settings save button"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Validate inputs
            if not self._validate_inputs():
                return

            # Check if backend or model changed (only these require stopping)
            backend_changed = False
            model_changed = False

            current_backend = self.database.get_setting('backend', self.config.backend)
            new_backend = self.backend_var.get()
            if current_backend != new_backend:
                backend_changed = True
                logger.info(f"Backend changed from {current_backend} to {new_backend}")

            # Check if Whisper model changed
            if new_backend == 'whisper':
                current_model = self.database.get_setting('whisper_model', self.config.whisper_model)
                display_name = self.whisper_model_var.get()
                new_model = self.model_ids.get(display_name, "Systran/faster-whisper-medium")
                if current_model != new_model:
                    model_changed = True
                    logger.info(f"Whisper model changed from {current_model} to {new_model}")

            # Only stop if backend or model changed
            if (backend_changed or model_changed) and self.controller.is_running():
                logger.info("Stopping current session due to backend/model change")
                self.controller.stop()

            # Save all settings to database
            self.database.save_setting('backend', self.backend_var.get())

            # Save Vosk settings
            if self.vosk_spanish_var.get():
                self.database.save_setting('vosk_model_es', self.vosk_spanish_var.get())
            if self.vosk_english_var.get():
                self.database.save_setting('vosk_model_en', self.vosk_english_var.get())

            # Save Whisper settings
            display_name = self.whisper_model_var.get()
            model_id = self.model_ids.get(display_name, "Systran/faster-whisper-medium")
            self.database.save_setting('whisper_model', model_id)
            self.database.save_setting('whisper_device', self.whisper_device_var.get())
            self.database.save_setting('whisper_compute_type', self.whisper_compute_type_var.get())
            self.database.save_setting('whisper_device_index', self.whisper_device_index_var.get())
            self.database.save_setting('whisper_silence_duration', str(self.whisper_silence_var.get()))
            self.database.save_setting('whisper_energy_threshold', str(self.whisper_energy_var.get()))
            self.database.save_setting('whisper_min_audio_length', str(self.whisper_min_audio_var.get()))

            # Save debug flag
            self.database.save_setting('debug_enabled', 'true' if self.debug_var.get() else 'false')

            # Reload config to apply changes
            self.config.reload_from_db()

            # Update controller's backend from the reloaded config
            self.controller.reload_backend_from_config()

            # Return to main view (no confirmation dialog)
            self.show_main_view()
            self._update_ui_from_config()
            self._update_status()

            logger.info("Settings saved and applied successfully")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )

    def _on_settings_cancel(self):
        """Handle Settings cancel button"""
        # Simply return to main view without saving
        self.show_main_view()

    def _on_settings_clicked(self):
        """Handle Settings button click"""
        # Switch to settings view
        self.show_settings_view()

    def show_download_progress(self, model_name):
        """Show download progress bar with model name"""
        self.progress_label.config(text=f"📥 Descargando modelo: {model_name}")
        self.progress_frame.grid()
        self.progress_bar.start(10)
        self.root.update_idletasks()

    def hide_download_progress(self):
        """Hide download progress bar"""
        self.progress_bar.stop()
        self.progress_frame.grid_remove()
        self.root.update_idletasks()

    def _on_stop_clicked(self):
        """Handle stop button click"""
        self.controller.stop()
        self._update_status()

    def _on_language_clicked(self, language):
        """Handle language button click"""
        import logging
        logger = logging.getLogger(__name__)

        # Get language code
        lang_code = self.config.languages.get(language, {}).get("code", language)
        logger.info(f"Language button clicked: {language} (code: {lang_code})")

        # Ensure controller uses the correct backend from config
        self.controller.reload_backend_from_config()

        # Check if using Whisper backend
        if self.config.backend == "whisper":
            # Show progress bar for Whisper
            model_name = self.config.whisper_model.split('/')[-1]
            self.show_download_progress(model_name)

            # Disable language buttons during loading
            self.spanish_btn.config(state='disabled')
            self.english_btn.config(state='disabled')

            # Start Whisper in background thread
            def start_whisper():
                logger.info(f"Starting Whisper backend with language '{lang_code}'")
                success, message = self.controller.start(lang_code, None)
                logger.info(f"Start result: success={success}, message={message}")

                # Schedule UI update in main thread with error handling
                if not success:
                    self.root.after(0, lambda: self._on_whisper_error(message))
                else:
                    self.root.after(0, self._on_whisper_started)

            thread = threading.Thread(target=start_whisper, daemon=True)
            thread.start()
        else:
            # Vosk backend - needs model path
            last_model = self.database.get_last_used_model(language)

            if last_model:
                logger.info(f"Starting with last used model: {last_model['path']}")
                success, message = self.controller.restart(lang_code, last_model["path"])
                if not success:
                    messagebox.showerror("Error", f"Failed to start Vosk:\n{message}")
            else:
                # Find first available model for this language
                models = self.config.get_available_models()
                matching_models = [m for m in models if m["language"] == language]

                if matching_models:
                    logger.info(f"Starting with first matching model: {matching_models[0]['path']}")
                    success, message = self.controller.restart(lang_code, matching_models[0]["path"])
                    if not success:
                        messagebox.showerror("Error", f"Failed to start Vosk:\n{message}")
                else:
                    logger.warning(f"No models found for language: {language}")
                    messagebox.showwarning("No Models", f"No Vosk models found for {language}")

            self._update_status()

    def _on_whisper_started(self):
        """Called after Whisper backend starts (in main thread)"""
        # Hide progress bar
        self.hide_download_progress()

        # Re-enable language buttons
        self.spanish_btn.config(state='normal')
        self.english_btn.config(state='normal')

        # Update status
        self._update_status()

    def _on_whisper_error(self, error_message):
        """Called when Whisper backend fails to start (in main thread)"""
        # Hide progress bar
        self.hide_download_progress()

        # Re-enable language buttons
        self.spanish_btn.config(state='normal')
        self.english_btn.config(state='normal')

        # Show error dialog
        messagebox.showerror(
            "Whisper Backend Error",
            f"Failed to start Whisper backend:\n\n{error_message}\n\n"
            "Possible solutions:\n"
            "• Check if another process is using VRAM (e.g., Ollama)\n"
            "• Try a smaller model (Settings → Whisper → Model Size)\n"
            "• Switch to CPU mode (Settings → Whisper → Device)\n"
            "• Use Vosk backend instead (Settings → Backend)"
        )

        # Update status to show error
        self._update_status()

    def _center_window(self, width, height):
        """Center window on screen after resizing"""
        # Update window to get accurate size info
        self.root.update_idletasks()

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate position for centering
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Ensure window is not off-screen
        x = max(0, x)
        y = max(0, y)

        # Set geometry with position
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _update_ui_from_config(self):
        """Update UI elements based on current config values"""
        import logging
        logger = logging.getLogger(__name__)

        # Log current backend
        logger.info(f"Updating UI with backend: {self.config.backend}")

        # Update window title
        backend_text = f" [{self.config.backend.upper()}]"
        self.root.title(f"Dictation Manager{backend_text}")

        # If not running, show backend info
        status = self.controller.get_status()
        if not status["running"]:
            if self.config.backend == "whisper":
                model_name = self.config.whisper_model.split('/')[-1]
                self.model_label.config(text=f"{self.config.backend.upper()}: {model_name}")
            else:
                self.model_label.config(text=f"{self.config.backend.upper()}")

    def _update_status(self):
        """Update status display"""
        status = self.controller.get_status()

        if status["running"]:
            self.status_label.config(text="🟢 Activo", foreground="green")
            self.model_label.config(text=status["model_name"])

            # Get language display name using the helper method
            lang_code = status["language"]
            lang_name = self.config.get_language_name(lang_code)
            self.language_label.config(text=lang_name)
        else:
            self.status_label.config(text="🔴 Detenido", foreground="red")
            # Show backend info when not running
            if self.config.backend == "whisper":
                model_name = self.config.whisper_model.split('/')[-1]
                self.model_label.config(text=f"{self.config.backend.upper()}: {model_name}")
            else:
                self.model_label.config(text=f"{self.config.backend.upper()}")
            self.language_label.config(text="Ninguno")

    def _schedule_status_update(self):
        """Schedule periodic status updates"""
        self._update_status()
        self.root.after(2000, self._schedule_status_update)