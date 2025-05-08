from setuptools import setup, find_packages

setup(
    name="adk-api",
    version="0.1.0",
    description="API for querying using the Agent Development Kit",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic>=2.0.0",
        "pydantic-settings",
        "httpx",
        "python-dotenv",
        "google-adk",  # Google ADK
        "qdrant-client",  # Qdrant client for vector DB operations
        "sentence-transformers",  # For embedding if needed
        "mcp",  # For MCP server support
        "python-multipart",  # For form data parsing
    ],
    entry_points={
        "console_scripts": [
            "adk-api=src.api.main:app"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: FastAPI",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)