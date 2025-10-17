from pathlib import Path
from setuptools import setup, find_packages


def _read_content(path: str) -> str:
    return (Path(__file__).parent / path).read_text(encoding="utf-8")


requirements = _read_content("requirements.txt").splitlines()

setup(
    name="libCRS",
    packages=find_packages(exclude=["test", "test.*"]),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
