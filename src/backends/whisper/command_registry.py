"""
Registry of available voice commands and their keyboard actions.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CommandAction:
    """Represents a keyboard action"""
    keys: List[str]
    description: str
    category: str
    enabled: bool = True
    custom: bool = False


class CommandRegistry:
    """Registry of voice commands and their keyboard mappings"""

    def __init__(self):
        self.commands: Dict[str, CommandAction] = {}
        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """Register built-in commands"""

        # Basic commands
        basic_commands = {
            'enter': CommandAction(['Return'], 'Press Enter key', 'Basic'),
            'space': CommandAction(['space'], 'Press Space key', 'Basic'),
            'backspace': CommandAction(['BackSpace'], 'Press Backspace key', 'Basic'),
            'delete': CommandAction(['Delete'], 'Press Delete key', 'Basic'),
            'escape': CommandAction(['Escape'], 'Press Escape key', 'Basic'),
            'tab': CommandAction(['Tab'], 'Press Tab key', 'Basic'),
            'home': CommandAction(['Home'], 'Press Home key', 'Basic'),
            'end': CommandAction(['End'], 'Press End key', 'Basic'),
            'pageup': CommandAction(['Prior'], 'Press Page Up key', 'Basic'),
            'pagedown': CommandAction(['Next'], 'Press Page Down key', 'Basic'),
            'print': CommandAction(['Print'], 'Press Print Screen key', 'Basic'),
        }

        # Navigation commands
        nav_commands = {
            'up': CommandAction(['Up'], 'Press Up arrow key', 'Navigation'),
            'down': CommandAction(['Down'], 'Press Down arrow key', 'Navigation'),
            'left': CommandAction(['Left'], 'Press Left arrow key', 'Navigation'),
            'right': CommandAction(['Right'], 'Press Right arrow key', 'Navigation'),
        }

        # System commands
        system_commands = {
            'copy': CommandAction(['Control_L', 'c'], 'Copy (Ctrl+C)', 'System'),
            'paste': CommandAction(['Control_L', 'v'], 'Paste (Ctrl+V)', 'System'),
            'cut': CommandAction(['Control_L', 'x'], 'Cut (Ctrl+X)', 'System'),
            'save': CommandAction(['Control_L', 's'], 'Save (Ctrl+S)', 'System'),
            'selectall': CommandAction(['Control_L', 'a'], 'Select All (Ctrl+A)', 'System'),
            'undo': CommandAction(['Control_L', 'z'], 'Undo (Ctrl+Z)', 'System'),
            'redo': CommandAction(['Control_L', 'y'], 'Redo (Ctrl+Y)', 'System'),
            'find': CommandAction(['Control_L', 'f'], 'Find (Ctrl+F)', 'System'),
            'close': CommandAction(['Alt_L', 'F4'], 'Close window (Alt+F4)', 'System'),
            'minimize': CommandAction(['Alt_L', 'F9'], 'Minimize window (Alt+F9)', 'System'),
            'maximize': CommandAction(['Alt_L', 'F10'], 'Maximize window (Alt+F10)', 'System'),
        }

        # Function keys
        function_commands = {
            'f1': CommandAction(['F1'], 'Press F1 key', 'Function'),
            'f2': CommandAction(['F2'], 'Press F2 key', 'Function'),
            'f3': CommandAction(['F3'], 'Press F3 key', 'Function'),
            'f4': CommandAction(['F4'], 'Press F4 key', 'Function'),
            'f5': CommandAction(['F5'], 'Press F5 key', 'Function'),
            'f6': CommandAction(['F6'], 'Press F6 key', 'Function'),
            'f7': CommandAction(['F7'], 'Press F7 key', 'Function'),
            'f8': CommandAction(['F8'], 'Press F8 key', 'Function'),
            'f9': CommandAction(['F9'], 'Press F9 key', 'Function'),
            'f10': CommandAction(['F10'], 'Press F10 key', 'Function'),
            'f11': CommandAction(['F11'], 'Press F11 key', 'Function'),
            'f12': CommandAction(['F12'], 'Press F12 key', 'Function'),
        }

        # Media commands (if supported)
        media_commands = {
            'playpause': CommandAction(['XF86AudioPlay'], 'Play/Pause media', 'Media'),
            'next': CommandAction(['XF86AudioNext'], 'Next track', 'Media'),
            'previous': CommandAction(['XF86AudioPrev'], 'Previous track', 'Media'),
            'mute': CommandAction(['XF86AudioMute'], 'Mute audio', 'Media'),
            'volumedown': CommandAction(['XF86AudioLowerVolume'], 'Volume down', 'Media'),
            'volumeup': CommandAction(['XF86AudioRaiseVolume'], 'Volume up', 'Media'),
        }

        # Register all commands
        self.commands.update(basic_commands)
        self.commands.update(nav_commands)
        self.commands.update(system_commands)
        self.commands.update(function_commands)
        self.commands.update(media_commands)

    def register_command(self,
                        name: str,
                        keys: List[str],
                        description: str,
                        category: str = "Custom"):
        """Register a new command"""
        command = CommandAction(
            keys=keys,
            description=description,
            category=category,
            custom=True
        )
        self.commands[name.lower()] = command
        logger.info(f"Registered custom command: '{name}' -> {keys}")

    def unregister_command(self, name: str):
        """Unregister a command (only custom commands)"""
        name_lower = name.lower()
        if name_lower in self.commands and self.commands[name_lower].custom:
            del self.commands[name_lower]
            logger.info(f"Unregistered custom command: '{name}'")
            return True
        return False

    def get_command(self, name: str) -> Optional[CommandAction]:
        """Get command by name"""
        return self.commands.get(name.lower())

    def find_matching_command(self, spoken_command: str) -> Optional[CommandAction]:
        """Find command that best matches spoken input"""
        spoken_lower = spoken_command.lower().strip()

        # Direct match
        if spoken_lower in self.commands:
            return self.commands[spoken_lower]

        # Fuzzy matching for common variations
        variations = {
            'return': 'enter',
            'returnkey': 'enter',
            'spacebar': 'space',
            'space key': 'space',
            'backspace key': 'backspace',
            'delete key': 'delete',
            'escape key': 'escape',
            'tab key': 'tab',
            'up arrow': 'up',
            'down arrow': 'down',
            'left arrow': 'left',
            'right arrow': 'right',
            'page up': 'pageup',
            'page down': 'pagedown',
            'ctrl c': 'copy',
            'ctrl v': 'paste',
            'ctrl x': 'cut',
            'ctrl s': 'save',
            'ctrl a': 'selectall',
            'control c': 'copy',
            'control v': 'paste',
            'control x': 'cut',
            'control s': 'save',
            'control a': 'selectall',
            'alt f4': 'close',
            'alt f9': 'minimize',
            'alt f10': 'maximize',
        }

        if spoken_lower in variations:
            matched = variations[spoken_lower]
            if matched in self.commands:
                return self.commands[matched]

        # Partial matching
        for cmd_name, command in self.commands.items():
            if cmd_name.startswith(spoken_lower) or spoken_lower.startswith(cmd_name):
                return command

        return None

    def get_commands_by_category(self, category: str) -> List[CommandAction]:
        """Get all commands in a category"""
        return [cmd for cmd in self.commands.values() if cmd.category == category]

    def get_all_categories(self) -> List[str]:
        """Get all available categories"""
        categories = set(cmd.category for cmd in self.commands.values())
        return sorted(list(categories))

    def get_enabled_commands(self) -> Dict[str, CommandAction]:
        """Get all enabled commands"""
        return {name: cmd for name, cmd in self.commands.items() if cmd.enabled}

    def enable_command(self, name: str, enabled: bool = True):
        """Enable or disable a command"""
        if name.lower() in self.commands:
            self.commands[name.lower()].enabled = enabled
            logger.info(f"Command '{name}' {'enabled' if enabled else 'disabled'}")
            return True
        return False

    def get_command_suggestions(self, partial: str) -> List[str]:
        """Get command suggestions for partial input"""
        partial_lower = partial.lower()
        suggestions = []

        for name in self.commands.keys():
            if partial_lower in name or name.startswith(partial_lower):
                suggestions.append(name)

        return sorted(suggestions)[:10]  # Limit to 10 suggestions

    def export_commands(self) -> Dict[str, Dict]:
        """Export commands configuration"""
        return {
            name: {
                'keys': cmd.keys,
                'description': cmd.description,
                'category': cmd.category,
                'enabled': cmd.enabled,
                'custom': cmd.custom
            }
            for name, cmd in self.commands.items()
        }

    def import_commands(self, commands_data: Dict[str, Dict]):
        """Import commands configuration"""
        for name, data in commands_data.items():
            if data.get('custom', False):
                self.register_command(
                    name=name,
                    keys=data['keys'],
                    description=data['description'],
                    category=data.get('category', 'Custom')
                )
                if not data.get('enabled', True):
                    self.enable_command(name, False)
