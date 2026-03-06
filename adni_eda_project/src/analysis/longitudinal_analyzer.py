"""
src/analysis/longitudinal_analyzer.py
---------------------------------------
Analyses how data changes over time within ADNI.

"Longitudinal" means the same participants are followed at many visits over
months or years.  This is central to Alzheimer's research: you want to know
whether a biomarker changes before symptoms appear, and how fast decline happens.

This module answers questions like:
  - How many times was each participant measured?
  - Which visit codes (bl, m06, m12 …) appear most often?
  - Over how many calendar years does each dataset span?
  - How long (in days) is the gap between consecutive visits?
  - Which ADNI study phases (ADNI1, ADNI2, ADNI3, ADNI4) contribute data?
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


class LongitudinalAnalyzer:
    """
    Analyses longitudinal (time-series) patterns in ADNI data.

    Key concepts:
      - RID       = unique participant identifier
      - VISCODE   = visit code label (e.g. 'bl' for baseline, 'm12' for month 12)
      - EXAMDATE  = calendar date of the visit

    Typical workflow:
        analyzer = LongitudinalAnalyzer(datasets)
        patterns = analyzer.analyze_visit_patterns('MOCA_13Feb2026')
        summary  = analyzer.get_visit_summary_table()
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
    # Single-dataset visit patterns
    # -----------------------------------------------------------------------

    def analyze_visit_patterns(self, dataset_name: str) -> Dict:
        """
        Count and summarise visits per participant in one dataset.

        Returns
        -------
        Dict with keys:
          total_participants         — how many unique people appear
          total_visits               — total rows (each row = one visit)
          mean_visits_per_participant
          median_visits_per_participant
          max_visits                 — most visits any one person has
          participants_with_1_visit  — people measured only once (no follow-up)
          participants_with_2plus_visits
          participants_with_3plus_visits
          pct_2plus_visits           — fraction of participants with ≥2 visits
          viscode_distribution       — top-15 visit codes and their counts
          viscode2_distribution      — same for VISCODE2
          date_range                 — {min, max} dates if a date column exists
          date_span_years            — calendar span in years
        """
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        df = self.datasets[dataset_name]['df']

        if 'RID' not in df.columns:
            return {'error': 'No RID column — cannot count visits per participant'}

        visits_per_participant = df.groupby('RID').size()

        results = {
            'total_participants':              int(df['RID'].nunique()),
            'total_visits':                    len(df),
            'mean_visits_per_participant':     float(visits_per_participant.mean()),
            'median_visits_per_participant':   float(visits_per_participant.median()),
            'max_visits':                      int(visits_per_participant.max()),
            'participants_with_1_visit':       int((visits_per_participant == 1).sum()),
            'participants_with_2plus_visits':  int((visits_per_participant >= 2).sum()),
            'participants_with_3plus_visits':  int((visits_per_participant >= 3).sum()),
            # Express as a percentage so we can compare datasets of different sizes
            'pct_2plus_visits': float((visits_per_participant >= 2).mean() * 100),
        }

        # Visit code distributions — shows which timepoints dominate
        if 'VISCODE' in df.columns:
            results['viscode_distribution'] = (
                df['VISCODE'].value_counts().head(15).to_dict()
            )
        if 'VISCODE2' in df.columns:
            results['viscode2_distribution'] = (
                df['VISCODE2'].value_counts().head(15).to_dict()
            )

        # Date range — use the first valid date column found
        date_cols = self.datasets[dataset_name].get('date_columns', [])
        for col in date_cols:
            if col not in df.columns:
                continue
            dates = df[col].dropna()
            if len(dates) == 0:
                continue

            results['date_column'] = col
            results['date_range']  = {'min': dates.min(), 'max': dates.max()}

            span = dates.max() - dates.min()
            if hasattr(span, 'days'):
                results['date_span_days']  = span.days
                results['date_span_years'] = round(span.days / 365.25, 1)
            break  # stop after first valid date column

        return results

    # -----------------------------------------------------------------------
    # Batch analysis across all datasets
    # -----------------------------------------------------------------------

    def analyze_all_datasets(self) -> Dict[str, Dict]:
        """
        Run analyze_visit_patterns() on every dataset that has an RID column.

        Returns
        -------
        Dict[str, Dict]
            {dataset_name: visit_pattern_result}
        """
        results = {}
        for name, data in self.datasets.items():
            if 'RID' in data['df'].columns:
                try:
                    results[name] = self.analyze_visit_patterns(name)
                except Exception as e:
                    results[name] = {'error': str(e)}
        return results

    # -----------------------------------------------------------------------
    # Study phase distribution
    # -----------------------------------------------------------------------

    def get_study_phase_distribution(self) -> pd.DataFrame:
        """
        Tally how many records come from each ADNI phase across all datasets.

        ADNI has run in several phases:
          ADNI1  (~2004–2009) — initial cohort
          ADNIGO (~2009–2011) — focused on MCI intervention
          ADNI2  (~2011–2016) — expanded biomarker panel
          ADNI3  (~2016–2023) — tau PET and blood biomarkers
          ADNI4  (~2023–)     — fully blood-based screening

        Returns
        -------
        pd.DataFrame
            Columns: Phase, Count — sorted by record count descending.
        """
        phase_data = []

        for name, data in self.datasets.items():
            df = data['df']
            if 'PHASE' not in df.columns:
                continue

            for phase, count in df['PHASE'].value_counts().items():
                phase_data.append({'Dataset': name, 'Phase': phase, 'Count': int(count)})

        if not phase_data:
            return pd.DataFrame()

        phase_df = pd.DataFrame(phase_data)

        # Aggregate counts across all datasets — one row per phase
        summary = phase_df.groupby('Phase')['Count'].sum().sort_values(ascending=False)
        return summary.reset_index()

    # -----------------------------------------------------------------------
    # Visit-interval calculation
    # -----------------------------------------------------------------------

    def calculate_visit_intervals(self, dataset_name: str) -> pd.DataFrame:
        """
        For each participant in a dataset, calculate the number of days
        between consecutive visits.

        This reveals whether follow-up is actually happening at 6-month
        or 12-month intervals as planned, or whether there are long gaps
        (e.g. due to COVID-19 study disruptions).

        Parameters
        ----------
        dataset_name : str
            Dataset to use (must have a date column and RID).

        Returns
        -------
        pd.DataFrame
            Columns: RID, Interval_Days, Interval_Months
            One row per consecutive-visit pair per participant.
            Empty DataFrame if no date column is found.
        """
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        df = self.datasets[dataset_name]['df']

        # Try a few common date column names
        date_col = next(
            (c for c in ['EXAMDATE', 'VISDATE', 'USERDATE'] if c in df.columns),
            None
        )
        if date_col is None:
            return pd.DataFrame()

        intervals = []

        for rid, group in df.groupby('RID'):
            # Sort visits by date; skip participants with fewer than 2 visits
            dates = group[date_col].dropna().sort_values()
            if len(dates) < 2:
                continue

            # Calculate each consecutive gap
            for i in range(1, len(dates)):
                gap_days = (dates.iloc[i] - dates.iloc[i - 1]).days
                intervals.append({
                    'RID':             rid,
                    'Interval_Days':   gap_days,
                    'Interval_Months': round(gap_days / 30.44, 1),
                })

        return pd.DataFrame(intervals)

    # -----------------------------------------------------------------------
    # Temporal coverage
    # -----------------------------------------------------------------------

    def analyze_temporal_coverage(self) -> pd.DataFrame:
        """
        For every dataset that has a date column, report the earliest and
        latest date present and the resulting time span.

        Useful for spotting datasets that only cover a sub-period of ADNI
        or that have implausible dates due to data-entry errors.

        Returns
        -------
        pd.DataFrame
            Columns: Dataset, Date_Column, Min_Date, Max_Date, Span_Days, Span_Years
        """
        rows = []

        for name, data in self.datasets.items():
            df = data['df']
            date_cols = data.get('date_columns', [])

            for col in date_cols:
                if col not in df.columns:
                    continue
                dates = df[col].dropna()
                if len(dates) == 0:
                    continue

                span = dates.max() - dates.min()
                rows.append({
                    'Dataset':    name,
                    'Date_Column': col,
                    'Min_Date':    dates.min(),
                    'Max_Date':    dates.max(),
                    'Span_Days':   span.days if hasattr(span, 'days') else None,
                    'Span_Years':  round(span.days / 365.25, 1) if hasattr(span, 'days') else None,
                })
                break  # only the first valid date column per dataset

        return pd.DataFrame(rows)

    # -----------------------------------------------------------------------
    # Summary table for the most important datasets
    # -----------------------------------------------------------------------

    def get_visit_summary_table(self) -> pd.DataFrame:
        """
        Build a compact summary of visit patterns for the four datasets most
        commonly used in ADNI analyses.

        Returns
        -------
        pd.DataFrame
            Columns: Dataset, Participants, Total_Visits, Mean_Visits,
                     Max_Visits, Pct_2Plus_Visits
        """
        key_datasets = [
            'UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026',
            'MOCA_13Feb2026',
            'CDR_13Feb2026',
            'ADAS_13Feb2026',
        ]

        rows = []
        for name in key_datasets:
            if name not in self.datasets:
                continue

            analysis = self.analyze_visit_patterns(name)
            if 'error' in analysis:
                continue

            rows.append({
                'Dataset':        name,
                'Participants':   analysis['total_participants'],
                'Total_Visits':   analysis['total_visits'],
                'Mean_Visits':    round(analysis['mean_visits_per_participant'], 2),
                'Max_Visits':     analysis['max_visits'],
                'Pct_2Plus_Visits': round(analysis['pct_2plus_visits'], 1),
            })

        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from src.data.loader import load_and_preprocess_adni_data

    datasets, _ = load_and_preprocess_adni_data()
    analyzer = LongitudinalAnalyzer(datasets)

    print("Visit Pattern Summary:")
    print("=" * 80)
    for name in ['UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026',
                 'MOCA_13Feb2026', 'CDR_13Feb2026']:
        if name not in datasets:
            continue
        result = analyzer.analyze_visit_patterns(name)
        print(f"\n{name}:")
        print(f"  Participants:     {result['total_participants']:,}")
        print(f"  Mean visits:      {result['mean_visits_per_participant']:.2f}")
        print(f"  % with ≥2 visits: {result['pct_2plus_visits']:.1f}%")
