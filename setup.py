from setuptools import setup, find_packages

setup(
    name="crewai_log_parser",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",   # For DataFrame creation and CSV support
        "pydantic>=2.0.0", # For data validation and settings management
        "pyyaml>=6.0",     # For YAML parsing
        "rich>=13.0.0",    # For prettier CLI table output
    ],
    python_requires=">=3.8",
    description="A CrewAI Log Parser and Analyzer with Task Awareness",
    author="Manav Gupta",
    author_email="manavg@gmail.com",
    url="https://github.com/manavgup/crewai_log_parser",
)
