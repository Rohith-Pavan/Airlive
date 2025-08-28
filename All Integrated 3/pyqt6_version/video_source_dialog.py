#!/usr/bin/env python3
"""
Video Source Selection Dialog
Provides a dialog to select video input sources for camera inputs.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QListWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QMediaDevices, QCameraDevice


class VideoSourceDialog(QDialog):
    def __init__(self, current_source=None, parent=None):
        super().__init__(parent)
        self.selected_source = current_source
        self.setup_ui()
        self.refresh_sources()
        
    def setup_ui(self):
        self.setWindowTitle("Select Video Source")
        self.setModal(True)
        self.resize(400, 300)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title label
        title_label = QLabel("Available Video Sources:")
        layout.addWidget(title_label)
        
        # Video sources list
        self.sources_list = QListWidget()
        self.sources_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.sources_list)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_sources)
        buttons_layout.addWidget(self.refresh_button)
        
        buttons_layout.addStretch()  # Add space between refresh and done/cancel
        
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
        
    def refresh_sources(self):
        """Refresh the list of available video sources"""
        self.sources_list.clear()
        
        # Get available camera devices
        cameras = QMediaDevices.videoInputs()
        
        for camera in cameras:
            item = QListWidgetItem(camera.description())
            item.setData(Qt.ItemDataRole.UserRole, camera)
            self.sources_list.addItem(item)
            
        # Select current source if it exists
        if self.selected_source:
            for i in range(self.sources_list.count()):
                item = self.sources_list.item(i)
                camera_device = item.data(Qt.ItemDataRole.UserRole)
                if camera_device.id() == self.selected_source.id():
                    self.sources_list.setCurrentItem(item)
                    break
                    
    def get_selected_source(self):
        """Get the currently selected video source"""
        current_item = self.sources_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
        
    def accept(self):
        """Override accept to store selected source"""
        self.selected_source = self.get_selected_source()
        super().accept()
