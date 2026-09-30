#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="Oculon",
    version="1.0.0",
    description="Oculon: Delhi Hotspots ML Spatiotemporal Crime Forecasting & MCP Server",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Abhyuday Mishra",
    url="https://github.com/abhyudaymishr/Oculon",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "gradio>=5.20.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.30.0",
        "pydantic>=2.0.0",
        "pandas>=2.0.0",
    ],
    package_data={
        "oculon": ["data/*", "maps/*"],
    },
    entry_points={
        "console_scripts": [
            "oculon=oculon.mcp_server:main",
            "oculon-mcp=oculon.mcp_server:main",
            "oculon-app=oculon.app:main",
        ],
    },
)
