#!/usr/bin/env python3
"""
Comprehensive test suite for the new streaming system
Tests all components and edge cases to ensure robust functionality
"""

import sys
import time
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from new_stream_manager import NewStreamManager, StreamCaptureWorker, StreamState
from ffmpeg_locator import find_ffmpeg, ensure_ffmpeg_available


class MockGraphicsView:
    """Mock graphics view for testing"""
    
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        self._scene = MockScene()
    
    def scene(self):
        return self._scene
    
    def grab(self):
        """Return a test pixmap"""
        pixmap = QPixmap(self.width, self.height)
        pixmap.fill(Qt.GlobalColor.blue)
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(50, 50, "Test Graphics View")
        painter.end()
        
        return pixmap
    
    def size(self):
        from PyQt6.QtCore import QSize
        return QSize(self.width, self.height)


class MockScene:
    """Mock graphics scene for testing"""
    
    def sceneRect(self):
        from PyQt6.QtCore import QRectF
        return QRectF(0, 0, 1920, 1080)
    
    def render(self, painter):
        """Render test content"""
        painter.fillRect(0, 0, 1920, 1080, Qt.GlobalColor.green)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(100, 100, "Mock Scene Content")


class StreamingTestSuite:
    """Comprehensive streaming test suite"""
    
    def __init__(self):
        self.app = None
        self.stream_manager = None
        self.test_results = []
        self.failed_tests = []
    
    def setup(self):
        """Setup test environment"""
        print("Setting up test environment...")
        
        # Create QApplication if needed
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        
        # Create stream manager
        self.stream_manager = NewStreamManager()
        
        # Register mock graphics view
        mock_view = MockGraphicsView()
        self.stream_manager.register_graphics_view("TestStream", mock_view)
        
        print("✅ Test environment setup complete")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n🚀 Starting comprehensive streaming tests...\n")
        
        self.setup()
        
        # Test categories
        test_categories = [
            ("FFmpeg Tests", self._test_ffmpeg),
            ("Settings Validation Tests", self._test_settings_validation),
            ("Stream Manager Tests", self._test_stream_manager),
            ("Worker Thread Tests", self._test_worker_thread),
            ("Frame Capture Tests", self._test_frame_capture),
            ("Error Handling Tests", self._test_error_handling),
            ("Resource Cleanup Tests", self._test_resource_cleanup)
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n📋 {category_name}")
            print("-" * 50)
            try:
                test_function()
            except Exception as e:
                self._log_test("CATEGORY_ERROR", False, f"Category {category_name} failed: {e}")
        
        self._print_summary()
    
    def _test_ffmpeg(self):
        """Test FFmpeg functionality"""
        # Test 1: FFmpeg detection
        ffmpeg_path = find_ffmpeg()
        self._log_test("FFmpeg Detection", ffmpeg_path is not None, 
                      f"FFmpeg found at: {ffmpeg_path}" if ffmpeg_path else "FFmpeg not found")
        
        # Test 2: FFmpeg download if needed
        if not ffmpeg_path:
            print("  Attempting FFmpeg download...")
            ffmpeg_path = ensure_ffmpeg_available(auto_download=True)
            self._log_test("FFmpeg Download", ffmpeg_path is not None,
                          f"FFmpeg downloaded to: {ffmpeg_path}" if ffmpeg_path else "Download failed")
        
        # Test 3: FFmpeg version check
        if ffmpeg_path:
            import subprocess
            try:
                result = subprocess.run([ffmpeg_path, '-version'], 
                                      capture_output=True, timeout=10,
                                      creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                version_ok = result.returncode == 0
                self._log_test("FFmpeg Version Check", version_ok, 
                              "Version check passed" if version_ok else "Version check failed")
            except Exception as e:
                self._log_test("FFmpeg Version Check", False, f"Version check error: {e}")
    
    def _test_settings_validation(self):
        """Test settings validation"""
        # Test 1: Valid settings
        valid_settings = {
            "url": "rtmp://live.twitch.tv/live/",
            "key": "test_key_123",
            "resolution": "1920x1080",
            "fps": 30,
            "video_bitrate": 2500,
            "audio_bitrate": 128
        }
        
        success = self.stream_manager.configure_stream("TestStream", valid_settings)
        self._log_test("Valid Settings", success, "Valid settings accepted")
        
        # Test 2: Missing URL
        invalid_settings = valid_settings.copy()
        del invalid_settings["url"]
        success = self.stream_manager.configure_stream("TestStream2", invalid_settings)
        self._log_test("Missing URL Validation", not success, "Missing URL properly rejected")
        
        # Test 3: Invalid resolution
        invalid_settings = valid_settings.copy()
        invalid_settings["resolution"] = "invalid_resolution"
        success = self.stream_manager.configure_stream("TestStream3", invalid_settings)
        self._log_test("Invalid Resolution Validation", not success, "Invalid resolution properly rejected")
        
        # Test 4: Invalid FPS
        invalid_settings = valid_settings.copy()
        invalid_settings["fps"] = -1
        success = self.stream_manager.configure_stream("TestStream4", invalid_settings)
        self._log_test("Invalid FPS Validation", not success, "Invalid FPS properly rejected")
        
        # Test 5: Invalid bitrate
        invalid_settings = valid_settings.copy()
        invalid_settings["video_bitrate"] = 0
        success = self.stream_manager.configure_stream("TestStream5", invalid_settings)
        self._log_test("Invalid Bitrate Validation", not success, "Invalid bitrate properly rejected")
    
    def _test_stream_manager(self):
        """Test stream manager functionality"""
        # Test 1: Stream registration
        mock_view = MockGraphicsView()
        self.stream_manager.register_graphics_view("ManagerTest", mock_view)
        registered = "ManagerTest" in self.stream_manager._graphics_views
        self._log_test("Stream Registration", registered, "Stream registered successfully")
        
        # Test 2: Stream state tracking
        initial_state = self.stream_manager.get_stream_state("ManagerTest")
        self._log_test("Initial State", initial_state == StreamState.STOPPED, 
                      f"Initial state: {initial_state}")
        
        # Test 3: Stream configuration
        test_settings = {
            "url": "rtmp://test.example.com/live/",
            "key": "test_key",
            "resolution": "1280x720",
            "fps": 30,
            "video_bitrate": 1500,
            "audio_bitrate": 128
        }
        
        configured = self.stream_manager.configure_stream("ManagerTest", test_settings)
        self._log_test("Stream Configuration", configured, "Stream configured successfully")
        
        # Test 4: Multiple stream handling
        self.stream_manager.register_graphics_view("ManagerTest2", MockGraphicsView())
        configured2 = self.stream_manager.configure_stream("ManagerTest2", test_settings)
        self._log_test("Multiple Streams", configured2, "Multiple streams supported")
    
    def _test_worker_thread(self):
        """Test worker thread functionality"""
        # Test 1: Worker creation
        test_settings = {
            "url": "rtmp://test.example.com/live/",
            "key": "test_key",
            "resolution": "640x480",
            "fps": 30,
            "video_bitrate": 1000,
            "audio_bitrate": 128
        }
        
        mock_view = MockGraphicsView(640, 480)
        
        try:
            worker = StreamCaptureWorker("WorkerTest", mock_view, test_settings)
            self._log_test("Worker Creation", True, "Worker created successfully")
        except Exception as e:
            self._log_test("Worker Creation", False, f"Worker creation failed: {e}")
            return
        
        # Test 2: Settings validation in worker
        try:
            worker._validate_settings()
            self._log_test("Worker Settings Validation", True, "Settings validation passed")
        except Exception as e:
            self._log_test("Worker Settings Validation", False, f"Validation failed: {e}")
        
        # Test 3: Frame capture method
        try:
            pixmap = worker._capture_graphics_view(640, 480)
            capture_ok = not pixmap.isNull()
            self._log_test("Frame Capture", capture_ok, 
                          "Frame captured successfully" if capture_ok else "Frame capture failed")
        except Exception as e:
            self._log_test("Frame Capture", False, f"Frame capture error: {e}")
        
        # Test 4: RGB conversion
        if 'pixmap' in locals() and not pixmap.isNull():
            try:
                rgb_data = worker._pixmap_to_rgb(pixmap, 640, 480)
                conversion_ok = rgb_data is not None and len(rgb_data) == 640 * 480 * 3
                self._log_test("RGB Conversion", conversion_ok,
                              f"RGB data: {len(rgb_data) if rgb_data else 0} bytes")
            except Exception as e:
                self._log_test("RGB Conversion", False, f"RGB conversion error: {e}")
    
    def _test_frame_capture(self):
        """Test frame capture functionality"""
        # Test 1: Different resolutions
        resolutions = ["640x480", "1280x720", "1920x1080"]
        
        for resolution in resolutions:
            width, height = map(int, resolution.split('x'))
            mock_view = MockGraphicsView(width, height)
            
            test_settings = {
                "url": "rtmp://test.example.com/live/",
                "key": "test_key",
                "resolution": resolution,
                "fps": 30,
                "video_bitrate": 2500,
                "audio_bitrate": 128
            }
            
            try:
                worker = StreamCaptureWorker("CaptureTest", mock_view, test_settings)
                pixmap = worker._capture_graphics_view(width, height)
                
                success = not pixmap.isNull() and pixmap.width() == width and pixmap.height() == height
                self._log_test(f"Capture {resolution}", success,
                              f"Captured {pixmap.width()}x{pixmap.height()}" if not pixmap.isNull() else "Capture failed")
            except Exception as e:
                self._log_test(f"Capture {resolution}", False, f"Error: {e}")
        
        # Test 2: Fallback frame creation
        try:
            worker = StreamCaptureWorker("FallbackTest", None, {
                "url": "rtmp://test.example.com/live/",
                "key": "test_key",
                "resolution": "1280x720",
                "fps": 30,
                "video_bitrate": 2500,
                "audio_bitrate": 128
            })
            
            fallback_pixmap = worker._create_fallback_frame(1280, 720)
            fallback_ok = not fallback_pixmap.isNull()
            self._log_test("Fallback Frame", fallback_ok, "Fallback frame created successfully")
        except Exception as e:
            self._log_test("Fallback Frame", False, f"Fallback error: {e}")
    
    def _test_error_handling(self):
        """Test error handling scenarios"""
        # Test 1: Invalid settings handling
        invalid_settings_list = [
            ({}, "Empty settings"),
            ({"url": ""}, "Empty URL"),
            ({"url": "invalid_url", "key": "test"}, "Invalid URL format"),
            ({"url": "rtmp://test.com/live/", "key": "test", "resolution": "0x0"}, "Zero resolution"),
            ({"url": "rtmp://test.com/live/", "key": "test", "resolution": "1920x1080", "fps": 0}, "Zero FPS"),
        ]
        
        for invalid_settings, description in invalid_settings_list:
            try:
                success = self.stream_manager.configure_stream("ErrorTest", invalid_settings)
                self._log_test(f"Error Handling: {description}", not success, 
                              "Invalid settings properly rejected")
            except Exception as e:
                self._log_test(f"Error Handling: {description}", True, f"Exception caught: {e}")
        
        # Test 2: Missing graphics view
        try:
            success = self.stream_manager.start_stream("NonExistentStream")
            self._log_test("Missing Graphics View", not success, "Missing view properly handled")
        except Exception as e:
            self._log_test("Missing Graphics View", True, f"Exception caught: {e}")
    
    def _test_resource_cleanup(self):
        """Test resource cleanup"""
        # Test 1: Stream manager cleanup
        try:
            # Create some test streams
            for i in range(3):
                stream_name = f"CleanupTest{i}"
                self.stream_manager.register_graphics_view(stream_name, MockGraphicsView())
                self.stream_manager.configure_stream(stream_name, {
                    "url": "rtmp://test.example.com/live/",
                    "key": "test_key",
                    "resolution": "640x480",
                    "fps": 30,
                    "video_bitrate": 1000,
                    "audio_bitrate": 128
                })
            
            # Test cleanup
            self.stream_manager.stop_all_streams()
            
            # Check if all streams are stopped
            all_stopped = all(
                self.stream_manager.get_stream_state(f"CleanupTest{i}") == StreamState.STOPPED
                for i in range(3)
            )
            
            self._log_test("Stream Manager Cleanup", all_stopped, "All streams stopped successfully")
            
        except Exception as e:
            self._log_test("Stream Manager Cleanup", False, f"Cleanup error: {e}")
        
        # Test 2: Worker thread cleanup
        try:
            mock_view = MockGraphicsView()
            test_settings = {
                "url": "rtmp://test.example.com/live/",
                "key": "test_key",
                "resolution": "640x480",
                "fps": 30,
                "video_bitrate": 1000,
                "audio_bitrate": 128
            }
            
            worker = StreamCaptureWorker("CleanupWorkerTest", mock_view, test_settings)
            
            # Test cleanup method
            worker._cleanup()
            self._log_test("Worker Cleanup", True, "Worker cleanup completed")
            
        except Exception as e:
            self._log_test("Worker Cleanup", False, f"Worker cleanup error: {e}")
    
    def _log_test(self, test_name, success, message):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"  {status} {test_name}: {message}"
        print(result)
        
        self.test_results.append((test_name, success, message))
        if not success:
            self.failed_tests.append(test_name)
    
    def _print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success, _ in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("🏁 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for test_name in self.failed_tests:
                print(f"  - {test_name}")
        else:
            print(f"\n🎉 All tests passed!")
        
        print("="*60)


def main():
    """Run the test suite"""
    test_suite = StreamingTestSuite()
    test_suite.run_all_tests()
    
    # Keep the application running briefly to ensure cleanup
    if test_suite.app:
        QTimer.singleShot(1000, test_suite.app.quit)
        test_suite.app.exec()


if __name__ == "__main__":
    main()
