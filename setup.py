from setuptools import setup, find_packages

setup(
    name="crewai_log_parser",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",   # Added for DataFrame creation and CSV support
    ],
    python_requires=">=3.8",
    description="A CrewAI Log Parser and Analyzer",
    author="Manav Gupta",
    author_email="manavg@gmail.com",
    url="https://github.com/manavgup/crewai_log_parser",
)
