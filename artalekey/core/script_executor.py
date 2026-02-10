"""
Script Executor Module

Executes parsed scripts with keyboard operations.
"""

from enum import Enum
from typing import Optional, Set
import time
import threading

from PyQt6.QtCore import QThread, pyqtSignal
from pynput.keyboard import Key, KeyCode, Controller

from artalekey.core.script_parser import ParsedScript, ScriptOperation
from artalekey.core.logger import performance_logger


class ExecutionState(Enum):
    """Execution state enumeration"""
    IDLE = 0
    RUNNING = 1
    PAUSED = 2
    STOPPED = 3
    ERROR = 4


class ScriptExecutor(QThread):
    """Executes parsed scripts with keyboard operations"""

    # Signals
    execution_started = pyqtSignal()
    execution_stopped = pyqtSignal()
    execution_paused = pyqtSignal()
    execution_resumed = pyqtSignal()
    execution_progress = pyqtSignal(int, int)  # current_op, total_ops
    execution_error = pyqtSignal(str)
    operation_executed = pyqtSignal(str)  # operation description
    iteration_completed = pyqtSignal(int, int)  # current, total
    state_changed = pyqtSignal(ExecutionState)

    # Key mapping
    KEY_MAP = {
        # Letters
        **{chr(i): chr(i) for i in range(ord('a'), ord('z') + 1)},
        # Numbers
        **{str(i): str(i) for i in range(10)},
        # Arrows
        'up': Key.up,
        'down': Key.down,
        'left': Key.left,
        'right': Key.right,
        # Special
        'space': Key.space,
        'enter': Key.enter,
        'tab': Key.tab,
        'esc': Key.esc,
        'backspace': Key.backspace,
        # Modifiers
        'shift': Key.shift,
        'ctrl': Key.ctrl,
        'alt': Key.alt,
        'cmd': Key.cmd,
        # Function keys
        **{f'f{i}': getattr(Key, f'f{i}') for i in range(1, 13)}
    }

    def __init__(self):
        super().__init__()
        self.keyboard = Controller()
        self._script: Optional[ParsedScript] = None
        self._state = ExecutionState.IDLE
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._keys_pressed: Set = set()
        self._current_iteration = 0
        self._start_time = 0.0

        # Configuration
        self.pause_on_focus_loss = True
        self.resume_on_focus_gain = True

    def load_script(self, script: ParsedScript):
        """
        Load a parsed script for execution

        Args:
            script: ParsedScript object to execute
        """
        with self._lock:
            if self._state == ExecutionState.RUNNING:
                raise RuntimeError("Cannot load script while execution is running")
            self._script = script
            self._current_iteration = 0

    def start_execution(self):
        """Start script execution"""
        with self._lock:
            if self._state == ExecutionState.RUNNING:
                performance_logger.warning("Script execution already running")
                return

            if not self._script:
                self.execution_error.emit("No script loaded")
                return

            self._state = ExecutionState.RUNNING
            self._stop_event.clear()
            self._pause_event.clear()
            self._current_iteration = 0
            self._start_time = time.time()

        self.state_changed.emit(ExecutionState.RUNNING)
        self.start()  # Start QThread

    def pause_execution(self):
        """Pause script execution"""
        with self._lock:
            if self._state != ExecutionState.RUNNING:
                return
            self._state = ExecutionState.PAUSED
            self._pause_event.set()

        self.state_changed.emit(ExecutionState.PAUSED)
        self.execution_paused.emit()
        performance_logger.info("Script execution paused")

    def resume_execution(self):
        """Resume script execution"""
        with self._lock:
            if self._state != ExecutionState.PAUSED:
                return
            self._state = ExecutionState.RUNNING
            self._pause_event.clear()

        self.state_changed.emit(ExecutionState.RUNNING)
        self.execution_resumed.emit()
        performance_logger.info("Script execution resumed")

    def stop_execution(self):
        """Stop script execution"""
        with self._lock:
            if self._state in (ExecutionState.IDLE, ExecutionState.STOPPED):
                return
            self._state = ExecutionState.STOPPED
            self._stop_event.set()
            self._pause_event.clear()

        self._release_all_keys()
        self.state_changed.emit(ExecutionState.STOPPED)
        performance_logger.info("Script execution stopped")

    def is_running(self) -> bool:
        """Check if script is currently running"""
        with self._lock:
            return self._state == ExecutionState.RUNNING

    def is_paused(self) -> bool:
        """Check if script is currently paused"""
        with self._lock:
            return self._state == ExecutionState.PAUSED

    def get_state(self) -> ExecutionState:
        """Get current execution state"""
        with self._lock:
            return self._state

    def run(self):
        """QThread main loop"""
        try:
            self.execution_started.emit()
            performance_logger.info(
                f"Starting script execution: {self._script.name} "
                f"(mode: {self._script.execution_mode})"
            )

            # Flatten operations for easier execution
            from artalekey.core.script_parser import ScriptParser
            parser = ScriptParser()
            flat_operations = parser.flatten_operations(self._script.operations)
            total_ops = len(flat_operations)

            # Execute based on mode
            if self._script.execution_mode == 'duration':
                self._execute_duration_mode(flat_operations, total_ops)
            elif self._script.execution_mode == 'iterations':
                self._execute_iterations_mode(flat_operations, total_ops)
            elif self._script.execution_mode == 'continuous':
                self._execute_continuous_mode(flat_operations, total_ops)

        except Exception as e:
            performance_logger.error(f"Script execution error: {e}")
            self.execution_error.emit(str(e))
            with self._lock:
                self._state = ExecutionState.ERROR
            self.state_changed.emit(ExecutionState.ERROR)
        finally:
            self._release_all_keys()
            with self._lock:
                if self._state != ExecutionState.ERROR:
                    self._state = ExecutionState.IDLE
            self.execution_stopped.emit()
            if self._state != ExecutionState.ERROR:
                self.state_changed.emit(ExecutionState.IDLE)
            performance_logger.info("Script execution finished")

    def _execute_duration_mode(self, operations, total_ops):
        """Execute script for specified duration"""
        end_time = self._start_time + self._script.duration
        iteration = 0

        while time.time() < end_time and not self._stop_event.is_set():
            iteration += 1
            self._current_iteration = iteration
            self.iteration_completed.emit(iteration, -1)  # -1 = unknown total

            for i, op in enumerate(operations):
                if self._stop_event.is_set() or time.time() >= end_time:
                    break

                self._wait_if_paused()
                self._execute_operation(op)
                self.execution_progress.emit(i + 1, total_ops)

    def _execute_iterations_mode(self, operations, total_ops):
        """Execute script for specified number of iterations"""
        for iteration in range(1, self._script.iterations + 1):
            if self._stop_event.is_set():
                break

            self._current_iteration = iteration
            self.iteration_completed.emit(iteration, self._script.iterations)

            for i, op in enumerate(operations):
                if self._stop_event.is_set():
                    break

                self._wait_if_paused()
                self._execute_operation(op)
                self.execution_progress.emit(i + 1, total_ops)

    def _execute_continuous_mode(self, operations, total_ops):
        """Execute script continuously until stopped"""
        iteration = 0

        while not self._stop_event.is_set():
            iteration += 1
            self._current_iteration = iteration
            self.iteration_completed.emit(iteration, -1)  # -1 = infinite

            for i, op in enumerate(operations):
                if self._stop_event.is_set():
                    break

                self._wait_if_paused()
                self._execute_operation(op)
                self.execution_progress.emit(i + 1, total_ops)

    def _wait_if_paused(self):
        """Wait while execution is paused"""
        while self._pause_event.is_set() and not self._stop_event.is_set():
            time.sleep(0.1)

    def _execute_operation(self, operation: ScriptOperation):
        """
        Execute a single operation

        Args:
            operation: ScriptOperation to execute
        """
        try:
            if operation.op_type == 'press':
                self._execute_press(operation.params['key'])
            elif operation.op_type == 'long_press':
                self._execute_long_press(
                    operation.params['key'],
                    operation.params['duration']
                )
            elif operation.op_type == 'hold':
                self._execute_hold(operation.params['key'])
            elif operation.op_type == 'release':
                self._execute_release(operation.params['key'])
            elif operation.op_type == 'delay':
                self._execute_delay(operation.params['duration'])
            elif operation.op_type == 'combo':
                self._execute_combo(
                    operation.params['keys'],
                    operation.params['duration']
                )

            # Emit operation description
            self.operation_executed.emit(self._get_operation_description(operation))

        except Exception as e:
            performance_logger.error(f"Error executing operation {operation}: {e}")
            raise

    def _execute_press(self, key: str):
        """Execute a single key press"""
        pynput_key = self._convert_key_string(key)
        self.keyboard.press(pynput_key)
        time.sleep(0.05)  # Short delay for key press
        self.keyboard.release(pynput_key)

    def _execute_long_press(self, key: str, duration: int):
        """Execute a long key press"""
        pynput_key = self._convert_key_string(key)
        self.keyboard.press(pynput_key)
        self._keys_pressed.add(pynput_key)

        # Wait for duration with stop check
        duration_sec = duration / 1000.0
        if self._stop_event.wait(duration_sec):
            self.keyboard.release(pynput_key)
            self._keys_pressed.discard(pynput_key)
            return

        self.keyboard.release(pynput_key)
        self._keys_pressed.discard(pynput_key)

    def _execute_hold(self, key: str):
        """Hold a key down (keep pressed)"""
        pynput_key = self._convert_key_string(key)
        self.keyboard.press(pynput_key)
        self._keys_pressed.add(pynput_key)

    def _execute_release(self, key: str):
        """Release a held key"""
        pynput_key = self._convert_key_string(key)
        self.keyboard.release(pynput_key)
        self._keys_pressed.discard(pynput_key)

    def _execute_delay(self, duration: int):
        """Execute a delay"""
        duration_sec = duration / 1000.0
        self._stop_event.wait(duration_sec)

    def _execute_combo(self, keys: list, duration: int):
        """Execute a key combination"""
        pynput_keys = [self._convert_key_string(k) for k in keys]

        # Press all keys
        for key in pynput_keys:
            self.keyboard.press(key)
            self._keys_pressed.add(key)

        # Hold for duration
        duration_sec = duration / 1000.0
        self._stop_event.wait(duration_sec)

        # Release all keys in reverse order
        for key in reversed(pynput_keys):
            self.keyboard.release(key)
            self._keys_pressed.discard(key)

    def _release_all_keys(self):
        """Release all currently pressed keys"""
        try:
            for key in list(self._keys_pressed):
                self.keyboard.release(key)
            self._keys_pressed.clear()
        except Exception as e:
            performance_logger.error(f"Error releasing keys: {e}")

    def _convert_key_string(self, key_str: str):
        """
        Convert key string to pynput Key or KeyCode

        Args:
            key_str: Key string (e.g., 'a', 'shift', 'f1')

        Returns:
            pynput Key or KeyCode object
        """
        if key_str in self.KEY_MAP:
            key_obj = self.KEY_MAP[key_str]
            # If it's a string (letter/number), convert to KeyCode
            if isinstance(key_obj, str):
                return KeyCode.from_char(key_obj)
            return key_obj
        else:
            # Fallback: try to create KeyCode
            return KeyCode.from_char(key_str)

    def _get_operation_description(self, operation: ScriptOperation) -> str:
        """Get human-readable description of operation"""
        if operation.op_type == 'press':
            return f"Press {operation.params['key']}"
        elif operation.op_type == 'long_press':
            return (f"Long press {operation.params['key']} "
                   f"for {operation.params['duration']}ms")
        elif operation.op_type == 'hold':
            return f"Hold {operation.params['key']}"
        elif operation.op_type == 'release':
            return f"Release {operation.params['key']}"
        elif operation.op_type == 'delay':
            return f"Delay {operation.params['duration']}ms"
        elif operation.op_type == 'combo':
            keys_str = '+'.join(operation.params['keys'])
            return f"Combo {keys_str}"
        else:
            return f"Unknown operation: {operation.op_type}"
