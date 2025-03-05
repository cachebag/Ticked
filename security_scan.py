#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile


def create_project_requirements():
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".txt"
    ) as temp_file:
        try:
            try:
                import pkg_resources

                dist = pkg_resources.get_distribution("ticked")
                for req in dist.requires():
                    temp_file.write(f"{req}\n")
                return temp_file.name
            except (ImportError, pkg_resources.DistributionNotFound):
                print("Package not installed, trying alternative approach...")

            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"],
                check=True,
                capture_output=True,
            )

            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "ticked"],
                check=True,
                capture_output=True,
                text=True,
            )

            requires = []
            for line in result.stdout.split("\n"):
                if line.startswith("Requires:"):
                    requires = line.replace("Requires:", "").strip()
                    requires = [r.strip() for r in requires.split(",") if r.strip()]
                    break

            for req in requires:
                temp_file.write(f"{req}\n")

            return temp_file.name
        except Exception as e:
            print(f"Error creating requirements file: {e}")
            os.unlink(temp_file.name)
            return None


def run_security_checks(requirements_file):
    print("Running security checks on project dependencies...")

    with open(requirements_file, "r") as f:
        content = f.read().strip()
        if not content:
            print("Warning: Requirements file is empty!")
            return

    print("\n=== PIP-AUDIT RESULTS ===")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "-r",
                requirements_file,
                "--ignore-vuln",
                "GHSA-8495-4g3g-x7pr",
            ],
            check=False,
        )
    except subprocess.SubprocessError as e:
        print(f"Warning: pip-audit encountered an error: {e}")

    print("\n=== SAFETY CHECK RESULTS ===")
    try:
        subprocess.run(
            [sys.executable, "-m", "safety", "check", "-r", requirements_file],
            check=False,
        )
    except subprocess.SubprocessError as e:
        print(f"Warning: safety check encountered an error: {e}")

    print("\n=== BANDIT STATIC ANALYSIS ===")
    try:
        subprocess.run(
            [sys.executable, "-m", "bandit", "-r", "ticked/", "-ll", "-ii"], check=False
        )
    except subprocess.SubprocessError as e:
        print(f"Warning: bandit encountered an error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Run security checks on Ticked dependencies."
    )
    args = parser.parse_args()

    print("Installing security check tools...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pip-audit", "safety", "bandit"],
        check=True,
    )

    requirements_file = create_project_requirements()
    if requirements_file:
        try:
            run_security_checks(requirements_file)
        finally:
            os.unlink(requirements_file)
    else:
        print("Failed to create project requirements file.")
        return 1

    print("\nSecurity checks completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
