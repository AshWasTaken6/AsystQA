"""
Secret Redaction Service
Detects and redacts sensitive information (secrets, PII, credentials) from code
before storage to prevent data leakage.
"""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Pattern, Tuple

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import (
    EmailRecognizer,
    PhoneRecognizer,
)
from presidio_anonymizer import AnonymizerEngine
from utils.logger import get_logger

logger = get_logger(__name__)


# ============== Secret Categories ==============

class SecretType(str, Enum):
    """Types of secrets that can be detected"""
    API_KEY = "api_key"
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"
    TOKEN = "token"
    SECRET = "secret"
    CREDENTIAL = "credential"
    DATABASE_URL = "database_url"
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    GCP_SERVICE_KEY = "gcp_service_key"
    AZURE_CONNECTION_STRING = "azure_connection_string"
    BEARER_TOKEN = "bearer_token"
    JWT_SECRET = "jwt_secret"
    COOKIE_SECRET = "cookie_secret"
    SESSION_KEY = "session_key"
    ENCRYPTION_KEY = "encryption_key"


@dataclass
class SecretDetection:
    """Detected secret with metadata"""
    secret_type: SecretType
    value: str  # The captured secret value
    line: int
    match_start: int  # Start position of full match in line
    match_end: int   # End position of full match
    confidence: float
    redacted_value: str
    original_text: str


# ============== Custom Regex Patterns ==============

CUSTOM_PATTERNS: Dict[SecretType, Pattern] = {
    SecretType.API_KEY: re.compile(
        # Match api_key, API_KEY, api-key, apikey, api_token with value length >= 5
        r'(?i)(api[_-]?key|apikey|api_token)["\s]*[:=]["`\s]*([\'"]?[a-zA-Z0-9_\-]{5,}[\'"]?)'
    ),
    SecretType.PASSWORD: re.compile(
        r'(?i)(password|passwd|pwd)["\s]*[:=]["`\s]*([\'"]?[^\'"\s]{3,}[\'"]?)'
    ),
    SecretType.PRIVATE_KEY: re.compile(
        r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY-----'
    ),
    SecretType.TOKEN: re.compile(
        r'(?i)(access_token|auth_token|token|bearer)["\s]*[:=]["`\s]*([\'"]?(?:Bearer\s+)?[a-zA-Z0-9_\-\.]{5,}[\'"]?)'
    ),
    SecretType.CREDENTIAL: re.compile(
        r'(?i)(^|\s)(key)["\s]*[:=]["`\s]*([\'"]?[a-zA-Z0-9_\-]{5,}[\'"]?)'
    ),
    SecretType.SECRET: re.compile(
        r'(?i)(secret|client_secret)["\s]*[:=]["`\s]*([\'"]?[a-zA-Z0-9_\-]{5,}[\'"]?)'
    ),
    SecretType.AWS_ACCESS_KEY: re.compile(r'(?i)AKIA[0-9A-Z]{16}'),
    SecretType.AWS_SECRET_KEY: re.compile(
        r'(?i)aws(.?)secret(.?)access(.?)key["\s]*[:=]["`\s]*([\'"]?[a-zA-Z0-9/+=]{20,}[\'"]?)'
    ),
    SecretType.BEARER_TOKEN: re.compile(r' bearer [a-zA-Z0-9_\-\.]{5,}'),
    SecretType.JWT_SECRET: re.compile(
        r'(?i)(jwt|jsonwebtoken)["\s]*[:=]["`\s]*([\'"]?[a-zA-Z0-9_\-]{10,}[\'"]?)'
    ),
}

