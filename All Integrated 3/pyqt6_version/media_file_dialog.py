#!/usr/bin/env python3
"""
Media File Selection Dialog
Provides a dialog to select media files for media inputs.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QListWidgetItem, QFileDialog)
from PyQt6.QtCore import Qt
from pathlib import Path
import os


class MediaFileDialog(QDialog):
    def __init__(self, current_file=None, parent=None):
        super().__init__(parent)
        self.selected_file = current_file
        self.recent_files = []  # Store recently selected files
        self.setup_ui()
        self.load_recent_files()
        
    def setup_ui(self):
        self.setWindowTitle("Select Media File")
        self.setModal(True)
        self.resize(500, 400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title label
        title_label = QLabel("Select Media File:")
        layout.addWidget(title_label)
        
        # Browse button
        browse_layout = QHBoxLayout()
        self.browse_button = QPushButton("Browse for File...")
        self.browse_button.clicked.connect(self.browse_file)
        browse_layout.addWidget(self.browse_button)
        browse_layout.addStretch()
        layout.addLayout(browse_layout)
        
        # Recent files label
        recent_label = QLabel("Recent Files:")
        layout.addWidget(recent_label)
        
        # Recent files list
        self.files_list = QListWidget()
        self.files_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.files_list)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Clear list button
        self.clear_button = QPushButton("Clear List")
        self.clear_button.clicked.connect(self.clear_recent_files)
        buttons_layout.addWidget(self.clear_button)
        
        buttons_layout.addStretch()  # Add space between clear and done/cancel
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        # Done button
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.accept)
        self.done_button.setDefault(True)
        buttons_layout.addWidget(self.done_button)
        
        layout.addLayout(buttons_layout)
        
    def browse_file(self):
        """Open file browser to select media file"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilters([
            "Video files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)",
            "Audio files (*.mp3 *.wav *.aac *.flac *.ogg)",
            "All files (*.*)"
        ])
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self.add_to_recent_files(file_path)
                self.refresh_files_list()
                
                # Auto-select the newly added file
                for i in range(self.files_list.count()):
                    item = self.files_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == file_path:
                        self.files_list.setCurrentItem(item)
                        break
    
    def add_to_recent_files(self, file_path):
        """Add file to recent files list"""
        # Remove if already exists to avoid duplicates
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        # Add to beginning of list
        self.recent_files.insert(0, file_path)
        
        # Keep only last 10 files
        if len(self.recent_files) > 10:
            self.recent_files = self.recent_files[:10]
    
    def load_recent_files(self):
        """Load recent files (in a real app, this would load from settings)"""
        # For now, just initialize empty - could be extended to save/load from file
        pass
    
    def refresh_files_list(self):
        """Refresh the list of recent files"""
        self.files_list.clear()
        
        for file_path in self.recent_files:
            if os.path.exists(file_path):
                file_name = Path(file_path).name
                item = QListWidgetItem(f"{file_name}")
                item.setToolTip(file_path)  # Show full path on hover
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                self.files_list.addItem(item)
                
        # Select current file if it exists
        if self.selected_file:
            for i in range(self.files_list.count()):
                item = self.files_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.selected_file:
                    self.files_list.setCurrentItem(item)
                    break
    
    def clear_recent_files(self):
        """Clear the recent files list"""
        self.recent_files.clear()
        self.refresh_files_list()
                    
    def get_selected_file(self):
        """Get the currently selected media file"""
        current_item = self.files_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
        
    def accept(self):
        """Override accept to store selected file"""
        self.selected_file = self.get_selected_file()
        super().accept()
