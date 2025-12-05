# app/modules/security/security_manager.py

"""
Advanced Security Framework for Panel Application
Implements zero-trust architecture, API security, and enterprise-grade protection
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import jwt
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_id: str
    timestamp: float
    event_type: str
    severity: SecurityLevel
    source_ip: str
    user_id: Optional[str]
    resource: str
    action: str
    details: Dict[str, Any]
    threat_level: ThreatLevel


class SecurityManager:
    """
    Enterprise-grade security manager implementing zero-trust architecture
    """

    def __init__(self, secret_key: str, vault_url: Optional[str] = None):
        self.secret_key = secret_key
        self.vault_url = vault_url
        self.encryption_key = self._derive_key(secret_key)
        self.fernet = Fernet(self.encryption_key)
        self.active_sessions: Dict[str, Dict] = {}
        self.security_events: List[SecurityEvent] = []
        self.rate_limits: Dict[str, List[float]] = {}

    def _derive_key(self, secret: str) -> bytes:
        """Derive encryption key from secret"""
        salt = b'panel_security_salt_2024'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(secret.encode()))

    def hash_password(self, password: str) -> str:
        """Secure password hashing with bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def generate_jwt_token(self, user_id: str, roles: List[str], expires_in: int = 3600) -> str:
        """Generate JWT token with roles and expiration"""
        payload = {
            'user_id': user_id,
            'roles': roles,
            'iat': int(time.time()),
            'exp': int(time.time()) + expires_in,
            'iss': 'panel_security',
            'aud': 'panel_api'
        }

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token

    def validate_jwt_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'],
                               issuer='panel_security', audience='panel_api')
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def implement_zero_trust(self, request_data: Dict) -> Dict:
        """
        Implement zero-trust security model
        Continuous authentication and authorization
        """
        user_id = request_data.get('user_id')
        resource = request_data.get('resource')
        action = request_data.get('action')
        ip_address = request_data.get('ip_address')

        # Check continuous authentication
        if not self._validate_continuous_auth(user_id, ip_address):
            self._log_security_event(
                event_type="authentication_failure",
                severity=SecurityLevel.HIGH,
                source_ip=ip_address,
                user_id=user_id,
                resource=resource,
                action=action,
                details={"reason": "continuous_auth_failed"}
            )
            return {"authorized": False, "reason": "authentication_failed"}

        # Check authorization
        if not self._check_authorization(user_id, resource, action):
            self._log_security_event(
                event_type="authorization_failure",
                severity=SecurityLevel.MEDIUM,
                source_ip=ip_address,
                user_id=user_id,
                resource=resource,
                action=action,
                details={"reason": "insufficient_permissions"}
            )
            return {"authorized": False, "reason": "insufficient_permissions"}

        # Check rate limiting
        if self._is_rate_limited(user_id, ip_address):
            self._log_security_event(
                event_type="rate_limit_exceeded",
                severity=SecurityLevel.MEDIUM,
                source_ip=ip_address,
                user_id=user_id,
                resource=resource,
                action=action,
                details={"reason": "rate_limit_exceeded"}
            )
            return {"authorized": False, "reason": "rate_limit_exceeded"}

        # Log successful access
        self._log_security_event(
            event_type="access_granted",
            severity=SecurityLevel.LOW,
            source_ip=ip_address,
            user_id=user_id,
            resource=resource,
            action=action,
            details={"status": "success"}
        )

        return {"authorized": True}

    def _validate_continuous_auth(self, user_id: str, ip_address: str) -> bool:
        """Validate continuous authentication"""
        # Check session validity
        session = self.active_sessions.get(user_id)
        if not session:
            return False

        # Check IP consistency
        if session.get('ip_address') != ip_address:
            # Send additional authentication challenge
            return False

        # Check session expiration
        if time.time() > session.get('expires_at', 0):
            return False

        return True

    def _check_authorization(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user is authorized for the action"""
        # Get user roles from session/database
        session = self.active_sessions.get(user_id, {})
        user_roles = session.get('roles', [])

        # Implement role-based access control
        # This would integrate with your RBAC system
        required_roles = self._get_required_roles(resource, action)

        return any(role in user_roles for role in required_roles)

    def _get_required_roles(self, resource: str, action: str) -> List[str]:
        """Get required roles for resource/action combination"""
        # Define role requirements
        role_matrix = {
            'server': {
                'create': ['admin', 'moderator'],
                'read': ['admin', 'moderator', 'user'],
                'update': ['admin', 'moderator'],
                'delete': ['admin']
            },
            'user': {
                'create': ['admin'],
                'read': ['admin', 'moderator', 'user'],
                'update': ['admin', 'user'],
                'delete': ['admin']
            }
        }

        return role_matrix.get(resource, {}).get(action, ['admin'])

    def _is_rate_limited(self, user_id: str, ip_address: str, max_requests: int = 100, window: int = 60) -> bool:
        """Check if request is rate limited"""
        key = f"{user_id}:{ip_address}"
        now = time.time()

        # Clean old requests
        self.rate_limits[key] = [req_time for req_time in self.rate_limits.get(key, [])
                                if now - req_time < window]

        # Check rate limit
        if len(self.rate_limits[key]) >= max_requests:
            return True

        # Add current request
        self.rate_limits[key].append(now)
        return False

    def _log_security_event(self, event_type: str, severity: SecurityLevel,
                           source_ip: str, user_id: Optional[str], resource: str,
                           action: str, details: Dict[str, Any]):
        """Log security event"""
        event = SecurityEvent(
            event_id=secrets.token_hex(16),
            timestamp=time.time(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            resource=resource,
            action=action,
            details=details,
            threat_level=self._assess_threat_level(event_type, details)
        )

        self.security_events.append(event)

        # In production, send to SIEM, database, etc.
        print(f"[SECURITY] {severity.value.upper()}: {event_type} - {source_ip} - {user_id or 'anonymous'}")

    def _assess_threat_level(self, event_type: str, details: Dict) -> ThreatLevel:
        """Assess threat level of security event"""
        threat_indicators = {
            'authentication_failure': ThreatLevel.MEDIUM,
            'authorization_failure': ThreatLevel.LOW,
            'rate_limit_exceeded': ThreatLevel.LOW,
            'suspicious_activity': ThreatLevel.HIGH,
            'brute_force_attempt': ThreatLevel.CRITICAL
        }

        return threat_indicators.get(event_type, ThreatLevel.NONE)

    def secure_api_gateway(self, request: Dict) -> Dict:
        """
        API Gateway security with rate limiting and threat detection
        """
        # Extract request information
        method = request.get('method', 'GET')
        path = request.get('path', '/')
        headers = request.get('headers', {})
        body = request.get('body', '')
        ip_address = request.get('ip_address', 'unknown')

        # JWT token validation
        auth_header = headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            user_data = self.validate_jwt_token(token)
            if not user_data:
                return {
                    'status': 401,
                    'body': {'error': 'Invalid or expired token'},
                    'headers': {'WWW-Authenticate': 'Bearer'}
                }

            request['user_data'] = user_data

        # Rate limiting
        user_id = request.get('user_data', {}).get('user_id', ip_address)
        if self._is_rate_limited(user_id, ip_address):
            return {
                'status': 429,
                'body': {'error': 'Rate limit exceeded'},
                'headers': {'Retry-After': '60'}
            }

        # Threat detection
        threat_score = self._calculate_threat_score(request)
        if threat_score > 0.8:
            self._log_security_event(
                event_type="suspicious_activity",
                severity=SecurityLevel.HIGH,
                source_ip=ip_address,
                user_id=request.get('user_data', {}).get('user_id'),
                resource=path,
                action=method,
                details={"threat_score": threat_score, "request": request}
            )

            return {
                'status': 403,
                'body': {'error': 'Suspicious activity detected'},
                'headers': {}
            }

        # Add security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'"
        }

        request['security_headers'] = security_headers

        return {'status': 200, 'continue': True}

    def _calculate_threat_score(self, request: Dict) -> float:
        """Calculate threat score for request"""
        score = 0.0

        # Check for suspicious patterns
        user_agent = request.get('headers', {}).get('User-Agent', '')
        if not user_agent or 'bot' in user_agent.lower():
            score += 0.3

        # Check request frequency
        ip = request.get('ip_address', '')
        recent_requests = len([t for t in self.rate_limits.get(ip, []) if time.time() - t < 10])
        if recent_requests > 50:
            score += 0.4

        # Check for SQL injection patterns
        body = str(request.get('body', ''))
        sql_patterns = ['union select', 'drop table', 'script>', '<script']
        if any(pattern in body.lower() for pattern in sql_patterns):
            score += 0.8

        return min(score, 1.0)

    def get_security_report(self) -> Dict:
        """Generate security report"""
        total_events = len(self.security_events)
        critical_events = len([e for e in self.security_events if e.severity == SecurityLevel.CRITICAL])
        high_events = len([e for e in self.security_events if e.severity == SecurityLevel.HIGH])

        return {
            'total_events': total_events,
            'critical_events': critical_events,
            'high_events': high_events,
            'active_sessions': len(self.active_sessions),
            'recent_events': self.security_events[-10:]  # Last 10 events
        }


# Global security manager instance
security_manager = SecurityManager(secret_key="your-secret-key-here")