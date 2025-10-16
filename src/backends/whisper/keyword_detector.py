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
import logging

logger = logging.getLogger(__name__)


class DetectionMode(Enum):
    """Detection state enumeration"""
    NORMAL = "normal"
    COMMAND_ACTIVE = "command_active"


@dataclass
class DetectionResult:
    """Result of keyword detection"""
    detected_keyword: bool
    command_candidate: Optional[str] = None
    confidence: float = 0.0
    mode: DetectionMode = DetectionMode.NORMAL


class KeywordDetector:
    """Detects activation keywords in transcribed text"""

    def __init__(self,
                 keyword: str = "tony",
                 timeout_seconds: float = 3.0,
                 sensitivity: str = "normal",
                 language: str = "es"):
        """
        Initialize keyword detector.

        Args:
            keyword: Activation word/phrase
            timeout_seconds: Time to wait for command after keyword
            sensitivity: Detection sensitivity (low/normal/high)
            language: Language code
        """
        self.keyword = keyword.lower().strip()
        self.timeout_seconds = timeout_seconds
        self.sensitivity = sensitivity
        self.language = language

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

        logger.debug(f"Processing text: '{text_clean}', current mode: {self.current_mode}")

        # Check for command timeout
        if self.current_mode == DetectionMode.COMMAND_ACTIVE:
            if current_time - self.keyword_detected_time > self.timeout_seconds:
                logger.debug("Command timeout, returning to normal mode")
                self._reset_to_normal()
                return DetectionResult(detected_keyword=False, mode=DetectionMode.NORMAL)

        # Check for keyword in normal mode
        if self.current_mode == DetectionMode.NORMAL:
            if self._detect_keyword(text_clean):
                logger.info(f"Keyword detected: '{self.keyword}'")
                self.current_mode = DetectionMode.COMMAND_ACTIVE
                self.keyword_detected_time = current_time

                # Look for command immediately after keyword
                command = self._extract_command_after_keyword(text_clean)
                if command:
                    return self._process_command(command)
                else:
                    return DetectionResult(
                        detected_keyword=True,
                        mode=DetectionMode.COMMAND_ACTIVE,
                        confidence=self._calculate_confidence(text_clean)
                    )

        # Check for command in active mode
        elif self.current_mode == DetectionMode.COMMAND_ACTIVE:
            command = self._extract_command(text_clean)
            if command:
                return self._process_command(command)

        # No detection
        return DetectionResult(detected_keyword=False, mode=self.current_mode)

    def _detect_keyword(self, text: str) -> bool:
        """Detect if keyword is present in text"""
        matches = self.keyword_regex.findall(text)
        return len(matches) > 0

    def _extract_command_after_keyword(self, text: str) -> Optional[str]:
        """Extract command that appears immediately after keyword"""
        # Find keyword position
        keyword_match = self.keyword_regex.search(text)
        if not keyword_match:
            return None

        # Look for command after keyword
        after_keyword = text[keyword_match.end():]
        # Strip both whitespace AND punctuation
        after_keyword = self._strip_punctuation_and_whitespace(after_keyword)
        command_match = self.command_regex.match(after_keyword)

        if command_match:
            return command_match.group(1)

        return None

    def _extract_command(self, text: str) -> Optional[str]:
        """Extract command from text (assuming it's the first word)"""
        # Remove any common filler words
        filler_words = {'um', 'uh', 'eh', 'the', 'a', 'an'}

        words = text.split()
        for word in words:
            if word not in filler_words and len(word) > 1:
                return word

        return None

    def _process_command(self, command: str) -> DetectionResult:
        """Process detected command"""
        logger.info(f"Command detected: '{command}'")
        self._reset_to_normal()

        return DetectionResult(
            detected_keyword=True,
            command_candidate=command,
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
        logger.info(f"Keyword updated to: '{self.keyword}'")

    def update_timeout(self, timeout_seconds: float):
        """Update command timeout"""
        self.timeout_seconds = max(1.0, min(10.0, timeout_seconds))
        logger.info(f"Timeout updated to: {self.timeout_seconds}s")
