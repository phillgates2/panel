"""
Database Query Audit Log
Tracks all database operations for security and compliance
"""

import os
import json
from datetime import datetime
from pathlib import Path


class QueryAuditLog:
    """Audit logging for database queries"""
    
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or os.path.join(os.getcwd(), 'instance', 'audit_logs')
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, 'query_audit.jsonl')
    
    def log_query(self, user_id, user_email, query, success, execution_time=None, error=None, ip_address=None):
        """Log a database query"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'user_email': user_email,
            'query': query,
            'query_type': self._get_query_type(query),
            'success': success,
            'execution_time_ms': execution_time,
            'error': error,
            'ip_address': ip_address or 'unknown'
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Failed to write audit log: {e}")
    
    def _get_query_type(self, query):
        """Determine query type"""
        query_upper = query.strip().upper()
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        elif query_upper.startswith('CREATE'):
            return 'CREATE'
        elif query_upper.startswith('ALTER'):
            return 'ALTER'
        elif query_upper.startswith('DROP'):
            return 'DROP'
        elif query_upper.startswith('TRUNCATE'):
            return 'TRUNCATE'
        else:
            return 'OTHER'
    
    def get_recent_queries(self, limit=100, user_id=None, query_type=None):
        """Get recent queries from audit log"""
        if not os.path.exists(self.log_file):
            return []
        
        queries = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply filters
                        if user_id and entry.get('user_id') != user_id:
                            continue
                        if query_type and entry.get('query_type') != query_type:
                            continue
                        
                        queries.append(entry)
                    except json.JSONDecodeError:
                        continue
            
            # Return most recent first
            return queries[-limit:][::-1]
        except Exception as e:
            print(f"Failed to read audit log: {e}")
            return []
    
    def get_user_statistics(self, user_id):
        """Get query statistics for a user"""
        queries = self.get_recent_queries(limit=1000, user_id=user_id)
        
        stats = {
            'total_queries': len(queries),
            'successful_queries': sum(1 for q in queries if q['success']),
            'failed_queries': sum(1 for q in queries if not q['success']),
            'query_types': {},
            'avg_execution_time': 0
        }
        
        for query in queries:
            qtype = query.get('query_type', 'OTHER')
            stats['query_types'][qtype] = stats['query_types'].get(qtype, 0) + 1
            
            if query.get('execution_time_ms'):
                stats['avg_execution_time'] += query['execution_time_ms']
        
        if stats['total_queries'] > 0:
            stats['avg_execution_time'] /= stats['total_queries']
        
        return stats
