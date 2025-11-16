#!/bin/bash
# Export test database to SQL file

# Add PostgreSQL to PATH (for Mac with Homebrew)
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Export the database
pg_dump -U $(whoami) -h localhost ai_companies_test > databases/ai_companies_test_dump.sql

echo "✓ Database exported to databases/ai_companies_test_dump.sql"
echo ""
echo "To import in another environment:"
echo "createdb ai_companies_test"
echo "psql -U \$(whoami) -d ai_companies_test < databases/ai_companies_test_dump.sql"
