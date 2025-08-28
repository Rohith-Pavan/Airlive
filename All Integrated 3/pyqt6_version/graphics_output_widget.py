#!/usr/bin/env python3
"""
Graphics Output Widget for GoLive Studio
Uses QGraphicsScene + QGraphicsView for compositing video and PNG effects
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QWidget, QVBoxLayout, QGraphicsPixmapItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QCamera, QMediaCaptureSession
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem

# Global cache for PNG analysis results
_png_analysis_cache = {}

def analyze_transparent_area_fast(pixmap, file_path=None):
    """Fast analysis of transparent area with caching"""
    # Use file path as cache key if available
    cache_key = file_path if file_path else id(pixmap)
    
    # Check cache first
    if cache_key in _png_analysis_cache:
        return _png_analysis_cache[cache_key]
    
    if pixmap.isNull():
        return None
    
    # Convert to QImage to access pixel data
    image = pixmap.toImage()
    if image.isNull():
        return None
    
    width = image.width()
    height = image.height()
    
    # Find bounds of transparent area using much faster sampling
    min_x, min_y = width, height
    max_x, max_y = 0, 0
    
    transparent_count = 0
    
    # Use adaptive sampling - sample every nth pixel based on image size
    step = max(2, min(width, height) // 50)  # Much faster sampling
    
    for y in range(0, height, step):
        for x in range(0, width, step):
            pixel = image.pixel(x, y)
            alpha = (pixel >> 24) & 0xFF  # Extract alpha channel
            
            # If pixel is transparent or semi-transparent
            if alpha < 128:
                transparent_count += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    
    if transparent_count == 0:
        result = None
    else:
        # Calculate bounding rectangle
        bounds = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        
        # Quick circular detection using aspect ratio only (much faster)
        width_ratio = bounds.width() / bounds.height() if bounds.height() > 0 else 1
        is_circular = 0.8 <= width_ratio <= 1.2  # Roughly square bounds suggest circular
        
        result = {
            'bounds': bounds,
            'center': ((min_x + max_x) / 2, (min_y + max_y) / 2),
            'is_circular': is_circular,
            'radius': min(bounds.width(), bounds.height()) / 2 if is_circular else None
        }
    
    # Cache the result
    _png_analysis_cache[cache_key] = result
    return result

# Keep the old function name for compatibility
def analyze_transparent_area(pixmap, file_path=None):
    """Wrapper for the fast analysis function"""
    return analyze_transparent_area_fast(pixmap, file_path)

def preanalyze_effects_folder(effects_folder_path):
    """Pre-analyze all PNG files in the effects folder for faster loading"""
    if not os.path.exists(effects_folder_path):
        return
    
    print("Pre-analyzing PNG effects for faster loading...")
    analyzed_count = 0
    
    # Walk through all subfolders
    for root, dirs, files in os.walk(effects_folder_path):
        for file in files:
            if file.lower().endswith('.png'):
                file_path = os.path.join(root, file)
                try:
                    # Load and analyze the PNG
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        analyze_transparent_area_fast(pixmap, file_path)
                        analyzed_count += 1
                except Exception as e:
                    print(f"Error pre-analyzing {file_path}: {e}")
    
    print(f"Pre-analyzed {analyzed_count} PNG effects")

class MaskedVideoItem(QGraphicsVideoItem):
    """Custom video item that can be masked by a PNG's alpha channel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mask_shape = None
        # Optional frame to draw when provided by external pipelines (e.g., GStreamer)
        self._current_qimage = None
        
    def set_mask_shape(self, shape_info):
        """Set the mask shape information"""
        self.mask_shape = shape_info
        self.update()
    
    def clear_mask(self):
        """Clear the mask"""
        self.mask_shape = None
        self.update()
    
    def set_qimage_frame(self, qimage):
        """Provide a QImage to be drawn by this item.
        When set, paint() will render this image instead of the internal video.
        Pass None to clear and resume normal video rendering.
        """
        self._current_qimage = qimage
        self.update()
    
    def paint(self, painter, option, widget=None):
        """Custom paint method to apply masking"""
        # Reduce unnecessary repaints
        if option.exposedRect.isEmpty():
            return
            
        # Determine target rect
        video_rect = self.boundingRect()
        
        # Set render hints for smoother rendering
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # If we have an externally provided frame, draw it
        if self._current_qimage is not None and not self._current_qimage.isNull():
            if self.mask_shape and self.mask_shape.get('is_circular'):
                painter.save()
                from PyQt6.QtGui import QRegion
                region = QRegion(video_rect.toRect(), QRegion.RegionType.Ellipse)
                painter.setClipRegion(region)
                painter.drawImage(video_rect, self._current_qimage)
                painter.restore()
            else:
                painter.drawImage(video_rect, self._current_qimage)
        else:
            # Fall back to default video rendering path
            if self.mask_shape and self.mask_shape.get('is_circular'):
                painter.save()
                from PyQt6.QtGui import QRegion
                region = QRegion(video_rect.toRect(), QRegion.RegionType.Ellipse)
                painter.setClipRegion(region)
                super().paint(painter, option, widget)
                painter.restore()
            else:
                super().paint(painter, option, widget)