# Hardcoded credential patterns
HARDCODED_CRED_PATTERNS = [
    (re.compile(r'(?i)password\s*=\s*["\'][^"\']{8,}["\']'), SecretType.PASSWORD),
    (re.compile(r'(?i)api_key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']'), SecretType.API_KEY),
    (re.compile(r'(?i)token\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']'), SecretType.TOKEN),
    (re.compile(r'(?i)secret\s*=\s*["\'][a-zA-Z0-9_\-]{16,}["\']'), SecretType.SECRET),
]


# ============== PII Recognizers ==============

class CustomEmailRecognizer(EmailRecognizer):
    """Custom email recognizer with higher confidence threshold"""
    pass


class CustomPhoneRecognizer(PhoneRecognizer):
    """Custom phone recognizer"""
    pass


# ============== Redaction Service ==============

class SecretRedactor:
    """
    Detects and redacts secrets from code/text.
    Uses both regex patterns and NLP-based PII detection (Presidio).
    Maintains mapping for potential restoration under authorization.
    """

    def __init__(
        self,
        use_presidio: bool = True,
        enable_custom_patterns: bool = True,
        enable_pii_detection: bool = False  # PII less common in code
    ):
        self.use_presidio = use_presidio
        self.enable_custom_patterns = enable_custom_patterns
        self.enable_pii_detection = enable_pii_detection

        # Initialize Presidio
        if use_presidio:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()

            # Add custom recognizers
            self.analyzer.registry.add_recognizer(CustomEmailRecognizer())
            self.analyzer.registry.add_recognizer(CustomPhoneRecognizer())
            # Add more custom recognizers as needed

        # Storage for redaction mapping (encrypted in production)
        self._redaction_map: Dict[str, Dict[str, str]] = {}

    def detect_secrets(
        self,
        text: str,
        language: str = "generic"
    ) -> List[SecretDetection]:
        """
        Scan text for secrets using multiple detection methods.

        Args:
            text: Input code or text to scan
            language: Programming language for language-specific patterns

        Returns:
            List of detected secrets with metadata
        """
        detections: List[SecretDetection] = []

        # Method 1: Custom regex patterns
        if self.enable_custom_patterns:
            detections.extend(self._detect_with_regex(text))

        # Method 2: Presidio NLP for PII
        if self.use_presidio and self.enable_pii_detection:
            detections.extend(self._detect_with_presidio(text))

        # Method 3: Language-specific patterns
        detections.extend(self._detect_language_specific(text, language))

        # Deduplicate overlapping detections
        detections = self._deduplicate_detections(detections)

        logger.info(f"Secret detection found {len(detections)} potential secrets")
        return detections

    def _detect_with_regex(self, text: str) -> List[SecretDetection]:
        """Detect secrets using custom regex patterns"""
        detections = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            for secret_type, pattern in CUSTOM_PATTERNS.items():
                for match in pattern.finditer(line):
                    # The captured secret (group 2)
                    value_group = 3 if secret_type is SecretType.CREDENTIAL else 2
                    value = (
                        match.group(value_group)
                        if match.lastindex and match.lastindex >= value_group
                        else match.group(0)
                    )
                    # Generate redacted placeholder
                    token = hashlib.sha256(value.encode()).hexdigest()[:16]
                    redacted = f"[REDACTED-{secret_type.value}-{token}]"

                    detections.append(SecretDetection(
                        secret_type=secret_type,
                        value=value,
                        line=line_num,
                        match_start=match.start(),
                        match_end=match.end(),
                        confidence=0.9,
                        redacted_value=redacted,
                        original_text=line.strip()
                    ))

        return detections

    def _detect_with_presidio(self, text: str) -> List[SecretDetection]:
        """Detect PII using Presidio"""
        detections = []

        try:
            analyzer_results = self.analyzer.analyze(
                text=text,
                language="en",
                entities=[
                    "EMAIL_ADDRESS", "PHONE_NUMBER", "IP_ADDRESS",
                    "CREDIT_CARD", "US_SSN", "URL"
                ]
            )

            for result in analyzer_results:
                line_num = text[:result.start].count('\n') + 1
                detections.append(SecretDetection(
                    secret_type=SecretType.CREDENTIAL,
                    value=text[result.start:result.end],
                    line=line_num,
                    match_start=result.start,
                    match_end=result.end,
                    confidence=result.score,
                    redacted_value="[REDACTED-PII]",
                    original_text=text[max(0, result.start-20):result.end+20]
                ))
        except Exception as e:
            logger.warning(f"Presidio detection failed: {e}")

        return detections

    def _detect_language_specific(
        self,
        text: str,
        language: str
    ) -> List[SecretDetection]:
        """Language-specific secret detection"""
        detections = []

        # Generic environment variable access (any language)
        env_pattern = re.compile(r'(getenv|os\.environ|process\.env)')
        for match in env_pattern.finditer(text):
            line_num = text[:match.start()].count('\n') + 1
            detections.append(SecretDetection(
                secret_type=SecretType.CREDENTIAL,
                value=match.group(0),
                line=line_num,
                match_start=match.start(),
                match_end=match.end(),
                confidence=0.7,
                redacted_value="[REDACTED-ENV]",
                original_text=text[max(0, match.start()-30):match.end()+30]
            ))

        return detections

    def _deduplicate_detections(
        self,
        detections: List[SecretDetection]
    ) -> List[SecretDetection]:
        """Remove overlapping detections, keeping highest confidence"""
        if not detections:
            return []

        # Sort by line then match_start
        sorted_detections = sorted(
            detections,
            key=lambda d: (d.line, d.match_start)
        )

        result = [sorted_detections[0]]
        for detection in sorted_detections[1:]:
            last = result[-1]

            # Check overlap on same line
            if detection.line == last.line and detection.match_start < last.match_end:
                # Overlap - keep higher confidence
                if detection.confidence > last.confidence:
                    result[-1] = detection
            else:
                result.append(detection)

        return result

    def redact_code(
        self,
        code: str,
        language: str = "python"
    ) -> Tuple[str, Dict[str, str]]:
        """
        Redact all secrets from code.

        Args:
            code: Source code to redact
            language: Programming language

        Returns:
            Tuple of (redacted_code, secret_mapping)
            secret_mapping maps redacted tokens to original values (encrypted for storage)
        """
        detections = self.detect_secrets(code, language)
        secret_mapping: Dict[str, str] = {}
        redacted_code = code

        # Apply redactions from end to start to preserve positions
        for detection in reversed(detections):
            token = detection.redacted_value
            secret_mapping[token] = detection.value

            # Replace matched span (from match_start to match_end) with token
            lines = redacted_code.split('\n')
            line_idx = detection.line - 1
            line = lines[line_idx]
            # Replace using the stored match start/end
            new_line = (
                line[:detection.match_start] +
                token +
                line[detection.match_end:]
            )
            lines[line_idx] = new_line
            redacted_code = '\n'.join(lines)

        logger.info(
            f"Redacted {len(detections)} secrets from {len(code)} chars of {language} code"
        )
        return redacted_code, secret_mapping

    def restore_code(
        self,
        redacted_code: str,
        secret_mapping: Dict[str, str],
        authorized_user: bool = False
    ) -> str:
        """
        Restore original code from redacted version.
        Requires authorization to access original secrets.

        Args:
            redacted_code: Code with redaction tokens
            secret_mapping: Mapping of redacted tokens to original values
            authorized_user: Whether user is authorized to see secrets

        Returns:
            Original code if authorized, redacted code otherwise
        """
        if not authorized_user:
            logger.warning("Unauthorized secret restoration attempt blocked")
            return redacted_code

        restored_code = redacted_code
        for token, original in secret_mapping.items():
            restored_code = restored_code.replace(token, original)

        logger.info(f"Restored {len(secret_mapping)} secrets")
        return restored_code


# Global redactor instance
secret_redactor = SecretRedactor()


# ============== Convenience Functions ==============

def redact_secrets(code: str, language: str = "python") -> Tuple[str, Dict[str, str]]:
    """Redact secrets from code"""
    return secret_redactor.redact_code(code, language)


def restore_secrets(
    redacted_code: str,
    secret_map: Dict[str, str],
    authorized: bool = False
) -> str:
    """Restore original code from redacted version"""
    return secret_redactor.restore_code(redacted_code, secret_map, authorized)


def is_suspicious_pattern(code: str) -> List[str]:
    """
    Quick check for obviously suspicious patterns.
    Returns list of warnings, empty if clean.
    """
    warnings = []

    suspicious = [
        "os.system(",
        "subprocess.call(",
        "subprocess.Popen(",
        "exec(",
        "eval(",
        "__import__(",
        "compile(",
    ]

    for pattern in suspicious:
        if pattern in code:
            warnings.append(f"Suspicious function call: {pattern}")

    return warnings
