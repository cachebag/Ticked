#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

function print_header() {
    echo -e "\n${BLUE}$1${NC}"
}

function run_formatter() {
    print_header "📏 Checking code formatting with Black..."
    black --check . || echo -e "${YELLOW}Black formatting issues found${NC}"
}

function run_linters() {
    print_header "🔎 Linting with Ruff..."
    ruff check . || echo -e "${YELLOW}Ruff issues found${NC}"
    
    print_header "📦 Checking import sorting with isort..."
    isort --check-only --profile black . || echo -e "${YELLOW}Import sorting issues found${NC}"
    
    print_header "✅ Type checking with mypy..."
    mypy . || echo -e "${YELLOW}Mypy issues found${NC}"
    
    print_header "🔬 Running Pylint (errors and warnings)..."
    pylint --rcfile=pyproject.toml --disable=all --enable=error,warning --jobs=4 --recursive=y ticked/ || echo -e "${YELLOW}Pylint issues found${NC}"
}

function run_security() {
    print_header "🔐 Running security checks with Bandit..."
    bandit -r . -c pyproject.toml || echo -e "${YELLOW}Security issues found${NC}"
    
    if [ -f "security_scan.py" ]; then
        print_header "🔒 Running custom security scan..."
        chmod +x security_scan.py
        ./security_scan.py || echo -e "${YELLOW}Security scan issues found${NC}"
    fi
}

function run_tests() {
    print_header "🧪 Running pytest..."
    
    pip install -q pytest pytest-asyncio pytest-cov
    pip install -q -e .[test]
    
    print_header "Running database, utils, and system stats tests..."
    python -m pytest tests/test_database.py tests/test_utils.py tests/test_system_stats.py -v
    
    print_header "Running TUI tests (nest module)..."
    export PYTEST_RUNNING=1
    export TERM=xterm-256color
    python -m pytest tests/test_nest.py -v
    
    print_header "Running remaining tests with coverage..."
    python -m pytest --cov=ticked --cov-report=term
}

function install_dependencies() {
    print_header "📦 Installing development dependencies..."
    pip install -q black ruff isort mypy bandit pylint pytest pytest-asyncio pytest-cov
}

function show_help() {
    echo "Usage: $0 [format|lint|security|test|all|install]"
    echo "  format:   Check code formatting with Black"
    echo "  lint:     Run all linters (Ruff, isort, mypy, Pylint)"
    echo "  security: Run security checks (Bandit, custom scans)"
    echo "  test:     Run test suite with pytest"
    echo "  all:      Run all checks"
    echo "  install:  Install development dependencies"
    exit 1
}

case "$1" in
    format)
        run_formatter
        ;;
    lint)
        run_formatter
        run_linters
        ;;
    security)
        run_security
        ;;
    test)
        run_tests
        ;;
    all)
        echo -e "${BLUE}🔍 Running all checks...${NC}"
        run_formatter
        run_linters
        run_security
        run_tests
        echo -e "${GREEN}✨ All checks completed!${NC}"
        ;;
    install)
        install_dependencies
        ;;
    *)
        show_help
        ;;
esac
