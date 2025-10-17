#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name="exploit-kit",
    version="0.1.0",
    description="BEEP seed exploitation tool",
    author="Cen Zhang",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "exploit=exploit.exploit:main",
        ],
    },
    python_requires=">=3.8",
    install_requires=[
        "argparse",
    ],
)
