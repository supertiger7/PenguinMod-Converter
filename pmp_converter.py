#!/usr/bin/env python3
"""
PenguinMod File Converter - Main Application
Unpacks and repacks .pmp files with multiple GitHub-compatible formats
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
from datetime import datetime
from pathlib import Path

from pmp_core import PMPConverter
from pmp_types import ConverterType
from pmp_logger import LogEntry, LogFilter, LogLevel


class PMPConverterGUI:
    """Main GUI application for PenguinMod file conversion"""
    
    # Color scheme
    COLORS = {
        'bg_dark': '#1e1e1e',
        'bg_medium': '#2d2d2d',
        'bg_light': '#3e3e3e',
        'accent': '#007acc',
        'text': '#007acc',
        'success': '#4ec9b0',
        'warning': '#ce9178',
        'error': '#f48771',
        'info': '#569cd6',
    }
    
    # Emoji mapping for log levels
    EMOJI_MAP = {
        LogLevel.INFO: 'ℹ️',
        LogLevel.DEBUG: '🔍',
        LogLevel.NOTE: '📝',
        LogLevel.WARN: '⚠️',
        LogLevel.ERROR: '❌',
        LogLevel.FATAL: '💀'
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("🐧 PenguinMod File Converter")
        self.root.geometry("1280x720")
        self.root.minsize(1000, 600)
        
        # Configure dark theme
        self.root.configure(bg=self.COLORS['bg_dark'])
        
        # Initialize components
        self.converter = PMPConverter()
        self.log_queue = queue.Queue()
        self.log_entries = []
        self.log_filter = LogFilter()
        
        # Build UI
        self.setup_ui()
        
        # Start log processor
        self.process_logs()
        
        # Load settings and perform auto-convert if enabled
        self.load_settings()
        self.root.after(500, self.check_autoconvert_on_startup)
        
    def setup_ui(self):
        """Build the complete UI"""
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === HEADER SECTION ===
        self.create_header(main_frame)
        
        # === CONTROL SECTION ===
        self.create_controls(main_frame)
        
        # === AUTO-CONVERT SECTION ===
        self.create_autoconvert(main_frame)
        
        # === PROGRESS SECTION ===
        self.create_progress(main_frame)
        
        # === LOGS SECTION ===
        self.create_logs(main_frame)
        
    def create_header(self, parent):
        """Create application header"""
        header_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title = tk.Label(
            header_frame,
            text="🐧 PenguinMod File Converter",
            font=("Segoe UI", 24, "bold"),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_dark']
        )
        title.pack(side=tk.LEFT)
        
        subtitle = tk.Label(
            header_frame,
            text="Unpack & Repack .pmp files with GitHub compatibility",
            font=("Segoe UI", 10),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_dark']
        )
        subtitle.pack(side=tk.LEFT, padx=(15, 0))
        
    def create_controls(self, parent):
        """Create control buttons and converter type selector"""
        control_frame = tk.Frame(parent, bg=self.COLORS['bg_medium'])
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Inner frame for padding
        inner = tk.Frame(control_frame, bg=self.COLORS['bg_medium'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Left side - Converter type
        left_frame = tk.Frame(inner, bg=self.COLORS['bg_medium'])
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        label = tk.Label(
            left_frame,
            text="📦 Converter Type:",
            font=("Segoe UI", 11, "bold"),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium']
        )
        label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Converter type dropdown
        self.converter_type = tk.StringVar(value="Full Detail PMP Folder")
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Dark.TCombobox',
            fieldbackground=self.COLORS['bg_light'],
            background=self.COLORS['bg_light'],
            foreground=self.COLORS['text'],
            arrowcolor=self.COLORS['accent']
        )
        
        converter_dropdown = ttk.Combobox(
            left_frame,
            textvariable=self.converter_type,
            values=[
                "Legacy PMP Folder",
                "Refined PMP Folder",
                "Precise PMP Folder",
                "Full Detail PMP Folder"
            ],
            state="readonly",
            width=25,
            font=("Segoe UI", 10),
            style='Dark.TCombobox'
        )
        converter_dropdown.pack(side=tk.LEFT)
        converter_dropdown.bind('<<ComboboxSelected>>', self.on_converter_type_changed)
        
        # Description label
        self.type_description = tk.Label(
            left_frame,
            text=self.get_converter_description("Full Detail PMP Folder"),
            font=("Segoe UI", 9, "italic"),
            fg=self.COLORS['info'],
            bg=self.COLORS['bg_medium']
        )
        self.type_description.pack(side=tk.LEFT, padx=(15, 0))
        
        # Right side - Action buttons
        right_frame = tk.Frame(inner, bg=self.COLORS['bg_medium'])
        right_frame.pack(side=tk.RIGHT)
        
        self.unpack_btn = tk.Button(
            right_frame,
            text="📂 Unpack .pmp",
            command=self.unpack_file,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS['accent'],
            fg='white',
            activebackground='#005a9e',
            padx=20,
            pady=8,
            cursor="hand2",
            relief=tk.FLAT
        )
        self.unpack_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.repack_btn = tk.Button(
            right_frame,
            text="📦 Repack Folder",
            command=self.repack_folder,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS['success'],
            fg='white',
            activebackground='#3da088',
            padx=20,
            pady=8,
            cursor="hand2",
            relief=tk.FLAT
        )
        self.repack_btn.pack(side=tk.LEFT)
        
    def create_autoconvert(self, parent):
        """Create auto-convert on startup section"""
        autoconvert_frame = tk.Frame(parent, bg=self.COLORS['bg_medium'])
        autoconvert_frame.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(autoconvert_frame, bg=self.COLORS['bg_medium'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Checkbox for enable/disable
        self.autoconvert_enabled = tk.BooleanVar(value=False)
        
        checkbox = tk.Checkbutton(
            inner,
            text="🔄 Convert folder to .pmp on startup",
            variable=self.autoconvert_enabled,
            command=self.on_autoconvert_toggled,
            font=("Segoe UI", 10, "bold"),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium'],
            activebackground=self.COLORS['bg_medium'],
            activeforeground=self.COLORS['text'],
            selectcolor=self.COLORS['bg_light'],
            cursor="hand2"
        )
        checkbox.pack(anchor=tk.W, pady=(0, 10))
        
        # Folder selection frame (initially hidden)
        self.folder_frame = tk.Frame(inner, bg=self.COLORS['bg_medium'])
        
        # Source folder
        source_frame = tk.Frame(self.folder_frame, bg=self.COLORS['bg_medium'])
        source_frame.pack(fill=tk.X, pady=(0, 8))
        
        source_label = tk.Label(
            source_frame,
            text="📁 Source Folder:",
            font=("Segoe UI", 9),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium'],
            width=15,
            anchor=tk.W
        )
        source_label.pack(side=tk.LEFT, padx=(20, 10))
        
        self.source_folder_var = tk.StringVar(value="")
        self.source_folder_entry = tk.Entry(
            source_frame,
            textvariable=self.source_folder_var,
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            insertbackground=self.COLORS['text'],
            relief=tk.FLAT,
            state='readonly'
        )
        self.source_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        source_btn = tk.Button(
            source_frame,
            text="Browse...",
            command=self.browse_source_folder,
            font=("Segoe UI", 9),
            bg=self.COLORS['accent'],
            fg='white',
            activebackground='#005a9e',
            cursor="hand2",
            relief=tk.FLAT,
            padx=15,
            pady=4
        )
        source_btn.pack(side=tk.LEFT)
        
        # Destination folder
        dest_frame = tk.Frame(self.folder_frame, bg=self.COLORS['bg_medium'])
        dest_frame.pack(fill=tk.X)
        
        dest_label = tk.Label(
            dest_frame,
            text="💾 Save .pmp to:",
            font=("Segoe UI", 9),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium'],
            width=15,
            anchor=tk.W
        )
        dest_label.pack(side=tk.LEFT, padx=(20, 10))
        
        self.dest_folder_var = tk.StringVar(value="")
        self.dest_folder_entry = tk.Entry(
            dest_frame,
            textvariable=self.dest_folder_var,
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            insertbackground=self.COLORS['text'],
            relief=tk.FLAT,
            state='readonly'
        )
        self.dest_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        dest_btn = tk.Button(
            dest_frame,
            text="Browse...",
            command=self.browse_dest_folder,
            font=("Segoe UI", 9),
            bg=self.COLORS['accent'],
            fg='white',
            activebackground='#005a9e',
            cursor="hand2",
            relief=tk.FLAT,
            padx=15,
            pady=4
        )
        dest_btn.pack(side=tk.LEFT)
        
    def on_autoconvert_toggled(self):
        """Handle auto-convert checkbox toggle"""
        if self.autoconvert_enabled.get():
            self.folder_frame.pack(fill=tk.X, pady=(5, 0))
            self.add_log(LogLevel.INFO, "MAIN", "Auto-convert on startup enabled")
        else:
            self.folder_frame.pack_forget()
            self.add_log(LogLevel.INFO, "MAIN", "Auto-convert on startup disabled")
        self.save_settings()  # Save when toggled
    
    def browse_source_folder(self):
        """Browse for source folder"""
        folder = filedialog.askdirectory(title="Select Source Folder to Convert")
        if folder:
            self.source_folder_var.set(folder)
            self.add_log(LogLevel.INFO, "MAIN", f"Source folder set: {folder}")
            self.save_settings()  # Save when folder selected
    
    def browse_dest_folder(self):
        """Browse for destination folder"""
        folder = filedialog.askdirectory(title="Select Destination Folder for .pmp")
        if folder:
            self.dest_folder_var.set(folder)
            self.add_log(LogLevel.INFO, "MAIN", f"Destination folder set: {folder}")
            self.save_settings()  # Save when folder selected
        
    def create_progress(self, parent):
        """Create progress bars section"""
        progress_frame = tk.Frame(parent, bg=self.COLORS['bg_medium'])
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        inner = tk.Frame(progress_frame, bg=self.COLORS['bg_medium'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Total progress
        total_label = tk.Label(
            inner,
            text="🎯 Total Progress:",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium']
        )
        total_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.total_progress_label = tk.Label(
            inner,
            text="Ready",
            font=("Segoe UI", 9),
            fg=self.COLORS['info'],
            bg=self.COLORS['bg_medium']
        )
        self.total_progress_label.grid(row=0, column=1, sticky=tk.E, pady=(0, 5), padx=(10, 0))
        
        style = ttk.Style()
        style.configure(
            "Total.Horizontal.TProgressbar",
            troughcolor=self.COLORS['bg_light'],
            background=self.COLORS['accent'],
            thickness=20
        )
        
        self.total_progress = ttk.Progressbar(
            inner,
            style="Total.Horizontal.TProgressbar",
            mode='determinate',
            maximum=100
        )
        self.total_progress.grid(row=1, column=0, columnspan=2, sticky=tk.EW)
        
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=0)
        
    def create_logs(self, parent):
        """Create logs console section"""
        logs_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        logs_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with controls
        header = tk.Frame(logs_frame, bg=self.COLORS['bg_medium'])
        header.pack(fill=tk.X, pady=(0, 5))
        
        header_inner = tk.Frame(header, bg=self.COLORS['bg_medium'])
        header_inner.pack(fill=tk.X, padx=10, pady=8)
        
        log_title = tk.Label(
            header_inner,
            text="📋 Logs Console",
            font=("Segoe UI", 11, "bold"),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium']
        )
        log_title.pack(side=tk.LEFT)
        
        # Log control buttons
        btn_frame = tk.Frame(header_inner, bg=self.COLORS['bg_medium'])
        btn_frame.pack(side=tk.RIGHT)
        
        export_btn = tk.Button(
            btn_frame,
            text="💾 Export",
            command=self.export_logs,
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            activebackground=self.COLORS['accent'],
            padx=12,
            pady=4,
            cursor="hand2",
            relief=tk.FLAT
        )
        export_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_btn = tk.Button(
            btn_frame,
            text="🗑️ Clear",
            command=self.clear_logs,
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            activebackground=self.COLORS['error'],
            padx=12,
            pady=4,
            cursor="hand2",
            relief=tk.FLAT
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        filter_btn = tk.Button(
            btn_frame,
            text="🔍 Filter",
            command=self.show_filter_menu,
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            activebackground=self.COLORS['info'],
            padx=12,
            pady=4,
            cursor="hand2",
            relief=tk.FLAT
        )
        filter_btn.pack(side=tk.LEFT)
        
        # Log text widget with scrollbar
        log_container = tk.Frame(logs_frame, bg=self.COLORS['bg_light'])
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_container,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            insertbackground=self.COLORS['text'],
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for coloring
        self.log_text.tag_config('INFO', foreground=self.COLORS['info'])
        self.log_text.tag_config('DEBUG', foreground=self.COLORS['text'])
        self.log_text.tag_config('NOTE', foreground=self.COLORS['success'])
        self.log_text.tag_config('WARN', foreground=self.COLORS['warning'])
        self.log_text.tag_config('ERROR', foreground=self.COLORS['error'])
        self.log_text.tag_config('FATAL', foreground=self.COLORS['error'], font=("Consolas", 9, "bold"))
        
    def get_converter_description(self, converter_type):
        """Get description for converter type"""
        descriptions = {
            "Legacy PMP Folder": "Single project.json file + assets",
            "Refined PMP Folder": "Sprites in separate folders with json",
            "Precise PMP Folder": "Code split by top-level blocks",
            "Full Detail PMP Folder": "Every block in separate files"
        }
        return descriptions.get(converter_type, "")
        
    def on_converter_type_changed(self, event=None):
        """Handle converter type selection change"""
        converter_type = self.converter_type.get()
        self.type_description.config(text=self.get_converter_description(converter_type))
        self.add_log(LogLevel.INFO, "MAIN", f"Selected converter type: {converter_type}")
        
    def get_selected_converter_type(self):
        """Get the ConverterType enum from selected string"""
        mapping = {
            "Legacy PMP Folder": ConverterType.LEGACY,
            "Refined PMP Folder": ConverterType.IDEA1,
            "Precise PMP Folder": ConverterType.IDEA2,
            "Full Detail PMP Folder": ConverterType.HIDDEN
        }
        return mapping.get(self.converter_type.get(), ConverterType.HIDDEN)
        
    def unpack_file(self):
        """Handle unpack button click"""
        file_path = filedialog.askopenfilename(
            title="Select .pmp file to unpack",
            filetypes=[("PenguinMod Project", "*.pmp"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        output_dir = filedialog.askdirectory(
            title="Select output directory"
        )
        
        if not output_dir:
            return
            
        self.add_log(LogLevel.INFO, "MAIN", f"Starting unpack: {Path(file_path).name}")
        self.disable_buttons()
        
        # Run in thread to prevent UI freeze
        thread = threading.Thread(
            target=self.run_unpack,
            args=(file_path, output_dir),
            daemon=True
        )
        thread.start()
        
    def run_unpack(self, file_path, output_dir):
        """Run unpack operation in background thread"""
        try:
            converter_type = self.get_selected_converter_type()
            
            # Set up progress callbacks
            def total_progress_cb(percent, message):
                self.root.after(0, self.update_total_progress, percent, message)
                
            def item_progress_cb(percent, message):
                self.root.after(0, self.update_item_progress, percent, message)
                
            def log_cb(level, source, message):
                self.add_log(level, source, message)
                
            success = self.converter.unpack(
                file_path,
                output_dir,
                converter_type,
                total_progress_cb,
                item_progress_cb,
                log_cb
            )
            
            if success:
                self.add_log(LogLevel.INFO, "MAIN", "✅ Unpack completed successfully!")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"Project unpacked successfully!\n\nOutput: {output_dir}"
                ))
            else:
                self.add_log(LogLevel.FATAL, "MAIN", "❌ Unpack failed!")
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    "Failed to unpack project. Check logs for details."
                ))
                
        except Exception as e:
            self.add_log(LogLevel.FATAL, "MAIN", f"Exception during unpack: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror(
                "Fatal Error",
                f"An error occurred:\n{str(e)}"
            ))
        finally:
            self.root.after(0, self.enable_buttons)
            self.root.after(0, self.reset_progress)
            
    def repack_folder(self):
        """Handle repack button click"""
        folder_path = filedialog.askdirectory(
            title="Select unpacked project folder"
        )
        
        if not folder_path:
            return
            
        output_file = filedialog.asksaveasfilename(
            title="Save .pmp file",
            defaultextension=".pmp",
            filetypes=[("PenguinMod Project", "*.pmp"), ("All Files", "*.*")]
        )
        
        if not output_file:
            return
            
        self.add_log(LogLevel.INFO, "MAIN", f"Starting repack: {Path(folder_path).name}")
        self.disable_buttons()
        
        # Run in thread
        thread = threading.Thread(
            target=self.run_repack,
            args=(folder_path, output_file),
            daemon=True
        )
        thread.start()
        
    def run_repack(self, folder_path, output_file):
        """Run repack operation in background thread"""
        try:
            converter_type = self.get_selected_converter_type()
            
            def total_progress_cb(percent, message):
                self.root.after(0, self.update_total_progress, percent, message)
                
            def item_progress_cb(percent, message):
                self.root.after(0, self.update_item_progress, percent, message)
                
            def log_cb(level, source, message):
                self.add_log(level, source, message)
                
            success = self.converter.repack(
                folder_path,
                output_file,
                converter_type,
                total_progress_cb,
                item_progress_cb,
                log_cb
            )
            
            if success:
                self.add_log(LogLevel.INFO, "MAIN", "✅ Repack completed successfully!")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"Project repacked successfully!\n\nOutput: {output_file}"
                ))
            else:
                self.add_log(LogLevel.FATAL, "MAIN", "❌ Repack failed!")
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    "Failed to repack project. Check logs for details."
                ))
                
        except Exception as e:
            self.add_log(LogLevel.FATAL, "MAIN", f"Exception during repack: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror(
                "Fatal Error",
                f"An error occurred:\n{str(e)}"
            ))
        finally:
            self.root.after(0, self.enable_buttons)
            self.root.after(0, self.reset_progress)
            
    def update_total_progress(self, percent, message):
        """Update total progress bar"""
        self.total_progress['value'] = percent
        self.total_progress_label.config(text=f"{message} ({percent}%)")
        
    def update_item_progress(self, percent, message):
        """Update item progress bar - REMOVED"""
        pass  # Item progress bar removed from GUI
        
    def reset_progress(self):
        """Reset progress bars"""
        self.total_progress['value'] = 0
        self.total_progress_label.config(text="Ready")
        
    def disable_buttons(self):
        """Disable action buttons during operation"""
        self.unpack_btn.config(state=tk.DISABLED)
        self.repack_btn.config(state=tk.DISABLED)
        
    def enable_buttons(self):
        """Enable action buttons after operation"""
        self.unpack_btn.config(state=tk.NORMAL)
        self.repack_btn.config(state=tk.NORMAL)
        
    def add_log(self, level, source, message):
        """Add log entry to queue"""
        entry = LogEntry(level, source, message)
        self.log_queue.put(entry)
        
    def process_logs(self):
        """Process log queue and update UI"""
        try:
            while True:
                entry = self.log_queue.get_nowait()
                self.log_entries.append(entry)
                
                if self.log_filter.should_show(entry):
                    self.display_log(entry)
                    
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.process_logs)
            
    def display_log(self, entry):
        """Display a log entry in the text widget"""
        emoji = self.EMOJI_MAP.get(entry.level, '•')
        timestamp = entry.timestamp.strftime("%H:%M:%S")
        
        log_line = f"[{timestamp}] {emoji} [{entry.level.name}][{entry.source}] {entry.message}\n"
        
        self.log_text.insert(tk.END, log_line, entry.level.name)
        self.log_text.see(tk.END)
        
    def clear_logs(self):
        """Clear all logs"""
        result = messagebox.askyesno(
            "Clear Logs",
            "Are you sure you want to clear all logs?"
        )
        
        if result:
            self.log_text.delete(1.0, tk.END)
            self.log_entries.clear()
            self.add_log(LogLevel.INFO, "MAIN", "Logs cleared")
            
    def export_logs(self):
        """Export logs to file"""
        if not self.log_entries:
            messagebox.showinfo("Export Logs", "No logs to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("PenguinMod File Converter - Log Export\n")
                f.write("=" * 80 + "\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                for entry in self.log_entries:
                    emoji = self.EMOJI_MAP.get(entry.level, '•')
                    timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {emoji} [{entry.level.name}][{entry.source}] {entry.message}\n")
                    
            self.add_log(LogLevel.INFO, "MAIN", f"Logs exported to: {file_path}")
            messagebox.showinfo("Success", f"Logs exported successfully!\n\n{file_path}")
            
        except Exception as e:
            self.add_log(LogLevel.ERROR, "MAIN", f"Failed to export logs: {str(e)}")
            messagebox.showerror("Error", f"Failed to export logs:\n{str(e)}")
            
    def show_filter_menu(self):
        """Show filter menu popup"""
        popup = tk.Toplevel(self.root)
        popup.title("🔍 Filter Logs")
        popup.geometry("350x300")
        popup.configure(bg=self.COLORS['bg_medium'])
        popup.resizable(False, False)
        
        # Center popup
        popup.transient(self.root)
        popup.grab_set()
        
        # Title
        title = tk.Label(
            popup,
            text="Select Log Levels to Display",
            font=("Segoe UI", 12, "bold"),
            fg=self.COLORS['text'],
            bg=self.COLORS['bg_medium']
        )
        title.pack(pady=15)
        
        # Checkboxes frame
        check_frame = tk.Frame(popup, bg=self.COLORS['bg_medium'])
        check_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        checkboxes = {}
        for level in LogLevel:
            var = tk.BooleanVar(value=self.log_filter.is_enabled(level))
            checkboxes[level] = var
            
            emoji = self.EMOJI_MAP.get(level, '•')
            check = tk.Checkbutton(
                check_frame,
                text=f"{emoji} {level.name}",
                variable=var,
                font=("Segoe UI", 10),
                fg=self.COLORS['text'],
                bg=self.COLORS['bg_medium'],
                selectcolor=self.COLORS['bg_light'],
                activebackground=self.COLORS['bg_medium'],
                activeforeground=self.COLORS['text']
            )
            check.pack(anchor=tk.W, pady=5)
            
        # Buttons
        btn_frame = tk.Frame(popup, bg=self.COLORS['bg_medium'])
        btn_frame.pack(pady=15)
        
        def apply_filter():
            for level, var in checkboxes.items():
                self.log_filter.set_level(level, var.get())
            self.refresh_logs()
            popup.destroy()
            
        apply_btn = tk.Button(
            btn_frame,
            text="✓ Apply",
            command=apply_filter,
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS['success'],
            fg='white',
            padx=20,
            pady=5,
            cursor="hand2",
            relief=tk.FLAT
        )
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(
            btn_frame,
            text="✗ Cancel",
            command=popup.destroy,
            font=("Segoe UI", 10),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text'],
            padx=20,
            pady=5,
            cursor="hand2",
            relief=tk.FLAT
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
    def refresh_logs(self):
        """Refresh log display based on current filter"""
        self.log_text.delete(1.0, tk.END)
        for entry in self.log_entries:
            if self.log_filter.should_show(entry):
                self.display_log(entry)
    
    def load_settings(self):
        """Load settings from config file"""
        import json
        config_file = Path.home() / ".pmp_converter_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    settings = json.load(f)
                    
                self.autoconvert_enabled.set(settings.get('autoconvert_enabled', False))
                self.source_folder_var.set(settings.get('source_folder', ''))
                self.dest_folder_var.set(settings.get('dest_folder', ''))
                
                # Show folder frame if enabled
                if self.autoconvert_enabled.get():
                    self.folder_frame.pack(fill=tk.X, pady=(5, 0))
                    
                self.add_log(LogLevel.INFO, "SETTINGS", "Settings loaded")
            except Exception as e:
                self.add_log(LogLevel.WARN, "SETTINGS", f"Failed to load settings: {e}")
    
    def save_settings(self):
        """Save settings to config file"""
        import json
        config_file = Path.home() / ".pmp_converter_config.json"
        
        settings = {
            'autoconvert_enabled': self.autoconvert_enabled.get(),
            'source_folder': self.source_folder_var.get(),
            'dest_folder': self.dest_folder_var.get()
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(settings, f, indent=2)
            self.add_log(LogLevel.DEBUG, "SETTINGS", "Settings saved")
        except Exception as e:
            self.add_log(LogLevel.WARN, "SETTINGS", f"Failed to save settings: {e}")
    
    def check_autoconvert_on_startup(self):
        """Check and perform auto-convert if enabled"""
        if not self.autoconvert_enabled.get():
            return
            
        source = self.source_folder_var.get()
        dest = self.dest_folder_var.get()
        
        if not source or not dest:
            self.add_log(LogLevel.WARN, "AUTO-CONVERT", "Auto-convert enabled but folders not set")
            return
        
        source_path = Path(source)
        dest_path = Path(dest)
        
        if not source_path.exists():
            self.add_log(LogLevel.ERROR, "AUTO-CONVERT", f"Source folder does not exist: {source}")
            return
        
        if not dest_path.exists():
            self.add_log(LogLevel.ERROR, "AUTO-CONVERT", f"Destination folder does not exist: {dest}")
            return
        
        # Perform auto-convert
        self.add_log(LogLevel.INFO, "AUTO-CONVERT", "🔄 Starting automatic conversion on startup...")
        
        # Create output filename
        folder_name = source_path.name
        output_file = dest_path / f"{folder_name}.pmp"
        
        # Run repack in thread
        thread = threading.Thread(
            target=self._auto_repack_thread,
            args=(source, str(output_file)),
            daemon=True
        )
        thread.start()
    
    def _auto_repack_thread(self, folder_path, output_file):
        """Thread worker for auto-convert repack"""
        try:
            self.disable_buttons()
            self.root.after(0, self.add_log, LogLevel.INFO, "AUTO-CONVERT", f"Converting: {folder_path}")
            
            # Set up progress callbacks
            def total_progress_cb(percent, message):
                self.root.after(0, self.update_total_progress, percent, message)
            
            def item_progress_cb(percent, message):
                pass  # Item progress removed
            
            def log_cb(level, category, message):
                self.root.after(0, self.add_log, level, category, message)
            
            # Perform repack
            converter_type = self.get_selected_converter_type()
            success = self.converter.repack(
                folder_path,
                output_file,
                converter_type,
                total_progress_cb,
                item_progress_cb,
                log_cb
            )
            
            if success:
                self.root.after(0, self.add_log, LogLevel.INFO, "AUTO-CONVERT", f"✅ Auto-convert complete: {output_file}")
                self.root.after(0, messagebox.showinfo, "Auto-Convert Complete", 
                               f"Successfully converted to:\n{output_file}")
            else:
                self.root.after(0, self.add_log, LogLevel.ERROR, "AUTO-CONVERT", "❌ Auto-convert failed")
                self.root.after(0, messagebox.showerror, "Auto-Convert Failed", 
                               "Failed to convert project. Check logs for details.")
                
        except Exception as e:
            self.root.after(0, self.add_log, LogLevel.ERROR, "AUTO-CONVERT", f"Error: {str(e)}")
            self.root.after(0, messagebox.showerror, "Error", f"Auto-convert error:\n{str(e)}")
        finally:
            self.root.after(0, self.reset_progress)
            self.root.after(0, self.enable_buttons)



def main():
    """Main entry point"""
    root = tk.Tk()
    app = PMPConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
