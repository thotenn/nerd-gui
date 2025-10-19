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
        self.root.geometry("600x300")
        self.root.resizable(True, True)

        # Set minimum size for main view
        self.root.minsize(500, 300)

        # Center window on screen initially
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 300) // 2
        self.root.geometry(f"600x300+{x}+{y}")

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

        # Title frame with Settings button on the right
        title_frame = ttk.Frame(self.main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        title_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(
            title_frame,
            text="🎤 Dictation Manager",
            font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        # Settings button (icon only)
        self.settings_btn = ttk.Button(
            title_frame,
            text="⚙",
            command=self._on_settings_clicked,
            width=3
        )
        self.settings_btn.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))

        # Status frame (will include STOP button)
        self._create_status_frame(self.main_frame)

        # Language buttons frame (only language buttons, no STOP/Settings)
        self._create_language_buttons(self.main_frame)

        # Download progress frame (hidden by default)
        self._create_progress_frame(self.main_frame)

    def _create_settings_view(self):
        """Create the settings view with tabs"""
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
        settings_title.grid(row=0, column=0, pady=(0, 15), sticky=tk.W)

        # Create notebook (tabs)
        self.settings_notebook = ttk.Notebook(self.settings_frame)
        self.settings_notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create tabs
        self._create_general_tab()
        self._create_voice_commands_tab()
        self._create_debug_tab()

        # Settings buttons
        self._create_settings_buttons(self.settings_frame)

    def _create_general_tab(self):
        """Create General settings tab"""
        # Create scrollable frame for general settings
        general_frame = ttk.Frame(self.settings_notebook, padding="15")
        general_frame.columnconfigure(0, weight=1)

        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(general_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        general_frame.rowconfigure(0, weight=1)

        # Add backend selection to scrollable frame
        self._create_backend_section(scrollable_frame)

        # Add tab to notebook
        self.settings_notebook.add(general_frame, text="  General  ")

    def _create_voice_commands_tab(self):
        """Create Voice Commands settings tab"""
        # Create frame for voice commands
        voice_frame = ttk.Frame(self.settings_notebook, padding="15")
        voice_frame.columnconfigure(0, weight=1)

        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(voice_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(voice_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        voice_frame.rowconfigure(0, weight=1)

        # Add voice commands section to scrollable frame
        self._create_voice_commands_section(scrollable_frame)

        # Add tab to notebook
        self.settings_notebook.add(voice_frame, text="  Voice Commands  ")

    def _create_debug_tab(self):
        """Create Debug settings tab"""
        # Create frame for debug settings
        debug_frame = ttk.Frame(self.settings_notebook, padding="15")
        debug_frame.columnconfigure(0, weight=1)

        # Add debug section
        self._create_debug_section(debug_frame)

        # Add tab to notebook
        self.settings_notebook.add(debug_frame, text="  Debug  ")

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

        # Get available Vosk models from VoskModelManager (all available for download)
        from src.backends.vosk_model_manager import VoskModelManager
        manager = VoskModelManager(self.config.models_dir)

        # Get model sizes for each language (not file names, but sizes)
        spanish_models_dict = manager.list_available_models('es').get('es', {})
        english_models_dict = manager.list_available_models('en').get('en', {})

        # Create display-friendly options with size and description
        spanish_options = [
            f"{size} - {info['description']}"
            for size, info in spanish_models_dict.items()
        ]
        english_options = [
            f"{size} - {info['description']}"
            for size, info in english_models_dict.items()
        ]

        # Store mapping from display name to size
        self.vosk_spanish_size_map = {
            f"{size} - {info['description']}": size
            for size, info in spanish_models_dict.items()
        }
        self.vosk_english_size_map = {
            f"{size} - {info['description']}": size
            for size, info in english_models_dict.items()
        }

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
            values=spanish_options,
            state="readonly",
            width=50
        )
        self.vosk_spanish_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))

        # Set default to 'small'
        if spanish_options:
            default = [opt for opt in spanish_options if opt.startswith('small')]
            self.vosk_spanish_combo.set(default[0] if default else spanish_options[0])

        # Help text for Spanish
        ttk.Label(
            self.vosk_frame,
            text="💡 Models download automatically on first use",
            font=("Arial", 8),
            foreground="gray"
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
            values=english_options,
            state="readonly",
            width=50
        )
        self.vosk_english_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 5))

        # Set default to 'small'
        if english_options:
            default = [opt for opt in english_options if opt.startswith('small')]
            self.vosk_english_combo.set(default[0] if default else english_options[0])

        # Help text for English
        ttk.Label(
            self.vosk_frame,
            text="💡 Models download automatically on first use",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=3, column=1, sticky=tk.W, pady=(0, 10))

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

    def _create_voice_commands_section(self, parent):
        """Create voice commands configuration section"""
        voice_frame = ttk.LabelFrame(parent, text="🔊 Voice Commands (Experimental)", padding="15")
        voice_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        voice_frame.columnconfigure(1, weight=1)

        # Info label
        info_label = ttk.Label(
            voice_frame,
            text="ℹ️ Voice commands allow you to execute keyboard actions using voice (e.g., 'Tony Enter')\n"
                 "Only works with Whisper backend. Requires xdotool to be installed.",
            font=("Arial", 9, "italic"),
            foreground="#0066cc",
            wraplength=700,
            justify=tk.LEFT
        )
        info_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        # Enable checkbox
        self.voice_commands_enabled_var = tk.BooleanVar(value=False)
        enabled_check = ttk.Checkbutton(
            voice_frame,
            text="Enable Voice Commands",
            variable=self.voice_commands_enabled_var,
            command=self._on_voice_commands_toggle
        )
        enabled_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        # Keyword configuration
        ttk.Label(
            voice_frame,
            text="Activation Keyword:",
            font=("Arial", 10, "bold")
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))

        self.voice_keyword_var = tk.StringVar(value="tony")
        keyword_entry = ttk.Entry(
            voice_frame,
            textvariable=self.voice_keyword_var,
            width=20
        )
        keyword_entry.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Label(
            voice_frame,
            text="(e.g., 'tony', 'computer', 'jarvis')",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=2, column=2, sticky=tk.W, padx=(10, 0), pady=(0, 5))

        # Timeout configuration
        ttk.Label(
            voice_frame,
            text="Command Timeout:",
            font=("Arial", 10, "bold")
        ).grid(row=3, column=0, sticky=tk.W, pady=(5, 5))

        self.voice_timeout_var = tk.DoubleVar(value=3.0)
        timeout_spinbox = ttk.Spinbox(
            voice_frame,
            from_=1.0, to=10.0, increment=0.5,
            textvariable=self.voice_timeout_var,
            width=18
        )
        timeout_spinbox.grid(row=3, column=1, sticky=tk.W, pady=(5, 5))

        ttk.Label(
            voice_frame,
            text="seconds (time to wait for command after keyword)",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=3, column=2, sticky=tk.W, padx=(10, 0), pady=(5, 5))

        # Sensitivity configuration
        ttk.Label(
            voice_frame,
            text="Detection Sensitivity:",
            font=("Arial", 10, "bold")
        ).grid(row=4, column=0, sticky=tk.W, pady=(5, 5))

        self.voice_sensitivity_var = tk.StringVar(value="normal")
        sensitivity_combo = ttk.Combobox(
            voice_frame,
            textvariable=self.voice_sensitivity_var,
            values=["low", "normal", "high"],
            state="readonly",
            width=15
        )
        sensitivity_combo.grid(row=4, column=1, sticky=tk.W, pady=(5, 5))

        ttk.Label(
            voice_frame,
            text="(low = fewer false positives, high = better detection)",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=4, column=2, sticky=tk.W, padx=(10, 0), pady=(5, 5))

        # Max Command Words configuration
        ttk.Label(
            voice_frame,
            text="Max Command Words:",
            font=("Arial", 10, "bold")
        ).grid(row=5, column=0, sticky=tk.W, pady=(5, 5))

        self.voice_max_words_var = tk.IntVar(value=1)
        max_words_spinbox = ttk.Spinbox(
            voice_frame,
            from_=1, to=5, increment=1,
            textvariable=self.voice_max_words_var,
            width=18
        )
        max_words_spinbox.grid(row=5, column=1, sticky=tk.W, pady=(5, 5))

        ttk.Label(
            voice_frame,
            text="(max words for multi-word commands like 'enter doble')",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=5, column=2, sticky=tk.W, padx=(10, 0), pady=(5, 5))

        # Example commands
        ttk.Label(
            voice_frame,
            text="Example Commands:",
            font=("Arial", 10, "bold")
        ).grid(row=6, column=0, sticky=tk.W, pady=(15, 5))

        examples_text = (
            "• Basic: 'Tony Enter', 'Tony Space', 'Tony Backspace'\n"
            "• Navigation: 'Tony Up', 'Tony Down', 'Tony Left', 'Tony Right'\n"
            "• System: 'Tony Copy' (Ctrl+C), 'Tony Paste' (Ctrl+V), 'Tony Save' (Ctrl+S)\n"
            "• Windows: 'Tony Close' (Alt+F4), 'Tony Minimize', 'Tony Maximize'\n"
            "• Function: 'Tony F5', 'Tony F11', etc."
        )

        examples_label = ttk.Label(
            voice_frame,
            text=examples_text,
            font=("Arial", 9),
            foreground="#333333",
            justify=tk.LEFT
        )
        examples_label.grid(row=6, column=1, columnspan=2, sticky=tk.W, pady=(15, 5))

        # Warning about xdotool
        warning_label = ttk.Label(
            voice_frame,
            text="⚠️ Make sure xdotool is installed: sudo apt install xdotool",
            font=("Arial", 9, "bold"),
            foreground="orange"
        )
        warning_label.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=(15, 0))

        # Separator
        ttk.Separator(voice_frame, orient=tk.HORIZONTAL).grid(
            row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 20)
        )

        # Commands Configuration section
        ttk.Label(
            voice_frame,
            text="Commands Configuration (JSON)",
            font=("Arial", 11, "bold")
        ).grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Info text about JSON format
        json_info_label = ttk.Label(
            voice_frame,
            text="ℹ️ Edit the voice commands below in JSON format. Each command has:\n"
                 "  • keys: List of keyboard keys to press (e.g., [\"Control_L\", \"c\"] for Ctrl+C)\n"
                 "  • description: Human-readable description\n"
                 "  • category: Category name (Basic, Navigation, System, Function, Media, Custom)\n"
                 "  • enabled: true/false to enable/disable the command\n"
                 "xdotool key names: Return, space, BackSpace, Control_L, Alt_L, Shift_L, etc.",
            font=("Arial", 9),
            foreground="#555555",
            justify=tk.LEFT
        )
        json_info_label.grid(row=9, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # JSON textarea with scrollbar
        json_frame = ttk.Frame(voice_frame)
        json_frame.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        json_frame.columnconfigure(0, weight=1)

        # Create Text widget with scrollbar
        json_scrollbar = ttk.Scrollbar(json_frame, orient=tk.VERTICAL)
        self.commands_json_text = tk.Text(
            json_frame,
            height=20,
            width=80,
            font=("Courier", 9),
            wrap=tk.NONE,
            yscrollcommand=json_scrollbar.set
        )
        json_scrollbar.config(command=self.commands_json_text.yview)

        self.commands_json_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        json_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        json_frame.rowconfigure(0, weight=1)

        # Buttons frame
        json_buttons_frame = ttk.Frame(voice_frame)
        json_buttons_frame.grid(row=11, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # Reset to Defaults button
        reset_btn = ttk.Button(
            json_buttons_frame,
            text="↺ Reset to Defaults",
            command=self._on_reset_commands_to_defaults,
            width=20
        )
        reset_btn.grid(row=0, column=0, padx=(0, 10))

        # Info about resetting
        ttk.Label(
            json_buttons_frame,
            text="(Restores the original 44 default commands)",
            font=("Arial", 8),
            foreground="gray"
        ).grid(row=0, column=1, sticky=tk.W)

    def _on_voice_commands_toggle(self):
        """Handle voice commands enable/disable toggle"""
        # Could add validation or additional logic here if needed
        pass

    def _on_reset_commands_to_defaults(self):
        """Reset voice commands to default configuration"""
        import json
        from pathlib import Path
        from tkinter import messagebox

        # Confirm with user
        result = messagebox.askyesno(
            "Reset to Defaults",
            "Are you sure you want to reset all voice commands to the default configuration?\n\n"
            "This will remove any custom commands you have added.",
            icon='warning'
        )

        if not result:
            return

        try:
            # Load default commands from JSON file
            default_file = Path(__file__).parent.parent / 'backends' / 'whisper' / 'default_commands.json'
            if default_file.exists():
                with open(default_file, 'r') as f:
                    default_commands = json.load(f)

                # Format with 2-space indentation
                json_text = json.dumps(default_commands, indent=2)

                # Update textarea
                self.commands_json_text.delete('1.0', tk.END)
                self.commands_json_text.insert('1.0', json_text)

                messagebox.showinfo(
                    "Success",
                    "Commands have been reset to defaults.\n\n"
                    "Click 'Save' to apply these changes."
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"Default commands file not found:\n{default_file}"
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to reset commands:\n{str(e)}"
            )

    def _create_debug_section(self, parent):
        """Create debug settings section"""
        debug_frame = ttk.LabelFrame(parent, text="Debug Settings", padding="15")
        debug_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
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
        ).grid(row=1, column=0, sticky=tk.W, pady=(5, 15))

        # Log Filters Section
        log_filters_frame = ttk.LabelFrame(debug_frame, text="Log Level Filters", padding="10")
        log_filters_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        log_filters_frame.columnconfigure(0, weight=1)

        # Log level filter description
        ttk.Label(
            log_filters_frame,
            text="Select which log levels to display in console and log file:",
            font=("Arial", 9),
            foreground="gray",
            wraplength=650,
            justify=tk.LEFT
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Create log filter checkboxes
        self.log_filter_vars = {}
        log_levels = [
            ("INFO", "ℹ️ Information messages (general status, operations)"),
            ("WARNING", "⚠️ Warning messages (potential issues)"),
            ("ERROR", "❌ Error messages (failed operations)"),
            ("CRITICAL", "🔥 Critical messages (serious failures)")
        ]

        for i, (level, description) in enumerate(log_levels):
            var = tk.BooleanVar(value=True)  # All enabled by default
            self.log_filter_vars[level] = var

            check = ttk.Checkbutton(
                log_filters_frame,
                text=f"{level}:",
                variable=var
            )
            check.grid(row=i+1, column=0, sticky=tk.W, pady=2)

            # Description label
            desc_label = ttk.Label(
                log_filters_frame,
                text=description,
                font=("Arial", 8),
                foreground="gray",
                wraplength=600,
                justify=tk.LEFT
            )
            desc_label.grid(row=i+1, column=1, sticky=tk.W, padx=(20, 0), pady=2)

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
        """Create status display frame with STOP button on the right"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="15")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        status_frame.columnconfigure(1, weight=1)

        # Left side: Status info
        info_frame = ttk.Frame(status_frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.N))

        # Status indicator
        ttk.Label(info_frame, text="Estado:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_label = ttk.Label(info_frame, text="Detenido", font=("Arial", 10, "bold"))
        self.status_label.grid(row=0, column=1, sticky=tk.W)

        # Current model
        ttk.Label(info_frame, text="Modelo:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.model_label = ttk.Label(info_frame, text="Ninguno")
        self.model_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))

        # Language
        ttk.Label(info_frame, text="Idioma:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.language_label = ttk.Label(info_frame, text="Ninguno")
        self.language_label.grid(row=2, column=1, sticky=tk.W, pady=(5, 0))

        # Voice Commands status
        ttk.Label(info_frame, text="Comandos Voz:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.voice_commands_label = ttk.Label(info_frame, text="Deshabilitado", foreground="gray")
        self.voice_commands_label.grid(row=3, column=1, sticky=tk.W, pady=(5, 0))

        # Right side: STOP button (initially hidden)
        # Create a frame for the STOP button to control its size better
        stop_frame = ttk.Frame(status_frame)
        stop_frame.grid(row=0, column=1, sticky=tk.E, padx=(20, 0))

        self.stop_btn = tk.Button(
            stop_frame,
            text="⏹ STOP",
            command=self._on_stop_clicked,
            font=("Arial", 14, "bold"),
            bg="#ff4444",
            fg="white",
            activebackground="#cc0000",
            activeforeground="white",
            relief=tk.RAISED,
            bd=3,
            padx=20,
            pady=15,
            cursor="hand2"
        )
        self.stop_btn.pack()
        stop_frame.grid_remove()  # Hide initially
        self.stop_frame = stop_frame  # Store reference to frame

    def _create_language_buttons(self, parent):
        """Create language selection buttons (only language buttons, no STOP/Settings)"""
        # Store button frame reference for later recreation
        self.button_frame = ttk.Frame(parent)
        self.button_frame.grid(row=2, column=0, pady=(0, 20))

        # Dynamic language buttons based on current backend
        # Get supported languages for the current backend
        supported_languages = self.config.get_supported_languages(self.config.backend)

        # Store language buttons in a dictionary for easy access
        self.language_buttons = {}

        # Create a button for each supported language
        column_index = 0  # Start from column 0 (no STOP button here anymore)
        for lang_key, lang_info in supported_languages.items():
            # Get display info from language config
            flag = lang_info.get('flag', '')
            name = lang_info.get('name', lang_key.capitalize())

            # Create button with flag emoji and language name
            button_text = f"{flag} {name}" if flag else name

            lang_btn = ttk.Button(
                self.button_frame,
                text=button_text,
                command=lambda key=lang_key: self._on_language_clicked(key),
                width=15
            )
            lang_btn.grid(row=0, column=column_index, padx=5)

            # Store reference to button
            self.language_buttons[lang_key] = lang_btn

            column_index += 1

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
        self.root.geometry(f"600x300+{x}+{y}")
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

        # Optimized size for tabbed settings view
        self.root.geometry(f"850x700+{x}+{y}")
        self.root.minsize(800, 650)
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
        # Saved values could be sizes ("small"), model names ("vosk-model-es-0.42"), or paths
        # Need to convert to display format ("small - Small Spanish model...")
        vosk_es = self.database.get_setting('vosk_model_es', '')
        if vosk_es:
            # Normalize to size using backend logic
            from src.backends.vosk_backend import VoskBackend
            backend = VoskBackend(
                nerd_dictation_dir=str(self.config.nerd_dictation_dir),
                venv_python=str(self.config.nerd_dictation_dir / "venv" / "bin" / "python"),
                models_dir=str(self.config.models_dir)
            )
            size = backend._normalize_model_size('es', vosk_es)
            # Find matching display option
            for display_name, mapped_size in self.vosk_spanish_size_map.items():
                if mapped_size == size:
                    self.vosk_spanish_var.set(display_name)
                    break

        vosk_en = self.database.get_setting('vosk_model_en', '')
        if vosk_en:
            # Normalize to size
            from src.backends.vosk_backend import VoskBackend
            backend = VoskBackend(
                nerd_dictation_dir=str(self.config.nerd_dictation_dir),
                venv_python=str(self.config.nerd_dictation_dir / "venv" / "bin" / "python"),
                models_dir=str(self.config.models_dir)
            )
            size = backend._normalize_model_size('en', vosk_en)
            # Find matching display option
            for display_name, mapped_size in self.vosk_english_size_map.items():
                if mapped_size == size:
                    self.vosk_english_var.set(display_name)
                    break

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

        # Load log filters (only if log_filter_vars exists - might be loading before UI creation)
        if hasattr(self, 'log_filter_vars'):
            try:
                log_filters = self.database.get_log_filters()
                for level, var in self.log_filter_vars.items():
                    var.set(log_filters.get(level, True))  # Default to True if not found
            except Exception as e:
                # Set defaults if loading fails
                for var in self.log_filter_vars.values():
                    var.set(True)

        # Load voice commands settings
        try:
            voice_settings = self.database.get_voice_command_settings()
            self.voice_keyword_var.set(voice_settings.get('keyword', 'tony'))
            self.voice_timeout_var.set(voice_settings.get('timeout', 3.0))
            self.voice_sensitivity_var.set(voice_settings.get('sensitivity', 'normal'))
            self.voice_commands_enabled_var.set(voice_settings.get('enabled', False))
            self.voice_max_words_var.set(voice_settings.get('max_command_words', 1))
        except Exception as e:
            # import logging
            logging.getLogger(__name__).warning(f"Failed to load voice command settings: {e}")
            # Set defaults
            self.voice_keyword_var.set('tony')
            self.voice_timeout_var.set(3.0)
            self.voice_sensitivity_var.set('normal')
            self.voice_commands_enabled_var.set(False)
            self.voice_max_words_var.set(1)

        # Load voice commands JSON
        try:
            import json
            from pathlib import Path

            # Try to load from database first
            commands_json = self.database.get_commands_json()

            if not commands_json:
                # Load defaults from file
                default_file = Path(__file__).parent.parent / 'backends' / 'whisper' / 'default_commands.json'
                if default_file.exists():
                    with open(default_file, 'r') as f:
                        commands_data = json.load(f)
                    commands_json = json.dumps(commands_data, indent=2)
                else:
                    commands_json = "{}"

            # Update textarea
            self.commands_json_text.delete('1.0', tk.END)
            self.commands_json_text.insert('1.0', commands_json)
        except Exception as e:
            # import logging
            logging.getLogger(__name__).warning(f"Failed to load commands JSON: {e}")
            self.commands_json_text.delete('1.0', tk.END)
            self.commands_json_text.insert('1.0', "{}")

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
        from src.core.logging_controller import info, debug, warning, error, critical

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
                info(f"Backend changed from {current_backend} to {new_backend}")

            # Check if Whisper model changed
            if new_backend == 'whisper':
                current_model = self.database.get_setting('whisper_model', self.config.whisper_model)
                display_name = self.whisper_model_var.get()
                new_model = self.model_ids.get(display_name, "Systran/faster-whisper-medium")
                if current_model != new_model:
                    model_changed = True
                    info(f"Whisper model changed from {current_model} to {new_model}")

            # Only stop if backend or model changed
            if (backend_changed or model_changed) and self.controller.is_running():
                info("Stopping current session due to backend/model change")
                self.controller.stop()

            # Save all settings to database
            self.database.save_setting('backend', self.backend_var.get())

            # Save Vosk settings
            # Convert from display format back to size for storage
            if self.vosk_spanish_var.get():
                display_value = self.vosk_spanish_var.get()
                size = self.vosk_spanish_size_map.get(display_value, 'small')
                self.database.save_setting('vosk_model_es', size)
            if self.vosk_english_var.get():
                display_value = self.vosk_english_var.get()
                size = self.vosk_english_size_map.get(display_value, 'small')
                self.database.save_setting('vosk_model_en', size)

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

            # Save log filters
            try:
                log_filters = {}
                for level, var in self.log_filter_vars.items():
                    log_filters[level] = var.get()

                # Save to database
                from src.core.logging_controller import get_log_controller
                log_controller = get_log_controller()
                success = log_controller.update_log_filters(log_filters)

                if success:
                    info("Log filters saved to database")
                else:
                    warning("Failed to save log filters to database")
            except Exception as e:
                error(f"Failed to save log filters: {e}")

            # Validate and save commands JSON
            try:
                import json

                # Get JSON text from textarea
                commands_json_text = self.commands_json_text.get('1.0', tk.END).strip()

                # Validate JSON format
                try:
                    json.loads(commands_json_text)
                except json.JSONDecodeError as e:
                    messagebox.showerror(
                        "Invalid JSON",
                        f"Commands JSON is not valid:\n\n{str(e)}\n\n"
                        "Please fix the JSON syntax before saving."
                    )
                    return

                # Save commands JSON to database
                self.database.save_commands_json(commands_json_text)
                info("Commands JSON saved to database")

                # Update Whisper backend's command registry if active
                if self.controller.current_backend and self.controller.backend_type == 'whisper':
                    if hasattr(self.controller.current_backend, 'command_registry'):
                        success = self.controller.current_backend.command_registry.update_from_json(commands_json_text)
                        if success:
                            info("Commands updated in active Whisper backend")
                        else:
                            warning("Failed to update commands in active backend")

            except Exception as e:
                error(f"Failed to save commands JSON: {e}")
                messagebox.showerror(
                    "Error",
                    f"Failed to save commands JSON:\n{str(e)}"
                )
                return

            # Save voice commands settings
            try:
                self.database.save_voice_command_settings(
                    keyword=self.voice_keyword_var.get().strip().lower(),
                    timeout=self.voice_timeout_var.get(),
                    sensitivity=self.voice_sensitivity_var.get(),
                    enabled=self.voice_commands_enabled_var.get(),
                    max_command_words=self.voice_max_words_var.get()
                )
                info("Voice command settings saved to database")

                # Update Whisper backend settings (whether active or not)
                if self.controller.current_backend and self.controller.backend_type == 'whisper':
                    if hasattr(self.controller.current_backend, 'update_voice_command_settings'):
                        self.controller.current_backend.update_voice_command_settings(
                            keyword=self.voice_keyword_var.get().strip().lower(),
                            timeout=self.voice_timeout_var.get(),
                            sensitivity=self.voice_sensitivity_var.get(),
                            enabled=self.voice_commands_enabled_var.get(),
                            max_command_words=self.voice_max_words_var.get()
                        )
                        if self.controller.is_running():
                            info("Voice command settings applied to active backend")
                        else:
                            info("Voice command settings updated in backend (will apply on next start)")
            except Exception as e:
                error(f"Failed to save voice command settings: {e}")

            # Reload config to apply changes
            self.config.reload_from_db()

            # Update controller's backend from the reloaded config
            self.controller.reload_backend_from_config()

            # Return to main view (no confirmation dialog)
            self.show_main_view()
            self._update_ui_from_config()
            self._update_status()

            info("Settings saved and applied successfully")

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
        from src.core.logging_controller import info, debug, warning, error, critical

        # Get language code
        lang_code = self.config.languages.get(language, {}).get("code", language)
        info(f"Language button clicked: {language} (code: {lang_code})")

        # Ensure controller uses the correct backend from config
        self.controller.reload_backend_from_config()

        # Check if using Whisper backend
        if self.config.backend == "whisper":
            # Show progress bar for Whisper
            model_name = self.config.whisper_model.split('/')[-1]
            self.show_download_progress(model_name)

            # Disable language buttons during loading
            for lang_btn in self.language_buttons.values():
                lang_btn.config(state='disabled')

            # Start Whisper in background thread
            def start_whisper():
                info(f"Starting Whisper backend with language '{lang_code}'")
                success, message = self.controller.start(lang_code, None)
                info(f"Start result: success={success}, message={message}")

                # Schedule UI update in main thread with error handling
                if not success:
                    self.root.after(0, lambda: self._on_whisper_error(message))
                else:
                    self.root.after(0, self._on_whisper_started)

            thread = threading.Thread(target=start_whisper, daemon=True)
            thread.start()
        else:
            # Vosk backend - automatic model download
            # Determine model size from database settings or use default
            model_size_key = f"vosk_model_{lang_code}"
            saved_model = self.database.get_setting(model_size_key)

            # Default model sizes per language
            default_sizes = {
                'es': 'small',  # Spanish: start with small (40MB)
                'en': 'small'   # English: start with small (40MB)
            }

            # Use saved model, fallback to default
            if saved_model:
                # Saved model could be a path, name, or size - backend will normalize it
                model_size = saved_model
                info(f"Using saved model setting: {model_size}")
            else:
                model_size = default_sizes.get(lang_code, 'small')
                info(f"No saved model, using default size: {model_size}")

            # Show progress bar for Vosk (in case model needs to download)
            self.show_download_progress(f"vosk-{lang_code}-{model_size}")

            # Disable language buttons during loading
            for lang_btn in self.language_buttons.values():
                lang_btn.config(state='disabled')

            # Start Vosk in background thread (like Whisper)
            def start_vosk():
                info(f"Starting Vosk backend with language '{lang_code}', model size '{model_size}'")
                success, message = self.controller.start(lang_code, model_size)
                info(f"Start result: success={success}, message={message}")

                # Schedule UI update in main thread
                if not success:
                    self.root.after(0, lambda: self._on_vosk_error(message))
                else:
                    self.root.after(0, self._on_vosk_started)

            thread = threading.Thread(target=start_vosk, daemon=True)
            thread.start()

    def _on_whisper_started(self):
        """Called after Whisper backend starts (in main thread)"""
        # Hide progress bar
        self.hide_download_progress()

        # Re-enable language buttons
        for lang_btn in self.language_buttons.values():
            lang_btn.config(state='normal')

        # Update status
        self._update_status()

    def _on_whisper_error(self, error_message):
        """Called when Whisper backend fails to start (in main thread)"""
        # Hide progress bar
        self.hide_download_progress()

        # Re-enable language buttons
        for lang_btn in self.language_buttons.values():
            lang_btn.config(state='normal')

    def _on_vosk_started(self):
        """Called after Vosk backend starts (in main thread)"""
        # Hide progress bar
        self.hide_download_progress()

        # Re-enable language buttons
        for lang_btn in self.language_buttons.values():
            lang_btn.config(state='normal')

        # Update status
        self._update_status()

    def _on_vosk_error(self, error_message):
        """Called when Vosk backend fails to start (in main thread)"""
        # Hide progress bar
        self.hide_download_progress()

        # Re-enable language buttons
        for lang_btn in self.language_buttons.values():
            lang_btn.config(state='normal')

        # Show error message
        from tkinter import messagebox
        messagebox.showerror("Error", f"Failed to start Vosk:\n{error_message}")

        # Update status
        self._update_status()

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

    def _recreate_language_buttons(self):
        """Recreate language buttons based on current backend"""
        from src.core.logging_controller import info, debug

        # Destroy existing language buttons
        for lang_btn in self.language_buttons.values():
            lang_btn.destroy()

        # Clear dictionary
        self.language_buttons.clear()

        # Get supported languages for current backend
        supported_languages = self.config.get_supported_languages(self.config.backend)

        debug(f"Recreating language buttons for backend '{self.config.backend}': {list(supported_languages.keys())}")

        # Create a button for each supported language
        column_index = 0  # Start from column 0 (no STOP button here anymore)
        for lang_key, lang_info in supported_languages.items():
            # Get display info from language config
            flag = lang_info.get('flag', '')
            name = lang_info.get('name', lang_key.capitalize())

            # Create button with flag emoji and language name
            button_text = f"{flag} {name}" if flag else name

            lang_btn = ttk.Button(
                self.button_frame,
                text=button_text,
                command=lambda key=lang_key: self._on_language_clicked(key),
                width=15
            )
            lang_btn.grid(row=0, column=column_index, padx=5)

            # Store reference to button
            self.language_buttons[lang_key] = lang_btn

            column_index += 1

        info(f"Recreated {len(self.language_buttons)} language buttons for backend: {self.config.backend}")

    def _update_ui_from_config(self):
        """Update UI elements based on current config values"""
        from src.core.logging_controller import info, debug, warning, error, critical

        # Log current backend
        info(f"Updating UI with backend: {self.config.backend}")

        # Recreate language buttons for current backend
        self._recreate_language_buttons()

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

            # Show STOP button when running
            self.stop_frame.grid()
        else:
            self.status_label.config(text="🔴 Detenido", foreground="red")
            # Show backend info when not running
            if self.config.backend == "whisper":
                model_name = self.config.whisper_model.split('/')[-1]
                self.model_label.config(text=f"{self.config.backend.upper()}: {model_name}")
            else:
                self.model_label.config(text=f"{self.config.backend.upper()}")
            self.language_label.config(text="Ninguno")

            # Hide STOP button when not running
            self.stop_frame.grid_remove()

        # Update voice commands status
        try:
            # Get voice command settings from database (always available)
            vc_settings = self.database.get_voice_command_settings()
            enabled = vc_settings.get('enabled', False)
            keyword = vc_settings.get('keyword', 'tony')

            # If Whisper backend is active, check real-time status
            if self.controller.current_backend and self.controller.backend_type == 'whisper':
                if hasattr(self.controller.current_backend, 'get_voice_command_status'):
                    vc_status = self.controller.current_backend.get_voice_command_status()
                    if vc_status.get('enabled', False):
                        # Get current keyword from active backend (may have been updated)
                        keyword = vc_status.get('keyword', keyword)
                        if vc_status.get('command_mode_active', False):
                            remaining = vc_status.get('remaining_timeout', 0)
                            self.voice_commands_label.config(
                                text=f"🟡 [{keyword}] Esperando comando ({remaining:.1f}s)",
                                foreground="orange"
                            )
                        else:
                            self.voice_commands_label.config(
                                text=f"✓ Activo [{keyword}]",
                                foreground="green"
                            )
                    else:
                        self.voice_commands_label.config(text="Deshabilitado", foreground="gray")
                else:
                    self.voice_commands_label.config(text="Deshabilitado", foreground="gray")
            else:
                # Backend not active - show settings from database
                if self.config.backend == 'whisper':
                    if enabled:
                        self.voice_commands_label.config(
                            text=f"Configurado [{keyword}]",
                            foreground="gray"
                        )
                    else:
                        self.voice_commands_label.config(text="Deshabilitado", foreground="gray")
                else:
                    self.voice_commands_label.config(text="Solo Whisper", foreground="gray")
        except Exception as e:
            # import logging
            logging.getLogger(__name__).debug(f"Error updating voice command status: {e}")
            self.voice_commands_label.config(text="Deshabilitado", foreground="gray")

    def _schedule_status_update(self):
        """Schedule periodic status updates"""
        self._update_status()
        self.root.after(2000, self._schedule_status_update)