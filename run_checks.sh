#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

run_security_checks() {
    echo -e "${BLUE}Running security checks...${NC}"
    
    chmod +x security_scan.py
    
    ./security_scan.py
    
    echo -e "${GREEN}Security checks completed.${NC}"
}

run_lint() {
    echo -e "${BLUE}Running linting checks...${NC}"
    
    pip install black ruff
    
    echo -e "${BLUE}Running black (check only)...${NC}"
    black --check ticked/ || echo -e "${RED}black check failed${NC}"
    
    echo -e "${BLUE}Running ruff...${NC}"
    ruff check ticked/ || echo -e "${RED}ruff check failed${NC}"
    
    echo -e "${GREEN}Linting checks completed.${NC}"
}

run_pytest() {
    echo -e "${BLUE}Running pytest...${NC}"
    
    pip install pytest pytest-asyncio pytest-cov
    pip install -e .[test]
    
    echo -e "${BLUE}Running database, utils, and system stats tests...${NC}"
    python -m pytest tests/test_database.py tests/test_utils.py tests/test_system_stats.py -v
    
    echo -e "${BLUE}Running TUI tests (nest module)...${NC}"
    export PYTEST_RUNNING=1
    export TERM=xterm-256color
    python -m pytest tests/test_nest.py -v
    
    echo -e "${BLUE}Running remaining tests with coverage...${NC}"
    python -m pytest --cov=ticked --cov-report=term
    
    echo -e "${GREEN}Tests completed.${NC}"
}

if [ "$1" == "security" ]; then
    run_security_checks
elif [ "$1" == "lint" ]; then
    run_lint
elif [ "$1" == "pytest" ]; then
    run_pytest
elif [ "$1" == "all" ]; then
    run_security_checks
    run_lint
    run_pytest
    echo -e "${GREEN}All checks completed successfully!${NC}"
else
    echo "Usage: $0 [security|lint|pytest|all]"
    echo "  security: Run security checks using security_scan.py"
    echo "  lint: Run linting tools (black, ruff)"
    echo "  pytest: Run test suite with pytest"
    echo "  all: Run all checks"
    exit 1
fi
