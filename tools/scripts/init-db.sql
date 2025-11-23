-- Database initialization script for Panel application
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_buffercache";

-- Create indexes for better performance
-- These will be created by Alembic migrations, but we include them here for reference

-- Example indexes (will be created by migrations):
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);

-- Set up maintenance and monitoring
-- Vacuum settings for better performance
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_naptime = '20s';
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;

-- Connection settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

-- Logging settings for monitoring
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET log_temp_files = '1MB';

-- Performance monitoring
ALTER SYSTEM SET track_activities = on;
ALTER SYSTEM SET track_counts = on;
ALTER SYSTEM SET track_functions = 'all';
ALTER SYSTEM SET track_io_timing = on;

-- Security settings
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Reload configuration
SELECT pg_reload_conf();