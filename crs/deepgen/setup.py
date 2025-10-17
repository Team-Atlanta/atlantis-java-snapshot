#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name="deepgen",
    version="0.1.0",
    description="Deep Generator for CRS Java",
    packages=find_packages(include=["."]),
    python_requires=">=3.9",
)
