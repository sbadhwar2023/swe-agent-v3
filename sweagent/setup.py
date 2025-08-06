"""
Setup script for SWE Agent
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="sweagent",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A powerful LangGraph-based multi-agent task execution system for software engineering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/sweagent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0", 
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "notebook": [
            "jupyter>=1.0.0",
            "matplotlib>=3.5.0",
        ],
        "analysis": [
            "pandas>=1.5.0",
            "numpy>=1.21.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "sweagent=sweagent.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "sweagent": ["*.yaml", "*.json"],
    },
)