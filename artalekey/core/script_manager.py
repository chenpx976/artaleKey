"""
Script Manager Module

Manages script files and storage.
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal

from artalekey.core.script_parser import ScriptParser, ParsedScript


class ScriptManager(QObject):
    """Manages script files and storage"""

    # Signals
    scripts_changed = pyqtSignal()
    script_saved = pyqtSignal(str)  # script_path
    script_deleted = pyqtSignal(str)  # script_path

    def __init__(self):
        super().__init__()
        self.parser = ScriptParser()
        self._scripts_dir = self._get_scripts_directory()
        self._ensure_scripts_directory()

    def _get_scripts_directory(self) -> str:
        """
        Get the default scripts directory

        Returns:
            Path to scripts directory
        """
        # macOS: ~/Library/Application Support/ArtaleKey/scripts/
        # Windows: %APPDATA%/ArtaleKey/scripts/
        # Linux: ~/.config/ArtaleKey/scripts/

        if os.name == 'posix':
            if os.uname().sysname == 'Darwin':  # macOS
                base_dir = Path.home() / 'Library' / 'Application Support' / 'ArtaleKey'
            else:  # Linux
                base_dir = Path.home() / '.config' / 'ArtaleKey'
        else:  # Windows
            base_dir = Path(os.getenv('APPDATA', Path.home())) / 'ArtaleKey'

        scripts_dir = base_dir / 'scripts'
        return str(scripts_dir)

    def _ensure_scripts_directory(self):
        """Ensure scripts directory exists"""
        Path(self._scripts_dir).mkdir(parents=True, exist_ok=True)

        # Create examples subdirectory
        examples_dir = Path(self._scripts_dir) / 'examples'
        examples_dir.mkdir(exist_ok=True)

    def get_scripts_directory(self) -> str:
        """
        Get the scripts directory path

        Returns:
            Path to scripts directory
        """
        return self._scripts_dir

    def set_scripts_directory(self, directory: str):
        """
        Set a custom scripts directory

        Args:
            directory: Path to custom scripts directory
        """
        if not os.path.isdir(directory):
            raise ValueError(f"Directory does not exist: {directory}")
        self._scripts_dir = directory
        self.scripts_changed.emit()

    def list_scripts(self) -> List[Dict[str, str]]:
        """
        List all available scripts

        Returns:
            List of dictionaries with script metadata:
            [{'name': str, 'path': str, 'modified': str}]
        """
        scripts = []
        scripts_path = Path(self._scripts_dir)

        # Search for .yaml and .yml files
        for pattern in ('*.yaml', '*.yml'):
            for file_path in scripts_path.rglob(pattern):
                try:
                    # Get file modification time
                    mtime = file_path.stat().st_mtime
                    modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

                    # Try to parse script to get name
                    try:
                        script = self.parser.parse_file(str(file_path))
                        name = script.name
                    except Exception:
                        # If parsing fails, use filename
                        name = file_path.stem

                    scripts.append({
                        'name': name,
                        'path': str(file_path),
                        'modified': modified
                    })
                except Exception:
                    # Skip files that can't be read
                    continue

        # Sort by modification time (newest first)
        scripts.sort(key=lambda x: x['modified'], reverse=True)
        return scripts

    def load_script(self, script_path: str) -> ParsedScript:
        """
        Load a script from file

        Args:
            script_path: Path to script file

        Returns:
            ParsedScript object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If script is invalid
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")

        return self.parser.parse_file(script_path)

    def save_script(self, script_content: str, file_path: str) -> bool:
        """
        Save script content to file

        Args:
            script_content: YAML script content
            file_path: Path to save file

        Returns:
            True if successful

        Raises:
            ValueError: If script content is invalid
            IOError: If file cannot be written
        """
        # Validate script before saving
        try:
            script = self.parser.parse_yaml(script_content)
            is_valid, errors = self.parser.validate_script(script)
            if not is_valid:
                raise ValueError(f"Invalid script: {', '.join(errors)}")
        except Exception as e:
            raise ValueError(f"Script validation failed: {e}")

        # Ensure parent directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
        except Exception as e:
            raise IOError(f"Failed to write script file: {e}")

        self.script_saved.emit(file_path)
        self.scripts_changed.emit()
        return True

    def delete_script(self, script_path: str) -> bool:
        """
        Delete a script file

        Args:
            script_path: Path to script file

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be deleted
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")

        try:
            os.remove(script_path)
        except Exception as e:
            raise IOError(f"Failed to delete script file: {e}")

        self.script_deleted.emit(script_path)
        self.scripts_changed.emit()
        return True

    def create_new_script(self, name: str) -> str:
        """
        Create a new script file with default template

        Args:
            name: Script name

        Returns:
            Path to new script file
        """
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        filename = f"{safe_name}_{timestamp}.yaml"
        file_path = os.path.join(self._scripts_dir, filename)

        # Create default template
        template = f"""name: "{name}"
