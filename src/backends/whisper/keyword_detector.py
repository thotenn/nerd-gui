"""
Keyword detection for voice commands.
Detects activation keywords and switches to command mode.
"""

import time
import re
import string
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from src.core.logging_controller import info, debug, warning, error, critical


class DetectionMode(Enum):
    """Detection state enumeration"""
    NORMAL = "normal"
    COMMAND_ACTIVE = "command_active"


@dataclass
class DetectionResult:
    """Result of keyword detection"""
    detected_keyword: bool
    command_candidate: Optional[str] = None
    remaining_text: Optional[str] = None  # Text after command to be typed
    confidence: float = 0.0
    mode: DetectionMode = DetectionMode.NORMAL


class KeywordDetector:
    """Detects activation keywords in transcribed text"""

    def __init__(self,
                 keyword: str = "tony",
                 timeout_seconds: float = 3.0,
                 sensitivity: str = "normal",
                 language: str = "es",
                 max_command_words: int = 1,
                 command_registry=None):
        """
        Initialize keyword detector.

        Args:
            keyword: Activation word/phrase
            timeout_seconds: Time to wait for command after keyword
            sensitivity: Detection sensitivity (low/normal/high)
            language: Language code
            max_command_words: Maximum words to analyze for command (1-5)
            command_registry: CommandRegistry instance for multi-word lookup
        """
        self.keyword = keyword.lower().strip()
        self.timeout_seconds = timeout_seconds
        self.sensitivity = sensitivity
        self.language = language
        self.max_command_words = max(1, min(5, max_command_words))  # Limit 1-5
        self.command_registry = command_registry

        # State management
        self.current_mode = DetectionMode.NORMAL
        self.keyword_detected_time: Optional[float] = None
        self.last_text = ""

        # Compile regex patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for keyword detection"""
        # Pattern to match keyword (case-insensitive, word boundaries)
        keyword_pattern = r'\b' + re.escape(self.keyword) + r'\b'
        self.keyword_regex = re.compile(keyword_pattern, re.IGNORECASE)

        # Pattern for command detection (single word after keyword)
        self.command_regex = re.compile(r'\b(\w+)\b', re.IGNORECASE)

    def process_text(self, text: str) -> DetectionResult:
        """
        Process transcribed text for keyword detection.

        Args:
            text: Transcribed text from Whisper

        Returns:
            DetectionResult with detection status
        """
        text_clean = text.lower().strip()
        current_time = time.time()

        debug(f"Processing text: '{text_clean}', current mode: {self.current_mode}")

        # Check for command timeout
        if self.current_mode == DetectionMode.COMMAND_ACTIVE:
            if current_time - self.keyword_detected_time > self.timeout_seconds:
                debug("Command timeout, returning to normal mode")
                self._reset_to_normal()
                return DetectionResult(detected_keyword=False, mode=DetectionMode.NORMAL)

        # Check for keyword in normal mode
        if self.current_mode == DetectionMode.NORMAL:
            if self._detect_keyword(text_clean):
                info(f"Keyword detected: '{self.keyword}'")
                self.current_mode = DetectionMode.COMMAND_ACTIVE
                self.keyword_detected_time = current_time

                # Look for command immediately after keyword
                result = self._extract_command_with_remaining(text_clean, after_keyword=True)
                if result and result['command']:
                    return self._process_command(result['command'], result.get('remaining_text'))
                else:
                    return DetectionResult(
                        detected_keyword=True,
                        mode=DetectionMode.COMMAND_ACTIVE,
                        confidence=self._calculate_confidence(text_clean)
                    )

        # Check for command in active mode
        elif self.current_mode == DetectionMode.COMMAND_ACTIVE:
            result = self._extract_command_with_remaining(text_clean, after_keyword=False)
            if result and result['command']:
                return self._process_command(result['command'], result.get('remaining_text'))

        # No detection
        return DetectionResult(detected_keyword=False, mode=self.current_mode)

    def _detect_keyword(self, text: str) -> bool:
        """Detect if keyword is present in text"""
        matches = self.keyword_regex.findall(text)
        return len(matches) > 0

    def _extract_command_with_remaining(self, text: str, after_keyword: bool = False) -> Optional[dict]:
        """
        Extract command and remaining text.

        Args:
            text: Text to process
            after_keyword: If True, extract command after keyword position

        Returns:
            Dictionary with 'command' and 'remaining_text', or None
        """
        if after_keyword:
            # Find keyword position
            keyword_match = self.keyword_regex.search(text)
            if not keyword_match:
                return None

            # Look for command after keyword
            after_keyword_text = text[keyword_match.end():]
            # Strip both whitespace AND punctuation
            after_keyword_text = self._strip_punctuation_and_whitespace(after_keyword_text)

            # Extract command with multi-word support
            return self._extract_multiword_command(after_keyword_text)
        else:
            # Extract from full text
            return self._extract_multiword_command(text)

    def _extract_multiword_command(self, text: str) -> Optional[dict]:
        """
        Extract multi-word command with cascading search.

        Tries to find commands starting with max_command_words, then reducing
        until a match is found or only 1 word remains.

        Args:
            text: Text after keyword

        Returns:
            Dictionary with 'command' and 'remaining_text', or None
        """
        if not text or not self.command_registry:
            # Fallback to single word if no registry
            words = text.split()
            if words:
                return {'command': words[0], 'remaining_text': ' '.join(words[1:]) if len(words) > 1 else None}
            return None

        # Extract words
        words = text.split()
        if not words:
            return None

        # Remove filler words from the beginning
        filler_words = {'um', 'uh', 'eh', 'the', 'a', 'an'}
        while words and words[0].lower() in filler_words:
            words.pop(0)

        if not words:
            return None

        # Try to find command with cascading word count
        # Start with max_command_words, then reduce until match found
        max_words = min(self.max_command_words, len(words))

        for num_words in range(max_words, 0, -1):
            # Build candidate command (join first num_words words)
            command_candidate = ' '.join(words[:num_words]).lower()

            # Check if this command exists in registry
            if self.command_registry.get_command(command_candidate):
                info(f"Found multi-word command: '{command_candidate}' ({num_words} words)")
                remaining_words = words[num_words:]
                remaining_text = ' '.join(remaining_words) if remaining_words else None
                return {
                    'command': command_candidate,
                    'remaining_text': remaining_text
                }

        # No command found - return None (all text will be typed)
        debug(f"No command found in first {max_words} words, text will be typed")
        return None

    def _extract_command(self, text: str) -> Optional[str]:
        """Extract command from text with multi-word support"""
        result = self._extract_multiword_command(text)
        if result and result['command']:
            return result['command']
        return None

    def _process_command(self, command: str, remaining_text: Optional[str] = None) -> DetectionResult:
        """Process detected command"""
        if remaining_text:
            info(f"Command detected: '{command}', remaining text: '{remaining_text}'")
        else:
            info(f"Command detected: '{command}'")
        self._reset_to_normal()

        return DetectionResult(
            detected_keyword=True,
            command_candidate=command,
            remaining_text=remaining_text,
            confidence=self._calculate_confidence(command),
            mode=DetectionMode.NORMAL
        )

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for detection"""
        base_confidence = 0.8

        # Adjust based on sensitivity
        sensitivity_multiplier = {
            'low': 0.9,
            'normal': 1.0,
            'high': 1.1
        }.get(self.sensitivity, 1.0)

        # Adjust based on text clarity (no filler words, clear speech)
        clarity_bonus = 0.1 if len(text.split()) == 1 else 0.0

        confidence = min(1.0, base_confidence * sensitivity_multiplier + clarity_bonus)
        return confidence

    def _strip_punctuation_and_whitespace(self, text: str) -> str:
        """
        Strip leading/trailing punctuation and whitespace from text.
        This ensures "tony, enter" and "tony,enter" work the same as "tony enter".
        """
        # Strip from the left
        while text and (text[0] in string.punctuation or text[0].isspace()):
            text = text[1:]

        # Strip from the right
        while text and (text[-1] in string.punctuation or text[-1].isspace()):
            text = text[:-1]

        return text

    def _reset_to_normal(self):
        """Reset detector to normal mode"""
        self.current_mode = DetectionMode.NORMAL
        self.keyword_detected_time = None

    def is_command_mode_active(self) -> bool:
        """Check if command mode is currently active"""
        return self.current_mode == DetectionMode.COMMAND_ACTIVE

    def get_remaining_timeout(self) -> float:
        """Get remaining time before command timeout"""
        if not self.keyword_detected_time:
            return 0.0

        elapsed = time.time() - self.keyword_detected_time
        remaining = max(0.0, self.timeout_seconds - elapsed)
        return remaining

    def reset(self):
        """Reset detector to initial state"""
        self._reset_to_normal()
        self.last_text = ""

    def update_keyword(self, keyword: str):
        """Update the activation keyword"""
        self.keyword = keyword.lower().strip()
        self._compile_patterns()
        self.reset()
        info(f"Keyword updated to: '{self.keyword}'")

    def update_timeout(self, timeout_seconds: float):
        """Update command timeout"""
        self.timeout_seconds = max(1.0, min(10.0, timeout_seconds))
        info(f"Timeout updated to: {self.timeout_seconds}s")
