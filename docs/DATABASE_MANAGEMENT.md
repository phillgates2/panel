# Database Management Guide

## Accessing the Database Manager

1. Login to Panel with admin credentials
2. Navigate to **Admin Tools** from the main menu
3. Click on **🗄️ Database Manager**

## Features

### 📊 Database Browser
- View all database tables
- See table structure (columns, types, constraints)
- Browse table data with pagination
- Quick statistics (row counts, table sizes)

### 📝 SQL Query Interface
Execute custom SQL queries directly:

```sql
-- View all users
SELECT * FROM user LIMIT 10;

-- Count records
SELECT COUNT(*) as total FROM user;

-- Join queries
SELECT s.*, u.email
FROM server s
JOIN user u ON s.owner_id = u.id;
```

### 📤 Data Export
- Export individual tables as CSV
- Preserve NULL values and formatting
- Download directly to your computer

### 🔒 Security Features
- Admin-only access (system_admin or server_admin)
- Query validation with dangerous operation warnings
- Rate limiting (30 queries per minute)
- Query timeout protection (30 seconds)
- Audit logging of all queries

## Common Tasks

### View Database Tables
For SQLite:
```sql
SELECT name FROM sqlite_master WHERE type='table';
```

For MySQL/MariaDB:
```sql
SHOW TABLES;
```

### View Table Structure
For SQLite:
```sql
PRAGMA table_info(table_name);
```

For MySQL/MariaDB:
```sql
DESCRIBE table_name;
```

### Count Records
```sql
SELECT COUNT(*) as count FROM table_name;
```

### Export Data
1. Navigate to the table
2. Click "Export as CSV"
3. File downloads automatically

## Safety Guidelines

### ⚠️ Dangerous Operations
The system will warn you about:
- `DROP DATABASE` - Deletes entire database
- `DROP TABLE` - Deletes a table
- `TRUNCATE` - Removes all rows
- `DELETE` without WHERE - Deletes all records
- `UPDATE` without WHERE - Updates all records

### ✅ Best Practices
1. **Always backup before modifications**
   - Export tables before UPDATE/DELETE
   - Use transactions for complex changes

2. **Test queries on small datasets**
   ```sql
   -- Test with LIMIT first
   SELECT * FROM users WHERE status='inactive' LIMIT 5;

   -- Then run the actual operation
   DELETE FROM users WHERE status='inactive';
   ```

3. **Use WHERE clauses**
   ```sql
   -- Good
   UPDATE users SET status='active' WHERE id=123;

   -- Dangerous (updates ALL rows)
   UPDATE users SET status='active';
   ```

4. **Check affected rows**
   - Review the query result message
   - Verify row count before/after operations

## Query History
Your last 10 queries are automatically saved:
- Access from the Query History tab
- Re-run previous queries with one click
- Review execution times and results

## Troubleshooting

### Query Timeout
If your query times out (> 30 seconds):
- Add WHERE clauses to limit rows
- Add LIMIT to restrict result size
- Use indexes on searched columns

### Rate Limit Exceeded
Maximum 30 queries per minute:
- Wait 60 seconds and try again
- Optimize queries to reduce count
- Use batch operations where possible

### Permission Denied
Database manager requires admin access:
- System admin role
- Server admin role
- Contact your administrator

### Connection Errors
If database connection fails:
- Check database service status
- Verify credentials in configuration
- Review application logs

## Advanced Features

### Query Execution Time
All queries display execution time in milliseconds:
- Helps identify slow queries
- Optimize based on timing data

### Syntax Highlighting
SQL keywords are highlighted automatically:
- Improves readability
- Helps catch syntax errors

### Auto-Complete
Start typing to see suggestions:
- Table names
- Column names
- SQL keywords

## Keyboard Shortcuts

- `Ctrl+Enter` - Execute query
- `Ctrl+/` - Comment/uncomment line
- `Ctrl+D` - Duplicate line
- `Ctrl+Z` - Undo
- `Ctrl+Shift+F` - Format SQL

## Data Import (Coming Soon)
- CSV file import
- SQL file execution
- Drag-and-drop interface
- Column mapping wizard

## Backup & Restore (Coming Soon)
- Scheduled automatic backups
- One-click restore points
- Incremental backups
- Export full database

## Support

For issues or questions:
- Check application logs
- Review audit logs for query history
- Contact system administrator
- GitHub Issues: https://github.com/phillgates2/panel/issues
