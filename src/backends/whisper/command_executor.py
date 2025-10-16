"""
Executes voice commands via keyboard actions using xdotool.
"""

import subprocess
import logging
from typing import List, Optional
from .command_registry import CommandAction

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes voice commands using xdotool"""

    def __init__(self):
        self.xdotool_available = self._check_xdotool()

        if not self.xdotool_available:
            logger.error("xdotool not available, command execution disabled")

    def _check_xdotool(self) -> bool:
        """Check if xdotool is available"""
        try:
            subprocess.run(['xdotool', '--version'],
                         capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def execute_command(self, command_action: CommandAction) -> bool:
        """
        Execute a command action.

        Args:
            command_action: CommandAction to execute

        Returns:
            True if successful, False otherwise
        """
        if not self.xdotool_available:
            logger.error("Cannot execute command: xdotool not available")
            return False

        if not command_action.enabled:
            logger.warning(f"Command disabled: {command_action}")
            return False

        try:
            success = self._execute_keys(command_action.keys)
            if success:
                logger.info(f"Command executed successfully: {command_action.description}")
            return success
        except Exception as e:
            logger.error(f"Failed to execute command {command_action.keys}: {e}")
            return False

    def _execute_keys(self, keys: List[str]) -> bool:
        """Execute key combination"""
        if not keys:
            return False

        try:
            # Build xdotool command
            # For key combinations, we use "key" with modifiers
            if len(keys) == 1:
                # Single key
                cmd = ['xdotool', 'key', keys[0]]
            else:
                # Key combination - join with '+'
                key_combo = '+'.join(keys)
                cmd = ['xdotool', 'key', key_combo]

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)

            if result.returncode != 0:
                logger.error(f"xdotool failed: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.error("Command execution timed out")
            return False
        except Exception as e:
            logger.error(f"Error executing keys {keys}: {e}")
            return False

    def test_xdotool(self) -> bool:
        """Test xdotool functionality"""
        try:
            # Try to execute a harmless key test
            result = subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Shift_L'],
                                 capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    def get_xdotool_version(self) -> Optional[str]:
        """Get xdotool version"""
        try:
            result = subprocess.run(['xdotool', '--version'],
                                 capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
