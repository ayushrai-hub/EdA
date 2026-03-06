"""
src/data/loader.py
------------------
Loads every ADNI CSV file from a directory, cleans up sentinel/missing values,
and parses date columns automatically.

Why this exists:
  ADNI delivers data as a folder of CSV files — 30+ files across biomarkers,
  cognitive tests, and MRI measurements. This module gives you all of them in
  one tidy Python dictionary so every downstream analysis module can work
  from the same data structure.

Data structure returned:
  datasets = {
      'MOCA_13Feb2026': {
          'df':           <pandas DataFrame>,
          'filename':     'MOCA_13Feb2026.csv',
          'category':     'neuropsychological',
          'shape':        (rows, cols),
          'date_columns': ['EXAMDATE'],
      },
      ...
  }
"""

import hashlib
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config.settings import (
    DATA_DIR, SENTINEL_VALUES, FILES_TO_EXCLUDE, FILE_CATEGORIES
)

# Suppress the many pandas type-inference warnings that arise with mixed CSVs
warnings.filterwarnings('ignore')


# ===========================================================================
# ADNI LOADER CLASS
# ===========================================================================

class ADNILoader:
    """
    Loads ADNI CSV files from a given directory.

    Responsibilities:
      - Find all CSVs in the data directory
      - Detect and skip exact-duplicate files (ADNI sometimes ships duplicates)
      - Load each unique CSV into a pandas DataFrame
      - Tag each dataset with its domain category (biospecimen / neuro / MRI)

    Usage:
        loader = ADNILoader('/path/to/adni/csv/files')
        datasets = loader.load_all_datasets()
    """

    def __init__(self, data_dir: Optional[Path] = None):
        # Use the path from settings if the caller doesn't specify one
        self.data_dir = data_dir or DATA_DIR

        # Will hold the loaded data — populated by load_all_datasets()
        self.datasets: Dict[str, Dict] = {}

        # Will hold groups of files that are byte-for-byte identical
        self.duplicate_groups: Dict[str, List[str]] = {}

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _compute_file_hash(self, filepath: Path) -> str:
        """
        Return the MD5 hash of a file's raw bytes.
        Two files with the same hash are byte-for-byte identical duplicates.
        """
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    # -----------------------------------------------------------------------
    # Duplicate detection
    # -----------------------------------------------------------------------

    def find_duplicates(self) -> Dict[str, List[str]]:
        """
        Scan all CSVs in data_dir and group any that are identical by MD5 hash.

        ADNI often delivers the same file twice with a "(1)" or "(2)" suffix
        in the filename. We detect these programmatically rather than relying
        on the suffix alone, so we catch any hash-collision duplicates too.

        Returns
        -------
        Dict[str, List[str]]
            Keys are MD5 hashes; values are lists of file names that share that hash.
            Only groups with 2+ files are included (i.e. actual duplicates).
        """
        csv_files = sorted(self.data_dir.glob('*.csv'))
        hash_groups: Dict[str, List[str]] = {}

        for f in csv_files:
            h = self._compute_file_hash(f)
            hash_groups.setdefault(h, []).append(f.name)

        # Only keep groups where more than one file has the same hash
        self.duplicate_groups = {
            h: files for h, files in hash_groups.items() if len(files) > 1
        }

        return self.duplicate_groups

    def get_unique_files(self) -> List[Path]:
        """
        Return a list of CSV files that should actually be loaded —
        excluding known duplicates.

        Strategy: for each duplicate group, sort the names and keep the first
        (usually the one without a "(1)" suffix). The rest go into the exclusion set.

        Returns
        -------
        List[Path]
            Sorted list of unique CSV file paths.
        """
        all_files = sorted(self.data_dir.glob('*.csv'))

        # Run duplicate detection if not done yet
        if not self.duplicate_groups:
            self.find_duplicates()

        # Seed with the explicit exclusion list from settings
        files_to_skip = set(FILES_TO_EXCLUDE)

        # Add duplicates: for each group, keep the "first" (alphabetically),
        # skip the rest
        for files in self.duplicate_groups.values():
            sorted_files = sorted(
                files,
                key=lambda x: ('(1)' in x, '(2)' in x, '(3)' in x)
            )
            files_to_skip.update(sorted_files[1:])

        return [f for f in all_files if f.name not in files_to_skip]

    # -----------------------------------------------------------------------
    # CSV loading
    # -----------------------------------------------------------------------

    def load_csv(self, filepath: Path) -> Optional[pd.DataFrame]:
        """
        Load a single CSV file, trying several text encodings in order.

        Why multiple encodings?
          ADNI files sometimes contain characters (e.g. special dashes or
          accented letters in participant notes) that break UTF-8 decoding.
          Falling back to latin-1 handles 99% of these cases.

        Returns None if all encodings fail.
        """
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                # low_memory=False avoids mixed-type column warnings
                return pd.read_csv(filepath, encoding=encoding, low_memory=False)
            except UnicodeDecodeError:
                continue  # try the next encoding
            except Exception as e:
                print(f"  Error loading {filepath.name}: {e}")
                return None

        print(f"  Failed to load {filepath.name} with any encoding")
        return None

    # -----------------------------------------------------------------------
    # Main loader
    # -----------------------------------------------------------------------

    def load_all_datasets(self) -> Dict[str, Dict]:
        """
        Load every unique CSV from data_dir.

        Datasets are stored in self.datasets keyed by the file stem (filename
        without the .csv extension), e.g. 'MOCA_13Feb2026'.

        Returns
        -------
        Dict[str, Dict]
            {
              dataset_name: {
                'df':       DataFrame,
                'filename': 'MOCA_13Feb2026.csv',
                'category': 'neuropsychological',
                'shape':    (rows, cols),
              },
              ...
            }
        """
        unique_files = self.get_unique_files()
        print(f"Loading {len(unique_files)} unique datasets...\n")

        for f in unique_files:
            df = self.load_csv(f)
            if df is None:
                continue

            # Look up which domain category this file belongs to
            category = 'uncategorized'
            for cat, file_list in FILE_CATEGORIES.items():
                if f.name in file_list:
                    category = cat
                    break

            self.datasets[f.stem] = {
                'df':       df,
                'filename': f.name,
                'category': category,
                'shape':    df.shape,
            }
            print(f"  ✓ {f.name}: {df.shape[0]:,} rows × {df.shape[1]} columns")

        print(f"\nSuccessfully loaded {len(self.datasets)} datasets")
        return self.datasets

    # -----------------------------------------------------------------------
    # Convenience accessors
    # -----------------------------------------------------------------------

    def get_dataset(self, name: str) -> Optional[pd.DataFrame]:
        """
        Retrieve a single dataset DataFrame by name.

        Parameters
        ----------
        name : str
            Dataset stem, e.g. 'CDR_13Feb2026'.

        Returns
        -------
        pd.DataFrame or None
        """
        entry = self.datasets.get(name)
        return entry['df'] if entry else None

    def get_datasets_by_category(self, category: str) -> Dict[str, pd.DataFrame]:
        """
        Get all DataFrames belonging to a given domain category.

        Parameters
        ----------
        category : str
            One of: 'biospecimen', 'neuropsychological', 'imaging_mri', 'uncategorized'.

        Returns
        -------
        Dict[str, pd.DataFrame]
        """
        return {
            name: data['df']
            for name, data in self.datasets.items()
            if data['category'] == category
        }

    def get_summary(self) -> pd.DataFrame:
        """
        Build a one-row-per-dataset summary table with basic shape and memory stats.

        Returns
        -------
        pd.DataFrame
            Columns: Dataset, Category, Rows, Columns, Memory_MB
        """
        rows = []
        for name, data in self.datasets.items():
            df = data['df']
            rows.append({
                'Dataset':   name,
                'Category':  data['category'],
                'Rows':      df.shape[0],
                'Columns':   df.shape[1],
                # deep=True gives accurate memory for object columns
                'Memory_MB': round(df.memory_usage(deep=True).sum() / (1024**2), 2),
            })
        return pd.DataFrame(rows)


