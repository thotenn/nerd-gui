"""
Registry of available voice commands and their keyboard actions.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path
from src.core.logging_controller import info, debug, warning, error, critical


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

    def __init__(self, database=None):
        """
        Initialize command registry.

        Args:
            database: Database instance to load/save commands (optional)
        """
        self.database = database
        self.commands: Dict[str, CommandAction] = {}
        self._load_commands()

    def _load_commands(self):
        """Load commands from database or default JSON file"""
        try:
            # Try to load from database first
            if self.database:
                commands_json = self.database.get_commands_json()
                if commands_json:
                    info("Loading commands from database")
                    self._load_from_json_string(commands_json)
                    return

            # If no database or no saved commands, load defaults
            info("Loading default commands from JSON file")
            self._load_default_commands()

        except Exception as e:
            error(f"Error loading commands: {e}")
            info("Falling back to default commands")
            self._load_default_commands()

    def _load_default_commands(self):
        """Load default commands from JSON file"""
        default_file = self.get_default_commands_path()
        if default_file.exists():
            with open(default_file, 'r') as f:
                commands_data = json.load(f)
                self._load_from_dict(commands_data)
        else:
            error(f"Default commands file not found: {default_file}")

    def _load_from_json_string(self, json_string: str):
        """Load commands from JSON string"""
        commands_data = json.loads(json_string)
        self._load_from_dict(commands_data)

    def _load_from_dict(self, commands_data: Dict):
        """Load commands from dictionary"""
        self.commands.clear()
        for name, data in commands_data.items():
            command = CommandAction(
                keys=data['keys'],
                description=data.get('description', ''),
                category=data.get('category', 'Custom'),
                enabled=data.get('enabled', True),
                custom=data.get('custom', False)
            )
            self.commands[name.lower()] = command
        info(f"Loaded {len(self.commands)} commands")

    @staticmethod
    def get_default_commands_path() -> Path:
        """Get path to default commands JSON file"""
        return Path(__file__).parent / 'default_commands.json'

    def reset_to_defaults(self):
        """Reset commands to default values"""
        info("Resetting commands to defaults")
        self._load_default_commands()

        # Save to database if available
        if self.database:
            commands_json = self.export_commands_json()
            self.database.save_commands_json(commands_json)
            info("Default commands saved to database")

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
        info(f"Registered custom command: '{name}' -> {keys}")

    def unregister_command(self, name: str):
        """Unregister a command (only custom commands)"""
        name_lower = name.lower()
        if name_lower in self.commands and self.commands[name_lower].custom:
            del self.commands[name_lower]
            info(f"Unregistered custom command: '{name}'")
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
            info(f"Command '{name}' {'enabled' if enabled else 'disabled'}")
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
        """Export commands configuration as dictionary"""
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

    def export_commands_json(self, indent=2) -> str:
        """Export commands configuration as JSON string"""
        commands_dict = {}
        for name, cmd in self.commands.items():
            commands_dict[name] = {
                'keys': cmd.keys,
                'description': cmd.description,
                'category': cmd.category,
                'enabled': cmd.enabled
            }
        return json.dumps(commands_dict, indent=indent)

    def update_from_json(self, json_string: str):
        """
        Update commands from JSON string.

        Args:
            json_string: JSON string with commands configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            commands_data = json.loads(json_string)
            self._load_from_dict(commands_data)

            # Save to database if available
            if self.database:
                self.database.save_commands_json(json_string)
                info("Commands updated and saved to database")

            return True
        except json.JSONDecodeError as e:
            error(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            error(f"Error updating commands from JSON: {e}")
            return False

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
