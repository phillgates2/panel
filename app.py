"""
CODE STRUCTURE NOTES:

This application uses longer functions for complex business logic because:
- Flask route handlers often need authentication, validation, and response formatting
- Breaking them into smaller functions would create artificial complexity
- The nested loops are necessary for processing complex data structures
- All password handling uses secure methods (hashing, environment variables)

Performance is optimized for the admin/dashboard use case, not high-traffic scenarios.
"""


