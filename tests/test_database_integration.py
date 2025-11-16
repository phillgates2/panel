"""
Tests for phpMyAdmin Integration
"""

import pytest
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phpmyadmin_integration import PhpMyAdminIntegration
from db_security import DatabaseSecurity
from db_audit import QueryAuditLog


class TestDatabaseSecurity:
    """Test database security features"""
    
    def test_dangerous_query_detection(self):
        """Test detection of dangerous SQL patterns"""
        dangerous_queries = [
            "DROP DATABASE panel",
            "DROP TABLE users",
            "TRUNCATE TABLE users",
            "DELETE FROM users",
            "UPDATE users SET role='admin'",
            "SELECT * FROM users; DROP TABLE users;--",
        ]
        
        for query in dangerous_queries:
            warnings = DatabaseSecurity.check_dangerous_query(query)
            assert len(warnings) > 0, f"Failed to detect dangerous query: {query}"
    
    def test_read_only_query_detection(self):
        """Test read-only query detection"""
        read_only = [
            "SELECT * FROM users",
            "SHOW TABLES",
            "DESCRIBE users",
            "EXPLAIN SELECT * FROM users",
        ]
        
        read_write = [
            "INSERT INTO users VALUES (1, 'test')",
            "UPDATE users SET name='test'",
            "DELETE FROM users WHERE id=1",
        ]
        
        for query in read_only:
            assert DatabaseSecurity.is_read_only_query(query), f"Failed to identify as read-only: {query}"
        
        for query in read_write:
            assert not DatabaseSecurity.is_read_only_query(query), f"Incorrectly identified as read-only: {query}"
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        user_id = 'test_user_123'
        
        # Should allow first request
        allowed, message = DatabaseSecurity.rate_limit_check(user_id, 'query')
        assert allowed is True
        
        # Simulate hitting rate limit (we need to exceed MAX_QUERIES_PER_MINUTE)
        # First request already done above, so do MAX-1 more to reach limit
        for _ in range(DatabaseSecurity.MAX_QUERIES_PER_MINUTE - 1):
            DatabaseSecurity.rate_limit_check(user_id, 'query')
        
        # Next request should be blocked (exceeds limit)
        allowed, message = DatabaseSecurity.rate_limit_check(user_id, 'query')
        assert allowed is False
        assert 'Rate limit' in message
    
    def test_table_name_sanitization(self):
        """Test table name sanitization"""
        # Valid names
        valid_names = ['users', 'user_data', 'table123', 'my_table_name']
        for name in valid_names:
            assert DatabaseSecurity.sanitize_table_name(name) == name
        
        # Invalid names
        invalid_names = ['users; DROP TABLE', 'table-name', 'table.name', 'table name']
        for name in invalid_names:
            with pytest.raises(ValueError):
                DatabaseSecurity.sanitize_table_name(name)


class TestQueryAuditLog:
    """Test query audit logging"""
    
    def test_audit_log_creation(self, tmp_path):
        """Test audit log file creation"""
        log_dir = str(tmp_path / 'audit_logs')
        audit_log = QueryAuditLog(log_dir=log_dir)
        
        assert os.path.exists(audit_log.log_dir)
        assert os.path.exists(os.path.dirname(audit_log.log_file))
    
    def test_query_logging(self, tmp_path):
        """Test logging queries"""
        log_dir = str(tmp_path / 'audit_logs')
        audit_log = QueryAuditLog(log_dir=log_dir)
        
        audit_log.log_query(
            user_id=1,
            user_email='test@example.com',
            query='SELECT * FROM users',
            success=True,
            execution_time=15.5,
            ip_address='127.0.0.1'
        )
        
        # Verify log was written
        assert os.path.exists(audit_log.log_file)
        
        # Verify log content
        queries = audit_log.get_recent_queries(limit=10)
        assert len(queries) == 1
        assert queries[0]['user_email'] == 'test@example.com'
        assert queries[0]['query_type'] == 'SELECT'
        assert queries[0]['success'] is True
    
    def test_query_type_detection(self, tmp_path):
        """Test query type detection"""
        log_dir = str(tmp_path / 'audit_logs')
        audit_log = QueryAuditLog(log_dir=log_dir)
        
        test_queries = [
            ('SELECT * FROM users', 'SELECT'),
            ('INSERT INTO users VALUES (1)', 'INSERT'),
            ('UPDATE users SET name="test"', 'UPDATE'),
            ('DELETE FROM users WHERE id=1', 'DELETE'),
            ('CREATE TABLE test (id INT)', 'CREATE'),
            ('ALTER TABLE users ADD COLUMN age INT', 'ALTER'),
            ('DROP TABLE test', 'DROP'),
        ]
        
        for query, expected_type in test_queries:
            assert audit_log._get_query_type(query) == expected_type
    
    def test_user_statistics(self, tmp_path):
        """Test user statistics generation"""
        log_dir = str(tmp_path / 'audit_logs')
        audit_log = QueryAuditLog(log_dir=log_dir)
        
        # Log several queries
        for i in range(5):
            audit_log.log_query(
                user_id=1,
                user_email='test@example.com',
                query=f'SELECT * FROM users WHERE id={i}',
                success=True,
                execution_time=10.0 + i
            )
        
        # Log a failed query
        audit_log.log_query(
            user_id=1,
            user_email='test@example.com',
            query='SELECT * FROM nonexistent',
            success=False,
            error='Table not found'
        )
        
        stats = audit_log.get_user_statistics(user_id=1)
        
        assert stats['total_queries'] == 6
        assert stats['successful_queries'] == 5
        assert stats['failed_queries'] == 1
        assert 'SELECT' in stats['query_types']
        assert stats['query_types']['SELECT'] == 6


class TestPhpMyAdminIntegration:
    """Test phpMyAdmin integration (requires test database)"""
    
    @pytest.fixture
    def app_context(self):
        """Create Flask app context for testing"""
        # This would need actual Flask app setup
        pass
    
    def test_database_connection(self):
        """Test database connection"""
        # Set environment for SQLite testing
        os.environ['PANEL_USE_SQLITE'] = '1'
        
        # Would need actual app and db instances
        # This is a placeholder for integration tests
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