# ===========================================================================
# STANDALONE PREPROCESSING FUNCTIONS
# ===========================================================================
# These are plain functions (not class methods) so they can be used on
# any DataFrame — not only ones loaded by ADNILoader.

def normalize_missing_values(
    df: pd.DataFrame,
    sentinel_values: Optional[List] = None
) -> pd.DataFrame:
    """
    Replace every sentinel "missing" code in a DataFrame with NaN.

    ADNI records missing data as -4, -999, 'NA', 'NULL', etc.
    Pandas treats NaN specially: it is skipped by .mean(), .std(), etc.
    After this function, you can safely call descriptive statistics without
    the missing codes distorting the results.

    Parameters
    ----------
    df : pd.DataFrame
        The raw DataFrame from pd.read_csv().
    sentinel_values : list, optional
        Override the default sentinel list from settings.

    Returns
    -------
    pd.DataFrame
        A copy with sentinels replaced by NaN.
        (We never modify the original DataFrame in place.)
    """
    if sentinel_values is None:
        sentinel_values = SENTINEL_VALUES

    df_clean = df.copy()

    for col in df_clean.columns:
        if df_clean[col].dtype in ['object', 'string']:
            # Replace string sentinels first (e.g. 'NA', 'NULL')
            df_clean[col] = df_clean[col].replace(sentinel_values, np.nan)

            # Many ADNI columns arrive as strings but contain numbers like '1.23'.
            # Try to convert; if conversion yields at least one real number, accept it.
            try:
                numeric = pd.to_numeric(df_clean[col], errors='coerce')
                if numeric.notna().sum() > 0:
                    df_clean[col] = numeric
            except Exception:
                pass  # leave the column as strings if conversion fails
        else:
            # For already-numeric columns just replace the numeric sentinel codes
            df_clean[col] = df_clean[col].replace([-4, -4.0, -999, -999.0], np.nan)

    return df_clean


