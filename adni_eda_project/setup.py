"""
setup.py
---------
Package installation configuration.

Running 'pip install -e .' from the project root installs the project in
"editable" mode — meaning Python reads from this directory directly, so
any code changes take effect immediately without reinstalling.

The entry_points section creates a CLI command 'adni-eda' that you can run
from anywhere in the terminal once the package is installed:
    adni-eda --data-dir /path/to/data
"""

from setuptools import setup, find_packages

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Read dependency list from requirements.txt, ignoring comment lines
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith('#')
    ]

setup(
    name='adni-eda',
    version='1.0.0',
    description='Exploratory Data Analysis pipeline for the ADNI dataset',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),          # auto-discovers src/, config/, etc.
    install_requires=requirements,
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            # After installation: run 'adni-eda --data-dir ...' in the terminal
            'adni-eda=run_eda:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python :: 3',
    ],
)
