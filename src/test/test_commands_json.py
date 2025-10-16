#!/usr/bin/env python3
"""
Test script for voice commands JSON functionality
"""

import sys
import json
from pathlib import Path

# Add src to path (go up to src directory)
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from backends.whisper.command_registry import CommandRegistry

def test_commands_json():
    """Test voice commands JSON workflow"""
    print("=" * 70)
    print("Testing Voice Commands JSON System")
    print("=" * 70)
    print()

    # Initialize database
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "dictation_test.db"
    print(f"1. Initializing test database: {db_path}")
    db = Database(db_path=str(db_path))
    db.initialize()
    print("   ✓ Database initialized")
    print()

    # Test 1: Load default commands
    print("2. Testing CommandRegistry with default commands...")
    registry = CommandRegistry(database=db)
    print(f"   ✓ Loaded {len(registry.commands)} commands")
    print(f"   ✓ Categories: {registry.get_all_categories()}")
    print()

    # Test 2: Export commands to JSON
    print("3. Testing export to JSON...")
    json_output = registry.export_commands_json()
    commands_dict = json.loads(json_output)
    print(f"   ✓ Exported {len(commands_dict)} commands")
    print(f"   ✓ Sample command 'enter': {commands_dict.get('enter', 'NOT FOUND')}")
    print()

    # Test 3: Save to database
    print("4. Testing save to database...")
    db.save_commands_json(json_output)
    print("   ✓ Commands saved to database")
    print()

    # Test 4: Load from database
    print("5. Testing load from database...")
    registry2 = CommandRegistry(database=db)
    print(f"   ✓ Loaded {len(registry2.commands)} commands from database")
    print()

    # Test 5: Modify a command
    print("6. Testing command modification...")
    modified_commands = json.loads(json_output)
    modified_commands['test_command'] = {
        'keys': ['Control_L', 't'],
        'description': 'Test command (Ctrl+T)',
        'category': 'Custom',
        'enabled': True
    }
    modified_json = json.dumps(modified_commands, indent=2)
    print("   ✓ Added custom 'test_command'")
    print()

    # Test 6: Update from modified JSON
    print("7. Testing update from modified JSON...")
    success = registry2.update_from_json(modified_json)
    if success:
        print(f"   ✓ Updated successfully")
        print(f"   ✓ Total commands: {len(registry2.commands)}")
        test_cmd = registry2.get_command('test_command')
        if test_cmd:
            print(f"   ✓ Found test_command: {test_cmd.description}")
        else:
            print("   ✗ test_command not found!")
    else:
        print("   ✗ Update failed!")
    print()

    # Test 7: Reset to defaults
    print("8. Testing reset to defaults...")
    registry2.reset_to_defaults()
    print(f"   ✓ Reset completed")
    print(f"   ✓ Commands after reset: {len(registry2.commands)}")
    test_cmd = registry2.get_command('test_command')
    if not test_cmd:
        print("   ✓ Custom command removed successfully")
    else:
        print("   ✗ Custom command still present!")
    print()

    # Test 8: Verify specific commands
    print("9. Verifying specific commands...")
    test_cmds = ['enter', 'copy', 'paste', 'f5', 'up', 'down']
    all_found = True
    for cmd_name in test_cmds:
        cmd = registry2.get_command(cmd_name)
        if cmd:
            print(f"   ✓ {cmd_name}: {cmd.description} -> {cmd.keys}")
        else:
            print(f"   ✗ {cmd_name}: NOT FOUND")
            all_found = False
    print()

    # Test 9: Test command matching
    print("10. Testing command matching...")
    test_matches = [
        ('enter', 'enter'),
        ('ENTER', 'enter'),
        ('space bar', 'space'),
        ('ctrl c', 'copy'),
        ('control v', 'paste'),
    ]
    for spoken, expected in test_matches:
        matched = registry2.find_matching_command(spoken)
        if matched:
            actual = next((k for k, v in registry2.commands.items() if v == matched), None)
            status = "✓" if actual == expected else "✗"
            print(f"   {status} '{spoken}' -> '{actual}' (expected '{expected}')")
        else:
            print(f"   ✗ '{spoken}' -> NO MATCH (expected '{expected}')")
    print()

    # Cleanup
    print("11. Cleaning up...")
    Path(db_path).unlink(missing_ok=True)
    print("   ✓ Test database deleted")
    print()

    print("=" * 70)
    if all_found:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("=" * 70)

if __name__ == '__main__':
    test_commands_json()