def detect_date_columns(df: pd.DataFrame) -> List[str]:
    """
    Identify columns whose names suggest they store dates.

    We scan for substrings like 'date', 'stamp', 'time' (case-insensitive)
    rather than parsing every column — this is much faster than trial-parsing
    and works reliably for ADNI's naming conventions like EXAMDATE, VISDATE.

    Returns
    -------
    List[str]
        Column names that likely contain date data.
    """
    from config.settings import DATE_COLUMN_PATTERNS

    date_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(pattern.lower() in col_lower for pattern in DATE_COLUMN_PATTERNS):
            date_cols.append(col)
    return date_cols


def parse_date_columns(
    df: pd.DataFrame,
    date_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Convert date columns from strings to pandas datetime objects.

    Why datetime?
      Once a column holds datetime objects you can subtract two dates to get
      a timedelta, extract the year/month, sort chronologically, etc.
      Strings don't support any of that.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame whose date columns should be parsed.
    date_cols : list, optional
        Explicit list of column names. If None, auto-detected via detect_date_columns().

    Returns
    -------
    pd.DataFrame
        A copy with the specified columns converted to datetime (invalid dates → NaT).
    """
    df_parsed = df.copy()

    if date_cols is None:
        date_cols = detect_date_columns(df)

    for col in date_cols:
        if col in df_parsed.columns:
            try:
                # errors='coerce' turns unparseable strings into NaT instead of raising
                df_parsed[col] = pd.to_datetime(df_parsed[col], errors='coerce')
            except Exception:
                pass  # column stays as-is if pandas can't interpret it at all

    return df_parsed


# ===========================================================================
# CONVENIENCE PIPELINE FUNCTION
# ===========================================================================

def load_and_preprocess_adni_data(
    data_dir: Optional[Path] = None
) -> Tuple[Dict[str, Dict], pd.DataFrame]:
    """
    One-call entry point: load → clean sentinels → parse dates → summarize.

    This is the function that run_eda.py and the Jupyter notebook call.
    It chains ADNILoader with the two preprocessing functions above so
    you never have to call them separately.

    Parameters
    ----------
    data_dir : Path, optional
        Directory containing ADNI CSV files. Defaults to DATA_DIR in settings.

    Returns
    -------
    datasets : Dict[str, Dict]
        All datasets, each with 'df', 'filename', 'category', 'date_columns'.
    summary : pd.DataFrame
        One-row-per-dataset overview (name, category, rows, columns, memory).
    """
    loader = ADNILoader(data_dir)
    datasets = loader.load_all_datasets()

    # Preprocess each dataset in-place (sentinels → NaN, strings → datetime)
    for name, data in datasets.items():
        df = data['df']

        df = normalize_missing_values(df)

        date_cols = detect_date_columns(df)
        df = parse_date_columns(df, date_cols)

        data['df'] = df
        data['date_columns'] = date_cols

    summary = loader.get_summary()
    return datasets, summary


# ---------------------------------------------------------------------------
# Quick self-test — run this file directly to verify loading works
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    datasets, summary = load_and_preprocess_adni_data()
    print("\nDataset Summary:")
    print(summary.to_string(index=False))
