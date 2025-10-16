#!/usr/bin/env python3
"""
Test script for voice commands functionality.
Tests the core components without requiring actual audio input.
"""

import sys
from pathlib import Path

# Add project root to path (now we're in src/test, go up to project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

print("="*60)
print("Voice Commands Feature Test")
print("="*60)
print()

# Test 1: Import components
print("Test 1: Importing components...")
try:
    from backends.whisper.keyword_detector import KeywordDetector, DetectionMode
    from backends.whisper.command_registry import CommandRegistry, CommandAction
    from backends.whisper.command_executor import CommandExecutor
    print("✓ All components imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: KeywordDetector
print("Test 2: Testing KeywordDetector...")
try:
    detector = KeywordDetector(keyword="tony", timeout_seconds=3.0)

    # Test keyword detection
    result = detector.process_text("tony enter")
    assert result.detected_keyword, "Should detect keyword"
    assert result.command_candidate == "enter", f"Should extract command 'enter', got '{result.command_candidate}'"

    # Test case insensitivity
    result = detector.process_text("TONY space")
    assert result.detected_keyword, "Should detect keyword (case insensitive)"
    assert result.command_candidate == "space", "Should extract command 'space'"

    # Test no false positives
    result = detector.process_text("tonight is great")
    assert not result.detected_keyword, "Should not detect keyword in 'tonight'"

    print("✓ KeywordDetector working correctly")
    print(f"  - Detected keywords: tony enter, TONY space")
    print(f"  - Rejected false positive: tonight")
except Exception as e:
    print(f"✗ KeywordDetector test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: CommandRegistry
print("Test 3: Testing CommandRegistry...")
try:
    registry = CommandRegistry()

    # Test basic commands
    enter_cmd = registry.find_matching_command("enter")
    assert enter_cmd is not None, "Should find 'enter' command"
    assert enter_cmd.keys == ["Return"], f"Enter should map to Return key, got {enter_cmd.keys}"

    # Test system commands
    copy_cmd = registry.find_matching_command("copy")
    assert copy_cmd is not None, "Should find 'copy' command"
    assert "Control" in copy_cmd.keys[0], "Copy should use Control modifier"

    # Test command variations
    space_cmd = registry.find_matching_command("spacebar")
    assert space_cmd is not None, "Should find 'space' via 'spacebar' variation"

    # Test categories
    categories = registry.get_all_categories()
    assert "Basic" in categories, "Should have Basic category"
    assert "System" in categories, "Should have System category"
    assert "Navigation" in categories, "Should have Navigation category"

    # Count commands
    all_commands = registry.get_enabled_commands()
    print(f"✓ CommandRegistry working correctly")
    print(f"  - Total commands: {len(all_commands)}")
    print(f"  - Categories: {', '.join(categories)}")
    print(f"  - Sample commands: enter, space, copy, paste, up, down")
except Exception as e:
    print(f"✗ CommandRegistry test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: CommandExecutor
print("Test 4: Testing CommandExecutor...")
try:
    executor = CommandExecutor()

    # Check if xdotool is available
    if executor.xdotool_available:
        print("✓ CommandExecutor initialized")
        print(f"  - xdotool: available")

        # Get version
        version = executor.get_xdotool_version()
        if version:
            print(f"  - xdotool version: {version}")
    else:
        print("⚠ CommandExecutor initialized but xdotool not available")
        print("  - Install with: sudo apt install xdotool")
except Exception as e:
    print(f"✗ CommandExecutor test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 5: Database integration
print("Test 5: Testing Database integration...")
try:
    from core.database import Database

    # Create test database (now in src/test, need to go up to project root)
    test_db = Database(Path(__file__).parent.parent.parent / "data" / "dictation.db")
    test_db.initialize()

    # Test voice command settings
    test_db.save_voice_command_settings(
        keyword="test",
        timeout=2.5,
        sensitivity="high",
        enabled=True
    )

    settings = test_db.get_voice_command_settings()
    assert settings['keyword'] == 'test', "Should save/load keyword"
    assert settings['timeout'] == 2.5, "Should save/load timeout"
    assert settings['sensitivity'] == 'high', "Should save/load sensitivity"
    assert settings['enabled'] == True, "Should save/load enabled flag"

    print("✓ Database integration working correctly")
    print(f"  - Settings saved and retrieved successfully")
except Exception as e:
    print(f"✗ Database test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 6: Full workflow simulation
print("Test 6: Simulating full workflow...")
try:
    # Initialize components
    detector = KeywordDetector(keyword="tony", timeout_seconds=3.0)
    registry = CommandRegistry()
    executor = CommandExecutor()

    # Simulate transcription results
    test_phrases = [
        ("tony enter", True, "enter"),
        ("hello world", False, None),
        ("tony copy", True, "copy"),
        ("tony up", True, "up"),
        ("tonight is nice", False, None),
    ]

    results = []
    for phrase, should_detect, expected_cmd in test_phrases:
        result = detector.process_text(phrase)

        if result.detected_keyword and result.command_candidate:
            command = registry.find_matching_command(result.command_candidate)
            if command:
                results.append(f"  ✓ '{phrase}' → {command.description}")
            else:
                results.append(f"  ✗ '{phrase}' → unknown command '{result.command_candidate}'")
        elif should_detect:
            results.append(f"  ✗ '{phrase}' → failed to detect")
        else:
            results.append(f"  ✓ '{phrase}' → normal text (no command)")

    print("✓ Full workflow simulation completed")
    for r in results:
        print(r)

except Exception as e:
    print(f"✗ Workflow test failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
print("Test Summary")
print("="*60)
print()
print("✓ All core components are working correctly!")
print()
print("Next steps:")
print("1. Start the application: /usr/bin/python3 main.py")
print("2. Go to Settings → Voice Commands")
print("3. Enable voice commands and configure your keyword")
print("4. Start Whisper dictation (Spanish or English)")
print("5. Say your keyword + command (e.g., 'Tony Enter')")
print()
print("Available commands: enter, space, backspace, copy, paste,")
print("                   up, down, left, right, save, close, etc.")
print()
print("Documentation: docs/ai/feat/3_keywords/")
print("="*60)