description: "New script"
version: "1.0"
author: ""

execution:
  mode: "continuous"

window:
  auto_activate: true
  pause_on_focus_loss: true
  target_window: "MapleStory Worlds"

operations:
  - type: "press"
    key: "a"
  - type: "delay"
    duration: 500
"""

        # Write template to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(template)

        self.scripts_changed.emit()
        return file_path

    def import_script(self, external_path: str) -> str:
        """
        Import a script from external location

        Args:
            external_path: Path to external script file

        Returns:
            Path to imported script in scripts directory

        Raises:
            FileNotFoundError: If external file doesn't exist
            ValueError: If script is invalid
            IOError: If file cannot be copied
        """
        if not os.path.isfile(external_path):
            raise FileNotFoundError(f"Script file not found: {external_path}")

        # Validate script before importing
        try:
            script = self.parser.parse_file(external_path)
            is_valid, errors = self.parser.validate_script(script)
            if not is_valid:
                raise ValueError(f"Invalid script: {', '.join(errors)}")
        except Exception as e:
            raise ValueError(f"Script validation failed: {e}")

        # Generate destination filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = "".join(c for c in script.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        filename = f"{safe_name}_{timestamp}.yaml"
        dest_path = os.path.join(self._scripts_dir, filename)

        # Copy file
        try:
            import shutil
            shutil.copy2(external_path, dest_path)
        except Exception as e:
            raise IOError(f"Failed to import script: {e}")

        self.scripts_changed.emit()
        return dest_path

    def export_script(self, script_path: str, destination: str) -> bool:
        """
        Export a script to external location

        Args:
            script_path: Path to script file in scripts directory
            destination: Destination path for exported script

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If script file doesn't exist
            IOError: If file cannot be copied
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")

        # Ensure destination directory exists
        Path(destination).parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        try:
            import shutil
            shutil.copy2(script_path, destination)
        except Exception as e:
            raise IOError(f"Failed to export script: {e}")

        return True

    def duplicate_script(self, script_path: str) -> str:
        """
        Duplicate an existing script

        Args:
            script_path: Path to script file to duplicate

        Returns:
            Path to duplicated script file

        Raises:
            FileNotFoundError: If script file doesn't exist
            IOError: If file cannot be copied
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")

        # Load original script
        script = self.parser.parse_file(script_path)

        # Generate new filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = "".join(c for c in script.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        filename = f"{safe_name}_copy_{timestamp}.yaml"
        dest_path = os.path.join(self._scripts_dir, filename)

        # Copy file
        try:
            import shutil
            shutil.copy2(script_path, dest_path)
        except Exception as e:
            raise IOError(f"Failed to duplicate script: {e}")

        self.scripts_changed.emit()
        return dest_path

    def validate_script_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a script file

        Args:
            file_path: Path to script file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            script = self.parser.parse_file(file_path)
            return self.parser.validate_script(script)
        except Exception as e:
            return (False, [str(e)])
