#!/bin/bash
set -e

echo "🔍 Running linters and code quality checks..."

echo -e "\n📏 Checking code formatting with Black..."
black --check .

echo -e "\n🔎 Linting with Ruff..."
ruff check .

echo -e "\n📦 Checking import sorting with isort..."
isort --check-only --profile black .

echo -e "\n✅ Type checking with mypy..."
mypy . || true

echo -e "\n🔐 Security checking with Bandit..."
bandit -r . -c pyproject.toml || true

echo -e "\n🔬 Fast Pylint check (errors and warnings only)..."
pylint --rcfile=pyproject.toml --disable=all --enable=error,warning --jobs=4 --recursive=y ticked/ || true

echo -e "\n✨ All checks complete!"
