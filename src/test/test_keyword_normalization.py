#!/usr/bin/env python3
"""
Test script to verify keyword normalization fix.
Tests that keywords with capital letters are properly detected.
"""

import sys
from pathlib import Path

# Add project root to path (now we're in src/test, go up to project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from backends.whisper.keyword_detector import KeywordDetector

print("="*60)
print("Keyword Normalization Test")
print("="*60)
print()

# Initialize detector with lowercase keyword
detector = KeywordDetector(keyword="tony", timeout_seconds=3.0)

# Test cases with various capitalizations
test_cases = [
    ("tony enter", True, "enter", "lowercase keyword + command"),
    ("Tony enter", True, "enter", "Capitalized keyword + command"),
    ("TONY enter", True, "enter", "UPPERCASE keyword + command"),
    ("Tony Enter", True, "enter", "Both capitalized"),
    ("TONY ENTER", True, "enter", "Both uppercase"),
    ("tony", True, None, "lowercase keyword only"),
    ("Tony", True, None, "Capitalized keyword only"),
    ("TONY", True, None, "UPPERCASE keyword only"),
    ("hello world", False, None, "no keyword"),
    ("tonight enter", False, None, "false positive check"),
]

print("Testing keyword detection with various capitalizations:")
print()

all_passed = True
for text, should_detect, expected_cmd, description in test_cases:
    result = detector.process_text(text)

    # Check detection
    detected = result.detected_keyword
    command = result.command_candidate

    # Normalize command for comparison
    if command:
        command = command.lower()
    if expected_cmd:
        expected_cmd = expected_cmd.lower()

    # Verify results
    detection_ok = detected == should_detect
    command_ok = command == expected_cmd

    if detection_ok and command_ok:
        status = "✓ PASS"
    else:
        status = "✗ FAIL"
        all_passed = False

    print(f"{status}: '{text}'")
    print(f"        {description}")
    print(f"        Expected: detect={should_detect}, cmd={expected_cmd}")
    print(f"        Got:      detect={detected}, cmd={command}")
    print()

    # Reset detector for next test
    detector.reset()

print("="*60)
if all_passed:
    print("✅ All tests PASSED!")
    print()
    print("Keyword detection correctly handles all capitalizations.")
    print("The fix ensures 'Tony', 'TONY', 'tony' all work correctly.")
else:
    print("❌ Some tests FAILED!")
    print()
    print("Please check the implementation.")

print("="*60)
