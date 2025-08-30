#!/usr/bin/env python3
"""
Display Manager for GoLive Studio
Handles detection and management of multiple displays for HDMI output
"""

from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QRect, Qt
from typing import List, Dict, Optional, Tuple
import sys


class DisplayInfo:
    """Information about a display"""
    
    def __init__(self, screen: QScreen, index: int):
        self.screen = screen
        self.index = index
        self.name = screen.name()
        self.geometry = screen.geometry()
        self.available_geometry = screen.availableGeometry()
        self.device_pixel_ratio = screen.devicePixelRatio()
        self.is_primary = screen == QApplication.primaryScreen()
        
    def __str__(self):
        return f"Display {self.index + 1}: {self.name} ({self.geometry.width()}x{self.geometry.height()})"
    
    @property
    def resolution_string(self):
        """Get resolution as string"""
        return f"{self.geometry.width()}x{self.geometry.height()}"
    
    @property
    def display_name(self):
        """Get friendly display name"""
        primary_text = " (Primary)" if self.is_primary else ""
        return f"Display {self.index + 1}: {self.name} - {self.resolution_string}{primary_text}"


class HDMIDisplayWindow(QWidget):
    """Fullscreen window for HDMI display output"""
    
    def __init__(self, display_info: DisplayInfo, parent=None):
        super().__init__(parent)
        self.display_info = display_info
        self.video_widget = None
        self.setup_window()
        
    def setup_window(self):
        """Setup the display window"""
        # Set window properties for fullscreen display
        self.setWindowTitle("GoLive Studio - HDMI Output")
        self.setStyleSheet("background-color: black;")
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add placeholder label (will be replaced with video widget)
        self.placeholder_label = QLabel("HDMI Display Ready")
        self.placeholder_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                text-align: center;
            }
        """)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder_label)
        
    def set_video_widget(self, video_widget):
        """Set the video widget for display"""
        if self.video_widget:
            self.layout().removeWidget(self.video_widget)
            
        if self.placeholder_label:
            self.layout().removeWidget(self.placeholder_label)
            self.placeholder_label.hide()
            
        self.video_widget = video_widget
        if video_widget:
            self.layout().addWidget(video_widget)
            
    def show_fullscreen_on_display(self):
        """Show window fullscreen on the target display"""
        # Move window to target display
        self.setGeometry(self.display_info.geometry)
        
        # Show fullscreen
        self.showFullScreen()
        
        # Ensure window is on correct screen
        self.move(self.display_info.geometry.topLeft())
        
    def show_windowed_on_display(self, width: int = 800, height: int = 600):
        """Show window in windowed mode on target display"""
        # Calculate center position on target display
        display_rect = self.display_info.available_geometry
        x = display_rect.x() + (display_rect.width() - width) // 2
        y = display_rect.y() + (display_rect.height() - height) // 2
        
        self.setGeometry(x, y, width, height)
        self.show()


class DisplayManager(QObject):
    """Manager for handling multiple displays"""
    
    displays_changed = pyqtSignal()  # Emitted when display configuration changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.displays: List[DisplayInfo] = []
        self.hdmi_windows: Dict[int, HDMIDisplayWindow] = {}
        
        # Monitor for display changes
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._check_display_changes)
        self.monitor_timer.start(1000)  # Check every 1 second for faster detection
        
        # Also connect to Qt's screen change signals for immediate detection
        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screen_added)
            app.screenRemoved.connect(self._on_screen_removed)
        
        # Initial scan
        self.scan_displays()
        
    def scan_displays(self):
        """Scan for available displays"""
        app = QApplication.instance()
        if not app:
            return
            
        screens = app.screens()
        new_displays = []
        
        for i, screen in enumerate(screens):
            display_info = DisplayInfo(screen, i)
            new_displays.append(display_info)
            
        # Check if displays changed
        if len(new_displays) != len(self.displays) or self._displays_different(new_displays):
            self.displays = new_displays
            self.displays_changed.emit()
            print(f"Display configuration changed: {len(self.displays)} displays detected")
            
    def _displays_different(self, new_displays: List[DisplayInfo]) -> bool:
        """Check if display configuration is different"""
        if len(new_displays) != len(self.displays):
            return True
            
        for new_display, old_display in zip(new_displays, self.displays):
            if (new_display.name != old_display.name or 
                new_display.geometry != old_display.geometry):
                return True
                
        return False
        
    def _check_display_changes(self):
        """Check for display configuration changes"""
        old_count = len(self.displays)
        self.scan_displays()
        new_count = len(self.displays)
        
        if new_count != old_count:
            print(f"Display count changed: {old_count} -> {new_count}")
            for i, display in enumerate(self.displays):
                print(f"  Display {i}: {display.display_name}")
        
    def get_displays(self) -> List[DisplayInfo]:
        """Get list of available displays"""
        return self.displays.copy()
        
    def get_external_displays(self) -> List[DisplayInfo]:
        """Get list of external (non-primary) displays"""
        return [display for display in self.displays if not display.is_primary]
        
    def get_display_by_index(self, index: int) -> Optional[DisplayInfo]:
        """Get display by index"""
        if 0 <= index < len(self.displays):
            return self.displays[index]
        return None
        
    def create_hdmi_window(self, display_index: int) -> Optional[HDMIDisplayWindow]:
        """Create HDMI display window for specified display"""
        display_info = self.get_display_by_index(display_index)
        if not display_info:
            return None
            
        # Close existing window for this display
        if display_index in self.hdmi_windows:
            self.hdmi_windows[display_index].close()
            
        # Create new window
        window = HDMIDisplayWindow(display_info)
        self.hdmi_windows[display_index] = window
        
        return window
        
    def close_hdmi_window(self, display_index: int):
        """Close HDMI window for specified display"""
        if display_index in self.hdmi_windows:
            self.hdmi_windows[display_index].close()
            del self.hdmi_windows[display_index]
            
    def close_all_hdmi_windows(self):
        """Close all HDMI windows"""
        for window in self.hdmi_windows.values():
            window.close()
        self.hdmi_windows.clear()
        
    def get_display_options_for_combo(self) -> List[Tuple[str, int]]:
        """Get display options formatted for combo box"""
        options = []
        for display in self.displays:
            # Show all displays, but mark non-primary ones as preferred for HDMI
            display_name = display.display_name
            if not display.is_primary and len(self.displays) > 1:
                display_name += " (Recommended for HDMI)"
            options.append((display_name, display.index))
        return options
        
    def has_external_displays(self) -> bool:
        """Check if there are external displays available"""
        return len(self.get_external_displays()) > 0
    
    def _on_screen_added(self, screen):
        """Handle Qt screen added signal"""
        print(f"Qt detected screen added: {screen.name()}")
        self.scan_displays()
        
    def _on_screen_removed(self, screen):
        """Handle Qt screen removed signal"""
        print(f"Qt detected screen removed: {screen.name()}")
        self.scan_displays()
        
    def force_refresh(self):
        """Force a display refresh"""
        print("Forcing display refresh...")
        self.scan_displays()


# Global display manager instance
_display_manager = None

def get_display_manager() -> DisplayManager:
    """Get global display manager instance"""
    global _display_manager
    if _display_manager is None:
        _display_manager = DisplayManager()
    return _display_manager


if __name__ == "__main__":
    """Test display detection"""
    app = QApplication(sys.argv)
    
    manager = DisplayManager()
    
    print("Available displays:")
    for display in manager.get_displays():
        print(f"  {display}")
        
    print(f"\nExternal displays: {len(manager.get_external_displays())}")
    print(f"Has external displays: {manager.has_external_displays()}")
    
    # Test HDMI window creation
    if manager.has_external_displays():
        external = manager.get_external_displays()[0]
        print(f"\nCreating test window on {external}")
        
        window = manager.create_hdmi_window(external.index)
        if window:
            window.show_windowed_on_display()
            
    app.exec()