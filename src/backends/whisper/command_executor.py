"""
Executes voice commands via keyboard actions using xdotool (Linux) or PyAutoGUI (macOS).
"""

import subprocess
import platform
from typing import List, Optional
from .command_registry import CommandAction

from src.core.logging_controller import info, debug, warning, error, critical

# Platform detection
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Try to import PyAutoGUI on macOS
if IS_MACOS:
    try:
        import pyautogui
        PYAUTOGUI_AVAILABLE = True
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05  # Small delay between actions
    except ImportError:
        PYAUTOGUI_AVAILABLE = False
        warning("PyAutoGUI not available - install with: pip install pyautogui")
else:
    PYAUTOGUI_AVAILABLE = False


class CommandExecutor:
    """Executes voice commands using platform-appropriate method"""

    def __init__(self):
        self.use_pyautogui = False
        self.xdotool_available = False

        if IS_MACOS:
            if PYAUTOGUI_AVAILABLE:
                self.use_pyautogui = True
                self.xdotool_available = True  # Compatibility flag
                info("Using PyAutoGUI for command execution on macOS")
            else:
                error("PyAutoGUI not available, command execution disabled")
        else:
            self.xdotool_available = self._check_xdotool()
            if not self.xdotool_available:
                error("xdotool not available, command execution disabled")

    def _check_xdotool(self) -> bool:
        """Check if xdotool is available"""
        try:
            subprocess.run(['xdotool', '--version'],
                         capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _xdotool_to_pyautogui_key(xdotool_key: str) -> str:
        """
        Convert xdotool key name to PyAutoGUI key name.

        Maps X11 key names (used by xdotool) to PyAutoGUI key names.
        """
        key_mapping = {
            # Basic keys
            'Return': 'enter',
            'BackSpace': 'backspace',
            'Tab': 'tab',
            'Escape': 'esc',
            'space': 'space',
            'Delete': 'delete',

            # Modifiers
            'Control_L': 'ctrl',
            'Control_R': 'ctrl',
            'Alt_L': 'alt',
            'Alt_R': 'alt',
            'Shift_L': 'shift',
            'Shift_R': 'shift',
            'Super_L': 'command' if IS_MACOS else 'win',
            'Super_R': 'command' if IS_MACOS else 'win',
            'Meta_L': 'command' if IS_MACOS else 'win',
            'Meta_R': 'command' if IS_MACOS else 'win',

            # Navigation
            'Up': 'up',
            'Down': 'down',
            'Left': 'left',
            'Right': 'right',
            'Home': 'home',
            'End': 'end',
            'Prior': 'pageup',
            'Next': 'pagedown',
            'Insert': 'insert',

            # Function keys
            'F1': 'f1', 'F2': 'f2', 'F3': 'f3', 'F4': 'f4',
            'F5': 'f5', 'F6': 'f6', 'F7': 'f7', 'F8': 'f8',
            'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12',

            # Special keys
            'Print': 'printscreen',
            'Scroll_Lock': 'scrolllock',
            'Pause': 'pause',
            'Caps_Lock': 'capslock',
            'Num_Lock': 'numlock',

            # Media keys - PyAutoGUI uses different names
            'XF86AudioPlay': 'playpause',
            'XF86AudioPause': 'playpause',
            'XF86AudioNext': 'nexttrack',
            'XF86AudioPrev': 'prevtrack',
            'XF86AudioMute': 'volumemute',
            'XF86AudioLowerVolume': 'volumedown',
            'XF86AudioRaiseVolume': 'volumeup',
        }

        # Return mapped key or original key (lowercase for PyAutoGUI)
        return key_mapping.get(xdotool_key, xdotool_key.lower())

    def execute_command(self, command_action: CommandAction) -> bool:
        """
        Execute a command action.

        Args:
            command_action: CommandAction to execute

        Returns:
            True if successful, False otherwise
        """
        if not self.xdotool_available:
            error("Cannot execute command: xdotool not available")
            return False

        if not command_action.enabled:
            warning(f"Command disabled: {command_action}")
            return False

        try:
            success = self._execute_keys(command_action.keys)
            if success:
                info(f"Command executed successfully: {command_action.description}")
            return success
        except Exception as e:
            error(f"Failed to execute command {command_action.keys}: {e}")
            return False

    def _execute_keys(self, keys: List[str]) -> bool:
        """
        Execute key combination or sequence.

        Automatically detects:
        - Single key: ["Return"] -> press key
        - Combination (with modifiers): ["Control_L", "c"] -> press modifier+key
        - Sequence (no modifiers): ["Return", "space"] -> press keys in sequence
        """
        if not keys:
            return False

        try:
            if self.use_pyautogui:
                return self._execute_keys_pyautogui(keys)
            else:
                return self._execute_keys_xdotool(keys)

        except subprocess.TimeoutExpired:
            error("Command execution timed out")
            return False
        except Exception as e:
            error(f"Error executing keys {keys}: {e}")
            return False

    def _execute_keys_pyautogui(self, keys: List[str]) -> bool:
        """Execute keys using PyAutoGUI (macOS)"""
        # Convert xdotool key names to PyAutoGUI names
        converted_keys = [self._xdotool_to_pyautogui_key(k) for k in keys]

        # List of modifier keys (PyAutoGUI names)
        modifiers = {'ctrl', 'alt', 'shift', 'command', 'win', 'option'}

        if len(converted_keys) == 1:
            # Single key
            debug(f"PyAutoGUI: pressing '{converted_keys[0]}'")
            pyautogui.press(converted_keys[0])
            return True
        else:
            # Check if this is a combination (has modifiers) or sequence
            has_modifier = any(key in modifiers for key in converted_keys[:-1])

            if has_modifier:
                # Key combination - use hotkey
                debug(f"PyAutoGUI: hotkey {converted_keys}")
                pyautogui.hotkey(*converted_keys)
                return True
            else:
                # Key sequence - press each key in order
                debug(f"PyAutoGUI: sequence {converted_keys}")
                for key in converted_keys:
                    pyautogui.press(key)
                return True

    def _execute_keys_xdotool(self, keys: List[str]) -> bool:
        """Execute keys using xdotool (Linux)"""
        # List of modifier keys
        modifiers = {
            'Control_L', 'Control_R', 'Shift_L', 'Shift_R',
            'Alt_L', 'Alt_R', 'Super_L', 'Super_R', 'Meta_L', 'Meta_R'
        }

        # Build xdotool command
        if len(keys) == 1:
            # Single key
            cmd = ['xdotool', 'key', keys[0]]
        else:
            # Check if this is a combination (has modifiers) or sequence
            has_modifier = any(key in modifiers for key in keys[:-1])

            if has_modifier:
                # Key combination - join with '+' (e.g., Ctrl+C)
                key_combo = '+'.join(keys)
                cmd = ['xdotool', 'key', key_combo]
            else:
                # Key sequence - pass as separate arguments (e.g., Return space)
                # xdotool will execute them in order
                cmd = ['xdotool', 'key'] + keys

        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)

        if result.returncode != 0:
            error(f"xdotool failed: {result.stderr}")
            return False

        return True

    def test_xdotool(self) -> bool:
        """Test command execution functionality"""
        if self.use_pyautogui:
            # Test PyAutoGUI
            try:
                # Just verify PyAutoGUI is available and can be called
                # Don't actually press any keys during test
                return PYAUTOGUI_AVAILABLE
            except Exception:
                return False
        else:
            # Test xdotool
            try:
                # Try to execute a harmless key test
                result = subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Shift_L'],
                                     capture_output=True, timeout=2)
                return result.returncode == 0
            except Exception:
                return False

    def get_xdotool_version(self) -> Optional[str]:
        """Get command executor version/info"""
        if self.use_pyautogui:
            try:
                return f"PyAutoGUI {pyautogui.__version__}"
            except Exception:
                return "PyAutoGUI (version unknown)"
        else:
            try:
                result = subprocess.run(['xdotool', '--version'],
                                     capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
            return None
