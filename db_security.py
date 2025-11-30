"""
Database Security Module
Provides security features for database management
"""

import re
import time
from collections import defaultdict, deque
from functools import wraps

from flask import jsonify, request, session


class DatabaseSecurity:
    """Security features for database operations"""

    # Rate limiting storage
    _query_attempts = defaultdict(lambda: deque(maxlen=100))  # Enough to track queries
    _failed_logins = defaultdict(lambda: deque(maxlen=10))

    # Dangerous SQL patterns
    DANGEROUS_PATTERNS = [
        (r"\bDROP\s+DATABASE\b", "DROP DATABASE"),
        (r"\bDROP\s+TABLE\b", "DROP TABLE"),
        (r"\bTRUNCATE\b", "TRUNCATE"),
        (r"\bDELETE\s+FROM\s+\w+\s*(?:WHERE|$)", "DELETE without WHERE"),
        (r"\bUPDATE\s+\w+\s+SET\s+.*?(?:WHERE|$)", "UPDATE without WHERE"),
        (r";\s*DROP\b", "SQL Injection attempt"),
        (r"--\s*$", "SQL comment"),
        (r"/\*.*?\*/", "SQL comment block"),
    ]

    # Query timeout in seconds
    QUERY_TIMEOUT = 30
    MAX_QUERIES_PER_MINUTE = 30
    MAX_FAILED_LOGINS = 5

    @staticmethod
    def check_dangerous_query(query):
        """Check if query contains dangerous patterns"""
        warnings = []
        for pattern, description in DatabaseSecurity.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                warnings.append(description)

        return warnings

    @staticmethod
    def is_read_only_query(query):
        """Check if query is read-only"""
        query_upper = query.strip().upper()
        read_only_keywords = ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "PRAGMA"]
        return any(query_upper.startswith(kw) for kw in read_only_keywords)

    @staticmethod
    def rate_limit_check(user_id, operation="query"):
        """Check rate limiting for user"""
        now = time.time()

        if operation == "query":
            attempts = DatabaseSecurity._query_attempts[user_id]
            # Remove attempts older than 1 minute
            while attempts and now - attempts[0] > 60:
                attempts.popleft()

            if len(attempts) >= DatabaseSecurity.MAX_QUERIES_PER_MINUTE:
                return (
                    False,
                    f"Rate limit exceeded. Maximum {DatabaseSecurity.MAX_QUERIES_PER_MINUTE} queries per minute.",
                )

            attempts.append(now)
            return True, None

        elif operation == "login":
            attempts = DatabaseSecurity._failed_logins[user_id]
            # Remove attempts older than 15 minutes
            while attempts and now - attempts[0] > 900:
                attempts.popleft()

            if len(attempts) >= DatabaseSecurity.MAX_FAILED_LOGINS:
                return False, "Too many failed login attempts. Please try again later."

            return True, None

    @staticmethod
    def record_failed_login(user_id):
        """Record a failed login attempt"""
        DatabaseSecurity._failed_logins[user_id].append(time.time())

    @staticmethod
    def validate_ip_access(allowed_ips=None):
        """Validate IP address against whitelist"""
        if not allowed_ips:
            return True

        client_ip = request.remote_addr
        return client_ip in allowed_ips

    @staticmethod
    def sanitize_table_name(table_name):
        """Sanitize table name to prevent SQL injection"""
        # Only allow alphanumeric characters and underscores
        if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        return table_name

    @staticmethod
    def get_query_hash(query):
        """Get hash of query for tracking"""
        import hashlib

        return hashlib.sha256(query.encode()).hexdigest()


def require_db_admin(f):
    """Decorator to require database admin access"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401

        # Check rate limiting
        allowed, message = DatabaseSecurity.rate_limit_check(
            session["user_id"], "login"
        )
        if not allowed:
            return jsonify({"error": message}), 429

        return f(*args, **kwargs)

    return decorated_function
