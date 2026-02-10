"""
Script Automation Tab Module

Provides UI for script automation feature.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget,
    QListWidgetItem, QPushButton, QPlainTextEdit, QLabel, QComboBox,
    QCheckBox, QMessageBox, QFileDialog, QInputDialog, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any, Optional

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.yaml_highlighter import YAMLHighlighter
from artalekey.core.script_manager import ScriptManager
from artalekey.core.script_executor import ScriptExecutor, ExecutionState
from artalekey.core.script_parser import ScriptParser
from artalekey.core.config import config_manager
from artalekey.core.logger import performance_logger


class ScriptAutomationTab(BaseTab):
    """Script automation tab"""

    # Signals
    script_execution_started = pyqtSignal()
    script_execution_stopped = pyqtSignal()

    def __init__(self, parent=None):
        self.script_manager = ScriptManager()
        self.script_parser = ScriptParser()
        self.script_executor: Optional[ScriptExecutor] = None

        # UI components
        self.script_list: Optional[QListWidget] = None
        self.script_editor: Optional[QPlainTextEdit] = None
        self.highlighter: Optional[YAMLHighlighter] = None
        self.target_window_combo: Optional[QComboBox] = None
        self.auto_activate_check: Optional[QCheckBox] = None
        self.pause_on_focus_check: Optional[QCheckBox] = None
        self.start_button: Optional[QPushButton] = None
        self.pause_button: Optional[QPushButton] = None
        self.stop_button: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self.progress_label: Optional[QLabel] = None
        self.iteration_label: Optional[QLabel] = None

        # State
        self.current_script_path: Optional[str] = None
        self.is_modified = False

        super().__init__("script_automation", parent)

    def init_ui(self):
        """Initialize UI"""
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Script list and management
        left_panel = self._create_script_list_widget()
        splitter.addWidget(left_panel)

        # Right panel: Script editor and execution control
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Script editor
        editor_widget = self._create_script_editor_widget()
        right_layout.addWidget(editor_widget, stretch=3)

        # Execution control
        control_widget = self._create_execution_control_widget()
        right_layout.addWidget(control_widget, stretch=1)

        splitter.addWidget(right_panel)

        # Set splitter sizes (30% left, 70% right)
        splitter.setSizes([300, 700])

        # Add splitter to main layout
        self.main_layout.addWidget(splitter)

        # Load scripts
        self._refresh_script_list()

        # Load configuration
        self._load_config()

    def _create_script_list_widget(self) -> QWidget:
        """Create script list widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Group box
        group = QGroupBox("Scripts")
        group_layout = QVBoxLayout(group)

        # Script list
        self.script_list = QListWidget()
        self.script_list.itemClicked.connect(self._on_script_selected)
        self.script_list.itemDoubleClicked.connect(self._on_script_double_clicked)
        group_layout.addWidget(self.script_list)

        # Management buttons
        button_layout = QHBoxLayout()

        new_button = QPushButton("New")
        new_button.clicked.connect(self._on_new_script)
        button_layout.addWidget(new_button)

        import_button = QPushButton("Import")
        import_button.clicked.connect(self._on_import_script)
        button_layout.addWidget(import_button)

        export_button = QPushButton("Export")
        export_button.clicked.connect(self._on_export_script)
        button_layout.addWidget(export_button)

        group_layout.addLayout(button_layout)

        button_layout2 = QHBoxLayout()

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._on_delete_script)
        button_layout2.addWidget(delete_button)

        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(self._on_duplicate_script)
        button_layout2.addWidget(duplicate_button)

        group_layout.addLayout(button_layout2)

        layout.addWidget(group)
        return widget

    def _create_script_editor_widget(self) -> QWidget:
        """Create script editor widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Group box
        group = QGroupBox("Script Editor")
        group_layout = QVBoxLayout(group)

        # Editor
        self.script_editor = QPlainTextEdit()
        self.script_editor.setFont(QFont("Courier", 11))
        self.script_editor.textChanged.connect(self._on_editor_text_changed)

        # Apply syntax highlighting
        self.highlighter = YAMLHighlighter(self.script_editor.document())

        group_layout.addWidget(self.script_editor)

        # Editor buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_current_script)
        button_layout.addWidget(save_button)

        validate_button = QPushButton("Validate")
        validate_button.clicked.connect(self._validate_current_script)
        button_layout.addWidget(validate_button)

        button_layout.addStretch()

        group_layout.addLayout(button_layout)

        layout.addWidget(group)
        return widget

    def _create_execution_control_widget(self) -> QWidget:
        """Create execution control widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Group box
        group = QGroupBox("Execution Control")
        group_layout = QVBoxLayout(group)

        # Target window selection
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Target Window:"))
        self.target_window_combo = QComboBox()
        self.target_window_combo.addItems([
            "MapleStory Worlds",
            "Any Window"
        ])
        self.target_window_combo.setEditable(True)
        window_layout.addWidget(self.target_window_combo, stretch=1)
        group_layout.addLayout(window_layout)

        # Options
        self.auto_activate_check = QCheckBox("Auto-activate window")
        self.auto_activate_check.setChecked(True)
        group_layout.addWidget(self.auto_activate_check)

        self.pause_on_focus_check = QCheckBox("Pause on focus loss")
        self.pause_on_focus_check.setChecked(True)
        group_layout.addWidget(self.pause_on_focus_check)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("▶ Start")
        self.start_button.clicked.connect(self._on_start_execution)
        button_layout.addWidget(self.start_button)

        self.pause_button = QPushButton("⏸ Pause")
        self.pause_button.clicked.connect(self._on_pause_execution)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)

        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.clicked.connect(self._on_stop_execution)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        group_layout.addLayout(button_layout)

        # Status labels
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold;")
        group_layout.addWidget(self.status_label)

        self.progress_label = QLabel("Progress: 0/0 operations")
        group_layout.addWidget(self.progress_label)

        self.iteration_label = QLabel("Iteration: 0/0")
        group_layout.addWidget(self.iteration_label)

        layout.addWidget(group)
        return widget

    def set_script_executor(self, executor: ScriptExecutor):
        """
        Set the script executor instance

        Args:
            executor: ScriptExecutor instance
        """
        self.script_executor = executor

        # Connect signals
        self.script_executor.execution_started.connect(self._on_execution_started)
        self.script_executor.execution_stopped.connect(self._on_execution_stopped)
        self.script_executor.execution_paused.connect(self._on_execution_paused)
        self.script_executor.execution_resumed.connect(self._on_execution_resumed)
        self.script_executor.execution_progress.connect(self._on_execution_progress)
        self.script_executor.execution_error.connect(self._on_execution_error)
        self.script_executor.iteration_completed.connect(self._on_iteration_completed)
        self.script_executor.state_changed.connect(self._on_state_changed)

    def _refresh_script_list(self):
        """Refresh the script list"""
        self.script_list.clear()
        scripts = self.script_manager.list_scripts()

        for script_info in scripts:
            item = QListWidgetItem(script_info['name'])
            item.setData(Qt.ItemDataRole.UserRole, script_info['path'])
            item.setToolTip(f"Modified: {script_info['modified']}\nPath: {script_info['path']}")
            self.script_list.addItem(item)

    def _on_script_selected(self, item: QListWidgetItem):
        """Handle script selection"""
        # Check if current script is modified
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Current script has unsaved changes. Do you want to save before switching?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._save_current_script()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        # Load selected script
        script_path = item.data(Qt.ItemDataRole.UserRole)
        self._load_script_into_editor(script_path)

    def _on_script_double_clicked(self, item: QListWidgetItem):
        """Handle script double-click (same as single click for now)"""
        pass

    def _load_script_into_editor(self, script_path: str):
        """Load script into editor"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.script_editor.setPlainText(content)
            self.current_script_path = script_path
            self.is_modified = False
            performance_logger.info(f"Loaded script: {script_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load script:\n{e}"
            )
            performance_logger.error(f"Failed to load script {script_path}: {e}")

    def _on_editor_text_changed(self):
        """Handle editor text change"""
        self.is_modified = True

    def _on_new_script(self):
        """Create new script"""
        name, ok = QInputDialog.getText(
            self,
            "New Script",
            "Enter script name:"
        )

        if ok and name:
            try:
                script_path = self.script_manager.create_new_script(name)
                self._refresh_script_list()
                self._load_script_into_editor(script_path)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Script created: {name}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create script:\n{e}"
                )

    def _on_import_script(self):
        """Import script from external location"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Script",
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if file_path:
            try:
                imported_path = self.script_manager.import_script(file_path)
                self._refresh_script_list()
                QMessageBox.information(
                    self,
                    "Success",
                    f"Script imported successfully"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to import script:\n{e}"
                )

    def _on_export_script(self):
        """Export current script"""
        if not self.current_script_path:
            QMessageBox.warning(
                self,
                "Warning",
                "No script selected"
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Script",
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if file_path:
            try:
                self.script_manager.export_script(self.current_script_path, file_path)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Script exported successfully"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to export script:\n{e}"
                )

    def _on_delete_script(self):
        """Delete selected script"""
        current_item = self.script_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Warning",
                "No script selected"
            )
            return

        script_path = current_item.data(Qt.ItemDataRole.UserRole)
        script_name = current_item.text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{script_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.script_manager.delete_script(script_path)
                self._refresh_script_list()

                # Clear editor if deleted script was loaded
                if self.current_script_path == script_path:
                    self.script_editor.clear()
                    self.current_script_path = None
                    self.is_modified = False

                QMessageBox.information(
                    self,
                    "Success",
                    f"Script deleted successfully"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete script:\n{e}"
                )

    def _on_duplicate_script(self):
        """Duplicate selected script"""
        current_item = self.script_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Warning",
                "No script selected"
            )
            return

        script_path = current_item.data(Qt.ItemDataRole.UserRole)

        try:
            duplicated_path = self.script_manager.duplicate_script(script_path)
            self._refresh_script_list()
            QMessageBox.information(
                self,
                "Success",
                f"Script duplicated successfully"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to duplicate script:\n{e}"
            )

    def _save_current_script(self):
        """Save current script"""
        if not self.current_script_path:
            QMessageBox.warning(
                self,
                "Warning",
                "No script loaded"
            )
            return

        try:
            content = self.script_editor.toPlainText()
            self.script_manager.save_script(content, self.current_script_path)
            self.is_modified = False
            QMessageBox.information(
                self,
                "Success",
                "Script saved successfully"
            )
            self._refresh_script_list()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save script:\n{e}"
            )

    def _validate_current_script(self):
        """Validate current script"""
        try:
            content = self.script_editor.toPlainText()
            script = self.script_parser.parse_yaml(content)
            is_valid, errors = self.script_parser.validate_script(script)

            if is_valid:
                QMessageBox.information(
                    self,
                    "Validation Success",
                    "Script is valid!"
                )
            else:
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Icon.Warning)
                error_dialog.setWindowTitle("Validation Failed")
                error_dialog.setText("The script contains the following errors:")
                error_dialog.setDetailedText("\n".join(errors))
                error_dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"Failed to validate script:\n{e}"
            )

    def _on_start_execution(self):
        """Start script execution"""
        if not self.script_executor:
            QMessageBox.warning(
                self,
                "Warning",
                "Script executor not initialized"
            )
            return

        # Validate script first
        try:
            content = self.script_editor.toPlainText()
            script = self.script_parser.parse_yaml(content)
            is_valid, errors = self.script_parser.validate_script(script)

            if not is_valid:
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Icon.Warning)
                error_dialog.setWindowTitle("Validation Failed")
                error_dialog.setText("Cannot execute invalid script:")
                error_dialog.setDetailedText("\n".join(errors))
                error_dialog.exec()
                return

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to parse script:\n{e}"
            )
            return

        # Load script into executor
        try:
            self.script_executor.load_script(script)

            # Configure executor
            self.script_executor.pause_on_focus_loss = self.pause_on_focus_check.isChecked()
            self.script_executor.resume_on_focus_gain = self.pause_on_focus_check.isChecked()

            # Start execution
            self.script_executor.start_execution()

            # Emit signal
            self.script_execution_started.emit()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to start execution:\n{e}"
            )

    def _on_pause_execution(self):
        """Pause script execution"""
        if self.script_executor:
            if self.script_executor.is_paused():
                self.script_executor.resume_execution()
            else:
                self.script_executor.pause_execution()

    def _on_stop_execution(self):
        """Stop script execution"""
        if self.script_executor:
            self.script_executor.stop_execution()
            self.script_execution_stopped.emit()

    def _on_execution_started(self):
        """Handle execution started"""
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")

    def _on_execution_stopped(self):
        """Handle execution stopped"""
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")

    def _on_execution_paused(self):
        """Handle execution paused"""
        self.pause_button.setText("▶ Resume")
        self.status_label.setText("Status: Paused")
        self.status_label.setStyleSheet("font-weight: bold; color: orange;")

    def _on_execution_resumed(self):
        """Handle execution resumed"""
        self.pause_button.setText("⏸ Pause")
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")

    def _on_execution_progress(self, current: int, total: int):
        """Handle execution progress"""
        self.progress_label.setText(f"Progress: {current}/{total} operations")

    def _on_execution_error(self, error: str):
        """Handle execution error"""
        QMessageBox.critical(
            self,
            "Execution Error",
            f"Script execution failed:\n{error}"
        )
        self.status_label.setText("Status: Error")
        self.status_label.setStyleSheet("font-weight: bold; color: red;")

    def _on_iteration_completed(self, current: int, total: int):
        """Handle iteration completed"""
        if total > 0:
            self.iteration_label.setText(f"Iteration: {current}/{total}")
        else:
            self.iteration_label.setText(f"Iteration: {current}/∞")

    def _on_state_changed(self, state: ExecutionState):
        """Handle state change"""
        if state == ExecutionState.IDLE:
            self.status_label.setText("Status: Idle")
            self.status_label.setStyleSheet("font-weight: bold;")
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def _load_config(self):
        """Load configuration"""
        try:
            script_config = config_manager.get('scripts', {})
            target_window = script_config.get('target_window', 'MapleStory Worlds')
            auto_activate = script_config.get('auto_activate_window', True)
            pause_on_focus = script_config.get('pause_on_focus_loss', True)

            self.target_window_combo.setCurrentText(target_window)
            self.auto_activate_check.setChecked(auto_activate)
            self.pause_on_focus_check.setChecked(pause_on_focus)

        except Exception as e:
            performance_logger.error(f"Failed to load script automation config: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            'target_window': self.target_window_combo.currentText(),
            'auto_activate_window': self.auto_activate_check.isChecked(),
            'pause_on_focus_loss': self.pause_on_focus_check.isChecked(),
            'current_script': self.current_script_path
        }

    def set_config(self, config: Dict[str, Any]):
        """Set configuration"""
        if 'target_window' in config:
            self.target_window_combo.setCurrentText(config['target_window'])
        if 'auto_activate_window' in config:
            self.auto_activate_check.setChecked(config['auto_activate_window'])
        if 'pause_on_focus_loss' in config:
            self.pause_on_focus_check.setChecked(config['pause_on_focus_loss'])
        if 'current_script' in config and config['current_script']:
            self._load_script_into_editor(config['current_script'])
