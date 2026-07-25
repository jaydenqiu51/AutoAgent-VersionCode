"""Setup script for the AI Coding Agent Framework."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aicoder",
    version="0.1.0",
    author="Jayden Qiu",
    description="A modular AI coding agent framework with pluggable LLMs and extensible tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jaydenqiu51/Ai-Coding-Agent-Framework",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.30.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "aicoder=aicoder.cli:main",
        ],
    },
)
