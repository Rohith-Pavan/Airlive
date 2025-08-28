#!/usr/bin/env python3
"""
Test frame capture functionality
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtGui import QRectF

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from graphics_output_widget import GraphicsOutputManager

class FrameCaptureTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame Capture Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create graphics output
        self.graphics_manager = GraphicsOutputManager()
        self.graphics_widget = self.graphics_manager.create_output_widget("test_output")
        layout.addWidget(self.graphics_widget)
        
        # Create test content
        self.create_test_content()
        
        # Create controls
        self.create_controls(layout)
        
        # Status label
        self.status_label = QLabel("Ready - Click 'Test Capture' to test frame capture")
        layout.addWidget(self.status_label)
        
    def create_test_content(self):
        """Create test content in the graphics scene"""
        from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
        from PyQt6.QtGui import QBrush, QFont
        
        scene = self.graphics_widget.scene()
        if scene:
            # Create a colored rectangle
            rect_item = QGraphicsRectItem(50, 50, 200, 150)
            rect_item.setBrush(QBrush(QColor(255, 0, 0)))  # Red
            rect_item.setZValue(1)
            scene.addItem(rect_item)
            
            # Create another rectangle
            rect_item2 = QGraphicsRectItem(300, 100, 150, 100)
            rect_item2.setBrush(QBrush(QColor(0, 255, 0)))  # Green
            rect_item2.setZValue(1)
            scene.addItem(rect_item2)
            
            # Add text
            text_item = QGraphicsTextItem("Test Content")
            text_item.setFont(QFont("Arial", 20))
            text_item.setDefaultTextColor(QColor(255, 255, 255))
            text_item.setPos(100, 250)
            text_item.setZValue(2)
            scene.addItem(text_item)
            
            print("Test content created")
    
    def create_controls(self, layout):
        """Create control buttons"""
        from PyQt6.QtWidgets import QHBoxLayout
        
        control_layout = QHBoxLayout()
        
        # Test capture button
        self.test_capture_btn = QPushButton("Test Capture")
        self.test_capture_btn.clicked.connect(self.test_capture)
        control_layout.addWidget(self.test_capture_btn)
        
        # Test RGB extraction button
        self.test_rgb_btn = QPushButton("Test RGB Extraction")
        self.test_rgb_btn.clicked.connect(self.test_rgb_extraction)
        control_layout.addWidget(self.test_rgb_btn)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
    
    def test_capture(self):
        """Test frame capture"""
        try:
            self.status_label.setText("Testing frame capture...")
            
            # Test capture at different resolutions
            resolutions = [(640, 480), (1280, 720), (1920, 1080)]
            
            for width, height in resolutions:
                print(f"\nTesting capture at {width}x{height}")
                
                # Capture frame
                pixmap = self.capture_frame(width, height)
                if not pixmap.isNull():
                    print(f"✓ Successfully captured {width}x{height} frame")
                    print(f"  Pixmap size: {pixmap.width()}x{pixmap.height()}")
                else:
                    print(f"✗ Failed to capture {width}x{height} frame")
            
            self.status_label.setText("Frame capture test completed")
            
        except Exception as e:
            self.status_label.setText(f"Capture error: {str(e)}")
            print(f"Capture error: {e}")
    
    def test_rgb_extraction(self):
        """Test RGB data extraction"""
        try:
            self.status_label.setText("Testing RGB extraction...")
            
            # Capture a frame
            pixmap = self.capture_frame(640, 480)
            if pixmap.isNull():
                self.status_label.setText("Failed to capture frame for RGB test")
                return
            
            # Convert to image
            image = pixmap.toImage()
            if image.isNull():
                self.status_label.setText("Failed to convert pixmap to image")
                return
            
            # Test RGB extraction
            from stream_manager import StreamCaptureThread
            
            # Create a dummy thread to access the extraction method
            dummy_thread = StreamCaptureThread(None, {})
            
            # Test extraction
            rgb_data = dummy_thread.extract_rgb_data(image, 640, 480)
            if rgb_data:
                expected_size = 640 * 480 * 3
                print(f"✓ RGB extraction successful")
                print(f"  Expected size: {expected_size} bytes")
                print(f"  Actual size: {len(rgb_data)} bytes")
                print(f"  Size match: {len(rgb_data) == expected_size}")
            else:
                print("✗ RGB extraction failed")
            
            self.status_label.setText("RGB extraction test completed")
            
        except Exception as e:
            self.status_label.setText(f"RGB extraction error: {str(e)}")
            print(f"RGB extraction error: {e}")
    
    def capture_frame(self, width, height):
        """Capture frame from graphics view"""
        try:
            # Create a pixmap of the target size
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.black)
            
            # Create a painter to draw the scene
            painter = QPainter(pixmap)
            
            # Get the scene from the graphics view
            scene = self.graphics_widget.scene()
            if not scene:
                print("No scene available for capture")
                painter.end()
                return QPixmap()
            
            # Get scene rect
            scene_rect = scene.sceneRect()
            if scene_rect.isEmpty():
                # Use view size if scene rect is empty
                scene_rect = QRectF(0, 0, self.graphics_widget.width(), self.graphics_widget.height())
            
            if scene_rect.isEmpty():
                print("Scene rect is empty")
                painter.end()
                return QPixmap()
            
            # Render the scene to the pixmap
            scene.render(painter, QRectF(0, 0, width, height), scene_rect)
            painter.end()
            
            return pixmap
            
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return QPixmap()

def main():
    app = QApplication(sys.argv)
    window = FrameCaptureTestWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
