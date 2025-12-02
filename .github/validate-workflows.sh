#!/bin/bash
# Workflow validation and troubleshooting script

set -e

echo "🔍 Panel GitHub Actions Workflow Validator"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements/requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements/requirements.txt not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

echo "📋 Checking Workflow Files..."
echo ""

# Check workflow files exist
WORKFLOWS=(
    ".github/workflows/ci-cd.yml"
    ".github/workflows/code-quality.yml"
    ".github/workflows/security-monitoring.yml"
    ".github/workflows/playwright-e2e.yml"
    ".github/workflows/aws-deploy.yml"
    ".github/workflows/e2e.yml"
    ".github/workflows/release.yml"
    ".github/workflows/dependency-updates.yml"
)

MISSING_WORKFLOWS=0
for workflow in "${WORKFLOWS[@]}"; do
    if [ -f "$workflow" ]; then
        echo -e "${GREEN}✅${NC} $workflow"
    else
        echo -e "${RED}❌${NC} $workflow (missing)"
        MISSING_WORKFLOWS=$((MISSING_WORKFLOWS + 1))
    fi
done

echo ""
echo "📦 Checking Requirements Files..."
echo ""

# Check requirements files
REQUIREMENTS=(
    "requirements/requirements.txt"
    "requirements/requirements-test.txt"
    "requirements/requirements-dev.txt"
    "requirements/requirements-prod.txt"
)

for req in "${REQUIREMENTS[@]}"; do
    if [ -f "$req" ]; then
        echo -e "${GREEN}✅${NC} $req"
    else
        echo -e "${YELLOW}⚠️${NC}  $req (missing, may be optional)"
    fi
done

echo ""
echo "🧪 Checking Test Files..."
echo ""

# Check test directory
if [ -d "tests" ]; then
    TEST_COUNT=$(find tests -name "test_*.py" -o -name "*_test.py" | wc -l)
    echo -e "${GREEN}✅${NC} tests/ directory exists"
    echo -e "${GREEN}✅${NC} Found $TEST_COUNT test files"
    
    if [ -f "tests/__init__.py" ]; then
        echo -e "${GREEN}✅${NC} tests/__init__.py exists"
    else
        echo -e "${YELLOW}⚠️${NC}  tests/__init__.py missing (recommended)"
    fi
    
    if [ -f "tests/conftest.py" ]; then
        echo -e "${GREEN}✅${NC} tests/conftest.py exists"
    else
        echo -e "${YELLOW}⚠️${NC}  tests/conftest.py missing (recommended)"
    fi
else
    echo -e "${RED}❌${NC} tests/ directory missing"
fi

echo ""
echo "⚙️  Checking Configuration Files..."
echo ""

# Check configuration files
CONFIGS=(
    "pytest.ini:pytest configuration"
    ".pre-commit-config.yaml:pre-commit hooks"
    "mypy.ini:mypy type checking"
    "setup.py:package setup (optional)"
    "pyproject.toml:modern Python config (optional)"
)

for config in "${CONFIGS[@]}"; do
    IFS=':' read -r file desc <<< "$config"
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file ($desc)"
    else
        echo -e "${YELLOW}⚠️${NC}  $file ($desc) - missing"
    fi
done

echo ""
echo "🔐 Checking for Secrets (placeholder check)..."
echo ""

# Note: We can't actually check GitHub secrets from local machine
# This is just informational
echo -e "${YELLOW}ℹ️${NC}  Remember to configure these secrets in GitHub:"
echo "   - CODECOV_TOKEN (optional)"
echo "   - DOCKER_USERNAME (for Docker deployment)"
echo "   - DOCKER_PASSWORD (for Docker deployment)"
echo "   - AWS_ACCESS_KEY_ID (for AWS deployment)"
echo "   - AWS_SECRET_ACCESS_KEY (for AWS deployment)"
echo "   - SLACK_WEBHOOK (optional, for notifications)"

echo ""
echo "📊 Summary"
echo "=========="

if [ $MISSING_WORKFLOWS -eq 0 ]; then
    echo -e "${GREEN}✅ All workflow files present${NC}"
else
    echo -e "${RED}❌ $MISSING_WORKFLOWS workflow file(s) missing${NC}"
fi

if [ -d "tests" ] && [ $TEST_COUNT -gt 0 ]; then
    echo -e "${GREEN}✅ Test suite configured${NC}"
else
    echo -e "${RED}❌ Test suite needs setup${NC}"
fi

echo ""
echo "💡 Recommendations:"
echo ""

if [ ! -d "tests" ] || [ $TEST_COUNT -eq 0 ]; then
    echo "1. Create test files in tests/ directory"
fi

if [ ! -f "tests/conftest.py" ]; then
    echo "2. Add tests/conftest.py for pytest configuration"
fi

if [ ! -f ".pre-commit-config.yaml" ]; then
    echo "3. Set up pre-commit hooks for code quality"
fi

echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Review workflow logs: https://github.com/phillgates2/panel/actions"
echo "2. Configure required GitHub secrets in repository settings"
echo "3. Run tests locally: pytest tests/ -v"
echo "4. Check workflow documentation: .github/WORKFLOWS.md"

echo ""
echo "✨ Done!"
