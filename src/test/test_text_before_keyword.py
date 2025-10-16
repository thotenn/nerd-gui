#!/usr/bin/env python3
"""
Test script to verify that text BEFORE keyword is not lost.
Tests the fix for: "hola que tal tony enter" should write "hola que tal" AND execute "enter"
"""

import sys
from pathlib import Path
import re

# Add project root to path (now we're in src/test, go up to project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from backends.whisper.keyword_detector import KeywordDetector

print("="*60)
print("Text Before Keyword Preservation Test")
print("="*60)
print()

def extract_text_before_keyword(text: str, keyword: str) -> str:
    """
    Helper to extract text before keyword (same logic as in WhisperBackend)
    """
    keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    match = re.search(keyword_pattern, text.lower())

    if match:
        return text[:match.start()].strip()
    return ""

# Initialize detector
detector = KeywordDetector(keyword="tony", timeout_seconds=3.0)

# Test cases
test_cases = [
    # (input_text, should_detect, expected_cmd, expected_text_before)
    ("hola que tal tony enter", True, "enter", "hola que tal"),
    ("hola que tal como estan tony space", True, "space", "hola que tal como estan"),
    ("esto es una prueba tony copy", True, "copy", "esto es una prueba"),
    ("tony enter", True, "enter", ""),  # No text before
    ("solo tony", True, None, "solo"),  # Text before but no command
    ("primera parte tony segunda parte", True, "segunda", "primera parte"),
    ("Tony, enter", True, "enter", ""),  # Capitalized with punctuation
    ("Hola Tony, enter", True, "enter", "Hola"),  # Text + capital + punctuation
    ("hola", False, None, ""),  # No keyword
]

print("Testing that text before keyword is preserved:")
print()

all_passed = True
for text, should_detect, expected_cmd, expected_text_before in test_cases:
    # Test keyword detection
    result = detector.process_text(text.lower())

    # Extract text before keyword
    text_before = extract_text_before_keyword(text, "tony")

    # Check results
    detected = result.detected_keyword
    command = result.command_candidate

    # Normalize for comparison
    if command:
        command = command.lower()
    if expected_cmd:
        expected_cmd = expected_cmd.lower()

    # Verify
    detection_ok = detected == should_detect
    command_ok = command == expected_cmd
    text_before_ok = text_before.lower() == expected_text_before.lower() if expected_text_before else text_before == expected_text_before

    if detection_ok and command_ok and text_before_ok:
        status = "✓ PASS"
    else:
        status = "✗ FAIL"
        all_passed = False

    print(f"{status}: '{text}'")
    if expected_text_before:
        print(f"        Expected text before: '{expected_text_before}'")
        print(f"        Got text before:      '{text_before}'")
    print(f"        Expected: detect={should_detect}, cmd={expected_cmd}")
    print(f"        Got:      detect={detected}, cmd={command}")
    print()

    # Reset detector for next test
    detector.reset()

print("="*60)
if all_passed:
    print("✅ All tests PASSED!")
    print()
    print("Text before keyword is correctly preserved.")
    print("Example: 'hola que tal tony enter' will:")
    print("  1. Write: 'hola que tal'")
    print("  2. Execute: ENTER command")
else:
    print("❌ Some tests FAILED!")
    print()
    print("Text extraction logic needs review.")

print("="*60)
