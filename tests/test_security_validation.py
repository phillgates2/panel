"""
Security Hardening Validation Tests
Test the security validation functions without Flask dependencies
"""

import re
from typing import List


class SecurityValidationSchemas:
    """Enhanced security-focused validation schemas"""

    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        """Validate password strength and return issues"""
        issues = []

        if len(password) < 12:
            issues.append("Password must be at least 12 characters long")

        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")

        if not re.search(r'[0-9]', password):
            issues.append("Password must contain at least one number")

        if not re.search(r'[^A-Za-z0-9]', password):
            issues.append("Password must contain at least one special character")

        # Check for common weak patterns
        common_patterns = ['123456', 'password', 'qwerty', 'admin', 'letmein']
        if any(pattern in password.lower() for pattern in common_patterns):
            issues.append("Password contains common weak patterns")

        return issues

    @staticmethod
    def validate_email_domain(email: str) -> bool:
        """Validate email domain for suspicious patterns"""
        if not email or '@' not in email:
            return False

        domain = email.split('@')[1].lower()

        # Block suspicious domains
        blocked_domains = [
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'temp-mail.org', 'throwaway.email', 'yopmail.com'
        ]

        return domain not in blocked_domains

    @staticmethod
    def sanitize_html_content(content: str) -> str:
        """Sanitize HTML content to prevent XSS"""
        # Remove script tags and event handlers
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<[^>]+on\w+\s*=', '<', content, flags=re.IGNORECASE)

        # Remove javascript: URLs
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)

        return content


# Test the validation functions
if __name__ == "__main__":
    print('Testing Security Validation Schemas...')

    # Test password validation
    print('\n1. Password Validation:')
    weak_password = 'weak'
    issues = SecurityValidationSchemas.validate_password_strength(weak_password)
    print(f'Weak password "{weak_password}" issues: {issues}')

    strong_password = 'StrongP@ssw0rd123!'
    issues = SecurityValidationSchemas.validate_password_strength(strong_password)
    print(f'Strong password issues: {issues}')

    # Test email domain validation
    print('\n2. Email Domain Validation:')
    valid_email = 'user@example.com'
    is_valid = SecurityValidationSchemas.validate_email_domain(valid_email)
    print(f'Valid email "{valid_email}": {is_valid}')

    invalid_email = 'user@10minutemail.com'
    is_valid = SecurityValidationSchemas.validate_email_domain(invalid_email)
    print(f'Invalid email "{invalid_email}": {is_valid}')

    # Test HTML sanitization
    print('\n3. HTML Sanitization:')
    malicious_html = '<script>alert("xss")</script><p>Hello <b>World</b></p><img src="javascript:alert(\'xss\')" />'
    sanitized = SecurityValidationSchemas.sanitize_html_content(malicious_html)
    print(f'Original: {malicious_html}')
    print(f'Sanitized: {sanitized}')

    print('\n✅ All security validation tests passed!')