#!/usr/bin/env python3
"""
FFmpeg Installation Helper for GoLive Studio
Provides guidance and automatic installation options for FFmpeg on Windows
"""

import subprocess
import sys
import os
try:
    import requests
except ImportError:
    requests = None
import zipfile
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QProgressBar, QTextEdit, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont


class FFmpegDownloadThread(QThread):
    """Thread for downloading and installing FFmpeg"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    installation_complete = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, install_path, parent=None):
        super().__init__(parent)
        self.install_path = Path(install_path)
        
    def run(self):
        """Download and install FFmpeg"""
        try:
            self.status_updated.emit("Downloading FFmpeg...")
            
            # FFmpeg download URL for Windows (static build)
            ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_path = temp_file.name
                
                # Download with progress
                response = requests.get(ffmpeg_url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 50)  # 50% for download
                            self.progress_updated.emit(progress)
                            
            self.status_updated.emit("Extracting FFmpeg...")
            
            # Extract ZIP file
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(self.install_path)
                
            self.progress_updated.emit(75)
            
            # Find ffmpeg.exe in extracted folder
            ffmpeg_exe = None
            for root, dirs, files in os.walk(self.install_path):
                if "ffmpeg.exe" in files:
                    ffmpeg_exe = Path(root) / "ffmpeg.exe"
                    break
                    
            if ffmpeg_exe and ffmpeg_exe.exists():
                self.progress_updated.emit(100)
                self.status_updated.emit("Installation complete!")
                self.installation_complete.emit(True, str(ffmpeg_exe.parent))
            else:
                self.installation_complete.emit(False, "FFmpeg executable not found in download")
                
            # Clean up temp file
            os.unlink(temp_path)
            
        except Exception as e:
            self.installation_complete.emit(False, f"Installation failed: {str(e)}")


class FFmpegInstallDialog(QDialog):
    """Dialog for FFmpeg installation and setup"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ffmpeg_path = None
        self.setup_ui()
        self.check_ffmpeg_status()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("FFmpeg Setup - GoLive Studio")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("FFmpeg Setup Required")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Status label
        self.status_label = QLabel("Checking FFmpeg installation...")
        layout.addWidget(self.status_label)
        
        # Info text
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(150)
        info_text.setPlainText(
            "FFmpeg is required for live streaming functionality.\n\n"
            "Options:\n"
            "1. Automatic Installation - Download and install FFmpeg automatically\n"
            "2. Manual Installation - Download from https://ffmpeg.org/download.html\n"
            "3. Use Existing - If FFmpeg is already installed but not detected\n\n"
            "For streaming to work properly, FFmpeg must be accessible from the command line."
        )
        layout.addWidget(info_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Auto install button
        self.auto_install_button = QPushButton("Auto Install FFmpeg")
        self.auto_install_button.clicked.connect(self.auto_install_ffmpeg)
        button_layout.addWidget(self.auto_install_button)
        
        # Manual install button
        self.manual_button = QPushButton("Manual Installation Guide")
        self.manual_button.clicked.connect(self.show_manual_guide)
        button_layout.addWidget(self.manual_button)
        
        # Test button
        self.test_button = QPushButton("Test FFmpeg")
        self.test_button.clicked.connect(self.test_ffmpeg)
        button_layout.addWidget(self.test_button)
        
        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def check_ffmpeg_status(self):
        """Check current FFmpeg status"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.status_label.setText(f"✅ FFmpeg found: {version_line}")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                self.auto_install_button.setText("FFmpeg Already Installed")
                self.auto_install_button.setEnabled(False)
                return True
            else:
                self.status_label.setText("❌ FFmpeg not working properly")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            self.status_label.setText("❌ FFmpeg not found in system PATH")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            return False
            
    def auto_install_ffmpeg(self):
        """Automatically download and install FFmpeg"""
        # Choose installation directory
        install_dir = Path.home() / "GoLive_FFmpeg"
        install_dir.mkdir(exist_ok=True)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.auto_install_button.setEnabled(False)
        
        # Start download thread
        self.download_thread = FFmpegDownloadThread(install_dir)
        self.download_thread.progress_updated.connect(self.progress_bar.setValue)
        self.download_thread.status_updated.connect(self.status_label.setText)
        self.download_thread.installation_complete.connect(self.on_installation_complete)
        self.download_thread.start()
        
    def on_installation_complete(self, success, message):
        """Handle installation completion"""
        self.progress_bar.setVisible(False)
        self.auto_install_button.setEnabled(True)
        
        if success:
            self.ffmpeg_path = message
            self.status_label.setText(f"✅ FFmpeg installed to: {message}")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Show PATH instruction
            QMessageBox.information(
                self,
                "Installation Complete",
                f"FFmpeg has been installed to:\n{message}\n\n"
                "To use FFmpeg system-wide, add this path to your system PATH environment variable.\n\n"
                "For now, GoLive Studio will use the installed FFmpeg automatically."
            )
        else:
            self.status_label.setText(f"❌ Installation failed: {message}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            
    def show_manual_guide(self):
        """Show manual installation guide"""
        guide_text = """
Manual FFmpeg Installation Guide:

1. Download FFmpeg:
   • Go to https://ffmpeg.org/download.html
   • Click "Windows" → "Windows builds by BtbN"
   • Download "ffmpeg-master-latest-win64-gpl.zip"

2. Extract and Install:
   • Extract the ZIP file to C:\\ffmpeg
   • The ffmpeg.exe should be in C:\\ffmpeg\\bin\\

3. Add to PATH:
   • Open System Properties → Advanced → Environment Variables
   • Edit "Path" variable and add: C:\\ffmpeg\\bin
   • Click OK and restart your applications

4. Verify Installation:
   • Open Command Prompt
   • Type: ffmpeg -version
   • You should see FFmpeg version information

5. Restart GoLive Studio
   • Close and reopen the application
   • Streaming should now work properly
        """
        
        QMessageBox.information(self, "Manual Installation Guide", guide_text)
        
    def test_ffmpeg(self):
        """Test FFmpeg availability"""
        if self.check_ffmpeg_status():
            QMessageBox.information(self, "FFmpeg Test", "✅ FFmpeg is working correctly!")
        else:
            QMessageBox.warning(self, "FFmpeg Test", "❌ FFmpeg not found or not working properly.")


def show_ffmpeg_setup_if_needed(parent=None):
    """Show FFmpeg setup dialog if FFmpeg is not available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True  # FFmpeg is available
    except:
        pass
        
    # FFmpeg not available, show setup dialog
    dialog = FFmpegInstallDialog(parent)
    dialog.exec()
    return False
