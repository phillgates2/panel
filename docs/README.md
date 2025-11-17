# Panel Documentation

Welcome to the Panel documentation! This directory contains comprehensive guides and references for using and developing Panel.

## 📚 Documentation Index

### User Guides
- **[Database Management Guide](DATABASE_MANAGEMENT.md)** - Complete guide to using the integrated database manager
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Solutions to common issues and problems

### Developer Documentation  
- **[API Documentation](API_DOCUMENTATION.md)** - REST API reference and examples
- **[Development Guide](../README_DEV.md)** - Development setup and contributing guidelines
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute to Panel

### System Administration
- **[README](../README.md)** - Main documentation with installation and configuration
- **[Changelog](../CHANGELOG.md)** - Version history and changes

## 🚀 Quick Start

### For Users
1. [Install Panel](../README.md#quick-start)
2. [Access Database Manager](DATABASE_MANAGEMENT.md#accessing-the-database-manager)
3. [Learn SQL Basics](DATABASE_MANAGEMENT.md#common-tasks)

### For Developers
1. [Setup Development Environment](../README_DEV.md)
2. [Read API Documentation](API_DOCUMENTATION.md)
3. [Run Tests](../README_DEV.md#testing)
4. [Submit Pull Request](../CONTRIBUTING.md)

### For Administrators
1. [Production Installation](../README.md#production-installation)
2. [Security Configuration](DATABASE_MANAGEMENT.md#security-features)
3. [Backup Procedures](TROUBLESHOOTING.md#backup-and-recovery)
4. [Monitoring Setup](../README.md#monitoring)

## 📖 Learning Path

### Beginner
1. Install Panel with `--sqlite-only` option
2. Create admin account
3. Explore the web interface
4. Try basic database queries

### Intermediate
1. Set up MariaDB for production
2. Configure Nginx and SSL
3. Use the API for automation
4. Create custom queries and exports

### Advanced
1. Develop custom integrations
2. Contribute to the codebase
3. Optimize performance
4. Deploy in Docker/Kubernetes

## 🔍 Finding Information

### Search Tips
- Use Ctrl+F to search within documents
- Check the troubleshooting guide first for errors
- Review API docs for programmatic access
- See README_DEV.md for development questions

### Common Topics

| Topic | Document | Section |
|-------|----------|---------|
| Installation | README.md | Quick Start |
| Database Queries | DATABASE_MANAGEMENT.md | SQL Query Interface |
| API Usage | API_DOCUMENTATION.md | Examples |
| Error Messages | TROUBLESHOOTING.md | Common Issues |
| Development Setup | README_DEV.md | Installation |
| Contributing | CONTRIBUTING.md | Pull Requests |

## 💡 Examples

### Database Query Example
```sql
-- Count users by role
SELECT role, COUNT(*) as count 
FROM user 
GROUP BY role 
ORDER BY count DESC;
```

### API Example
```python
import requests

# Execute query via API
response = requests.post('http://localhost:8080/admin/database/query', 
    json={'query': 'SELECT * FROM user LIMIT 5'},
    cookies=session_cookies
)
print(response.json())
```

### Docker Example
```bash
# Run Panel in development mode
docker-compose -f docker-compose.dev.yml up
```

## 🆘 Getting Help

### Troubleshooting Steps
1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Search [GitHub Issues](https://github.com/phillgates2/panel/issues)
3. Review application logs
4. Ask in GitHub Discussions

### Reporting Bugs
1. Check if issue already exists
2. Collect debug information
3. Create detailed issue report
4. Include steps to reproduce

### Feature Requests
1. Search existing requests
2. Describe the feature
3. Explain the use case
4. Open GitHub issue with `enhancement` label

## 📝 Documentation Standards

When contributing documentation:
- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Test all commands and code
- Follow Markdown best practices
- Keep TOC updated

## 🔄 Updates

Documentation is updated with each release. Check:
- [CHANGELOG.md](../CHANGELOG.md) for version changes
- GitHub commits for latest updates
- Release notes for new features

## 📋 Checklist for New Users

- [ ] Read main README
- [ ] Install Panel
- [ ] Create admin account  
- [ ] Access database manager
- [ ] Read database management guide
- [ ] Try example queries
- [ ] Set up backups
- [ ] Review security settings
- [ ] Bookmark documentation
- [ ] Join GitHub community

## 🎯 Next Steps

- **New Users**: Start with [Database Management Guide](DATABASE_MANAGEMENT.md)
- **Developers**: Read [API Documentation](API_DOCUMENTATION.md)
- **Admins**: Review [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Contributors**: See [Contributing Guide](../CONTRIBUTING.md)

---

**Need help?** Open an issue on [GitHub](https://github.com/phillgates2/panel/issues)
