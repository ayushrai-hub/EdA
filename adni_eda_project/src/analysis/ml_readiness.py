"""
src/analysis/ml_readiness.py
-----------------------------
Assesses whether the ADNI data is ready to be used as input to a machine
learning model.

"ML readiness" is a checklist that catches common problems before you spend
time building a model on data that won't work well:

  ✓ Do features have enough variance?  (low variance → feature is useless)
  ✓ Are features too correlated (multicollinear)?  (redundant features can
    confuse regularised models)
  ✓ How many samples have all required features filled in?  (complete cases)
  ✓ Is the target variable (what we're predicting) heavily imbalanced?
    (e.g. 90% of participants have CDR=0 — a naive model would just always
    predict 0 and be "90% accurate", which is meaningless)

The integrated dataset built here merges:
  - Plasma biomarkers (p-tau217, Aβ42/40, NfL, GFAP)
  - MoCA cognitive score
  - ADAS-Cog score
  - CDR Global score (used as the prediction target)

All joined on (RID, VISCODE2) so each row represents one participant at
one specific visit.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional


class MLReadinessAnalyzer:
    """
    Evaluates ADNI data quality for machine learning use.

    Typical workflow:
        analyzer = MLReadinessAnalyzer(datasets)
        assessment = analyzer.full_ml_assessment()
        analyzer.print_ml_report()
    """

    def __init__(self, datasets: Dict[str, Dict]):
        """
        Parameters
        ----------
        datasets : Dict[str, Dict]
            The dictionary returned by load_and_preprocess_adni_data().
        """
        self.datasets = datasets

        # Will hold the merged biomarker + cognitive DataFrame once built
        self.integrated_data: Optional[pd.DataFrame] = None

    # -----------------------------------------------------------------------
    # Build the integrated dataset
    # -----------------------------------------------------------------------

    def create_integrated_dataset(self) -> pd.DataFrame:
        """
        Merge biomarker, MoCA, ADAS, and CDR data into a single wide table.

        Why merge?
          Each domain lives in its own CSV file. If we want to predict
          CDR from biomarkers, we need all those columns in the same row.
          We merge on (RID, VISCODE2) — same person, same visit.

        We use left-joins from biomarkers outward, so we keep all biomarker
        rows even if a matching cognitive record doesn't exist at that visit
        (the cognitive columns will simply be NaN for that row).

        Returns
        -------
        pd.DataFrame
            Integrated wide-format dataset.  One row = one participant-visit.
        """
        upenn = self.datasets.get('UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026', {}).get('df')
        moca  = self.datasets.get('MOCA_13Feb2026',  {}).get('df')
        adas  = self.datasets.get('ADAS_13Feb2026',  {}).get('df')
        cdr   = self.datasets.get('CDR_13Feb2026',   {}).get('df')

        if upenn is None:
            raise ValueError("UPENN plasma dataset is required for ML integration baseline")

        # Start with biomarker columns
        bio_cols = [c for c in ['RID', 'VISCODE2', 'PHASE',
                                 'pT217_F', 'AB42_F', 'AB40_F',
                                 'AB42_AB40_F', 'NfL_Q', 'GFAP_Q']
                    if c in upenn.columns]
        integrated = upenn[bio_cols].copy()

        # Null out remaining negative sentinels in biomarker columns
        for col in ['pT217_F', 'AB42_F', 'AB40_F', 'AB42_AB40_F', 'NfL_Q', 'GFAP_Q']:
            if col in integrated.columns:
                integrated[col] = integrated[col].where(integrated[col] >= 0)

        # --- Merge MoCA ---
        if moca is not None and 'VISCODE2' in moca.columns:
            moca_cols = [c for c in ['RID', 'VISCODE2', 'MOCA'] if c in moca.columns]
            moca_data = moca[moca_cols].copy()
            moca_data['MOCA'] = moca_data['MOCA'].where(moca_data['MOCA'] >= 0)
            integrated = integrated.merge(
                moca_data, on=['RID', 'VISCODE2'], how='left', suffixes=('', '_moca')
            )

        # --- Merge ADAS ---
        if adas is not None and 'VISCODE2' in adas.columns:
            adas_cols = [c for c in ['RID', 'VISCODE2', 'TOTSCORE', 'TOTAL13']
                         if c in adas.columns]
            adas_data = adas[adas_cols].copy()
            for col in ['TOTSCORE', 'TOTAL13']:
                if col in adas_data.columns:
                    adas_data[col] = adas_data[col].where(adas_data[col] >= 0)
            integrated = integrated.merge(
                adas_data, on=['RID', 'VISCODE2'], how='left', suffixes=('', '_adas')
            )

        # --- Merge CDR ---
        if cdr is not None and 'VISCODE2' in cdr.columns:
            cdr_cols = [c for c in ['RID', 'VISCODE2', 'CDRSB', 'CDGLOBAL']
                        if c in cdr.columns]
            cdr_data = cdr[cdr_cols].copy()
            for col in ['CDRSB', 'CDGLOBAL']:
                if col in cdr_data.columns:
                    cdr_data[col] = cdr_data[col].where(cdr_data[col] >= 0)
            integrated = integrated.merge(
                cdr_data, on=['RID', 'VISCODE2'], how='left', suffixes=('', '_cdr')
            )

        self.integrated_data = integrated
        return integrated

    # -----------------------------------------------------------------------
    # Feature variance analysis
    # -----------------------------------------------------------------------

    def analyze_feature_variance(self, feature_cols: List[str]) -> pd.DataFrame:
        """
        Check whether each feature column has enough spread to be useful.

        A feature with near-zero variance (CV < 0.01) carries almost no
        information — every participant has nearly the same value — so it
        cannot help a model distinguish between groups.

        Metrics:
          N         — valid (non-NaN) observation count
          Mean, Std — central tendency and spread
          CV        — coefficient of variation = Std / Mean
          Variance  — Std²
          Near_Zero_Variance — flag (True = probably useless feature)

        Parameters
        ----------
        feature_cols : List[str]

        Returns
        -------
        pd.DataFrame
        """
        if self.integrated_data is None:
            self.create_integrated_dataset()

        rows = []
        for col in feature_cols:
            if col not in self.integrated_data.columns:
                continue

            data = self.integrated_data[col].dropna()
            if len(data) == 0:
                continue

            mean = data.mean()
            std  = data.std()
            cv   = std / mean if mean != 0 else np.nan

            rows.append({
                'Feature':            col,
                'N':                  len(data),
                'Mean':               mean,
                'Std':                std,
                'CV':                 cv,
                'Variance':           data.var(),
                # Flag features where std is < 1% of the mean
                'Near_Zero_Variance': cv < 0.01,
            })

        return pd.DataFrame(rows)

    # -----------------------------------------------------------------------
    # Multicollinearity check
    # -----------------------------------------------------------------------

    def analyze_multicollinearity(self, feature_cols: List[str]) -> Dict:
        """
        Detect pairs of features that are highly correlated with each other.

        Why it matters:
          If two features have |r| > 0.7 they carry nearly the same information.
          In linear models this inflates coefficient variances (making coefficients
          unreliable). Tree-based models are less affected but it can still cause
          feature-importance instability.

        Parameters
        ----------
        feature_cols : List[str]

        Returns
        -------
        Dict with keys:
          'correlation_matrix'    — full pairwise correlation matrix
          'high_correlation_pairs' — DataFrame of pairs where |r| > 0.7
          'n_high_correlations'   — count of such pairs
        """
        if self.integrated_data is None:
            self.create_integrated_dataset()

        available = [c for c in feature_cols if c in self.integrated_data.columns]

        if len(available) < 2:
            return {'error': 'Need at least 2 features for multicollinearity analysis'}

        corr_matrix = self.integrated_data[available].corr()

        # Find pairs that exceed the 0.7 threshold (upper triangle only to avoid duplicates)
        high_corr = []
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.7:
                    high_corr.append({
                        'Feature_1':   available[i],
                        'Feature_2':   available[j],
                        'Correlation': round(r, 3),
                    })

        return {
            'correlation_matrix':     corr_matrix,
            'high_correlation_pairs': pd.DataFrame(high_corr),
            'n_high_correlations':    len(high_corr),
        }

    # -----------------------------------------------------------------------
    # Missing data pattern
    # -----------------------------------------------------------------------

    def analyze_missing_data_pattern(self, feature_cols: List[str]) -> pd.DataFrame:
        """
        Report how many values are missing for each feature in the integrated dataset.

        Severity thresholds:
          Low      — < 10% missing   (acceptable, imputation is straightforward)
          Moderate — 10–30% missing  (consider multiple imputation)
          High     — > 30% missing   (feature may not be usable without care)

        Returns
        -------
        pd.DataFrame
            Columns: Feature, N_Missing, Missing_Pct, Severity
        """
        if self.integrated_data is None:
            self.create_integrated_dataset()

        rows = []
        n_total = len(self.integrated_data)

        for col in feature_cols:
            if col not in self.integrated_data.columns:
                continue

            n_missing = int(self.integrated_data[col].isnull().sum())
            pct       = n_missing / n_total * 100

            rows.append({
                'Feature':     col,
                'N_Missing':   n_missing,
                'Missing_Pct': round(pct, 1),
                'Severity':    'High' if pct > 30 else ('Moderate' if pct > 10 else 'Low'),
            })

        return pd.DataFrame(rows)

    # -----------------------------------------------------------------------
    # Complete-case count
    # -----------------------------------------------------------------------

    def analyze_complete_cases(self, feature_cols: List[str]) -> Dict:
        """
        Count how many rows have all required features filled in.

        "Complete cases" are the rows a model can actually train on without
        needing imputation.  We also report partial availability — how many
        rows have at least one biomarker, and at least one cognitive score.

        Returns
        -------
        Dict with:
          total_records      — all rows in integrated dataset
          complete_cases     — rows with no NaN in feature_cols
          complete_cases_pct
          has_biomarker      — rows with ≥1 non-NaN biomarker
          has_cognitive      — rows with ≥1 non-NaN cognitive score
          has_both           — rows that have at least one of each
        """
        if self.integrated_data is None:
            self.create_integrated_dataset()

        available   = [c for c in feature_cols if c in self.integrated_data.columns]
        complete    = self.integrated_data[available].dropna()

        bio_cols = [c for c in ['pT217_F', 'AB42_AB40_F', 'NfL_Q', 'GFAP_Q']
                    if c in self.integrated_data.columns]
        cog_cols = [c for c in ['MOCA', 'TOTSCORE']
                    if c in self.integrated_data.columns]

        # Any available row means at least one column is non-NaN
        has_bio = self.integrated_data[bio_cols].notna().any(axis=1) if bio_cols else pd.Series(False, index=self.integrated_data.index)
        has_cog = self.integrated_data[cog_cols].notna().any(axis=1) if cog_cols else pd.Series(False, index=self.integrated_data.index)

        return {
            'total_records':       len(self.integrated_data),
            'complete_cases':      len(complete),
            'complete_cases_pct':  round(len(complete) / len(self.integrated_data) * 100, 1),
            'has_biomarker':       int(has_bio.sum()),
            'has_cognitive':       int(has_cog.sum()),
            'has_both':            int((has_bio & has_cog).sum()),
        }

    # -----------------------------------------------------------------------
    # Target variable analysis
    # -----------------------------------------------------------------------

    def analyze_target_variable(self, target_col: str = 'CDGLOBAL') -> Dict:
        """
        Examine the distribution of the prediction target variable.

        CDR Global score is the standard target for Alzheimer's classification:
          0   = cognitively normal
          0.5 = mild cognitive impairment (MCI)
          1   = mild dementia
          2   = moderate dementia
          3   = severe dementia

        We also compute:
          - Binary Alzheimer's-positive:  CDR > 0
          - Binary MCI or worse:          CDR >= 0.5
          - Class imbalance ratio:        most frequent class / least frequent class

        A high imbalance ratio means training a model will be tricky —
        you'll need class-weighting, oversampling (SMOTE), or other strategies.

        Returns
        -------
        Dict
        """
        if self.integrated_data is None:
            self.create_integrated_dataset()

        if target_col not in self.integrated_data.columns:
            return {'error': f"Target column '{target_col}' not found in integrated data"}

        target = self.integrated_data[target_col].dropna()
        target = target[target >= 0]

        distribution = target.value_counts().sort_index().to_dict()

        binary_targets = {}
        if target_col == 'CDGLOBAL':
            binary_targets['CDR_Positive'] = {
                'n':   int((target > 0).sum()),
                'pct': round((target > 0).mean() * 100, 1),
            }
            binary_targets['MCI_or_Worse'] = {
                'n':   int((target >= 0.5).sum()),
                'pct': round((target >= 0.5).mean() * 100, 1),
            }

        counts = list(distribution.values())
        imbalance_ratio = max(counts) / min(counts) if len(counts) >= 2 else None

        return {
            'target_column':  target_col,
            'n_valid':        len(target),
            'distribution':   distribution,
            'binary_targets': binary_targets,
            'imbalance_ratio': round(imbalance_ratio, 2) if imbalance_ratio else None,
        }

    # -----------------------------------------------------------------------
    # Full assessment entry-point
    # -----------------------------------------------------------------------

    def full_ml_assessment(self) -> Dict:
        """
        Run all ML readiness checks in one call.

        Feature columns assessed:
          pT217_F, AB42_AB40_F, NfL_Q, GFAP_Q — plasma biomarkers
          MOCA, TOTSCORE                         — cognitive scores

        Returns
        -------
        Dict with keys:
          'feature_variance', 'multicollinearity', 'missing_data',
          'complete_cases', 'target_analysis'
        """
        feature_cols = ['pT217_F', 'AB42_AB40_F', 'NfL_Q', 'GFAP_Q',
                        'MOCA', 'TOTSCORE']

        return {
            'feature_variance':   self.analyze_feature_variance(feature_cols),
            'multicollinearity':  self.analyze_multicollinearity(feature_cols),
            'missing_data':       self.analyze_missing_data_pattern(feature_cols),
            'complete_cases':     self.analyze_complete_cases(feature_cols),
            'target_analysis':    self.analyze_target_variable('CDGLOBAL'),
        }

    # -----------------------------------------------------------------------
    # Console report
    # -----------------------------------------------------------------------

    def print_ml_report(self):
        """Print the full ML readiness assessment to the terminal."""
        results = self.full_ml_assessment()

        print("=" * 100)
        print("MACHINE LEARNING READINESS ASSESSMENT")
        print("=" * 100)

        print("\n--- FEATURE VARIANCE ---")
        print(results['feature_variance'].to_string(index=False))

        print("\n--- MULTICOLLINEARITY ---")
        mc = results['multicollinearity']
        if 'correlation_matrix' in mc:
            print(mc['correlation_matrix'].round(3).to_string())
            if mc['n_high_correlations'] > 0:
                print("\nHigh Correlation Pairs (|r| > 0.7):")
                print(mc['high_correlation_pairs'].to_string(index=False))
            else:
                print("\nNo high correlations detected.")

        print("\n--- MISSING DATA ---")
        print(results['missing_data'].to_string(index=False))

        print("\n--- COMPLETE CASES ---")
        cc = results['complete_cases']
        print(f"  Total records:  {cc['total_records']:,}")
        print(f"  Complete cases: {cc['complete_cases']:,} ({cc['complete_cases_pct']:.1f}%)")
        print(f"  Has biomarker:  {cc['has_biomarker']:,}")
        print(f"  Has cognitive:  {cc['has_cognitive']:,}")
        print(f"  Has both:       {cc['has_both']:,}")

        print("\n--- TARGET VARIABLE (CDR Global) ---")
        ta = results['target_analysis']
        if 'distribution' in ta:
            print(f"  Valid samples:     {ta['n_valid']:,}")
            print(f"  Score distribution: {ta['distribution']}")
            for name, info in ta.get('binary_targets', {}).items():
                print(f"  {name}: {info['n']:,} ({info['pct']:.1f}%)")
            if ta.get('imbalance_ratio'):
                print(f"  Class imbalance ratio: {ta['imbalance_ratio']:.2f}:1")


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from src.data.loader import load_and_preprocess_adni_data

    datasets, _ = load_and_preprocess_adni_data()
    analyzer = MLReadinessAnalyzer(datasets)
    analyzer.print_ml_report()
