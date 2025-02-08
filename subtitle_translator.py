import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from tkinter import filedialog
import json
from subtitle_processor import SubtitleProcessor
from translator import GPTTranslator
import os
from subtitle_extractor import SubtitleExtractor
import logging
from pathlib import Path
from jellyfin_renamer import JellyfinRenamer

# Configure customtkinter
ctk.set_appearance_mode("dark")  # Modes: system (default), light, dark
ctk.set_default_color_theme("green")  # Themes: blue (default), dark-blue, green

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Colors:
    BG_DARK = "#0D1117"  # Dark background
    FRAME_BG = "#161B22"  # Slightly lighter background for frames
    TEXT = "#C9D1D9"      # Main text color
    ACCENT = "#238636"    # Green accent color
    HOVER = "#2EA043"     # Lighter green for hover
    ERROR = "#DA3633"     # Error red
    BORDER = "#30363D"    # Border color
    SEPARATOR = "#30363D" # Separator line color
    BUTTON_BG = "#238636" # Button background
    INPUT_BG = "#0D1117"  # Input background
    PROGRESS_BG = "#238636" # Progress bar color

class SubtitleTranslatorApp:
    LANGUAGE_CODES = {
        'english': 'eng',
        'spanish': 'spa',
        'french': 'fre',
        'german': 'ger',
        'italian': 'ita',
        'portuguese': 'por',
        'russian': 'rus',
        'japanese': 'jpn',
        'korean': 'kor',
        'chinese': 'chi'
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Subtitle Translator")
        self.root.geometry("1200x800")
        self.root.minsize(600, 1200)
        self.root.configure(bg=Colors.BG_DARK)
        
        # Configure styles for all widgets
        style = {
            "fg_color": Colors.FRAME_BG,
            "text_color": Colors.TEXT,
            "border_color": Colors.BORDER,
            "border_width": 1,
        }
        
        # Create scrollable container with theme
        self.main_container = ctk.CTkScrollableFrame(
            self.root,
            fg_color=Colors.BG_DARK,
            corner_radius=0
        )
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initialize all variables first
        self.file_path_var = tk.StringVar()
        self.file_frame = None
        self.auto_select_english = tk.BooleanVar(value=True)
        self.batch_mode = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.target_lang = tk.StringVar(value="Spanish")
        self.batch_info_var = tk.StringVar(value="")
        self.current_file_var = tk.StringVar(value="-")
        self.batch_status_var = tk.StringVar(value="-")
        self.batch_progress_var = tk.DoubleVar(value=0)
        self.api_key_var = tk.StringVar(value=os.getenv('OPENAI_API_KEY', ''))
        self.show_api_key = tk.BooleanVar(value=False)
        
        self.settings_file = "translator_settings.json"
        self.load_settings()
        
        self.setup_ui()
        self.translator = GPTTranslator()
        self.extractor = SubtitleExtractor()
        self.subtitle_processor = None
        self.subtitle_streams = []
        
        # Queue for batch processing
        self.batch_queue = []
        self.current_batch_index = 0
        
        self.jellyfin_renamer = JellyfinRenamer()
        
    def setup_ui(self):
        # Title section with new style
        title_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=Colors.FRAME_BG,
            corner_radius=8
        )
        title_frame.pack(fill="x", pady=(20, 30))
        
        ctk.CTkLabel(
            title_frame,
            text="Subtitle Translator",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=Colors.TEXT
        ).pack(side="left", padx=20)
        
        # Section separator function with themed line
        def add_section_separator():
            separator = ctk.CTkFrame(
                self.main_container,
                height=2,
                fg_color=Colors.SEPARATOR
            )
            separator.pack(fill="x", pady=15, padx=10)
        
        # Style for section headers
        section_header_style = {
            "font": ctk.CTkFont(size=16, weight="bold"),
            "text_color": Colors.TEXT
        }
        
        # Style for buttons
        button_style = {
            "fg_color": Colors.BUTTON_BG,
            "hover_color": Colors.HOVER,
            "corner_radius": 6,
            "border_width": 0
        }
        
        # Style for entry fields
        entry_style = {
            "fg_color": Colors.INPUT_BG,
            "border_color": Colors.BORDER,
            "border_width": 1,
            "corner_radius": 6
        }
        
        # 1. Mode Selection Section
        section_frame = ctk.CTkFrame(self.main_container)
        section_frame.pack(fill="x", pady=(0, 20), padx=10)  # More padding
        
        ctk.CTkLabel(
            section_frame,
            text="Step 1: Select Processing Mode 🔄",
            font=ctk.CTkFont(size=16, weight="bold")  # Larger section title
        ).pack(pady=10)  # More padding
        
        mode_frame = ctk.CTkFrame(section_frame)
        mode_frame.pack(fill="x", pady=(0, 10), padx=20)  # Inner padding
        
        ctk.CTkRadioButton(
            mode_frame,
            text="File Selection",
            variable=self.batch_mode,
            value=False,
            command=self.toggle_mode
        ).pack(side="left", padx=30)
        
        ctk.CTkRadioButton(
            mode_frame,
            text="Folder Scan",
            variable=self.batch_mode,
            value=True,
            command=self.toggle_mode
        ).pack(side="left", padx=30)
        
        add_section_separator()
        
        # 2. File Selection Section
        file_section = ctk.CTkFrame(self.main_container)
        file_section.pack(fill="x", pady=(0, 20), padx=10)
        
        ctk.CTkLabel(
            file_section,
            text="Step 2: Choose File(s) 📁",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        file_selection_frame = ctk.CTkFrame(file_section)
        file_selection_frame.pack(fill="x", pady=(0, 10), padx=20)
        
        self.path_label = ctk.CTkLabel(file_selection_frame, text="File:")
        self.path_label.pack(side="left", padx=(10, 5))
        
        path_entry = ctk.CTkEntry(
            file_selection_frame,
            textvariable=self.file_path_var,
            width=400
        )
        path_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        browse_button = ctk.CTkButton(
            file_selection_frame,
            text="Browse",
            command=self.browse_path,
            width=100
        )
        browse_button.pack(side="left", padx=5)
        
        # Batch info frame
        self.batch_frame = ctk.CTkFrame(file_section)
        batch_info_label = ctk.CTkLabel(
            self.batch_frame,
            textvariable=self.batch_info_var
        )
        batch_info_label.pack(pady=5)
        
        # Only show batch frame if in batch mode
        if self.batch_mode.get():
            self.batch_frame.pack(fill="x", pady=5)
        
        add_section_separator()
        
        # 3. Subtitle Options Section
        options_section = ctk.CTkFrame(self.main_container)
        options_section.pack(fill="x", pady=(0, 20), padx=10)
        
        ctk.CTkLabel(
            options_section,
            text="Step 3: Configure Translation Options 🌐",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Initialize stream_frame first
        self.stream_frame = ctk.CTkFrame(options_section)
        self.stream_frame.pack(fill="x", pady=(0, 10), padx=20)
        
        self.auto_select_english_btn = ctk.CTkCheckBox(
            self.stream_frame,
            text="Auto-select English subtitles",
            variable=self.auto_select_english
        )
        self.auto_select_english_btn.pack(side="left", padx=(10, 20))
        
        stream_label = ctk.CTkLabel(self.stream_frame, text="Stream:")
        stream_label.pack(side="left", padx=5)
        
        self.stream_combo = ctk.CTkComboBox(
            self.stream_frame,
            values=[],
            state="readonly",
            width=200
        )
        self.stream_combo.pack(side="left", padx=5)
        
        # Initially hide the stream frame until needed
        self.stream_frame.pack_forget()
        
        # Translation options frame
        translation_frame = ctk.CTkFrame(options_section)
        translation_frame.pack(fill="x", pady=(0, 10), padx=20)
        
        ctk.CTkLabel(
            translation_frame,
            text="Target Language:"
        ).pack(side="left", padx=(10, 5))
        
        target_lang_entry = ctk.CTkEntry(
            translation_frame,
            textvariable=self.target_lang,
            width=100
        )
        target_lang_entry.pack(side="left", padx=5)
        
        # API Key frame
        api_frame = ctk.CTkFrame(options_section)
        api_frame.pack(fill="x", pady=(0, 10), padx=20)
        
        ctk.CTkLabel(
            api_frame,
            text="OpenAI API Key:"
        ).pack(side="left", padx=(10, 5))
        
        self.api_key_entry = ctk.CTkEntry(
            api_frame,
            textvariable=self.api_key_var,
            width=300,
            show="•",  # Hide API key with dots
            **entry_style
        )
        self.api_key_entry.pack(side="left", padx=5)
        
        # Show/Hide API key button
        self.show_api_button = ctk.CTkButton(
            api_frame,
            text="👁️",
            width=30,
            command=self.toggle_api_visibility
        )
        self.show_api_button.pack(side="left", padx=5)
        
        # Block limit options
        block_frame = ctk.CTkFrame(options_section)
        block_frame.pack(fill="x", pady=(0, 10), padx=20)
        
        self.block_limit = tk.StringVar(value="all")
        ctk.CTkRadioButton(
            block_frame,
            text="All Subtitles",
            variable=self.block_limit,
            value="all"
        ).pack(side="left", padx=(10, 20))
        
        ctk.CTkRadioButton(
            block_frame,
            text="Limited",
            variable=self.block_limit,
            value="limited"
        ).pack(side="left", padx=5)
        
        self.num_blocks = tk.StringVar(value="10")
        blocks_entry = ctk.CTkEntry(
            block_frame,
            textvariable=self.num_blocks,
            width=60,
            validate='key',
            validatecommand=(self.root.register(self._validate_number), '%P')
        )
        blocks_entry.pack(side="left", padx=5)
        
        add_section_separator()
        
        # Example for the progress section:
        add_section_separator()
        
        progress_section = ctk.CTkFrame(self.main_container)
        progress_section.pack(fill="x", pady=(0, 20), padx=10)
        
        ctk.CTkLabel(
            progress_section,
            text="Step 4: Translation Progress 📊",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Batch progress with better spacing
        self.batch_progress_frame = ctk.CTkFrame(progress_section)
        self.batch_progress_frame.pack(fill="x", pady=(5, 10), padx=20)
        
        batch_progress_header = ctk.CTkFrame(self.batch_progress_frame)
        batch_progress_header.pack(fill="x", padx=10)
        
        self.batch_progress_label = ctk.CTkLabel(
            batch_progress_header, 
            text="Overall Progress:"
        )
        self.batch_progress_label.pack(side="left")
        
        self.batch_progress_percent = ctk.CTkLabel(
            batch_progress_header,
            text="0%",
            text_color=Colors.ACCENT
        )
        self.batch_progress_percent.pack(side="right")
        
        self.batch_progress = ctk.CTkProgressBar(
            self.batch_progress_frame,
            mode="determinate",
            orientation="horizontal",
            height=25,  # Taller progress bar
            corner_radius=3,
            fg_color=Colors.INPUT_BG,
            progress_color=Colors.PROGRESS_BG,
            border_color=Colors.BORDER,
            border_width=1
        )
        self.batch_progress.pack(fill="x", padx=10, pady=5)
        self.batch_progress.set(0)
        
        # Current progress with better spacing
        current_progress_frame = ctk.CTkFrame(progress_section)
        current_progress_frame.pack(fill="x", pady=5, padx=20)
        
        current_progress_header = ctk.CTkFrame(current_progress_frame)
        current_progress_header.pack(fill="x", padx=10)
        
        ctk.CTkLabel(
            current_progress_header, 
            text="Current File:"
        ).pack(side="left")
        
        self.progress_percent = ctk.CTkLabel(
            current_progress_header,
            text="0%",
            text_color=Colors.ACCENT
        )
        self.progress_percent.pack(side="right")
        
        self.progress_bar = ctk.CTkProgressBar(
            current_progress_frame,
            mode="determinate",
            orientation="horizontal",
            height=25,  # Taller progress bar
            corner_radius=3,
            fg_color=Colors.INPUT_BG,
            progress_color=Colors.PROGRESS_BG,
            border_color=Colors.BORDER,
            border_width=1
        )
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        
        # Add indeterminate progress for loading states
        self.loading_progress = ctk.CTkProgressBar(
            current_progress_frame,
            mode="indeterminate",
            orientation="horizontal",
            height=25,  # Match height
            corner_radius=3,
            fg_color=Colors.INPUT_BG,
            progress_color=Colors.PROGRESS_BG,
            border_color=Colors.BORDER,
            border_width=1
        )
        self.loading_progress.pack(fill="x", padx=10, pady=5)
        self.loading_progress.pack_forget()  # Hide initially
        
        # Control buttons with better spacing
        add_section_separator()
        
        control_frame = ctk.CTkFrame(self.main_container)
        control_frame.pack(fill="x", pady=(10, 20), padx=10)
        
        self.translate_button = ctk.CTkButton(
            control_frame, 
            text="▶️ Start Translation",
            command=self.start_translation,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=200,  # Fixed width buttons
            height=40,   # Taller buttons
            **button_style
        )
        self.translate_button.pack(side="left", padx=20)
        
        self.cancel_button = ctk.CTkButton(
            control_frame, 
            text="⏹️ Cancel",
            command=self.cancel_translation,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=200,
            height=40,
            state="disabled",  # Initially disabled
            **button_style
        )
        self.cancel_button.pack(side="left", padx=20)
        
        # 4. Jellyfin Naming Section
        jellyfin_section = ctk.CTkFrame(self.main_container)
        jellyfin_section.pack(fill="x", pady=(0, 20), padx=10)
        
        ctk.CTkLabel(
            jellyfin_section,
            text="Step 5: Jellyfin Naming Options 🏷️",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Flags frame
        flags_frame = ctk.CTkFrame(jellyfin_section)
        flags_frame.pack(fill="x", pady=(0, 10), padx=20)
        
        # Checkboxes frame
        checkbox_frame = ctk.CTkFrame(flags_frame)
        checkbox_frame.pack(side="left", padx=10)
        
        self.default_flag = tk.BooleanVar(value=False)
        self.forced_flag = tk.BooleanVar(value=False)
        self.sdh_flag = tk.BooleanVar(value=False)
        self.cleanup_originals = tk.BooleanVar(value=True)
        
        self.default_flag_btn = ctk.CTkCheckBox(
            checkbox_frame,
            text="Default",
            variable=self.default_flag
        )
        self.default_flag_btn.pack(side="left", padx=5)
        
        self.forced_flag_btn = ctk.CTkCheckBox(
            checkbox_frame,
            text="Forced",
            variable=self.forced_flag
        )
        self.forced_flag_btn.pack(side="left", padx=5)
        
        self.sdh_flag_btn = ctk.CTkCheckBox(
            checkbox_frame,
            text="SDH",
            variable=self.sdh_flag
        )
        self.sdh_flag_btn.pack(side="left", padx=5)
        
        self.cleanup_originals_btn = ctk.CTkCheckBox(
            checkbox_frame,
            text="Delete original files",
            variable=self.cleanup_originals
        )
        self.cleanup_originals_btn.pack(side="left", padx=20)
        
        # Buttons frame
        button_frame = ctk.CTkFrame(flags_frame)
        button_frame.pack(side="right", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Preview Rename",
            command=self.preview_jellyfin_rename,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Rename for Jellyfin",
            command=self.rename_for_jellyfin,
            width=120
        ).pack(side="left", padx=5)
        
        # Add Synchronization Section before Jellyfin section
        sync_section = ctk.CTkFrame(self.main_container)
        sync_section.pack(fill="x", pady=(0, 20), padx=10)
        
        ctk.CTkLabel(
            sync_section,
            text="Subtitle Synchronization ⏱️",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        sync_controls = ctk.CTkFrame(sync_section)
        sync_controls.pack(fill="x", pady=(0, 10), padx=20)
        
        # Time adjustment entry and buttons
        time_frame = ctk.CTkFrame(sync_controls)
        time_frame.pack(side="left", padx=10)
        
        self.time_adjustment = tk.StringVar(value="0")
        
        ctk.CTkLabel(
            time_frame,
            text="Time Adjustment (ms):"
        ).pack(side="left", padx=5)
        
        time_entry = ctk.CTkEntry(
            time_frame,
            textvariable=self.time_adjustment,
            width=100,
            validate='key',
            validatecommand=(self.root.register(self._validate_time_adjustment), '%P')
        )
        time_entry.pack(side="left", padx=5)
        
        # Quick adjustment buttons
        quick_adjust_frame = ctk.CTkFrame(sync_controls)
        quick_adjust_frame.pack(side="left", padx=10)
        
        ctk.CTkButton(
            quick_adjust_frame,
            text="-1s",
            command=lambda: self._quick_time_adjust(-1000),
            width=60
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            quick_adjust_frame,
            text="-500ms",
            command=lambda: self._quick_time_adjust(-500),
            width=60
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            quick_adjust_frame,
            text="+500ms",
            command=lambda: self._quick_time_adjust(500),
            width=60
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            quick_adjust_frame,
            text="+1s",
            command=lambda: self._quick_time_adjust(1000),
            width=60
        ).pack(side="left", padx=2)
        
        # Apply button
        apply_frame = ctk.CTkFrame(sync_controls)
        apply_frame.pack(side="right", padx=10)
        
        self.apply_sync_button = ctk.CTkButton(
            apply_frame,
            text="Apply Time Shift",
            command=self.apply_time_adjustment,
            width=120
        )
        self.apply_sync_button.pack(side="right", padx=5)
        
        add_section_separator()
        
        # Add tooltips to important controls
        self.create_tooltip(
            self.auto_select_english_btn, 
            "Automatically select English subtitles when available"
        )
        self.create_tooltip(
            self.cleanup_originals_btn,
            "Delete original subtitle files after renaming to Jellyfin format"
        )
        self.create_tooltip(
            self.default_flag_btn,
            "Mark this subtitle as the default track"
        )
        self.create_tooltip(
            self.forced_flag_btn,
            "Mark this subtitle as forced (for foreign language parts)"
        )
        self.create_tooltip(
            self.sdh_flag_btn,
            "Mark this subtitle as containing hearing impaired captions"
        )
        
        # Optional: If you want a visual separator, replace the CTkSeparator with this:
        separator = ctk.CTkFrame(self.main_container, height=2)
        separator.pack(fill="x", pady=5)
        
    def toggle_mode(self):
        """Toggle between folder batch mode and file selection mode"""
        is_batch = self.batch_mode.get()
        self.path_label.configure(text="Folder:" if is_batch else "File(s):")  # Updated label
        self.file_path_var.set("")  # Clear path
        self.batch_info_var.set("")
        self.batch_queue = []  # Clear batch queue
        
        if is_batch:
            self.batch_progress_frame.pack(fill="x", pady=(0, 5))
            self.batch_frame.pack(after=self.file_frame)
        else:
            self.batch_progress_frame.pack_forget()
            self.batch_frame.pack_forget()

    def browse_path(self):
        """Browse for file or folder depending on mode"""
        if self.batch_mode.get():
            initial_dir = os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else "."
            path = filedialog.askdirectory(initialdir=initial_dir)
            if path:
                self.file_path_var.set(path)
                self.scan_folder(path)
                self.save_settings()
        else:
            initial_dir = os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else "."
            file_paths = filedialog.askopenfilenames(
                initialdir=initial_dir,
                filetypes=[
                    ("Video/Subtitle files", "*.mp4 *.mkv *.avi *.srt"),
                    ("Video files", "*.mp4 *.mkv *.avi"),
                    ("Subtitle files", "*.srt"),
                    ("All files", "*.*")
                ]
            )
            if file_paths:
                # Convert tuple to list for batch processing
                self.batch_queue = list(file_paths)
                # Show all selected files in the entry with a counter
                if len(self.batch_queue) == 1:
                    self.file_path_var.set(self.batch_queue[0])
                    self.batch_info_var.set("")
                else:
                    first_file = os.path.basename(self.batch_queue[0])
                    self.file_path_var.set(f"{first_file} (+{len(self.batch_queue)-1} more files)")
                    self.batch_info_var.set(f"Selected {len(self.batch_queue)} files to process")
                    self.batch_frame.pack(fill="x", pady=5)
                
                # Check first file type
                self.check_file_type(self.batch_queue[0])
                self.save_settings()

    def scan_folder(self, folder_path):
        """Scan folder for video files"""
        video_extensions = {'.mp4', '.mkv', '.avi'}
        self.batch_queue = []
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                if Path(file).suffix.lower() in video_extensions:
                    self.batch_queue.append(os.path.join(root, file))
        
        self.batch_info_var.set(f"Found {len(self.batch_queue)} video files to process")
        logger.debug(f"Batch queue: {self.batch_queue}")
        
    def check_file_type(self, file_path):
        """Check if file is video or subtitle and handle accordingly"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            logger.debug(f"Checking file type for: {file_path}")
            
            if ext == '.srt':
                logger.debug("Direct subtitle file detected")
                self.stream_frame.pack_forget()
                self.subtitle_streams = []
            else:
                logger.debug("Video file detected, checking for subtitle streams")
                try:
                    self.subtitle_streams = self.extractor.list_subtitles(file_path)
                    if not self.subtitle_streams:
                        # Create and show a popup notification
                        popup = tk.Toplevel(self.root)
                        popup.title("No Subtitles Found")
                        popup.geometry("400x150")
                        popup.configure(bg=Colors.FRAME_BG)
                        
                        # Center the popup on the screen
                        popup.transient(self.root)
                        popup.grab_set()
                        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
                        y = self.root.winfo_y() + (self.root.winfo_height() - 150) // 2
                        popup.geometry(f"+{x}+{y}")
                        
                        # Add message
                        message_frame = ctk.CTkFrame(popup, fg_color=Colors.FRAME_BG)
                        message_frame.pack(expand=True, fill="both", padx=20, pady=20)
                        
                        ctk.CTkLabel(
                            message_frame,
                            text="❌ No subtitle streams found in this video file.\nPlease select a different file or add external subtitles.",
                            font=ctk.CTkFont(size=14),
                            text_color=Colors.TEXT,
                            wraplength=350
                        ).pack(pady=10)
                        
                        # Add OK button
                        ctk.CTkButton(
                            message_frame,
                            text="OK",
                            command=popup.destroy,
                            width=100
                        ).pack(pady=10)
                        
                        self.show_error("No subtitle streams found in video file")
                        if self.batch_mode.get():
                            self.current_batch_index += 1
                            self.process_next_batch_file()
                        return
                    
                    # Update combobox with available streams
                    stream_options = [
                        f"{s['title']} ({s['language']}) - {s['codec']}"
                        for s in self.subtitle_streams
                    ]
                    self.stream_combo.configure(values=stream_options)
                    
                    # Try to auto-select English subtitles if enabled
                    if self.auto_select_english.get():
                        eng_index = self._find_english_subtitle_index(self.subtitle_streams)
                        if eng_index >= 0:
                            self.stream_combo.set(stream_options[eng_index])
                            logger.debug(f"Auto-selected English subtitle stream {eng_index}")
                        else:
                            if self.batch_mode.get():
                                logger.warning(f"No English subtitles found in {file_path}, skipping...")
                                self.current_batch_index += 1
                                self.process_next_batch_file()
                            else:
                                self.stream_combo.set(stream_options[0])
                                logger.debug("No English subtitles found, selecting first stream")
                    else:
                        self.stream_combo.set(stream_options[0])
                    
                    self.stream_frame.pack(fill="x", after=self.file_frame)
                    logger.debug(f"Found {len(stream_options)} subtitle streams")
                    
                    # If in batch mode and we found English subtitles, start translation directly
                    if self.batch_mode.get() and eng_index >= 0:
                        self.start_single_translation()
                    
                except Exception as e:
                    self.show_error("Failed to process video file", e)
                    if self.batch_mode.get():
                        self.current_batch_index += 1
                        self.process_next_batch_file()
                    
        except Exception as e:
            self.show_error("Error checking file type", e)
            if self.batch_mode.get():
                self.current_batch_index += 1
                self.process_next_batch_file()

    def _find_english_subtitle_index(self, streams):
        """Find the best matching English subtitle stream"""
        # Keywords that might indicate English subtitles
        english_indicators = ['eng', 'en', 'english']
        
        for i, stream in enumerate(streams):
            # Check language tag
            language = stream.get('language', '').lower()
            title = stream.get('title', '').lower()
            
            # Check if any English indicators are in the language or title
            if any(ind in language for ind in english_indicators) or \
               any(ind in title for ind in english_indicators):
                logger.debug(f"Found English subtitle stream: {stream}")
                return i
                
        return -1
        
    def process_next_batch_file(self):
        """Process the next file in the batch queue"""
        try:
            if self.current_batch_index >= len(self.batch_queue):
                self.update_batch_status("Completed")
                self.update_file_status("-")
                self.update_status("Batch processing completed!")
                self.batch_progress.set(1.0)
                # Re-enable translate button and disable cancel button
                self.translate_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
                self.save_settings()
                return
                
            current_file = self.batch_queue[self.current_batch_index]
            filename = Path(current_file).name
            self.update_file_status(filename)
            self.update_batch_status(f"Processing file {self.current_batch_index + 1} of {len(self.batch_queue)}")
            self.file_path_var.set(current_file)  # Update displayed file path
            
            # Update batch progress
            progress = (self.current_batch_index / len(self.batch_queue)) * 100
            self.batch_progress.set(progress/100)
            self.batch_progress_percent.configure(text=f"{int(progress)}%")
            
            # Check if translation already exists
            if self.check_existing_translation(current_file, self.target_lang.get()):
                logger.info(f"Translation already exists for {filename}, skipping...")
                self.update_status("Skipping - Translation exists")
                self.current_batch_index += 1
                self.process_next_batch_file()
                return
            
            # Start translation for current file
            self.start_single_translation()
            
        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            self.update_status(f"Batch processing error: {str(e)}")
            # Move to next file even if there's an error
            self.current_batch_index += 1
            self.process_next_batch_file()

    def start_single_translation(self):
        """Start translation for a single file"""
        try:
            logger.debug("Starting single file translation")
            subtitle_path = self.file_path_var.get()
            
            if self.subtitle_streams:
                logger.debug("Processing video file with subtitle streams")
                selected_stream = self.stream_combo.get()
                if not selected_stream:
                    self.show_error("Please select a subtitle stream")
                    return
                    
                # Find the stream index from the selected value
                selected_index = next(
                    (i for i, s in enumerate(self.subtitle_streams)
                    if f"{s['title']} ({s['language']}) - {s['codec']}" == selected_stream),
                    -1
                )
                
                if selected_index < 0:
                    self.show_error("Invalid subtitle stream selected")
                    return
                    
                stream = self.subtitle_streams[selected_index]
                subtitle_path = self.extractor.extract_subtitle(
                    self.file_path_var.get(),
                    stream['index']
                )
                logger.info(f"Extracted subtitles from stream {stream['index']} to {subtitle_path}")
                self.status_var.set(f"Extracted subtitles from stream {stream['index']}")
            
            block_limit = None
            if self.block_limit.get() == "limited":
                try:
                    block_limit = int(self.num_blocks.get())
                    logger.debug(f"Using block limit: {block_limit}")
                except ValueError as e:
                    self.show_error("Please enter a valid number of blocks", e)
                    return
            
            logger.info(f"Starting translation with target language: {self.target_lang.get()}")
            self.subtitle_processor = SubtitleProcessor(
                subtitle_path,
                self.translator,
                self.target_lang.get(),
                self.update_progress,
                self.update_status,
                block_limit
            )
            
            self.subtitle_processor.translate()
            
        except Exception as e:
            self.show_error("Translation error", e)
            logger.exception("Detailed translation error:")
            # Move to next file if in batch mode
            if len(self.batch_queue) > 1:
                self.current_batch_index += 1
                self.process_next_batch_file()

    def start_translation(self):
        """Main translation entry point"""
        if not self.api_key_var.get():
            self.show_error("Please enter your OpenAI API key")
            return
        
        if not self.file_path_var.get():
            self.show_error("Please select a file or folder")
            return
        
        # Disable translate button and enable cancel button
        self.translate_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        
        # Update environment variable before starting
        os.environ['OPENAI_API_KEY'] = self.api_key_var.get()
        
        # Show loading state
        self.show_loading()
        
        try:
            # Reset batch progress
            self.current_batch_index = 0
            self.batch_progress.set(0)
            self.batch_progress_percent.configure(text="0%")
            
            # Show batch progress frame for multiple files
            if len(self.batch_queue) > 1:
                self.batch_progress_frame.pack(fill="x", pady=(0, 5))
            
            # Start processing files
            self.process_next_batch_file()
            
        except Exception as e:
            self.show_error("Translation error", e)
            # Re-enable translate button and disable cancel button
            self.translate_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
        finally:
            self.hide_loading()

    def update_progress(self, value):
        """Update progress bar with a value between 0 and 100"""
        normalized_value = value / 100  # Convert to 0-1 range
        self.progress_bar.set(normalized_value)
        self.progress_percent.configure(text=f"{int(value)}%")
        
        if value == 100:
            self.progress_percent.configure(text_color=Colors.ACCENT)
            
            # Only show completion message and re-enable buttons if this is the last file
            if self.current_batch_index >= len(self.batch_queue) - 1:
                self.flash_status("✅ All files completed successfully!")
                self.translate_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
            else:
                # Move to next file
                self.current_batch_index += 1
                self.progress_bar.set(0)  # Reset progress for next file
                self.progress_percent.configure(text="0%")
                self.progress_percent.configure(text_color=Colors.TEXT)  # Reset color
                self.process_next_batch_file()

    def update_status(self, message):
        """Update the status message"""
        if hasattr(self, 'status_var'):
            self.status_var.set(message)
            self.root.update_idletasks()

    def update_file_status(self, filename):
        """Update the current file being processed"""
        self.current_file_var.set(filename)
        self.root.update_idletasks()
        
    def update_batch_status(self, status):
        """Update the batch processing status"""
        self.batch_status_var.set(status)
        self.root.update_idletasks()
        
    def cancel_translation(self):
        """Cancel the current translation process"""
        if self.subtitle_processor:
            logger.info("Cancelling translation...")
            self.subtitle_processor.cancel_flag = True
            self.status_var.set("Translation cancelled")
            
            # Re-enable translate button and disable cancel button
            self.translate_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            
            # If in batch mode, reset batch processing
            if self.batch_mode.get():
                self.current_batch_index = 0
                self.batch_progress.set(0)
                self.batch_info_var.set("Batch processing cancelled")
        
        # Flash the cancel button
        style = ttk.Style()
        style.configure("Cancel.TButton", background="#dc3545")  # Red
        self.root.after(200, lambda: style.configure("Cancel.TButton", background=""))
        
    def show_error(self, message, error=None):
        """Display error message"""
        error_message = f"{message}"
        if error:
            error_message += f": {str(error)}"
        logger.error(error_message)
        self.update_status(f"Error: {error_message}")

    def load_settings(self):
        """Load saved settings if they exist"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    
                    # Safely set values
                    if 'target_language' in settings:
                        self.target_lang.set(settings['target_language'])
                    if 'auto_select_english' in settings:
                        self.auto_select_english.set(settings['auto_select_english'])
                    if 'last_directory' in settings:
                        last_dir = settings['last_directory']
                        if os.path.exists(last_dir):
                            self.file_path_var.set(last_dir)
                    if 'api_key' in settings:
                        self.api_key_var.set(settings['api_key'])
                        os.environ['OPENAI_API_KEY'] = settings['api_key']
                    
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            # Continue with defaults if settings can't be loaded

    def save_settings(self):
        """Save current settings"""
        try:
            settings = {
                'target_language': self.target_lang.get(),
                'auto_select_english': self.auto_select_english.get(),
                'last_directory': os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else '',
                'api_key': self.api_key_var.get()  # Add API key to settings
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
            
            # Update environment variable
            os.environ['OPENAI_API_KEY'] = self.api_key_var.get()
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            
    def _get_language_code(self, language):
        """Get the ISO 639-1/2 language code"""
        return self.LANGUAGE_CODES.get(language.lower(), language.lower()[:3])

    def check_existing_translation(self, video_path, target_language):
        """Check if translation already exists for this file"""
        try:
            base_path = os.path.splitext(video_path)[0]
            lang_code = self._get_language_code(target_language)
            
            # Check for both potential naming patterns
            patterns = [
                f"{base_path}.{lang_code}.srt",  # moviename.spa.srt
                f"{base_path}_{lang_code}.srt",  # moviename_spa.srt
                f"{base_path}.eng.{lang_code}.srt",  # moviename.eng.spa.srt (for extracted English)
                f"{base_path}_stream_*_{lang_code}.srt"  # moviename_stream_3_spa.srt
            ]
            
            for pattern in patterns:
                if '*' in pattern:
                    # Handle wildcard pattern
                    import glob
                    if glob.glob(pattern):
                        logger.debug(f"Found existing translation matching pattern: {pattern}")
                        return True
                elif os.path.exists(pattern):
                    logger.debug(f"Found existing translation: {pattern}")
                    return True
                    
            logger.debug(f"No existing translation found for {video_path}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking for existing translation: {e}")
            return False

    def get_jellyfin_flags(self):
        """Get current flag settings"""
        return {
            'default': self.default_flag.get(),
            'forced': self.forced_flag.get(),
            'sdh': self.sdh_flag.get()
        }
    
    def preview_jellyfin_rename(self):
        """Preview what files would be renamed"""
        if not self.file_path_var.get():
            self.show_error("Please select a folder first")
            return
            
        folder = self.file_path_var.get() if self.batch_mode.get() else os.path.dirname(self.file_path_var.get())
        changes = self.jellyfin_renamer.preview_changes(folder, self.get_jellyfin_flags())
        
        if not changes:
            self.status_var.set("No files need renaming")
            return
            
        # Create preview window
        preview = tk.Toplevel(self.root)
        preview.title("Rename Preview")
        preview.geometry("600x400")
        
        # Add preview content
        text = tk.Text(preview, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        
        text.insert(tk.END, "The following files will be renamed:\n\n")
        for old, new in changes:
            text.insert(tk.END, f"From: {old}\nTo:   {new}\n\n")
    
    def rename_for_jellyfin(self):
        """Rename subtitle files to Jellyfin standard"""
        if not self.file_path_var.get():
            self.show_error("Please select a folder first")
            return
            
        try:
            folder = self.file_path_var.get() if self.batch_mode.get() else os.path.dirname(self.file_path_var.get())
            renamed, deleted, errors = self.jellyfin_renamer.rename_subtitles(
                folder, 
                self.get_jellyfin_flags(),
                self.cleanup_originals.get()
            )
            
            if errors:
                error_msg = "\n".join(f"{file}: {error}" for file, error in errors)
                self.show_error(f"Some files could not be renamed:\n{error_msg}")
            
            status_msg = []
            if renamed:
                status_msg.append(f"Renamed {len(renamed)} files")
            if deleted:
                status_msg.append(f"Deleted {len(deleted)} original files")
                
            if status_msg:
                self.status_var.set(" and ".join(status_msg))
            else:
                self.status_var.set("No files needed renaming")
                
        except Exception as e:
            self.show_error("Error renaming files", e)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        def show_tooltip(event=None):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ctk.CTkLabel(
                tooltip,
                text=text,
                fg_color=Colors.FRAME_BG,
                text_color=Colors.TEXT,
                corner_radius=4
            )
            label.pack(padx=8, pady=4)
            
            def hide_tooltip(event=None):
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', hide_tooltip)
            tooltip.bind('<Leave>', hide_tooltip)
        
        widget.bind('<Enter>', show_tooltip)

    def flash_status(self, message, duration=3000):
        """Flash a status message temporarily"""
        if "completed" in message.lower():
            message = "✅ " + message
            # Show completion message in a popup
            popup = tk.Toplevel(self.root)
            popup.title("Success")
            popup.geometry("300x100")
            popup.configure(bg=Colors.FRAME_BG)
            
            label = ctk.CTkLabel(
                popup,
                text=message,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=Colors.ACCENT
            )
            label.pack(expand=True, fill="both", padx=20, pady=20)
            
            # Auto-close popup after duration
            popup.after(duration, popup.destroy)
            
        elif "error" in message.lower():
            message = "❌ " + message
            
        original_status = self.status_var.get()
        self.status_var.set(message)
        self.root.after(duration, lambda: self.status_var.set(original_status))

    def _validate_number(self, value):
        """Validate that input is a number between 1 and 1000"""
        if value == "":
            return True
        try:
            num = int(value)
            return 1 <= num <= 1000
        except ValueError:
            return False

    def update_batch_progress(self, value):
        """Update batch progress bar with a value between 0 and 100"""
        normalized_value = value / 100
        self.batch_progress.set(normalized_value)
        self.batch_progress_percent.configure(text=f"{int(value)}%")
        
        if value == 100:
            self.batch_progress_percent.configure(text_color=Colors.ACCENT)
            self.flash_status("✅ Batch processing completed successfully!")

    def toggle_api_visibility(self):
        """Toggle API key visibility"""
        if self.api_key_entry.cget('show') == "•":
            self.api_key_entry.configure(show="")
            self.show_api_button.configure(text="🔒")
        else:
            self.api_key_entry.configure(show="•")
            self.show_api_button.configure(text="👁️")

    def show_loading(self):
        """Show indeterminate loading progress"""
        self.progress_bar.pack_forget()
        self.progress_percent.configure(text="Loading...")
        self.loading_progress.pack(fill="x", padx=10, pady=5)
        self.loading_progress.start()

    def hide_loading(self):
        """Hide loading progress and show normal progress"""
        self.loading_progress.stop()
        self.loading_progress.pack_forget()
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_percent.configure(text="0%")

    def _validate_time_adjustment(self, value):
        """Validate time adjustment input"""
        if value == "" or value == "-":
            return True
        try:
            num = int(value)
            return -3600000 <= num <= 3600000  # Allow ±1 hour adjustment
        except ValueError:
            return False
            
    def _quick_time_adjust(self, ms):
        """Quick time adjustment by predefined amounts"""
        try:
            current = int(self.time_adjustment.get() or 0)
            new_value = current + ms
            if -3600000 <= new_value <= 3600000:
                self.time_adjustment.set(str(new_value))
        except ValueError:
            self.time_adjustment.set(str(ms))
            
    def apply_time_adjustment(self):
        """Apply time adjustment to current subtitle file"""
        try:
            if not self.file_path_var.get():
                self.show_error("Please select a subtitle file first")
                return
                
            time_shift = int(self.time_adjustment.get() or 0)
            if time_shift == 0:
                return
                
            file_path = self.file_path_var.get()
            if not file_path.lower().endswith('.srt'):
                self.show_error("Please select an SRT subtitle file")
                return
                
            # Create a subtitle processor if not exists
            if not self.subtitle_processor:
                self.subtitle_processor = SubtitleProcessor(
                    file_path,
                    self.translator,
                    self.target_lang.get(),
                    self.update_progress,
                    self.update_status
                )
                
            # Apply the time adjustment
            if self.subtitle_processor.adjust_timing(file_path, time_shift):
                self.flash_status(f"✅ Adjusted subtitle timing by {time_shift}ms")
            else:
                self.show_error("Failed to adjust subtitle timing")
                
        except Exception as e:
            self.show_error("Error adjusting subtitle timing", e)

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleTranslatorApp(root)
    root.mainloop() 