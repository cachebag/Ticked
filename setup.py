from setuptools import setup, find_packages

setup(
    name="assignment_tracker",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "psutil>=5.9.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "assignment-tracker=main:run",
        ],
    },
)
