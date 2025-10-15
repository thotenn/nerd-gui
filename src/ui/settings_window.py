"""
Settings window for Dictation Manager configuration
"""

import tkinter as tk
from tkinter import ttk, messagebox


class SettingsWindow:
    """Settings configuration window"""

    def __init__(self, parent, config, database):
        """
        Initialize settings window.

        Args:
            parent: Parent window (MainWindow root)
            config: Config instance
            database: Database instance
        """
        self.parent = parent
        self.config = config
        self.database = database

        # Create modal dialog
        self.window = tk.Toplevel(parent)
        self.window.title("⚙ Settings - Dictation Manager")
        self.window.geometry("800x700")
        self.window.resizable(True, True)
        self.window.minsize(700, 600)

        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()

        # Center window on screen
        self._center_window()

        # Settings state (will be populated from database)
        self.settings = {}

        # Create UI
        self._create_ui()

        # Load current settings
        self._load_settings()

    def _center_window(self):
        """Center the window on the screen"""
        self.window.update_idletasks()

        # Get window size
        width = self.window.winfo_width()
        height = self.window.winfo_height()

        # Get screen size
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # Calculate position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_ui(self):
        """Create the settings UI"""
        # Main container with padding
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Content area expands

        # Title
        title_label = ttk.Label(
            main_frame,
            text="⚙ Settings",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)

        # Content frame (scrollable in future if needed)
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)

        # Backend selection
        self._create_backend_section(content_frame)

        # Debug settings
        self._create_debug_section(content_frame)

        # Button frame
        self._create_button_frame(main_frame)

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

        # Info label for Spanish
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

        # Info label for English
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

        # Model selection (single dropdown for all languages)
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

        # Advanced settings section
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
        ttk.Label(
            self.whisper_frame,
            text="Device:",
            font=("Arial", 9)
        ).grid(row=6, column=0, sticky=tk.W, pady=5)

        self.whisper_device_var = tk.StringVar(value="cuda")
        device_combo = ttk.Combobox(
            self.whisper_frame,
            textvariable=self.whisper_device_var,
            values=["cuda", "cpu"],
            state="readonly",
            width=15
        )
        device_combo.grid(row=6, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            self.whisper_frame,
            text="(cuda for GPU, cpu for CPU-only)",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=6, column=2, sticky=tk.W, padx=(10, 0), pady=5)

        # Compute Type selection
        ttk.Label(
            self.whisper_frame,
            text="Compute Type:",
            font=("Arial", 9)
        ).grid(row=7, column=0, sticky=tk.W, pady=5)

        self.whisper_compute_type_var = tk.StringVar(value="float16")
        compute_combo = ttk.Combobox(
            self.whisper_frame,
            textvariable=self.whisper_compute_type_var,
            values=["float16", "float32"],
            state="readonly",
            width=15
        )
        compute_combo.grid(row=7, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            self.whisper_frame,
            text="(float16 for GPU, float32 for CPU)",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=7, column=2, sticky=tk.W, padx=(10, 0), pady=5)

        # Device Index (optional)
        ttk.Label(
            self.whisper_frame,
            text="Device Index:",
            font=("Arial", 9)
        ).grid(row=8, column=0, sticky=tk.W, pady=5)

        self.whisper_device_index_var = tk.StringVar(value="")
        device_index_entry = ttk.Entry(
            self.whisper_frame,
            textvariable=self.whisper_device_index_var,
            width=18
        )
        device_index_entry.grid(row=8, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            self.whisper_frame,
            text="(empty for auto-detect, or specific index)",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=8, column=2, sticky=tk.W, padx=(10, 0), pady=5)

        # Silence Duration
        ttk.Label(
            self.whisper_frame,
            text="Silence Duration:",
            font=("Arial", 9)
        ).grid(row=9, column=0, sticky=tk.W, pady=5)

        self.whisper_silence_var = tk.DoubleVar(value=1.0)
        silence_spinbox = ttk.Spinbox(
            self.whisper_frame,
            from_=0.5,
            to=2.0,
            increment=0.1,
            textvariable=self.whisper_silence_var,
            width=16
        )
        silence_spinbox.grid(row=9, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            self.whisper_frame,
            text="(0.5-2.0s, wait time before processing)",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=9, column=2, sticky=tk.W, padx=(10, 0), pady=5)

        # Energy Threshold
        ttk.Label(
            self.whisper_frame,
            text="Energy Threshold:",
            font=("Arial", 9)
        ).grid(row=10, column=0, sticky=tk.W, pady=5)

        self.whisper_energy_var = tk.DoubleVar(value=0.008)
        energy_spinbox = ttk.Spinbox(
            self.whisper_frame,
            from_=0.0001,
            to=0.01,
            increment=0.0001,
            textvariable=self.whisper_energy_var,
            width=16
        )
        energy_spinbox.grid(row=10, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            self.whisper_frame,
            text="(0.0001-0.01, microphone sensitivity)",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=10, column=2, sticky=tk.W, padx=(10, 0), pady=5)

        # Min Audio Length
        ttk.Label(
            self.whisper_frame,
            text="Min Audio Length:",
            font=("Arial", 9)
        ).grid(row=11, column=0, sticky=tk.W, pady=5)

        self.whisper_min_audio_var = tk.DoubleVar(value=0.3)
        min_audio_spinbox = ttk.Spinbox(
            self.whisper_frame,
            from_=0.3,
            to=1.0,
            increment=0.1,
            textvariable=self.whisper_min_audio_var,
            width=16
        )
        min_audio_spinbox.grid(row=11, column=1, sticky=tk.W, pady=5)

        ttk.Label(
            self.whisper_frame,
            text="(0.3-1.0s, minimum audio to process)",
            font=("Arial", 8, "italic"),
            foreground="gray"
        ).grid(row=11, column=2, sticky=tk.W, padx=(10, 0), pady=5)

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

    def _create_button_frame(self, parent):
        """Create button frame with Save and Cancel buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, pady=(20, 0))

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=15
        )
        cancel_btn.grid(row=0, column=0, padx=5)

        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="💾 Save",
            command=self._on_save,
            width=15
        )
        save_btn.grid(row=0, column=1, padx=5)

    def _on_backend_changed(self):
        """Handle backend selection change"""
        backend = self.backend_var.get()

        # Hide both frames first
        self.vosk_frame.grid_remove()
        self.whisper_frame.grid_remove()

        # Show the appropriate frame based on selection
        if backend == "vosk":
            self.vosk_frame.grid()
        elif backend == "whisper":
            self.whisper_frame.grid()

    def _load_settings(self):
        """Load current settings from database or config"""
        # Try to load from database first, fallback to config
        backend = self.database.get_setting('backend', self.config.backend)
        self.backend_var.set(backend)

        # Load Vosk settings
        vosk_es = self.database.get_setting('vosk_model_es', '')
        if vosk_es and vosk_es in [self.vosk_spanish_combo.cget('values')]:
            self.vosk_spanish_var.set(vosk_es)

        vosk_en = self.database.get_setting('vosk_model_en', '')
        if vosk_en and vosk_en in [self.vosk_english_combo.cget('values')]:
            self.vosk_english_var.set(vosk_en)

        # Load Whisper settings
        model_id = self.database.get_setting('whisper_model', self.config.whisper_model)
        # Convert model ID to display name (e.g., "Systran/faster-whisper-medium" -> "Medium (~1.5GB)")
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

        # Load numeric settings with proper type conversion
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

    def _on_cancel(self):
        """Handle Cancel button click"""
        self.window.destroy()

    def _on_save(self):
        """Handle Save button click"""
        try:
            # Validate inputs
            if not self._validate_inputs():
                return

            # Save all settings to database
            self.database.save_setting('backend', self.backend_var.get())

            # Save Vosk settings
            if self.vosk_spanish_var.get():
                self.database.save_setting('vosk_model_es', self.vosk_spanish_var.get())
            if self.vosk_english_var.get():
                self.database.save_setting('vosk_model_en', self.vosk_english_var.get())

            # Save Whisper settings
            # Convert display name to model ID (e.g., "Medium (~1.5GB)" -> "Systran/faster-whisper-medium")
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

            # Reload config to apply debug flag immediately
            self.config.reload_from_db()

            # Show success message
            messagebox.showinfo(
                "Settings Saved",
                "Settings have been saved successfully!\n\n"
                "Note: You may need to restart the application for some changes to take effect.",
                parent=self.window
            )

            # Close window
            self.window.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save settings:\n{str(e)}",
                parent=self.window
            )

    def _validate_inputs(self):
        """Validate all input fields"""
        # Validate device index (must be empty or integer)
        device_index = self.whisper_device_index_var.get().strip()
        if device_index:
            try:
                int(device_index)
            except ValueError:
                messagebox.showerror(
                    "Validation Error",
                    "Device Index must be a number or empty for auto-detect",
                    parent=self.window
                )
                return False

        # Validate numeric ranges
        silence = self.whisper_silence_var.get()
        if not (0.5 <= silence <= 2.0):
            messagebox.showerror(
                "Validation Error",
                "Silence Duration must be between 0.5 and 2.0 seconds",
                parent=self.window
            )
            return False

        energy = self.whisper_energy_var.get()
        if not (0.0001 <= energy <= 0.01):
            messagebox.showerror(
                "Validation Error",
                "Energy Threshold must be between 0.0001 and 0.01",
                parent=self.window
            )
            return False

        min_audio = self.whisper_min_audio_var.get()
        if not (0.3 <= min_audio <= 1.0):
            messagebox.showerror(
                "Validation Error",
                "Min Audio Length must be between 0.3 and 1.0 seconds",
                parent=self.window
            )
            return False

        return True
