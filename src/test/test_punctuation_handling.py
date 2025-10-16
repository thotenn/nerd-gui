#!/usr/bin/env python3
"""
Test script to verify punctuation handling in keyword detection.
Tests that keywords with punctuation (commas, periods, etc.) are properly detected.
"""

import sys
from pathlib import Path

# Add project root to path (now we're in src/test, go up to project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from backends.whisper.keyword_detector import KeywordDetector

print("="*60)
print("Punctuation Handling Test")
print("="*60)
print()

# Initialize detector with lowercase keyword
detector = KeywordDetector(keyword="tony", timeout_seconds=3.0)

# Test cases with various punctuation
test_cases = [
    ("tony enter", True, "enter", "Normal: keyword + command"),
    ("tony, enter", True, "enter", "Comma after keyword with space"),
    ("tony,enter", True, "enter", "Comma after keyword no space"),
    ("tony. enter", True, "enter", "Period after keyword with space"),
    ("tony.enter", True, "enter", "Period after keyword no space"),
    ("tony! enter", True, "enter", "Exclamation after keyword"),
    ("tony? enter", True, "enter", "Question mark after keyword"),
    ("tony; enter", True, "enter", "Semicolon after keyword"),
    ("tony: enter", True, "enter", "Colon after keyword"),
    ("Tony, Enter", True, "enter", "Capitals + comma + both words"),
    ("TONY, ENTER", True, "enter", "Uppercase + comma + both words"),
    ("tony,", True, None, "Keyword + comma only (no command)"),
    ("tony.", True, None, "Keyword + period only"),
    ("hello, world", False, None, "No keyword, just comma"),
]

print("Testing keyword detection with punctuation:")
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
    print("Punctuation handling works correctly.")
    print("Commands with commas, periods, etc. are detected properly.")
else:
    print("❌ Some tests FAILED!")
    print()
    print("Punctuation after the keyword is causing detection issues.")
    print("Need to strip punctuation in addition to whitespace.")

print("="*60)
