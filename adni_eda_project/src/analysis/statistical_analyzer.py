"""
src/analysis/statistical_analyzer.py
--------------------------------------
Computes descriptive statistics, detects outliers, and performs
cross-domain correlation analysis on ADNI biomarker, cognitive,
and imaging data.

Background for beginners:
  - "Descriptive statistics" = summarising a column with numbers like mean,
    median, standard deviation, min, max, quartiles.
  - "Outlier detection" = finding values that are far from the bulk of the data.
    Two approaches used here:
      * IQR method  — flag points outside [Q1 - 1.5×IQR,  Q3 + 1.5×IQR]
      * Z-score     — flag points more than 3 standard deviations from the mean
  - "Correlation" = a number between -1 and +1 that captures how strongly
    two variables move together (positive = same direction, negative = opposite).

All methods skip NaN values, and filter out negative numbers before computing
statistics because ADNI uses negative sentinel codes (e.g. -4) that were not
fully replaced by normalize_missing_values().  Numbers < 0 are physiologically
impossible for the biomarkers tracked here.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Tuple

from config.settings import (
    BIOMARKER_COLUMNS, COGNITIVE_COLUMNS, IMAGING_COLUMNS,
    OUTLIER_IQR_MULTIPLIER, OUTLIER_ZSCORE_THRESHOLD
)


class StatisticalAnalyzer:
    """
    Runs descriptive statistics, outlier detection, and correlation analysis
    on ADNI datasets.

    Typical usage:
        analyzer = StatisticalAnalyzer(datasets)

        bio   = analyzer.analyze_biomarkers()
        cog   = analyzer.analyze_cognitive_assessments()
        img   = analyzer.analyze_imaging()
        corr  = analyzer.multimodal_correlation_analysis()
    """

    def __init__(self, datasets: Dict[str, Dict]):
        """
        Parameters
        ----------
        datasets : Dict[str, Dict]
            The dictionary returned by load_and_preprocess_adni_data().
        """
        self.datasets = datasets

    # -----------------------------------------------------------------------
    # Descriptive statistics
    # -----------------------------------------------------------------------

    def descriptive_statistics(
        self,
        df: pd.DataFrame,
        columns: List[str],
        filter_negative: bool = True
    ) -> pd.DataFrame:
        """
        Compute a comprehensive summary table for the requested columns.

        Metrics produced for each column:
          N          — number of valid (non-NaN, non-negative) observations
          Mean       — arithmetic average
          Std        — standard deviation (spread around the mean)
          Min / Max  — smallest / largest value
          Q1, Median, Q3 — 25th, 50th, 75th percentiles
          IQR        — interquartile range = Q3 - Q1 (robust spread measure)
          Skewness   — asymmetry of the distribution
                       (positive = long right tail, negative = long left tail)
          Kurtosis   — heaviness of the tails relative to a normal distribution
          CV         — coefficient of variation = Std / Mean
                       (relative variability, useful to compare different-scale columns)

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to analyse.
        columns : List[str]
            Column names to include.
        filter_negative : bool
            If True, values < 0 are treated as sentinels and removed.

        Returns
        -------
        pd.DataFrame
            One row per column, with the metrics above as columns.
        """
        results = []

        for col in columns:
            if col not in df.columns:
                continue

            data = df[col].dropna()

            if filter_negative:
                data = data[data >= 0]

            if len(data) == 0:
                continue

            results.append({
                'Variable': col,
                'N':        len(data),
                'Mean':     data.mean(),
                'Std':      data.std(),
                'Min':      data.min(),
                'Q1':       data.quantile(0.25),
                'Median':   data.median(),
                'Q3':       data.quantile(0.75),
                'Max':      data.max(),
                'IQR':      data.quantile(0.75) - data.quantile(0.25),
                'Skewness': data.skew(),
                'Kurtosis': data.kurtosis(),
                # CV tells you the standard deviation as a fraction of the mean
                'CV':       data.std() / data.mean() if data.mean() != 0 else np.nan,
            })

        return pd.DataFrame(results)

    # -----------------------------------------------------------------------
    # Outlier detection — IQR method
    # -----------------------------------------------------------------------

    def detect_outliers_iqr(
        self,
        df: pd.DataFrame,
        columns: List[str],
        multiplier: float = OUTLIER_IQR_MULTIPLIER
    ) -> pd.DataFrame:
        """
        Flag outliers using the Interquartile Range (IQR) fence method.

        How IQR fences work:
          lower_bound = Q1 - multiplier × IQR
          upper_bound = Q3 + multiplier × IQR
          Any value outside these bounds is an outlier.

        The default multiplier of 1.5 is the standard "mild outlier" threshold.
        Use 3.0 for "extreme outliers" only.

        Parameters
        ----------
        df : pd.DataFrame
        columns : List[str]
        multiplier : float
            IQR multiplier for the fence (default 1.5).

        Returns
        -------
        pd.DataFrame
            One row per column with outlier counts and bounds.
        """
        results = []

        for col in columns:
            if col not in df.columns:
                continue

            data = df[col].dropna()
            data = data[data >= 0]   # drop remaining sentinel negatives

            if len(data) == 0:
                continue

            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1

            lower = Q1 - multiplier * IQR
            upper = Q3 + multiplier * IQR

            n_low  = int((data < lower).sum())
            n_high = int((data > upper).sum())
            total  = n_low + n_high

            results.append({
                'Variable':      col,
                'Lower_Bound':   lower,
                'Upper_Bound':   upper,
                'N_Low_Outliers':  n_low,
                'N_High_Outliers': n_high,
                'Total_Outliers':  total,
                'Outlier_Pct':   total / len(data) * 100,
            })

        return pd.DataFrame(results)

    # -----------------------------------------------------------------------
    # Outlier detection — Z-score method
    # -----------------------------------------------------------------------

    def detect_outliers_zscore(
        self,
        df: pd.DataFrame,
        columns: List[str],
        threshold: float = OUTLIER_ZSCORE_THRESHOLD
    ) -> pd.DataFrame:
        """
        Flag outliers using the Z-score (standard score) method.

        A Z-score measures how many standard deviations a value sits from
        the mean. Points with |Z| > threshold (default 3) are flagged.
        This is most appropriate when the data are roughly bell-shaped.
        For skewed biomarker distributions, IQR is often more reliable.

        Parameters
        ----------
        df : pd.DataFrame
        columns : List[str]
        threshold : float
            |Z| threshold above which a point is an outlier (default 3.0).

        Returns
        -------
        pd.DataFrame
        """
        results = []

        for col in columns:
            if col not in df.columns:
                continue

            data = df[col].dropna()
            data = data[data >= 0]

            # Need at least 3 points to compute a meaningful Z-score
            if len(data) < 3:
                continue

            z_scores     = np.abs(stats.zscore(data))
            n_outliers   = int((z_scores > threshold).sum())

            results.append({
                'Variable':   col,
                'Z_Threshold': threshold,
                'N_Outliers':  n_outliers,
                'Outlier_Pct': n_outliers / len(data) * 100,
                'Max_Z_Score': float(z_scores.max()),
            })

        return pd.DataFrame(results)

    # -----------------------------------------------------------------------
    # Domain-specific analyses
    # -----------------------------------------------------------------------

    def analyze_biomarkers(
        self,
        dataset_name: str = 'UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026'
    ) -> Dict:
        """
        Descriptive statistics and outlier analysis for plasma biomarkers.

        The UPENN plasma dataset (Fujirebio + Quanterix platforms) is the
        primary blood biomarker source.  Biomarker columns analysed are
        defined in BIOMARKER_COLUMNS in config/settings.py.

        Returns
        -------
        Dict with keys:
          'dataset'            — name of the dataset used
          'total_samples'      — total rows
          'unique_participants' — number of distinct RIDs
          'descriptive_stats'  — pd.DataFrame of stats
          'outliers_iqr'       — pd.DataFrame of IQR outlier results
        """
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        df = self.datasets[dataset_name]['df']
        biomarker_cols = [c for c in BIOMARKER_COLUMNS if c in df.columns]

        return {
            'dataset':             dataset_name,
            'total_samples':       len(df),
            'unique_participants': int(df['RID'].nunique()) if 'RID' in df.columns else 0,
            'descriptive_stats':   self.descriptive_statistics(df, biomarker_cols),
            'outliers_iqr':        self.detect_outliers_iqr(df, biomarker_cols),
        }

    def analyze_cognitive_assessments(self) -> Dict:
        """
        Summarise the three main cognitive assessment datasets.

        Datasets and columns covered:
          MoCA  → MOCA (0–30 scale, higher = better cognitive function)
          ADAS  → TOTSCORE, TOTAL13 (higher = worse)
          CDR   → CDRSB, CDGLOBAL (0 = normal, 0.5 = MCI, 1–3 = dementia severity)

        Returns
        -------
        Dict
            Keys are 'MOCA', 'ADAS', 'CDR', each holding a sub-dict with
            'total_assessments', 'unique_participants', 'descriptive_stats',
            and for CDR also 'cdr_distribution'.
        """
        # Define which datasets and columns to use for each cognitive tool
        cognitive_map = {
            'MOCA': ('MOCA_13Feb2026',  ['MOCA']),
            'ADAS': ('ADAS_13Feb2026',  ['TOTSCORE', 'TOTAL13']),
            'CDR':  ('CDR_13Feb2026',   ['CDRSB', 'CDGLOBAL']),
        }

        results = {}

        for label, (dataset_name, columns) in cognitive_map.items():
            if dataset_name not in self.datasets:
                continue

            df = self.datasets[dataset_name]['df']
            results[label] = {
                'total_assessments':   len(df),
                'unique_participants': int(df['RID'].nunique()) if 'RID' in df.columns else 0,
                'descriptive_stats':   self.descriptive_statistics(df, columns),
            }

            # For CDR specifically, also show the frequency of each score value.
            # CDR Global is used as the target variable in most Alzheimer's ML studies.
            if label == 'CDR' and 'CDGLOBAL' in df.columns:
                cdr_vals = df['CDGLOBAL'].dropna()
                cdr_vals = cdr_vals[cdr_vals >= 0]
                results[label]['cdr_distribution'] = (
                    cdr_vals.value_counts().sort_index().to_dict()
                )

        return results

    def analyze_imaging(
        self,
        dataset_name: str = 'UCSFSNTVOL_13Feb2026'
    ) -> Dict:
        """
        Analyse structural MRI-derived brain volumes.

        The UCSFSNTVOL dataset contains FreeSurfer subcortical volume
        measurements.  Hippocampal volume (left + right) is the most
        clinically relevant — it is known to shrink progressively in
        Alzheimer's disease.

        Returns
        -------
        Dict with descriptive stats for imaging columns, plus total
        hippocampal volume (left + right) if both are available.
        """
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        df = self.datasets[dataset_name]['df']
        imaging_cols = [c for c in IMAGING_COLUMNS if c in df.columns]

        results = {
            'dataset':             dataset_name,
            'total_scans':         len(df),
            'unique_participants': int(df['RID'].nunique()) if 'RID' in df.columns else 0,
            'descriptive_stats':   self.descriptive_statistics(
                df, imaging_cols, filter_negative=True
            ),
        }

        # Total hippocampal volume = left + right, useful as a single summary metric
        if 'LEFTHIPPO' in df.columns and 'RIGHTHIPPO' in df.columns:
            paired = df[['LEFTHIPPO', 'RIGHTHIPPO']].dropna()
            paired = paired[(paired > 0).all(axis=1)]  # both sides must be positive

            if len(paired) > 0:
                total_vol = paired['LEFTHIPPO'] + paired['RIGHTHIPPO']
                results['total_hippocampal_volume'] = {
                    'N':      len(total_vol),
                    'Mean':   total_vol.mean(),
                    'Std':    total_vol.std(),
                    'Min':    total_vol.min(),
                    'Max':    total_vol.max(),
                    'Median': total_vol.median(),
                }

        return results

    # -----------------------------------------------------------------------
    # Correlation analysis
    # -----------------------------------------------------------------------

    def calculate_correlation_matrix(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = 'pearson'
    ) -> pd.DataFrame:
        """
        Compute a correlation matrix for a set of columns.

        Before correlating, we set any value < 0 to NaN so that remaining
        sentinel values do not skew the correlation.

        Parameters
        ----------
        df : pd.DataFrame
        columns : List[str]
            Columns to include (only those present in df are used).
        method : str
            'pearson' (linear), 'spearman' (rank-based), or 'kendall'.
            Spearman is more robust when data are skewed — often preferable
            for biomarker data.

        Returns
        -------
        pd.DataFrame
            Square correlation matrix.
        """
        available = [c for c in columns if c in df.columns]

        if len(available) < 2:
            return pd.DataFrame()

        data = df[available].copy()

        # Replace any residual negative sentinels with NaN
        for col in available:
            data[col] = data[col].where(data[col] >= 0)

        return data.corr(method=method)

    def multimodal_correlation_analysis(self) -> Dict:
        """
        Correlate biomarkers against cognitive scores and brain volumes by
        merging datasets on shared participant + visit keys.

        Two analyses:
          'biomarker_cognitive' — plasma biomarkers vs MoCA score
          'biomarker_imaging'   — plasma biomarkers vs hippocampal volumes
            (uses last visit per participant to avoid repeated-measures bias)

        Returns
        -------
        Dict
            Sub-dicts describing each analysis: n records, n participants,
            and the correlation matrix.
        """
        upenn  = self.datasets.get('UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026', {}).get('df')
        moca   = self.datasets.get('MOCA_13Feb2026',   {}).get('df')
        sntvol = self.datasets.get('UCSFSNTVOL_13Feb2026', {}).get('df')

        results = {}

        # --- Biomarker vs Cognitive -----------------------------------------
        if upenn is not None and moca is not None:
            bio_cols = [c for c in ['RID', 'VISCODE2', 'pT217_F', 'AB42_AB40_F',
                                    'NfL_Q', 'GFAP_Q'] if c in upenn.columns]
            cog_cols = [c for c in ['RID', 'VISCODE2', 'MOCA'] if c in moca.columns]

            bio_data = upenn[bio_cols].copy()
            cog_data = moca[cog_cols].copy()

            # Can only merge if both have VISCODE2 (not all ADNI phases use it)
            if 'VISCODE2' in bio_data.columns and 'VISCODE2' in cog_data.columns:
                merged = bio_data.merge(cog_data, on=['RID', 'VISCODE2'], how='inner')
                corr_cols = [c for c in ['pT217_F', 'AB42_AB40_F',
                                          'NfL_Q', 'GFAP_Q', 'MOCA']
                             if c in merged.columns]

                if len(corr_cols) >= 2:
                    results['biomarker_cognitive'] = {
                        'n_records':       len(merged),
                        'n_participants':  int(merged['RID'].nunique()),
                        'correlation_matrix': self.calculate_correlation_matrix(
                            merged, corr_cols
                        ),
                    }

        # --- Biomarker vs Imaging -------------------------------------------
        if upenn is not None and sntvol is not None:
            # Use each participant's latest available visit to avoid repeated
            # measures inflating the correlation
            bio_latest = upenn.groupby('RID').last().reset_index()
            img_latest = sntvol.groupby('RID').last().reset_index()

            merged = bio_latest.merge(img_latest, on='RID', how='inner')
            corr_cols = [c for c in ['pT217_F', 'AB42_AB40_F', 'NfL_Q',
                                      'GFAP_Q', 'LEFTHIPPO', 'RIGHTHIPPO']
                         if c in merged.columns]

            if len(corr_cols) >= 2:
                results['biomarker_imaging'] = {
                    'n_participants':  len(merged),
                    'correlation_matrix': self.calculate_correlation_matrix(
                        merged, corr_cols
                    ),
                }

        return results


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from src.data.loader import load_and_preprocess_adni_data

    datasets, _ = load_and_preprocess_adni_data()
    analyzer = StatisticalAnalyzer(datasets)

    print("--- Biomarker Statistics ---")
    bio = analyzer.analyze_biomarkers()
    print(bio['descriptive_stats'].round(4).to_string(index=False))

    print("\n--- Cognitive Assessments ---")
    for name, result in analyzer.analyze_cognitive_assessments().items():
        print(f"\n{name}:")
        print(result['descriptive_stats'].round(2).to_string(index=False))
