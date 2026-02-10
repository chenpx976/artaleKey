"""
Script Parser Module

Parses and validates YAML scripts for keyboard automation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import yaml


@dataclass
class ScriptOperation:
    """Represents a single script operation"""
    op_type: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"ScriptOperation(type={self.op_type}, params={self.params})"


@dataclass
class ParsedScript:
    """Represents a parsed YAML script"""
    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    execution_mode: str = "continuous"  # duration, iterations, continuous
    duration: int = 0  # seconds
    iterations: int = 0
    window_config: Dict[str, Any] = field(default_factory=dict)
    operations: List[ScriptOperation] = field(default_factory=list)

    def __repr__(self) -> str:
        return (f"ParsedScript(name={self.name}, mode={self.execution_mode}, "
                f"ops={len(self.operations)})")


class ScriptParser:
    """Parses YAML scripts into executable operations"""

    # Supported operation types
    VALID_OPERATIONS = {
        'press', 'long_press', 'hold', 'release', 'delay', 'repeat', 'combo', 'random'
    }

    # Supported keys
    VALID_KEYS = {
        # Letters
        *[chr(i) for i in range(ord('a'), ord('z') + 1)],
        # Numbers
        *[str(i) for i in range(10)],
        # Arrows
        'up', 'down', 'left', 'right',
        # Special
        'space', 'enter', 'tab', 'esc', 'backspace',
        # Modifiers
        'shift', 'ctrl', 'alt', 'cmd',
        # Function keys
        *[f'f{i}' for i in range(1, 13)]
    }

    # Maximum nested repeat depth
    MAX_REPEAT_DEPTH = 3

    def parse_file(self, file_path: str) -> ParsedScript:
        """
        Load YAML from file and parse

        Args:
            file_path: Path to YAML script file

        Returns:
            ParsedScript object

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If script structure is invalid
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
        return self.parse_yaml(yaml_content)

    def parse_yaml(self, yaml_content: str) -> ParsedScript:
        """
        Parse YAML string into ParsedScript

        Args:
            yaml_content: YAML string content

        Returns:
            ParsedScript object

        Raises:
            yaml.YAMLError: If YAML is invalid
            ValueError: If script structure is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

        if not isinstance(data, dict):
            raise ValueError("Script must be a YAML dictionary")

        # Parse metadata
        name = data.get('name')
        if not name:
            raise ValueError("Script must have a 'name' field")

        description = data.get('description', '')
        version = data.get('version', '1.0')
        author = data.get('author', '')

        # Parse execution configuration
        execution = data.get('execution', {})
        if not isinstance(execution, dict):
            raise ValueError("'execution' must be a dictionary")

        execution_mode = execution.get('mode', 'continuous')
        if execution_mode not in ('duration', 'iterations', 'continuous'):
            raise ValueError(
                f"Invalid execution mode: {execution_mode}. "
                "Must be 'duration', 'iterations', or 'continuous'"
            )

        duration = execution.get('duration', 0)
        iterations = execution.get('iterations', 0)

        if execution_mode == 'duration' and duration <= 0:
            raise ValueError("Duration mode requires positive 'duration' value")
        if execution_mode == 'iterations' and iterations <= 0:
            raise ValueError("Iterations mode requires positive 'iterations' value")

        # Parse window configuration
        window_config = data.get('window', {})
        if not isinstance(window_config, dict):
            raise ValueError("'window' must be a dictionary")

        # Parse operations
        operations_data = data.get('operations')
        if not operations_data:
            raise ValueError("Script must have 'operations' list")
        if not isinstance(operations_data, list):
            raise ValueError("'operations' must be a list")

        operations = self._parse_operations(operations_data, depth=0)

        # Create ParsedScript object
        script = ParsedScript(
            name=name,
            description=description,
            version=version,
            author=author,
            execution_mode=execution_mode,
            duration=duration,
            iterations=iterations,
            window_config=window_config,
            operations=operations
        )

        return script

    def validate_script(self, script: ParsedScript) -> Tuple[bool, List[str]]:
        """
        Validate a parsed script

        Args:
            script: ParsedScript object to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate name
        if not script.name or not script.name.strip():
            errors.append("Script name cannot be empty")

        # Validate execution mode
        if script.execution_mode not in ('duration', 'iterations', 'continuous'):
            errors.append(f"Invalid execution mode: {script.execution_mode}")

        if script.execution_mode == 'duration' and script.duration <= 0:
            errors.append("Duration mode requires positive duration value")

        if script.execution_mode == 'iterations' and script.iterations <= 0:
            errors.append("Iterations mode requires positive iterations value")

        # Validate operations
        if not script.operations:
            errors.append("Script must have at least one operation")

        for i, op in enumerate(script.operations):
            op_errors = self._validate_operation(op, i)
            errors.extend(op_errors)

        return (len(errors) == 0, errors)

    def _parse_operations(
        self,
        ops_list: List[Dict],
        depth: int = 0
    ) -> List[ScriptOperation]:
        """
        Recursively parse operations list

        Args:
            ops_list: List of operation dictionaries
            depth: Current nesting depth (for repeat operations)

        Returns:
            List of ScriptOperation objects

        Raises:
            ValueError: If operation structure is invalid
        """
        if depth > self.MAX_REPEAT_DEPTH:
            raise ValueError(
                f"Maximum repeat nesting depth ({self.MAX_REPEAT_DEPTH}) exceeded"
            )

        operations = []

        for i, op_data in enumerate(ops_list):
            if not isinstance(op_data, dict):
                raise ValueError(f"Operation {i} must be a dictionary")

            op_type = op_data.get('type')
            if not op_type:
                raise ValueError(f"Operation {i} missing 'type' field")

            if op_type not in self.VALID_OPERATIONS:
                raise ValueError(
                    f"Operation {i}: Invalid type '{op_type}'. "
                    f"Valid types: {', '.join(sorted(self.VALID_OPERATIONS))}"
                )

            # Parse operation parameters based on type
            params = {}

            if op_type == 'press':
                key = op_data.get('key')
                if not key:
                    raise ValueError(f"Operation {i}: 'press' requires 'key' field")
                if key not in self.VALID_KEYS:
                    raise ValueError(f"Operation {i}: Invalid key '{key}'")
                params['key'] = key

            elif op_type == 'long_press':
                key = op_data.get('key')
                duration = op_data.get('duration')
                if not key:
                    raise ValueError(f"Operation {i}: 'long_press' requires 'key' field")
                if not duration:
                    raise ValueError(
                        f"Operation {i}: 'long_press' requires 'duration' field"
                    )
                if key not in self.VALID_KEYS:
                    raise ValueError(f"Operation {i}: Invalid key '{key}'")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    raise ValueError(
                        f"Operation {i}: 'duration' must be positive number"
                    )
                params['key'] = key
                params['duration'] = int(duration)

            elif op_type == 'hold':
                key = op_data.get('key')
                if not key:
                    raise ValueError(f"Operation {i}: 'hold' requires 'key' field")
                if key not in self.VALID_KEYS:
                    raise ValueError(f"Operation {i}: Invalid key '{key}'")
                params['key'] = key

            elif op_type == 'release':
                key = op_data.get('key')
                if not key:
                    raise ValueError(f"Operation {i}: 'release' requires 'key' field")
                if key not in self.VALID_KEYS:
                    raise ValueError(f"Operation {i}: Invalid key '{key}'")
                params['key'] = key

            elif op_type == 'delay':
                duration = op_data.get('duration')
                if not duration:
                    raise ValueError(f"Operation {i}: 'delay' requires 'duration' field")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    raise ValueError(
                        f"Operation {i}: 'duration' must be positive number"
                    )
                params['duration'] = int(duration)

            elif op_type == 'repeat':
                count = op_data.get('count')
                nested_ops = op_data.get('operations')
                if not count:
                    raise ValueError(f"Operation {i}: 'repeat' requires 'count' field")
                if not nested_ops:
                    raise ValueError(
                        f"Operation {i}: 'repeat' requires 'operations' field"
                    )
                if not isinstance(count, int) or count <= 0:
                    raise ValueError(f"Operation {i}: 'count' must be positive integer")
                if not isinstance(nested_ops, list):
                    raise ValueError(
                        f"Operation {i}: 'operations' must be a list"
                    )

                # Recursively parse nested operations
                parsed_nested = self._parse_operations(nested_ops, depth + 1)
                params['count'] = count
                params['operations'] = parsed_nested

            elif op_type == 'combo':
                keys = op_data.get('keys')
                duration = op_data.get('duration', 100)
                if not keys:
                    raise ValueError(f"Operation {i}: 'combo' requires 'keys' field")
                if not isinstance(keys, list):
                    raise ValueError(f"Operation {i}: 'keys' must be a list")
                if len(keys) < 2:
                    raise ValueError(
                        f"Operation {i}: 'combo' requires at least 2 keys"
                    )
                for key in keys:
                    if key not in self.VALID_KEYS:
                        raise ValueError(f"Operation {i}: Invalid key '{key}'")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    raise ValueError(
                        f"Operation {i}: 'duration' must be positive number"
                    )
                params['keys'] = keys
                params['duration'] = int(duration)

            elif op_type == 'random':
                min_duration = op_data.get('min')
                max_duration = op_data.get('max')
                if min_duration is None:
                    raise ValueError(f"Operation {i}: 'random' requires 'min' field")
                if max_duration is None:
                    raise ValueError(f"Operation {i}: 'random' requires 'max' field")
                if not isinstance(min_duration, (int, float)) or min_duration <= 0:
                    raise ValueError(
                        f"Operation {i}: 'min' must be positive number"
                    )
                if not isinstance(max_duration, (int, float)) or max_duration <= 0:
                    raise ValueError(
                        f"Operation {i}: 'max' must be positive number"
                    )
                if min_duration >= max_duration:
                    raise ValueError(
                        f"Operation {i}: 'min' must be less than 'max'"
                    )
                params['min'] = int(min_duration)
                params['max'] = int(max_duration)

            # Create operation object
            operation = ScriptOperation(op_type=op_type, params=params)
            operations.append(operation)

        return operations

    def _validate_operation(self, op: ScriptOperation, index: int) -> List[str]:
        """
        Validate a single operation

        Args:
            op: ScriptOperation to validate
            index: Operation index (for error messages)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if op.op_type not in self.VALID_OPERATIONS:
            errors.append(f"Operation {index}: Invalid type '{op.op_type}'")
            return errors

        # Validate parameters based on operation type
        if op.op_type in ('press', 'long_press', 'hold', 'release'):
            key = op.params.get('key')
            if not key:
                errors.append(f"Operation {index}: Missing 'key' parameter")
            elif key not in self.VALID_KEYS:
                errors.append(f"Operation {index}: Invalid key '{key}'")

        if op.op_type in ('long_press', 'delay'):
            duration = op.params.get('duration')
            if duration is None:
                errors.append(f"Operation {index}: Missing 'duration' parameter")
            elif not isinstance(duration, (int, float)) or duration <= 0:
                errors.append(
                    f"Operation {index}: 'duration' must be positive number"
                )

        if op.op_type == 'repeat':
            count = op.params.get('count')
            nested_ops = op.params.get('operations')
            if count is None:
                errors.append(f"Operation {index}: Missing 'count' parameter")
            elif not isinstance(count, int) or count <= 0:
                errors.append(f"Operation {index}: 'count' must be positive integer")
            if not nested_ops:
                errors.append(f"Operation {index}: Missing 'operations' parameter")
            elif not isinstance(nested_ops, list):
                errors.append(f"Operation {index}: 'operations' must be a list")

        if op.op_type == 'combo':
            keys = op.params.get('keys')
            if not keys:
                errors.append(f"Operation {index}: Missing 'keys' parameter")
            elif not isinstance(keys, list):
                errors.append(f"Operation {index}: 'keys' must be a list")
            elif len(keys) < 2:
                errors.append(f"Operation {index}: 'combo' requires at least 2 keys")
            else:
                for key in keys:
                    if key not in self.VALID_KEYS:
                        errors.append(f"Operation {index}: Invalid key '{key}'")

        if op.op_type == 'random':
            min_val = op.params.get('min')
            max_val = op.params.get('max')
            if min_val is None:
                errors.append(f"Operation {index}: Missing 'min' parameter")
            if max_val is None:
                errors.append(f"Operation {index}: Missing 'max' parameter")
            if min_val is not None and max_val is not None:
                if not isinstance(min_val, (int, float)) or min_val <= 0:
                    errors.append(f"Operation {index}: 'min' must be positive number")
                if not isinstance(max_val, (int, float)) or max_val <= 0:
                    errors.append(f"Operation {index}: 'max' must be positive number")
                if min_val >= max_val:
                    errors.append(f"Operation {index}: 'min' must be less than 'max'")

        return errors

    def flatten_operations(self, operations: List[ScriptOperation]) -> List[ScriptOperation]:
        """
        Flatten nested repeat operations into a flat list

        Args:
            operations: List of operations (may contain nested repeats)

        Returns:
            Flattened list of operations
        """
        flattened = []

        for op in operations:
            if op.op_type == 'repeat':
                count = op.params['count']
                nested_ops = op.params['operations']
                # Recursively flatten nested operations
                flat_nested = self.flatten_operations(nested_ops)
                # Repeat the flattened operations
                for _ in range(count):
                    flattened.extend(flat_nested)
            else:
                flattened.append(op)

        return flattened
