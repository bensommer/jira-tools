#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="jira-tools",
    version="1.0.0",
    author="Your Name",
    description="Robust JIRA CLI tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bensommer/jira-tools",
    py_modules=['jira_client', 'jira_cli'],
    install_requires=[
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'tabulate>=0.9.0',
    ],
    entry_points={
        'console_scripts': [
            'jira=jira_cli:main',
        ],
    },
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)