# setup.py
from setuptools import setup, find_packages

setup(
    name="ticked",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "tick": [
            "config/*.tcss",
        ],
    },
    install_requires=[
        'textual',
        'python-dotenv',
        'spotipy',
        'redis'
        # Add other dependencies from your requirements.txt
    ],
    entry_points={
        'console_scripts': [
            'tick=src.app:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A terminal-based task management and productivity tool",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/tick",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)