#!/usr/bin/env python3
"""
Complete HDMI Integration Test
Tests the full video pipeline integration with HDMI display streaming
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QTextEdit, QGroupBox,
                             QComboBox, QCheckBox, QSlider)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QCamera, QMediaCaptureSession, QMediaDevices
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush

from display_manager import get_display_manager
from hdmi_stream_manager import get_hdmi_stream_manager
from graphics_output_widget import GraphicsOutputWidget, GraphicsOutputManager
from stream_settings_dialog import StreamSettingsDialog


class CompleteHDMITestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Complete HDMI Integration Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Managers
        self.display_manager = get_display_manager()
        self.hdmi_manager = get_hdmi_stream_manager()
        self.graphics_manager = GraphicsOutputManager()
        
        # Media components
        self.camera = None
        self.camera_session = None
        self.media_player = None
        
        # Test content
        self.test_content_timer = QTimer()
        self.test_content_timer.timeout.connect(self.update_test_content)
        self.test_frame_counter = 0
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Main output and controls
        left_panel = QVBoxLayout()
        
        # Title
        title_label = QLabel("Complete HDMI Integration Test")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        left_panel.addWidget(title_label)
        
        # Main graphics output
        output_group = QGroupBox("Main Output (with Effects)")
        output_layout = QVBoxLayout(output_group)
        
        # Create graphics output widget
        self.graphics_widget = self.graphics_manager.create_output_widget("main", self)
        self.graphics_widget.setMinimumSize(640, 360)
        output_layout.addWidget(self.graphics_widget)
        
        left_panel.addWidget(output_group)
        
        # Source controls
        source_group = QGroupBox("Video Source")
        source_layout = QVBoxLayout(source_group)
        
        source_controls = QHBoxLayout()
        
        self.camera_btn = QPushButton("Start Camera")
        self.camera_btn.clicked.connect(self.toggle_camera)
        source_controls.addWidget(self.camera_btn)
        
        self.media_btn = QPushButton("Load Video")
        self.media_btn.clicked.connect(self.load_media)
        source_controls.addWidget(self.media_btn)
        
        self.test_content_btn = QPushButton("Test Pattern")
        self.test_content_btn.clicked.connect(self.toggle_test_content)
        source_controls.addWidget(self.test_content_btn)
        
        source_layout.addLayout(source_controls)
        left_panel.addWidget(source_group)
        
        # Effects controls
        effects_group = QGroupBox("Effects & Overlays")
        effects_layout = QVBoxLayout(effects_group)
        
        effects_controls = QHBoxLayout()
        
        self.add_frame_btn = QPushButton("Add Frame Effect")
        self.add_frame_btn.clicked.connect(self.add_frame_effect)
        effects_controls.addWidget(self.add_frame_btn)
        
        self.clear_effects_btn = QPushButton("Clear Effects")
        self.clear_effects_btn.clicked.connect(self.clear_effects)
        effects_controls.addWidget(self.clear_effects_btn)
        
        effects_layout.addLayout(effects_controls)
        left_panel.addWidget(effects_group)
        
        main_layout.addLayout(left_panel)
        
        # Right panel - HDMI controls and status
        right_panel = QVBoxLayout()
        
        # Display info
        display_group = QGroupBox("Display Information")
        display_layout = QVBoxLayout(display_group)
        
        displays = self.display_manager.get_displays()
        display_layout.addWidget(QLabel(f"Total displays: {len(displays)}"))
        
        for display in displays:
            display_layout.addWidget(QLabel(f"  • {display}"))
        
        external_displays = self.display_manager.get_external_displays()
        display_layout.addWidget(QLabel(f"External displays: {len(external_displays)}"))
        
        right_panel.addWidget(display_group)
        
        # HDMI controls
        hdmi_group = QGroupBox("HDMI Display Controls")
        hdmi_layout = QVBoxLayout(hdmi_group)
        
        # Display selection
        display_select_layout = QHBoxLayout()
        display_select_layout.addWidget(QLabel("Target Display:"))
        
        self.display_combo = QComboBox()
        self.update_display_combo()
        display_select_layout.addWidget(self.display_combo)
        
        hdmi_layout.addLayout(display_select_layout)
        
        # Display mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Fullscreen",
            "Windowed (800x600)",
            "Windowed (1024x768)",
            "Windowed (1280x720)"
        ])
        mode_layout.addWidget(self.mode_combo)
        
        hdmi_layout.addLayout(mode_layout)
        
        # Options
        self.always_on_top_check = QCheckBox("Always on top")
        self.always_on_top_check.setChecked(True)
        hdmi_layout.addWidget(self.always_on_top_check)
        
        # HDMI control buttons
        hdmi_controls = QHBoxLayout()
        
        self.settings_btn = QPushButton("Stream Settings")
        self.settings_btn.clicked.connect(self.open_stream_settings)
        hdmi_controls.addWidget(self.settings_btn)
        
        self.start_hdmi_btn = QPushButton("Start HDMI")
        self.start_hdmi_btn.clicked.connect(self.start_hdmi_display)
        self.start_hdmi_btn.setEnabled(self.display_manager.has_external_displays())
        hdmi_controls.addWidget(self.start_hdmi_btn)
        
        self.stop_hdmi_btn = QPushButton("Stop HDMI")
        self.stop_hdmi_btn.clicked.connect(self.stop_hdmi_display)
        self.stop_hdmi_btn.setEnabled(False)
        hdmi_controls.addWidget(self.stop_hdmi_btn)
        
        hdmi_layout.addLayout(hdmi_controls)
        
        right_panel.addWidget(hdmi_group)
        
        # Status and log
        status_group = QGroupBox("Status & Log")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(200)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        right_panel.addWidget(status_group)
        
        main_layout.addLayout(right_panel)
        
        # Initial status
        if not self.display_manager.has_external_displays():
            self.log_status("⚠️ No external displays detected. Connect an HDMI display to test HDMI streaming.")
        else:
            self.log_status("✅ External displays detected. Ready for HDMI streaming test.")
            
        self.log_status("🎬 Graphics output widget created with effects support")
    
    def connect_signals(self):
        """Connect manager signals"""
        self.hdmi_manager.hdmi_started.connect(self.on_hdmi_started)
        self.hdmi_manager.hdmi_stopped.connect(self.on_hdmi_stopped)
        self.hdmi_manager.hdmi_error.connect(self.on_hdmi_error)
        
        self.display_manager.displays_changed.connect(self.on_displays_changed)
    
    def update_display_combo(self):
        """Update display combo box"""
        self.display_combo.clear()
        display_options = self.display_manager.get_display_options_for_combo()
        for display_name, display_index in display_options:
            self.display_combo.addItem(display_name, display_index)
    
    def toggle_camera(self):
        """Toggle camera input"""
        if self.camera is None:
            # Start camera
            cameras = QMediaDevices.videoInputs()
            if cameras:
                self.camera = QCamera(cameras[0])
                self.camera_session = QMediaCaptureSession()
                self.camera_session.setCamera(self.camera)
                
                # Connect to graphics video item
                video_item = self.graphics_widget.get_video_item()
                if video_item:
                    self.camera_session.setVideoOutput(video_item)
                    self.camera.start()
                    
                    self.camera_btn.setText("Stop Camera")
                    self.log_status("📹 Camera started and connected to graphics output")
                else:
                    self.log_status("❌ Failed to get video item from graphics widget")
            else:
                self.log_status("❌ No cameras available")
        else:
            # Stop camera
            if self.camera:
                self.camera.stop()
                self.camera = None
                self.camera_session = None
                
            self.camera_btn.setText("Start Camera")
            self.log_status("⏹️ Camera stopped")
    
    def load_media(self):
        """Load media file"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File", 
            "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        
        if file_path:
            if not self.media_player:
                self.media_player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
                
                # Connect to graphics video item
                video_item = self.graphics_widget.get_video_item()
                if video_item:
                    self.media_player.setVideoOutput(video_item)
                else:
                    self.log_status("❌ Failed to get video item from graphics widget")
                    return
            
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()
            
            self.log_status(f"🎥 Loaded and playing: {file_path}")
    
    def toggle_test_content(self):
        """Toggle test pattern content"""
        if not self.test_content_timer.isActive():
            self.test_content_timer.start(100)  # 10 FPS test pattern
            self.test_content_btn.setText("Stop Test Pattern")
            self.log_status("🎨 Started animated test pattern")
        else:
            self.test_content_timer.stop()
            self.test_content_btn.setText("Test Pattern")
            
            # Clear test content
            video_item = self.graphics_widget.get_video_item()
            if video_item and hasattr(video_item, 'set_qimage_frame'):
                video_item.set_qimage_frame(None)
                
            self.log_status("⏹️ Stopped test pattern")
    
    def update_test_content(self):
        """Update test pattern content"""
        try:
            from PyQt6.QtGui import QImage, QLinearGradient
            
            # Create animated test pattern
            width, height = 640, 360
            image = QImage(width, height, QImage.Format.Format_RGB888)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Animated gradient background
            gradient = QLinearGradient(0, 0, width, height)
            
            # Animate colors based on frame counter
            hue1 = (self.test_frame_counter * 2) % 360
            hue2 = (self.test_frame_counter * 3 + 180) % 360
            
            color1 = QColor.fromHsv(hue1, 150, 200)
            color2 = QColor.fromHsv(hue2, 150, 100)
            
            gradient.setColorAt(0, color1)
            gradient.setColorAt(1, color2)
            painter.fillRect(0, 0, width, height, QBrush(gradient))
            
            # Moving elements
            painter.setPen(QColor(255, 255, 255))
            
            # Moving circle
            circle_x = (self.test_frame_counter * 3) % (width + 100) - 50
            circle_y = height // 2 + 50 * (self.test_frame_counter % 60 - 30) / 30
            painter.drawEllipse(int(circle_x - 25), int(circle_y - 25), 50, 50)
            
            # Frame counter and info
            font = painter.font()
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            
            painter.drawText(20, 40, f"HDMI Test Pattern - Frame {self.test_frame_counter}")
            painter.drawText(20, height - 60, f"Resolution: {width}x{height}")
            
            # Timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            painter.drawText(20, height - 20, f"Time: {timestamp}")
            
            painter.end()
            
            # Send to graphics video item
            video_item = self.graphics_widget.get_video_item()
            if video_item and hasattr(video_item, 'set_qimage_frame'):
                video_item.set_qimage_frame(image)
            
            self.test_frame_counter += 1
            
        except Exception as e:
            self.log_status(f"❌ Error updating test content: {e}")
    
    def add_frame_effect(self):
        """Add a frame effect overlay"""
        # Create a simple test frame effect
        try:
            from PyQt6.QtGui import QImage, QPen
            
            width, height = 640, 360
            frame_image = QImage(width, height, QImage.Format.Format_ARGB32)
            frame_image.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(frame_image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw decorative frame
            pen = QPen(QColor(255, 215, 0), 8)  # Gold color
            painter.setPen(pen)
            
            # Outer border
            painter.drawRect(10, 10, width - 20, height - 20)
            
            # Inner decorative elements
            painter.drawEllipse(width//2 - 50, 20, 100, 40)
            painter.drawEllipse(width//2 - 50, height - 60, 100, 40)
            
            # Corner decorations
            painter.drawEllipse(20, 20, 30, 30)
            painter.drawEllipse(width - 50, 20, 30, 30)
            painter.drawEllipse(20, height - 50, 30, 30)
            painter.drawEllipse(width - 50, height - 50, 30, 30)
            
            painter.end()
            
            # Convert to pixmap and apply to graphics widget
            pixmap = QPixmap.fromImage(frame_image)
            
            # Save as temporary file and apply
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                pixmap.save(f.name, 'PNG')
                self.graphics_widget.set_frame_overlay(f.name)
                
            self.log_status("🖼️ Added decorative frame effect")
            
        except Exception as e:
            self.log_status(f"❌ Error adding frame effect: {e}")
    
    def clear_effects(self):
        """Clear all effects"""
        self.graphics_widget.clear_frame_overlay()
        self.log_status("🧹 Cleared all effects")
    
    def open_stream_settings(self):
        """Open stream settings dialog"""
        dialog = StreamSettingsDialog("HDMITest", self)
        if dialog.exec():
            self.log_status("💾 Stream settings configured")
    
    def start_hdmi_display(self):
        """Start HDMI display output"""
        if not self.display_manager.has_external_displays():
            self.log_status("❌ No external displays available")
            return
        
        # Get selected display
        display_index = self.display_combo.currentData()
        if display_index is None:
            self.log_status("❌ No display selected")
            return
        
        # Create settings
        settings = {
            'platform': 'HDMI Display',
            'hdmi_display_index': display_index,
            'hdmi_display_mode': self.mode_combo.currentText(),
            'hdmi_always_on_top': self.always_on_top_check.isChecked(),
            'hdmi_match_resolution': False
        }
        
        # Configure and start
        if self.hdmi_manager.configure_hdmi_stream("HDMITest", settings):
            if self.hdmi_manager.start_hdmi_stream("HDMITest", self.graphics_widget):
                self.start_hdmi_btn.setEnabled(False)
                self.stop_hdmi_btn.setEnabled(True)
                
                display_info = self.display_manager.get_display_by_index(display_index)
                self.log_status(f"🖥️ Started HDMI display on {display_info.name}")
                self.log_status("✨ All effects and content will appear on HDMI display!")
            else:
                self.log_status("❌ Failed to start HDMI display")
        else:
            self.log_status("❌ Failed to configure HDMI stream")
    
    def stop_hdmi_display(self):
        """Stop HDMI display output"""
        if self.hdmi_manager.stop_hdmi_stream("HDMITest"):
            self.start_hdmi_btn.setEnabled(True)
            self.stop_hdmi_btn.setEnabled(False)
            self.log_status("⏹️ Stopped HDMI display")
        else:
            self.log_status("❌ Failed to stop HDMI display")
    
    def on_hdmi_started(self, stream_name):
        """Handle HDMI stream started"""
        self.log_status(f"✅ HDMI stream '{stream_name}' started successfully")
    
    def on_hdmi_stopped(self, stream_name):
        """Handle HDMI stream stopped"""
        self.log_status(f"⏹️ HDMI stream '{stream_name}' stopped")
    
    def on_hdmi_error(self, stream_name, error_message):
        """Handle HDMI stream error"""
        self.log_status(f"❌ HDMI stream '{stream_name}' error: {error_message}")
    
    def on_displays_changed(self):
        """Handle display configuration changes"""
        displays = self.display_manager.get_displays()
        external = self.display_manager.get_external_displays()
        
        self.log_status(f"🔄 Display configuration changed: {len(displays)} total, {len(external)} external")
        
        # Update combo box
        self.update_display_combo()
        
        # Update button states
        has_external = self.display_manager.has_external_displays()
        self.start_hdmi_btn.setEnabled(has_external and not self.hdmi_manager.is_hdmi_streaming("HDMITest"))
    
    def log_status(self, message):
        """Log status message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.status_text.append(formatted_message)
        print(formatted_message)  # Also print to console
    
    def closeEvent(self, event):
        """Handle window close"""
        # Clean up
        if self.camera:
            self.camera.stop()
        
        if self.media_player:
            self.media_player.stop()
            
        if self.test_content_timer.isActive():
            self.test_content_timer.stop()
        
        self.hdmi_manager.cleanup()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = CompleteHDMITestWindow()
    window.show()
    
    sys.exit(app.exec())