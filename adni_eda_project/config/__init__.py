"""
config/__init__.py
------------------
Exposes the most commonly needed configuration constants at the top level
of the config package so other modules can write:

    from config import DATA_DIR, BIOMARKER_COLUMNS

instead of:

    from config.settings import DATA_DIR, BIOMARKER_COLUMNS
"""

from .settings import (
    DATA_DIR,
    OUTPUT_DIR,
    SENTINEL_VALUES,
    FILE_CATEGORIES,
    ID_COLUMNS,
    BIOMARKER_COLUMNS,
    COGNITIVE_COLUMNS,
    IMAGING_COLUMNS,
    COLORS,
)

__all__ = [
    'DATA_DIR',
    'OUTPUT_DIR',
    'SENTINEL_VALUES',
    'FILE_CATEGORIES',
    'ID_COLUMNS',
    'BIOMARKER_COLUMNS',
    'COGNITIVE_COLUMNS',
    'IMAGING_COLUMNS',
    'COLORS',
]
