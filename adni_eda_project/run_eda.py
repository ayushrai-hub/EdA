#!/usr/bin/env python3
"""
run_eda.py
----------
Main entry point for the ADNI EDA pipeline.

Runs the full analysis in six sequential phases:
  Phase 1 — Load and preprocess all datasets
  Phase 2 — Schema analysis (structure, keys, missing data)
  Phase 3 — Statistical analysis (descriptive stats, outliers, correlations)
  Phase 4 — Longitudinal analysis (visit patterns, temporal coverage)
  Phase 5 — ML readiness assessment (variance, collinearity, complete cases)
  Phase 6 — Figure generation (saves PNG files to output/visualizations/)

Usage from the project root:
  python run_eda.py --data-dir /path/to/adni/csv/files
  python run_eda.py --data-dir /path/to/data --output-dir ./results
  python run_eda.py --data-dir /path/to/data --skip-viz
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Make sure Python can find the project's src/ and config/ modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import all the modules that do the actual work
from src.data.loader          import load_and_preprocess_adni_data
from src.analysis.schema_analyzer     import SchemaAnalyzer
from src.analysis.statistical_analyzer import StatisticalAnalyzer
from src.analysis.longitudinal_analyzer import LongitudinalAnalyzer
from src.analysis.ml_readiness         import MLReadinessAnalyzer
from src.visualization.plots           import ADNIVisualizer

from config.settings import DATA_DIR, OUTPUT_DIR


# ===========================================================================
# ARGUMENT PARSING
# ===========================================================================

def parse_arguments():
    """
    Parse command-line arguments.

    Why argparse?
      It lets you change key settings (e.g. the data directory) without
      editing the source code — just pass a different --data-dir flag.
    """
    parser = argparse.ArgumentParser(
        description='ADNI Exploratory Data Analysis Pipeline',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=DATA_DIR,
        help='Directory containing ADNI CSV files',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=OUTPUT_DIR,
        help='Directory to write all outputs (tables, figures, reports)',
    )
    parser.add_argument(
        '--skip-viz',
        action='store_true',
        help='Skip figure generation (faster when you only need the CSVs)',
    )
    return parser.parse_args()


# ===========================================================================
# MAIN EDA PIPELINE
# ===========================================================================

def run_eda_pipeline(data_dir: Path, output_dir: Path, skip_viz: bool = False):
    """
    Orchestrate the full EDA from data loading through to figure generation.

    Each phase is clearly separated and its outputs are saved before the
    next phase begins — this way, if the pipeline crashes mid-way, you
    still have the outputs of completed phases.

    Parameters
    ----------
    data_dir : Path
        Folder containing all ADNI CSV files.
    output_dir : Path
        Root output folder; sub-folders tables/, reports/, visualizations/
        are created automatically.
    skip_viz : bool
        If True, Phase 6 (figure generation) is skipped.
    """
    print("=" * 100)
    print("ADNI COMPREHENSIVE EXPLORATORY DATA ANALYSIS")
    print("=" * 100)
    print(f"\nStarted:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data directory:   {data_dir}")
    print(f"Output directory: {output_dir}")

    # =========================================================================
    # PHASE 1 — Data Loading
    # =========================================================================
    print("\n" + "=" * 100)
    print("PHASE 1: DATA LOADING AND PREPROCESSING")
    print("=" * 100)

    # load_and_preprocess_adni_data does three things in sequence:
    #   1. Find all unique CSV files (deduplication by MD5 hash)
    #   2. Replace sentinel values (-4, 'NA', etc.) with NaN
    #   3. Parse date string columns into datetime objects
    datasets, summary_df = load_and_preprocess_adni_data(data_dir)

    # Save the top-level dataset inventory
    summary_df.to_csv(output_dir / 'tables' / 'dataset_summary.csv', index=False)
    print(f"\n  ✓ Loaded {len(datasets)} datasets")
    print(f"  ✓ Saved: output/tables/dataset_summary.csv")

    # =========================================================================
    # PHASE 2 — Schema Analysis
    # =========================================================================
    print("\n" + "=" * 100)
    print("PHASE 2: SCHEMA ANALYSIS")
    print("=" * 100)

    schema_analyzer = SchemaAnalyzer(datasets)
    schema_info     = schema_analyzer.analyze_all()

    # Save the per-dataset schema summary
    schema_df = schema_analyzer.get_summary_table()
    schema_df.to_csv(output_dir / 'tables' / 'schema_analysis.csv', index=False)
    print(f"\n  ✓ Saved: output/tables/schema_analysis.csv")

    # Show which datasets can be joined together
    print("\n--- Join Key Availability ---")
    print(schema_analyzer.get_join_analysis().to_string(index=False))

    print("\n--- Dataset Relationship Map ---")
    rel_map = schema_analyzer.get_relationship_map()
    for group_name, dataset_list in rel_map.items():
        print(f"  {group_name}: {len(dataset_list)} datasets")

    # =========================================================================
    # PHASE 3 — Statistical Analysis
    # =========================================================================
    print("\n" + "=" * 100)
    print("PHASE 3: STATISTICAL ANALYSIS")
    print("=" * 100)

    stat_analyzer = StatisticalAnalyzer(datasets)

    # --- Biomarker statistics ---
    print("\n--- Plasma Biomarker Analysis ---")
    bio_results = stat_analyzer.analyze_biomarkers()
    print(f"  Dataset: {bio_results['dataset']}")
    print(f"  Samples: {bio_results['total_samples']:,} | Participants: "
          f"{bio_results['unique_participants']:,}")
    print("\n  Descriptive Statistics:")
    print(bio_results['descriptive_stats'].round(4).to_string(index=False))

    # Save biomarker analysis CSVs
    bio_results['descriptive_stats'].to_csv(
        output_dir / 'tables' / 'biomarker_statistics.csv', index=False
    )
    bio_results['outliers_iqr'].to_csv(
        output_dir / 'tables' / 'biomarker_outliers.csv', index=False
    )
    print("\n  ✓ Saved: output/tables/biomarker_statistics.csv")
    print("  ✓ Saved: output/tables/biomarker_outliers.csv")

    # --- Cognitive assessment statistics ---
    print("\n--- Cognitive Assessment Analysis ---")
    cog_results = stat_analyzer.analyze_cognitive_assessments()
    for name, result in cog_results.items():
        print(f"\n  {name}:")
        print(f"    Assessments: {result['total_assessments']:,} | "
              f"Participants: {result['unique_participants']:,}")
        print(result['descriptive_stats'].round(2).to_string(index=False))

    # --- MRI imaging statistics ---
    print("\n--- MRI Imaging Analysis ---")
    try:
        img_results = stat_analyzer.analyze_imaging()
        print(f"  Dataset: {img_results['dataset']}")
        print(f"  Scans:   {img_results['total_scans']:,} | "
              f"Participants: {img_results['unique_participants']:,}")
        print(img_results['descriptive_stats'].round(2).to_string(index=False))

        if 'total_hippocampal_volume' in img_results:
            hv = img_results['total_hippocampal_volume']
            print(f"\n  Total Hippocampal Volume: "
                  f"Mean={hv['Mean']:.0f} mm³, Std={hv['Std']:.0f} mm³")
    except ValueError as e:
        print(f"  [Skipped: {e}]")

    # --- Cross-domain correlations ---
    print("\n--- Multimodal Correlation Analysis ---")
    corr_results = stat_analyzer.multimodal_correlation_analysis()

    if 'biomarker_cognitive' in corr_results:
        bc = corr_results['biomarker_cognitive']
        print(f"\n  Biomarker × Cognitive correlations "
              f"(n={bc['n_records']:,} records, {bc['n_participants']:,} participants):")
        print(bc['correlation_matrix'].round(3).to_string())
        bc['correlation_matrix'].to_csv(
            output_dir / 'tables' / 'correlation_matrix.csv'
        )
        print("  ✓ Saved: output/tables/correlation_matrix.csv")

    if 'biomarker_imaging' in corr_results:
        bi = corr_results['biomarker_imaging']
        print(f"\n  Biomarker × Imaging correlations "
              f"(n={bi['n_participants']:,} participants):")
        print(bi['correlation_matrix'].round(3).to_string())

    # =========================================================================
    # PHASE 4 — Longitudinal Analysis
    # =========================================================================
    print("\n" + "=" * 100)
    print("PHASE 4: LONGITUDINAL ANALYSIS")
    print("=" * 100)

    long_analyzer = LongitudinalAnalyzer(datasets)

    # Visit pattern table for key datasets
    print("\n--- Visit Patterns (key datasets) ---")
    visit_summary = long_analyzer.get_visit_summary_table()
    print(visit_summary.to_string(index=False))
    visit_summary.to_csv(output_dir / 'tables' / 'visit_patterns.csv', index=False)
    print("  ✓ Saved: output/tables/visit_patterns.csv")

    # Record counts per ADNI study phase
    print("\n--- Study Phase Distribution ---")
    phase_dist = long_analyzer.get_study_phase_distribution()
    if not phase_dist.empty:
        print(phase_dist.to_string(index=False))

    # Earliest and latest dates per dataset
    print("\n--- Temporal Coverage ---")
    temporal = long_analyzer.analyze_temporal_coverage()
    if not temporal.empty:
        print(temporal.to_string(index=False))

    # =========================================================================
    # PHASE 5 — ML Readiness Assessment
    # =========================================================================
    print("\n" + "=" * 100)
    print("PHASE 5: MACHINE LEARNING READINESS ASSESSMENT")
    print("=" * 100)

    ml_analyzer = MLReadinessAnalyzer(datasets)
    ml_results  = ml_analyzer.full_ml_assessment()

    print("\n--- Feature Variance ---")
    print(ml_results['feature_variance'].round(4).to_string(index=False))
    ml_results['feature_variance'].to_csv(
        output_dir / 'tables' / 'ml_feature_variance.csv', index=False
    )
    print("  ✓ Saved: output/tables/ml_feature_variance.csv")

    print("\n--- Multicollinearity ---")
    mc = ml_results['multicollinearity']
    if 'correlation_matrix' in mc:
        print(mc['correlation_matrix'].round(3).to_string())
        n_high = mc['n_high_correlations']
        if n_high > 0:
            print(f"\n  ⚠  {n_high} pairs exceed |r| > 0.7 — consider removing one "
                  f"from each pair before training a linear model.")

    print("\n--- Complete Cases ---")
    cc = ml_results['complete_cases']
    print(f"  Total records:  {cc['total_records']:,}")
    print(f"  Complete cases: {cc['complete_cases']:,} ({cc['complete_cases_pct']:.1f}%)")
    print(f"  Has biomarker:  {cc['has_biomarker']:,}")
    print(f"  Has cognitive:  {cc['has_cognitive']:,}")
    print(f"  Has both:       {cc['has_both']:,}")

    print("\n--- Target Variable (CDR Global) ---")
    ta = ml_results['target_analysis']
    if 'distribution' in ta:
        print(f"  Valid samples:      {ta['n_valid']:,}")
        print(f"  Score distribution: {ta['distribution']}")
        for name, info in ta.get('binary_targets', {}).items():
            print(f"  {name}: {info['n']:,} ({info['pct']:.1f}%)")
        if ta.get('imbalance_ratio'):
            print(f"  Class imbalance ratio: {ta['imbalance_ratio']:.2f}:1")

    # =========================================================================
    # PHASE 6 — Visualization
    # =========================================================================
    if not skip_viz:
        print("\n" + "=" * 100)
        print("PHASE 6: GENERATING VISUALIZATIONS")
        print("=" * 100)

        visualizer = ADNIVisualizer(output_dir / 'visualizations')
        visualizer.create_all_visualizations(datasets, schema_info, summary_df)

        # Figure 04 (correlation heatmap) requires a correlation matrix object —
        # generate it now from the biomarker-cognitive analysis if available
        if 'biomarker_cognitive' in corr_results:
            visualizer.plot_correlation_heatmap(
                corr_results['biomarker_cognitive']['correlation_matrix']
            )

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 100)
    print("EDA PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 100)
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nOutput saved to: {output_dir}")
    print("\nGenerated files:")
    print("  Tables:         output/tables/*.csv")
    print("  Visualizations: output/visualizations/*.png")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    """Parse arguments and run the pipeline."""
    args = parse_arguments()

    # Create output sub-directories if they don't exist yet
    for sub in ['reports', 'tables', 'visualizations']:
        (args.output_dir / sub).mkdir(parents=True, exist_ok=True)

    run_eda_pipeline(args.data_dir, args.output_dir, args.skip_viz)


if __name__ == '__main__':
    main()
