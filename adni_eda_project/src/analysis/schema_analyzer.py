"""
src/analysis/schema_analyzer.py
--------------------------------
Examines the structure of every loaded ADNI dataset and answers questions
like:
  - How large is each file?
  - Which "join keys" (RID, VISCODE, PHASE) does it contain?
  - How much data is missing?
  - Which datasets can be merged together?

Think of this as a health-check step that runs before any statistics.
You want to know what you're working with before you start analysing it.
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from config.settings import ID_COLUMNS, MISSING_HIGH_THRESHOLD


class SchemaAnalyzer:
    """
    Analyses the structure (schema) of ADNI datasets.

    A "schema" in this context means: what columns exist, what types they
    are, how complete they are, and how datasets relate to each other via
    shared identifiers (RID, VISCODE2, etc.).

    Typical workflow:
        analyzer = SchemaAnalyzer(datasets)
        schema_info = analyzer.analyze_all()       # analyse every dataset
        summary_table = analyzer.get_summary_table()
        join_matrix  = analyzer.get_join_analysis()
    """

    def __init__(self, datasets: Dict[str, Dict]):
        """
        Parameters
        ----------
        datasets : Dict[str, Dict]
            The dictionary returned by load_and_preprocess_adni_data().
            Each value has at least 'df' (DataFrame) and 'category' (str).
        """
        self.datasets = datasets

        # Will hold one result dict per dataset name after analyze_all() runs
        self.schema_info: Dict[str, Dict] = {}

    # -----------------------------------------------------------------------
    # Core analysis — single dataset
    # -----------------------------------------------------------------------

    def analyze_dataset(self, name: str) -> Dict:
        """
        Run schema analysis on one named dataset and store the result.

        What we measure:
          - Dimensions (rows × columns)
          - Memory footprint in MB
          - Presence and fill-rate of each ID column (RID, PTID, VISCODE…)
          - Overall missing-data percentage
          - Number of "sparse" columns (>50% missing)
          - Duplicate rows

        Parameters
        ----------
        name : str
            A key from self.datasets (e.g. 'CDR_13Feb2026').

        Returns
        -------
        Dict
            Analysis results for this dataset, also stored in self.schema_info.
        """
        if name not in self.datasets:
            raise ValueError(f"Dataset '{name}' not found in loaded datasets")

        df = self.datasets[name]['df']
        rows, cols = df.shape

        # --- Key column audit -----------------------------------------------
        # For each expected ID column, record whether it exists and
        # how complete it is (non-null count, unique values, coverage %).
        key_info = {}
        for key in ID_COLUMNS:
            if key in df.columns:
                non_null = int(df[key].notna().sum())
                unique   = int(df[key].nunique())
                coverage = non_null / rows * 100 if rows > 0 else 0
                key_info[key] = {
                    'present':  True,
                    'non_null': non_null,
                    'unique':   unique,
                    'coverage': round(coverage, 1),
                }
            else:
                key_info[key] = {'present': False}

        # --- Missing data ---------------------------------------------------
        missing_per_col = df.isnull().sum()
        total_cells     = rows * cols
        total_missing   = int(missing_per_col.sum())
        missing_pct     = total_missing / total_cells * 100 if total_cells > 0 else 0

        # "Sparse" = more than 50% of values in that column are missing
        sparse_cols = missing_per_col[
            missing_per_col > rows * MISSING_HIGH_THRESHOLD
        ].index.tolist()

        # --- Other quality checks -------------------------------------------
        dup_rows   = int(df.duplicated().sum())
        memory_mb  = float(df.memory_usage(deep=True).sum() / (1024 ** 2))
        date_cols  = self.datasets[name].get('date_columns', [])

        result = {
            'name':                name,
            'category':            self.datasets[name]['category'],
            'rows':                rows,
            'columns':             cols,
            'memory_mb':           round(memory_mb, 2),
            'key_columns':         key_info,
            'missing_pct':         round(missing_pct, 2),
            'sparse_columns':      len(sparse_cols),
            'sparse_column_names': sparse_cols,
            'duplicate_rows':      dup_rows,
            'date_columns':        date_cols,
        }

        self.schema_info[name] = result
        return result

    # -----------------------------------------------------------------------
    # Batch analysis
    # -----------------------------------------------------------------------

    def analyze_all(self) -> Dict[str, Dict]:
        """
        Run analyze_dataset() on every loaded dataset.

        Returns
        -------
        Dict[str, Dict]
            {dataset_name: schema_result, ...}
        """
        print("Analysing schema for all datasets...\n")
        for name in sorted(self.datasets.keys()):
            self.analyze_dataset(name)
            print(f"  ✓ {name}")
        print(f"\nCompleted schema analysis for {len(self.schema_info)} datasets")
        return self.schema_info

    # -----------------------------------------------------------------------
    # Join / relationship analysis
    # -----------------------------------------------------------------------

    def get_join_analysis(self) -> pd.DataFrame:
        """
        Build a matrix showing how many non-null values each dataset has for
        each ID column.

        Reading this table: if a row has a number under RID and VISCODE2,
        that dataset can be merged with another on those two keys. A '-' means
        the column is absent in that dataset.

        Returns
        -------
        pd.DataFrame
            Rows = datasets, Columns = ID columns (RID, PTID, …)
        """
        if not self.schema_info:
            self.analyze_all()

        rows = []
        for name, info in self.schema_info.items():
            row = {'Dataset': name}
            for key in ID_COLUMNS:
                kinfo = info['key_columns'].get(key, {})
                row[key] = kinfo['non_null'] if kinfo.get('present') else '-'
            rows.append(row)

        return pd.DataFrame(rows)

    def find_joinable_datasets(self, keys: List[str]) -> List[str]:
        """
        Return the names of datasets that have ALL of the specified keys.

        Example:
            find_joinable_datasets(['RID', 'VISCODE2'])
            → only datasets that have both RID and VISCODE2 can be merged
              using those two columns as join keys.

        Parameters
        ----------
        keys : List[str]
            Required join key columns (subset of ID_COLUMNS).

        Returns
        -------
        List[str]
            Dataset names with all keys present.
        """
        if not self.schema_info:
            self.analyze_all()

        return [
            name
            for name, info in self.schema_info.items()
            if all(
                info['key_columns'].get(k, {}).get('present', False)
                for k in keys
            )
        ]

    def get_relationship_map(self) -> Dict[str, List[str]]:
        """
        Group datasets by the join-key combination they support.

        Three groups:
          'rid_viscode2' — can be merged on (RID, VISCODE2)  [most common]
          'rid_viscode'  — can be merged on (RID, VISCODE)
          'rid_only'     — have RID but no visit codes (e.g. static genetics data)

        Returns
        -------
        Dict[str, List[str]]
        """
        if not self.schema_info:
            self.analyze_all()

        relationships = {
            'rid_viscode2': self.find_joinable_datasets(['RID', 'VISCODE2']),
            'rid_viscode':  self.find_joinable_datasets(['RID', 'VISCODE']),
            'rid_only':     [],
        }

        # A dataset with RID but no VISCODE at all (e.g. APOE genotype — one
        # value per person, not per visit)
        for name, info in self.schema_info.items():
            has_rid      = info['key_columns'].get('RID',      {}).get('present', False)
            has_viscode  = info['key_columns'].get('VISCODE',  {}).get('present', False)
            has_viscode2 = info['key_columns'].get('VISCODE2', {}).get('present', False)
            if has_rid and not has_viscode and not has_viscode2:
                relationships['rid_only'].append(name)

        return relationships

    # -----------------------------------------------------------------------
    # Summary tables for reporting
    # -----------------------------------------------------------------------

    def get_summary_table(self) -> pd.DataFrame:
        """
        Produce a flat summary row for each dataset — convenient for CSV export
        and for building visualisations.

        Returns
        -------
        pd.DataFrame
            Sorted by category then row-count (largest first).
        """
        if not self.schema_info:
            self.analyze_all()

        rows = []
        for name, info in self.schema_info.items():
            kc = info['key_columns']
            rows.append({
                'Dataset':        name,
                'Category':       info['category'],
                'Rows':           info['rows'],
                'Columns':        info['columns'],
                'Memory_MB':      info['memory_mb'],
                'Has_RID':        kc.get('RID',      {}).get('present', False),
                'Has_PTID':       kc.get('PTID',     {}).get('present', False),
                'Has_VISCODE':    kc.get('VISCODE',  {}).get('present', False),
                'Has_VISCODE2':   kc.get('VISCODE2', {}).get('present', False),
                'Has_PHASE':      kc.get('PHASE',    {}).get('present', False),
                'Unique_RID':     kc.get('RID',      {}).get('unique', 0),
                'Missing_Pct':    info['missing_pct'],
                'Sparse_Cols':    info['sparse_columns'],
                'Duplicate_Rows': info['duplicate_rows'],
            })

        df = pd.DataFrame(rows)
        return df.sort_values(['Category', 'Rows'], ascending=[True, False])

    def get_category_aggregates(self) -> pd.DataFrame:
        """
        Aggregate schema statistics across the three domain categories
        (biospecimen, neuropsychological, imaging_mri).

        Useful for a high-level summary: 'how many files and rows in each domain?'

        Returns
        -------
        pd.DataFrame
            Index = category name, columns = aggregate statistics.
        """
        summary = self.get_summary_table()

        agg = summary.groupby('Category').agg(
            Files          = ('Dataset',     'count'),
            Total_Rows     = ('Rows',        'sum'),
            Avg_Cols       = ('Columns',     'mean'),
            Total_Memory_MB= ('Memory_MB',   'sum'),
            Total_Unique_RID=('Unique_RID',  'sum'),
            Avg_Missing_Pct= ('Missing_Pct', 'mean'),
            Total_Sparse   = ('Sparse_Cols', 'sum'),
        ).round(2)

        return agg

    # -----------------------------------------------------------------------
    # Console report
    # -----------------------------------------------------------------------

    def print_detailed_report(self):
        """
        Print a full human-readable schema report to the terminal.
        Useful for a quick audit when you first get new ADNI data.
        """
        if not self.schema_info:
            self.analyze_all()

        print("=" * 100)
        print("SCHEMA ANALYSIS REPORT")
        print("=" * 100)

        for name, info in sorted(self.schema_info.items()):
            kc = info['key_columns']
            print(f"\n{'─' * 100}")
            print(f"DATASET: {name}  |  Category: {info['category'].upper()}")
            print(f"{'─' * 100}")
            print(f"  Dimensions:     {info['rows']:,} rows × {info['columns']} columns")
            print(f"  Memory:         {info['memory_mb']:.2f} MB")

            # Summarise which join keys are present
            flag = lambda k: kc.get(k, {}).get('present', False)
            print(
                f"  Key Columns:    RID={flag('RID')}, PTID={flag('PTID')}, "
                f"VISCODE={flag('VISCODE')}, VISCODE2={flag('VISCODE2')}, "
                f"PHASE={flag('PHASE')}"
            )

            if flag('RID'):
                print(f"  Unique RIDs:    {kc['RID'].get('unique', 0):,}")

            print(f"  Missing Data:   {info['missing_pct']:.2f}%")
            print(f"  Sparse Columns: {info['sparse_columns']} (>50% missing)")
            print(f"  Duplicate Rows: {info['duplicate_rows']:,}")

        # Tabular summary
        print("\n" + "=" * 100)
        print("SUMMARY TABLE")
        print("=" * 100)
        print(self.get_summary_table().to_string(index=False))

        print("\n" + "=" * 100)
        print("AGGREGATES BY CATEGORY")
        print("=" * 100)
        print(self.get_category_aggregates().to_string())


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from src.data.loader import load_and_preprocess_adni_data

    datasets, _ = load_and_preprocess_adni_data()
    analyzer = SchemaAnalyzer(datasets)
    analyzer.print_detailed_report()
