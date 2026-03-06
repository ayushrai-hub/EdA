"""
adni_pet_analysis.py
---------------------
Standalone module for PET (Positron Emission Tomography) imaging analysis.

This file lives outside the adni_eda_project/ package because PET data is
processed separately from the main MRI/biomarker/cognitive pipeline.
You can import it independently or run it directly.

PET modalities covered:
  Amyloid PET (AV45 tracer) — measures amyloid-β plaque deposition in the brain.
    High SUVR = more amyloid = greater Alzheimer's risk.
  Tau PET (Flortaucipir tracer) — measures tau tangle spread.
    The meta-temporal SUVR summarises tau across the regions most affected
    by Alzheimer's (temporal lobe, amygdala, etc.).
  FDG PET — measures brain glucose metabolism (a proxy for neuronal activity).
    Low FDG SUVR in key regions indicates neurodegeneration.

SUVR = Standardised Uptake Value Ratio — PET signal in a region of interest
       divided by a reference region (e.g. white matter or cerebellum),
       making it comparable across sessions and scanners.

Usage:
    from adni_pet_analysis import load_pet_data, analyze_pet_biomarkers

    datasets = load_pet_data(Path('/path/to/pet/csvs'))
    results  = analyze_pet_biomarkers(datasets)
    corr     = calculate_pet_correlations(datasets)
"""

import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')


# ===========================================================================
# CONFIGURATION
# ===========================================================================

# Which files belong to which PET modality.
# Keys = category labels used throughout this module.
# Values = expected filenames in the data directory.
PET_FILE_CATEGORIES = {
    'amyloid_pet': [
        'AMYMETA_13Feb2026.csv',                      # Amyloid PET metadata
        'AMYQC_13Feb2026.csv',                        # Amyloid PET quality control flags
        'BAIPETNMRCAV45_10_23_20_13Feb2026.csv',      # AV45 SUVR values (the main amyloid readout)
    ],
    'tau_pet': [
        'TAUMETA_13Feb2026.csv',                      # Tau PET metadata
        'TAUQC_13Feb2026.csv',                        # Tau PET quality control
        'UCBERKELEY_TAU_6MM_13Feb2026.csv',           # UC Berkeley tau SUVR (6mm smoothed)
        'UCBERKELEY_TAUPVC_6MM_13Feb2026.csv',        # Same with partial-volume correction
    ],
    'fdg_pet': [
        'BAIPETNMRCFDG_12_11_20_13Feb2026.csv',       # FDG SUVR from BAI pipeline
        'NYUFDGHIP_13Feb2026.csv',                    # NYU hippocampal FDG
        'UCBERKELEYFDG_8mm_02_17_23_13Feb2026.csv',  # UC Berkeley FDG (8mm smoothed)
    ],
    'pet_metadata': [
        'PETMETA_ADNI1_13Feb2026.csv',                # General PET metadata for ADNI1
        'PETQC_13Feb2026.csv',                        # Overall PET QC
        'CROSSVAL_13Feb2026.csv',                     # Cross-validation labels
    ],
}

# Same sentinel values as the main pipeline — see config/settings.py for explanation
SENTINEL_VALUES = [-4, -4.0, '-4', -999, -999.0, '', 'NA', 'N/A', 'NULL', 'None']


# ===========================================================================
# DATA LOADING UTILITIES
# ===========================================================================

def normalize_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace sentinel "missing data" codes with NaN in a PET DataFrame.

    Identical in logic to the main pipeline's normalize_missing_values()
    but duplicated here so this file stays self-contained (no import from
    adni_eda_project/).

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from pd.read_csv().

    Returns
    -------
    pd.DataFrame
        A copy with sentinel values replaced by NaN.
    """
    df_clean = df.copy()

    for col in df_clean.columns:
        if df_clean[col].dtype in ['object', 'string']:
            df_clean[col] = df_clean[col].replace(SENTINEL_VALUES, np.nan)

            # Many numeric columns arrive as strings — convert them
            try:
                numeric = pd.to_numeric(df_clean[col], errors='coerce')
                if numeric.notna().sum() > 0:
                    df_clean[col] = numeric
            except Exception:
                pass
        else:
            # For already-numeric columns, just replace the numeric sentinel codes
            df_clean[col] = df_clean[col].replace([-4, -4.0, -999, -999.0], np.nan)

    return df_clean


def parse_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert date-like string columns to pandas datetime objects.

    We detect date columns by looking for 'date', 'stamp', or 'time'
    in the column name (case-insensitive) — this matches ADNI conventions
    like EXAMDATE, VISDATE, etc.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        A copy with date columns converted (invalid strings → NaT).
    """
    df_parsed = df.copy()

    for col in df_parsed.columns:
        if any(kw in col.lower() for kw in ['date', 'stamp', 'time']):
            try:
                df_parsed[col] = pd.to_datetime(df_parsed[col], errors='coerce')
            except Exception:
                pass

    return df_parsed


