import os
from PyQt6.QtWidgets import QDialog, QFileDialog, QLineEdit, QPushButton, QHBoxLayout, QWidget
from PyQt6.uic import loadUi
from PyQt6.QtCore import QSettings

class RecordingSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load the UI file
        ui_path = os.path.join(os.path.dirname(__file__), 'recording_settings_dialog.ui')
        loadUi(ui_path, self)

        # Connect signals to slots
        self.qualityPresetComboBox.currentTextChanged.connect(self.update_bitrate_visibility)
        self.browseFolderButton.clicked.connect(self.browse_folder)
        self.browseScreenshotFolderButton.clicked.connect(self.browse_screenshot_folder)
        self.screenshotLocationComboBox.currentTextChanged.connect(self._update_screenshot_location_visibility)

        # Initialize UI state
        self.update_bitrate_visibility(self.qualityPresetComboBox.currentText())
        self._update_screenshot_location_visibility(self.screenshotLocationComboBox.currentText())

    def update_bitrate_visibility(self, text):
        """Show or hide the bitrate field based on the quality preset."""
        is_custom = (text == "Custom")
        self.bitrateLabel.setVisible(is_custom)
        self.bitrateLineEdit.setVisible(is_custom)

    def _update_screenshot_location_visibility(self, text):
        # Always show and enable the Screenshot Folder row, regardless of selection
        self.screenshotFolderLabel.setVisible(True)
        self.screenshotFolderLineEdit.setVisible(True)
        self.browseScreenshotFolderButton.setVisible(True)
        self.screenshotFolderLineEdit.setEnabled(True)

    def browse_screenshot_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Screenshot Folder", self.screenshotFolderLineEdit.text())
        if folder:
            self.screenshotFolderLineEdit.setText(folder)

    def browse_folder(self):
        """Open a dialog to select a destination folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.destinationFolderLineEdit.text())
        if folder:
            self.destinationFolderLineEdit.setText(folder)

    def get_settings(self):
        """Return a dictionary of the current settings."""
        return {
            'destination_folder': self.destinationFolderLineEdit.text(),
            'file_name_pattern': self.fileNamePatternLineEdit.text(),
            'video_format': self.videoFormatComboBox.currentText(),
            'quality_preset': self.qualityPresetComboBox.currentText(),
            'bitrate': self.bitrateLineEdit.text() if self.qualityPresetComboBox.currentText() == "Custom" else None,
            'resolution': self.resolutionComboBox.currentText(),
            'frame_rate': self.frameRateComboBox.currentText(),
            'screenshot_format': self.screenshotFormatComboBox.currentText(),
            'screenshot_location': self.screenshotLocationComboBox.currentText(),
            'custom_screenshot_path': self.screenshotFolderLineEdit.text(),
        }

    def set_settings(self, settings):
        """Set the dialog's widgets based on a settings dictionary."""
        self.destinationFolderLineEdit.setText(settings.get('destination_folder', ''))
        self.fileNamePatternLineEdit.setText(settings.get('file_name_pattern', 'Recording_{date}_{time}'))
        self.videoFormatComboBox.setCurrentText(settings.get('video_format', 'MP4'))
        self.qualityPresetComboBox.setCurrentText(settings.get('quality_preset', 'Medium'))
        if settings.get('quality_preset') == "Custom":
            self.bitrateLineEdit.setText(settings.get('bitrate', '4000'))
        self.resolutionComboBox.setCurrentText(settings.get('resolution', '1080p'))
        self.frameRateComboBox.setCurrentText(settings.get('frame_rate', '30'))
        self.screenshotFormatComboBox.setCurrentText(settings.get('screenshot_format', 'PNG'))
        self.screenshotLocationComboBox.setCurrentText(settings.get('screenshot_location', 'Same as video'))
        self.screenshotFolderLineEdit.setText(settings.get('custom_screenshot_path', ''))
        self.update_bitrate_visibility(self.qualityPresetComboBox.currentText())
        self._update_screenshot_location_visibility(self.screenshotLocationComboBox.currentText())

    def accept(self):
        # This method is called when the OK button is clicked.
        # The logic to save settings will be handled by the main window.
        super().accept()
