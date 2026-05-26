import re
from typing import Tuple, Dict, List


class PIIValidator:
    """Detect and redact Personally Identifiable Information from resumes."""

    # Patterns for common PII types
    PII_PATTERNS = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}(?:[-.\s]?[0-9]{1,2})?',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'date_of_birth': r'\b(?:DOB|Date of Birth|Born)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        'address': r'\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Circle|Cir)\b',
        'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/[^\s]+',
    }

    @staticmethod
    def detect_pii(text: str) -> Dict[str, List[str]]:
        """
        Find all PII in text.

        Returns:
            Dictionary with PII types as keys and list of matches as values
        """
        found_pii = {}
        for pii_type, pattern in PIIValidator.PII_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Remove duplicates while preserving order
                found_pii[pii_type] = list(dict.fromkeys(matches))
        return found_pii

    @staticmethod
    def redact_pii(text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Remove PII from text and replace with placeholders.

        Returns:
            Tuple of (redacted_text, dict_of_removed_pii)
        """
        redacted_text = text
        removed_pii = {}

        for pii_type, pattern in PIIValidator.PII_PATTERNS.items():
            matches = re.findall(pattern, redacted_text, re.IGNORECASE)
            if matches:
                removed_pii[pii_type] = list(dict.fromkeys(matches))
                placeholder = f"[REDACTED_{pii_type.upper()}]"
                redacted_text = re.sub(
                    pattern,
                    placeholder,
                    redacted_text,
                    flags=re.IGNORECASE
                )

        return redacted_text, removed_pii

    @staticmethod
    def validate_resume(resume_text: str, strict: bool = False) -> Tuple[bool, Dict]:
        """
        Validate resume doesn't contain excessive PII.

        Args:
            resume_text: The resume content to validate
            strict: If True, reject any PII. If False, warn but allow.

        Returns:
            Tuple of (is_valid, info_dict)
        """
        pii_found = PIIValidator.detect_pii(resume_text)

        if strict and pii_found:
            return False, {
                'error': 'Resume contains personal information that should not be included',
                'pii_types': list(pii_found.keys()),
                'pii_details': pii_found,
                'message': 'For privacy protection, please remove: names, emails, phone numbers, addresses, and dates of birth.'
            }

        if pii_found:
            return True, {
                'warning': True,
                'message': 'Resume contains personal information. It will be automatically redacted before analysis.',
                'pii_types': list(pii_found.keys()),
                'pii_details': pii_found
            }

        return True, {'warning': False, 'message': 'No PII detected'}

    @staticmethod
    def get_redaction_report(removed_pii: Dict[str, List[str]]) -> str:
        """
        Generate a human-readable report of what was redacted.

        Returns:
            String report for logging
        """
        if not removed_pii:
            return "No PII was redacted."

        report = "PII Redaction Report:\n"
        for pii_type, items in removed_pii.items():
            count = len(items)
            report += f"  - {pii_type.upper()}: {count} instance(s) redacted\n"
        return report