def load_pet_data(data_dir: Path) -> Dict[str, Dict]:
    """
    Load all PET datasets from a directory.

    For each expected file in PET_FILE_CATEGORIES:
      - Skip with a warning if the file isn't found
      - Try multiple text encodings if the default (UTF-8) fails
      - Normalize missing values and parse date columns
      - Store in a dictionary keyed by the filename stem (no extension)

    Parameters
    ----------
    data_dir : Path
        Directory containing PET CSV files.

    Returns
    -------
    Dict[str, Dict]
        {
          'BAIPETNMRCAV45_10_23_20_13Feb2026': {
              'df':       DataFrame,
              'filename': 'BAIPETNMRCAV45_10_23_20_13Feb2026.csv',
              'category': 'amyloid_pet',
          },
          ...
        }
    """
    datasets = {}

    # Flatten the nested file list into (filename, category) pairs
    all_files = [
        (filename, category)
        for category, files in PET_FILE_CATEGORIES.items()
        for filename in files
    ]

    for filename, category in all_files:
        filepath = data_dir / filename

        if not filepath.exists():
            print(f"  ⚠ Not found: {filename}")
            continue

        df = None
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
            try:
                df = pd.read_csv(filepath, encoding=encoding, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  ✗ Error loading {filename}: {e}")
                break

        if df is None:
            continue

        df = normalize_missing_values(df)
        df = parse_date_columns(df)

        stem = Path(filename).stem
        datasets[stem] = {
            'df':       df,
            'filename': filename,
            'category': category,
        }
        print(f"  ✓ {filename}: {df.shape[0]:,} rows × {df.shape[1]} columns")

    print(f"\nLoaded {len(datasets)} PET datasets")
    return datasets


# ===========================================================================
# BIOMARKER-SPECIFIC ANALYSIS FUNCTIONS
# ===========================================================================

def _descriptive_stats(data: pd.Series, label: str) -> Dict:
    """
    Compute descriptive statistics for a single pandas Series.

    Internal helper — not called directly by users.
    Returns a dict ready to be appended to a results list.
    """
    return {
        'Biomarker': label,
        'N':         len(data),
        'Mean':      data.mean(),
        'Std':       data.std(),
        'Min':       data.min(),
        'Q1':        data.quantile(0.25),
        'Median':    data.median(),
        'Q3':        data.quantile(0.75),
        'Max':       data.max(),
    }


def analyze_av45_amyloid(datasets: Dict) -> pd.DataFrame:
    """
    Summarise AV45 amyloid PET measurements.

    Columns analysed from the BAI AV45 dataset:
      MCSUVRWM    — mean cortical SUVR, reference = white matter
      MCSUVRCERE  — mean cortical SUVR, reference = cerebellar grey matter

    Both are standard summary measures of whole-brain amyloid burden.
    A threshold of ~1.10–1.18 SUVR (method-dependent) separates amyloid-
    negative (normal) from amyloid-positive participants.

    Returns
    -------
    pd.DataFrame
        One row per SUVR measure with descriptive statistics.
    """
    key = 'BAIPETNMRCAV45_10_23_20_13Feb2026'
    if key not in datasets:
        return pd.DataFrame()

    df      = datasets[key]['df']
    results = []

    for col in ['MCSUVRWM', 'MCSUVRCERE']:
        if col not in df.columns:
            continue

        data = df[col].dropna()
        data = data[data >= 0]   # remove any residual sentinel negatives

        if len(data) == 0:
            continue

        results.append(_descriptive_stats(data, f'AV45_{col}'))

    return pd.DataFrame(results)


def analyze_tau_pet(datasets: Dict) -> pd.DataFrame:
    """
    Summarise UC Berkeley Tau PET measurements.

    Column analysed:
      META_TEMPORAL_SUVR — meta-ROI temporal SUVR, a composite score
      across the inferior temporal, entorhinal, fusiform, parahippocampal,
      and middle temporal cortices — the regions most vulnerable to tau
      accumulation in Alzheimer's disease.

    Returns
    -------
    pd.DataFrame
    """
    key = 'UCBERKELEY_TAU_6MM_13Feb2026'
    if key not in datasets:
        return pd.DataFrame()

    df      = datasets[key]['df']
    results = []

    col  = 'META_TEMPORAL_SUVR'
    if col in df.columns:
        data = df[col].dropna()
        data = data[data >= 0]
        if len(data) > 0:
            results.append(_descriptive_stats(data, f'Tau_{col}'))

    return pd.DataFrame(results)


def analyze_fdg_pet(datasets: Dict) -> pd.DataFrame:
    """
    Summarise FDG PET measurements from multiple datasets.

    Three sources:
      1. BAI FDG — SROI.AD (Scaled ROI for Alzheimer's signature regions)
                   SROI.MCI (Scaled ROI for MCI signature regions)
      2. UC Berkeley FDG — MetaROI SUVR from the long-format dataset
                           (filtered to rows where ROINAME == 'MetaROI')

    Lower FDG SUVR in these ROIs indicates reduced metabolic activity
    (neuronal loss / dysfunction), consistent with neurodegeneration.

    Returns
    -------
    pd.DataFrame
    """
    results = []

    # Source 1 — BAI pipeline
    bai_key = 'BAIPETNMRCFDG_12_11_20_13Feb2026'
    if bai_key in datasets:
        df = datasets[bai_key]['df']
        for col in ['SROI.AD', 'SROI.MCI']:
            if col not in df.columns:
                continue
            data = df[col].dropna()
            data = data[data >= 0]
            if len(data) > 0:
                results.append(_descriptive_stats(data, f'FDG_{col}'))

    # Source 2 — UC Berkeley long-format dataset
    ucb_key = 'UCBERKELEYFDG_8mm_02_17_23_13Feb2026'
    if ucb_key in datasets:
        df = datasets[ucb_key]['df']
        # This dataset has one row per ROI per participant-visit; we
        # filter to the MetaROI summary row only
        if 'ROINAME' in df.columns and 'MEAN' in df.columns:
            metaroi = df.loc[df['ROINAME'] == 'MetaROI', 'MEAN'].dropna()
            metaroi = metaroi[metaroi > 0]
            if len(metaroi) > 0:
                results.append(_descriptive_stats(metaroi, 'FDG_MetaROI_SUVR'))

    return pd.DataFrame(results)


def analyze_pet_biomarkers(datasets: Dict) -> Dict[str, pd.DataFrame]:
    """
    Analyse all three PET modalities and return a summary dictionary.

    Parameters
    ----------
    datasets : Dict
        Output of load_pet_data().

    Returns
    -------
    Dict[str, pd.DataFrame]
        Keys: 'amyloid', 'tau', 'fdg'
        Values: descriptive stats DataFrames
    """
    return {
        'amyloid': analyze_av45_amyloid(datasets),
        'tau':     analyze_tau_pet(datasets),
        'fdg':     analyze_fdg_pet(datasets),
    }


# ===========================================================================
# CROSS-MODALITY CORRELATION
# ===========================================================================

def calculate_pet_correlations(datasets: Dict) -> pd.DataFrame:
    """
    Compute pairwise Pearson correlations between the three PET modalities.

    Records are matched by (RID, VISCODE2) so we only correlate measurements
    made at the same visit for the same person.  After merging we filter to
    non-negative values before computing the correlation matrix.

    Why correlate modalities?
      Amyloid and tau PET should be positively correlated (both track
      Alzheimer's pathology), while FDG should be negatively correlated
      with amyloid and tau (more pathology → less glucose metabolism).

    Returns
    -------
    pd.DataFrame
        3×3 correlation matrix with readable row/column labels
        (AV45, Tau, FDG), or an empty DataFrame if any dataset is missing.
    """
    av45 = datasets.get('BAIPETNMRCAV45_10_23_20_13Feb2026', {}).get('df')
    tau  = datasets.get('UCBERKELEY_TAU_6MM_13Feb2026',      {}).get('df')
    fdg  = datasets.get('BAIPETNMRCFDG_12_11_20_13Feb2026',  {}).get('df')

    if any(d is None for d in [av45, tau, fdg]):
        return pd.DataFrame()

    # Pull only the columns needed for correlation
    av45_data = av45[['RID', 'VISCODE2', 'MCSUVRWM']].copy()
    tau_data  = tau[['RID', 'VISCODE2', 'META_TEMPORAL_SUVR']].copy()
    fdg_data  = fdg[['RID', 'VISCODE2', 'SROI.AD']].copy()

    # Inner join: only participant-visits present in ALL THREE datasets
    merged = (
        av45_data
        .merge(tau_data, on=['RID', 'VISCODE2'], how='inner')
        .merge(fdg_data, on=['RID', 'VISCODE2'], how='inner')
    )

    corr_cols = ['MCSUVRWM', 'META_TEMPORAL_SUVR', 'SROI.AD']
    data      = merged[corr_cols].dropna()
    data      = data[(data >= 0).all(axis=1)]   # drop residual negatives

    if len(data) < 3:
        return pd.DataFrame()

    corr = data.corr()

    # Replace opaque column names with readable labels
    corr.index   = ['AV45 Amyloid', 'Tau (Meta-Temporal)', 'FDG MetaROI']
    corr.columns = ['AV45 Amyloid', 'Tau (Meta-Temporal)', 'FDG MetaROI']

    return corr


# ===========================================================================
# STANDALONE EXECUTION
# ===========================================================================

if __name__ == '__main__':
    # Point this to your PET CSV directory
    data_dir = Path('/mnt/okcomputer/upload')

    print("Loading PET datasets...")
    datasets = load_pet_data(data_dir)

    print("\nAnalysing PET biomarkers...")
    results = analyze_pet_biomarkers(datasets)
    for modality, df in results.items():
        if not df.empty:
            print(f"\n{modality.upper()}:")
            print(df.round(4).to_string(index=False))

    print("\nCross-modality PET correlations:")
    corr = calculate_pet_correlations(datasets)
    if not corr.empty:
        print(corr.round(3).to_string())
    else:
        print("  (insufficient overlapping data for correlation)")