class GraphicsOutputWidget(QGraphicsView):
    """Graphics view widget for compositing video and PNG overlays"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Ensure this view expands to fill its parent layout/container
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Create graphics scene (avoid shadowing QGraphicsView.scene())
        self.scene_obj = QGraphicsScene()
        self.setScene(self.scene_obj)
        
        # Video and overlay items
        self.video_item = None
        self.overlay_item = None
        self.current_frame_path = None
        
        # Setup the view
        self.setup_view()
        
        # Create video item
        self.create_video_item()
        
    def setup_view(self):
        """Configure the graphics view"""
        # Set background color
        self.setStyleSheet("background-color: black;")
        
        # Configure view properties
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Reduce update frequency to prevent blinking
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        
        # Fit scene in view
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        
    def create_video_item(self):
        """Create the video graphics item"""
        self.video_item = MaskedVideoItem()
        self.video_item.setZValue(0)  # Video layer at bottom
        self.scene_obj.addItem(self.video_item)
        
    def get_video_item(self):
        """Get the video graphics item for media connections"""
        return self.video_item
    
    def set_frame_overlay(self, frame_path):
        """Set PNG frame overlay"""
        try:
            if frame_path and os.path.exists(frame_path):
                self.current_frame_path = frame_path
                pixmap = QPixmap(frame_path)
                
                if not pixmap.isNull():
                    # Remove existing overlay if any
                    if self.overlay_item:
                        try:
                            self.scene_obj.removeItem(self.overlay_item)
                            self.overlay_item = None
                        except Exception as e:
                            print(f"Error removing existing overlay: {e}")
                    
                    # Create new overlay item
                    self.overlay_item = QGraphicsPixmapItem(pixmap)
                    self.overlay_item.setZValue(10)  # Overlay layer on top
                    
                    # Scale overlay to fit the scene
                    self.scale_overlay_to_scene()
                    
                    # Analyze and position video in the transparent area of the PNG (with caching)
                    self.setup_video_masking(pixmap, frame_path)
                    
                    # Add to scene
                    self.scene_obj.addItem(self.overlay_item)
                    
                    print(f"Frame overlay applied: {Path(frame_path).name}")
                else:
                    print(f"Failed to load frame: {frame_path}")
            else:
                self.clear_frame_overlay()
        except Exception as e:
            print(f"Error setting frame overlay: {e}")
            self.clear_frame_overlay()
    
    def clear_frame_overlay(self):
        """Clear the frame overlay"""
        try:
            if self.overlay_item:
                try:
                    self.scene_obj.removeItem(self.overlay_item)
                except Exception as e:
                    print(f"Error removing overlay item: {e}")
                finally:
                    self.overlay_item = None
            
            # Reset video to full scene size and clear mask
            if self.video_item:
                try:
                    scene_rect = self.scene_obj.sceneRect()
                    if not scene_rect.isEmpty():
                        self.video_item.setSize(scene_rect.size())
                        self.video_item.setPos(scene_rect.topLeft())
                    self.video_item.clear_mask()
                except Exception as e:
                    print(f"Error resetting video item: {e}")
            
            self.current_frame_path = None
            print("Frame overlay cleared")
        except Exception as e:
            print(f"Error clearing frame overlay: {e}")
    
    def scale_overlay_to_scene(self):
        """Scale the overlay to fit the scene size"""
        if not self.overlay_item:
            return
            
        # Get scene rect
        scene_rect = self.scene_obj.sceneRect()
        if scene_rect.isEmpty():
            # Use view size if scene rect is empty
            scene_rect = QRectF(0, 0, self.width(), self.height())
        
        # Get pixmap size
        pixmap = self.overlay_item.pixmap()
        pixmap_rect = pixmap.rect()
        
        # Calculate scale to fit scene
        scale_x = scene_rect.width() / pixmap_rect.width()
        scale_y = scene_rect.height() / pixmap_rect.height()
        
        # Use the smaller scale to maintain aspect ratio, or stretch to fill
        # For frame effects, we typically want to stretch to fill completely
        self.overlay_item.setScale(1.0)  # Reset scale first
        self.overlay_item.setTransform(
            self.overlay_item.transform().scale(scale_x, scale_y)
        )
        
        # Position at scene center
        self.overlay_item.setPos(scene_rect.topLeft())
    
    def setup_video_masking(self, frame_pixmap, file_path=None):
        """Setup video masking based on the transparent area of the frame"""
        try:
            if not self.video_item or not frame_pixmap:
                print("Error: Invalid video item or frame pixmap")
                return
            
            # Analyze the transparent area in the PNG (with caching)
            shape_info = analyze_transparent_area(frame_pixmap, file_path)
            if not shape_info:
                print("No transparent area found in PNG")
                return
            
            # Get scene dimensions
            scene_rect = self.scene_obj.sceneRect()
            if scene_rect.isEmpty():
                scene_rect = QRectF(0, 0, self.width(), self.height())
            
            if scene_rect.width() <= 0 or scene_rect.height() <= 0:
                print("Error: Invalid scene dimensions")
                return
            
            # Calculate the scale factors from PNG to scene
            png_rect = frame_pixmap.rect()
            scale_x = scene_rect.width() / png_rect.width()
            scale_y = scene_rect.height() / png_rect.height()
            
            # Scale the transparent area bounds to scene coordinates
            bounds = shape_info['bounds']
            scaled_bounds = QRectF(
                bounds.x() * scale_x,
                bounds.y() * scale_y,
                bounds.width() * scale_x,
                bounds.height() * scale_y
            )
            
            # Position video to fit the transparent area
            # QGraphicsVideoItem will maintain aspect ratio, which may cause small black borders
            # but this ensures the video doesn't overflow outside the frame
            
            if shape_info['is_circular']:
                # For circular areas, use the smaller dimension to ensure video fits within circle
                size = min(scaled_bounds.width(), scaled_bounds.height())
                
                # Center the video area within the circular bounds
                center_x = scaled_bounds.center().x()
                center_y = scaled_bounds.center().y()
                
                video_rect = QRectF(
                    center_x - size/2,
                    center_y - size/2,
                    size,
                    size
                )
                
                self.video_item.setPos(video_rect.topLeft())
                self.video_item.setSize(video_rect.size())
                
                # Set the circular mask
                self.video_item.set_mask_shape(shape_info)
                
                print(f"Video positioned in circular area: {video_rect}")
            else:
                # For rectangular areas, fit video with aspect ratio preserved
                video_aspect = 16.0 / 9.0  # Assume 16:9 for most cameras/videos
                bounds_aspect = scaled_bounds.width() / scaled_bounds.height()
                
                if bounds_aspect > video_aspect:
                    # Bounds are wider than video - fit by height
                    video_height = scaled_bounds.height()
                    video_width = video_height * video_aspect
                    x_offset = (scaled_bounds.width() - video_width) / 2
                    video_rect = QRectF(
                        scaled_bounds.x() + x_offset,
                        scaled_bounds.y(),
                        video_width,
                        video_height
                    )
                else:
                    # Bounds are taller than video - fit by width
                    video_width = scaled_bounds.width()
                    video_height = video_width / video_aspect
                    y_offset = (scaled_bounds.height() - video_height) / 2
                    video_rect = QRectF(
                        scaled_bounds.x(),
                        scaled_bounds.y() + y_offset,
                        video_width,
                        video_height
                    )
                
                self.video_item.setPos(video_rect.topLeft())
                self.video_item.setSize(video_rect.size())
                
                print(f"Video positioned in rectangular area: {video_rect}")
                
        except Exception as e:
            print(f"Error setting up video masking: {e}")
    
    def resizeEvent(self, event):
        """Handle resize events"""
        try:
            super().resizeEvent(event)
            
            # Validate dimensions
            if self.width() <= 0 or self.height() <= 0:
                return
            
            # Only update if size actually changed significantly
            new_size = event.size()
            old_size = event.oldSize()
            if old_size.isValid():
                size_diff = abs(new_size.width() - old_size.width()) + abs(new_size.height() - old_size.height())
                if size_diff < 5:  # Ignore minor size changes
                    return
            
            # Update scene rect to match view size
            self.scene_obj.setSceneRect(0, 0, self.width(), self.height())
            
            # Update video item size only if no overlay is present
            if self.video_item and not self.overlay_item:
                try:
                    self.video_item.setSize(self.scene_obj.sceneRect().size())
                except Exception as e:
                    print(f"Error updating video item size: {e}")
            
            # Rescale overlay if present and reposition video
            if self.overlay_item:
                try:
                    self.scale_overlay_to_scene()
                    # Reapply video masking with current frame
                    if self.current_frame_path:
                        pixmap = QPixmap(self.current_frame_path)
                        if not pixmap.isNull():
                            self.setup_video_masking(pixmap, self.current_frame_path)
                except Exception as e:
                    print(f"Error rescaling overlay: {e}")
            
            # Fit scene in view
            try:
                self.fitInView(self.scene_obj.sceneRect(), Qt.AspectRatioMode.IgnoreAspectRatio)
            except Exception as e:
                print(f"Error fitting scene in view: {e}")
        except Exception as e:
            print(f"Error in resize event: {e}")
    
    def has_frame(self):
        """Check if a frame overlay is currently active"""
        return self.current_frame_path is not None
    
    def get_current_frame(self):
        """Get the current frame path"""
        return self.current_frame_path

class GraphicsOutputManager(QObject):
    """Manager for handling graphics output widgets"""
    
    frame_applied = pyqtSignal(str)  # Emitted when frame is applied
    frame_cleared = pyqtSignal()     # Emitted when frame is cleared
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.output_widgets = {}  # Dictionary to store output widgets
        
    def create_output_widget(self, name, parent=None):
        """Create a new graphics output widget"""
        widget = GraphicsOutputWidget(parent)
        self.output_widgets[name] = widget
        return widget
    
    def get_output_widget(self, name):
        """Get output widget by name"""
        return self.output_widgets.get(name)
    
    def get_video_item_for_output(self, widget_name):
        """Get the video graphics item from an output widget for media connections"""
        widget = self.get_output_widget(widget_name)
        if widget:
            return widget.get_video_item()
        return None
    
    def set_frame_for_widget(self, widget_name, frame_path):
        """Set frame for a specific output widget"""
        widget = self.get_output_widget(widget_name)
        if widget:
            widget.set_frame_overlay(frame_path)
            if frame_path:
                self.frame_applied.emit(frame_path)
            else:
                self.frame_cleared.emit()
    
    def clear_frame_for_widget(self, widget_name):
        """Clear frame for a specific output widget"""
        widget = self.get_output_widget(widget_name)
        if widget:
            widget.clear_frame_overlay()
            self.frame_cleared.emit()
    
    def clear_all_frames(self):
        """Clear frames from all output widgets"""
        for widget in self.output_widgets.values():
            widget.clear_frame_overlay()
        self.frame_cleared.emit()
    
    def get_active_frames(self):
        """Get list of active frames across all widgets"""
        active = {}
        for name, widget in self.output_widgets.items():
            if widget and widget.has_frame():
                active[name] = widget.get_current_frame()
        return active
