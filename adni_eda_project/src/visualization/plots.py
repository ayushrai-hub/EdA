"""
src/visualization/plots.py
---------------------------
Generates all figures for the ADNI EDA project and saves them to disk.

Each method in ADNIVisualizer corresponds to one numbered figure:
  01 — Dataset overview by domain category
  02 — Missing data rates per dataset
  03 — Biomarker and cognitive score distributions (histograms)
  04 — Multimodal correlation heatmap
  05 — Study phase (ADNI1/2/3/4) breakdown
  06 — Longitudinal visit-count patterns
  07 — CDR Global score distribution (the ML target variable)

Design choices:
  - Non-interactive Agg backend so this works on servers without a display
  - seaborn whitegrid style for clean publication-ready backgrounds
  - The COLORS dict from settings ensures every figure has the same palette
"""

import matplotlib
matplotlib.use('Agg')   # must be set before importing pyplot (headless rendering)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import COLORS, FIGURE_DPI, FIGURE_FORMAT, FIGURE_SIZE


# Apply a consistent visual style for all figures
sns.set_style('whitegrid')
plt.rcParams['figure.dpi']   = FIGURE_DPI
plt.rcParams['savefig.dpi']  = FIGURE_DPI


class ADNIVisualizer:
    """
    Creates and saves EDA figures for ADNI data.

    Usage:
        viz = ADNIVisualizer(output_dir=Path('./output/visualizations'))
        viz.create_all_visualizations(datasets, schema_info, summary_df)
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Parameters
        ----------
        output_dir : Path, optional
            Where to save figures. Defaults to VISUALIZATIONS_DIR from settings.
        """
        from config.settings import VISUALIZATIONS_DIR
        self.output_dir = output_dir or VISUALIZATIONS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Internal save helper
    # -----------------------------------------------------------------------

    def save_figure(self, fig: plt.Figure, filename: str):
        """
        Save a matplotlib figure to disk and close it to free memory.

        Parameters
        ----------
        fig : plt.Figure
        filename : str
            Filename including extension, e.g. '01_dataset_overview.png'.
        """
        filepath = self.output_dir / filename
        fig.savefig(filepath, bbox_inches='tight', format=FIGURE_FORMAT)
        plt.close(fig)
        print(f"  Saved: {filename}")

    # -----------------------------------------------------------------------
    # Figure 01 — Dataset overview
    # -----------------------------------------------------------------------

    def plot_dataset_overview(
        self,
        summary_df: pd.DataFrame,
        filename: str = '01_dataset_overview.png'
    ):
        """
        Horizontal bar chart showing total record counts per domain category.

        Reading the chart: a taller bar means more total measurements in
        that domain — useful for understanding which domain drives sample size.

        Parameters
        ----------
        summary_df : pd.DataFrame
            Output of SchemaAnalyzer.get_summary_table(), with a 'Category'
            and 'Rows' column.
        """
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)

        # Aggregate total rows per category, sorted ascending for barh readability
        categories = summary_df.groupby('Category')['Rows'].sum().sort_values(ascending=True)
        colors     = [COLORS['primary'], COLORS['secondary'], COLORS['tertiary']]

        bars = ax.barh(categories.index, categories.values,
                       color=colors[:len(categories)])

        ax.set_xlabel('Total Records', fontsize=12)
        ax.set_title('ADNI Dataset Overview by Domain Category',
                     fontsize=14, fontweight='bold')

        # Add value labels just to the right of each bar
        x_pad = max(categories.values) * 0.02
        for bar, val in zip(bars, categories.values):
            ax.text(
                val + x_pad,
                bar.get_y() + bar.get_height() / 2,
                f'{val:,}',
                va='center', fontsize=10
            )

        ax.set_xlim(0, max(categories.values) * 1.15)
        sns.despine()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Figure 02 — Missing data
    # -----------------------------------------------------------------------

    def plot_missing_data(
        self,
        schema_info: Dict[str, Dict],
        filename: str = '02_missing_data.png'
    ):
        """
        Horizontal bar chart of missing-data percentage for each dataset,
        coloured by severity:
          Green  — < 10% missing
          Amber  — 10–30% missing
          Red    — > 30% missing

        Reference lines at 10% and 30% match the thresholds in settings.py.

        Parameters
        ----------
        schema_info : Dict[str, Dict]
            Output of SchemaAnalyzer.analyze_all().
        """
        fig, ax = plt.subplots(figsize=(14, 10))

        # Sort descending by missing % — worst datasets at the top
        sorted_info = sorted(
            schema_info.items(),
            key=lambda x: x[1]['missing_pct'],
            reverse=True
        )[:15]  # show worst 15 only so the chart remains readable

        labels   = [name[:30] for name, _ in sorted_info]
        pcts     = [info['missing_pct'] for _, info in sorted_info]

        bar_colors = [
            COLORS['danger']  if p > 30 else
            COLORS['warning'] if p > 10 else
            COLORS['success']
            for p in pcts
        ]

        bars = ax.barh(labels, pcts, color=bar_colors)
        ax.set_xlabel('Missing Data (%)', fontsize=12)
        ax.set_title('Missing Data by Dataset (Top 15 Worst)',
                     fontsize=14, fontweight='bold')

        # Reference lines at the severity thresholds
        ax.axvline(x=10, color='gray', linestyle='--', alpha=0.5, label='10% threshold')
        ax.axvline(x=30, color='gray', linestyle='--', alpha=0.5, label='30% threshold')
        ax.legend()

        # Label each bar with its actual percentage
        for bar, val in zip(bars, pcts):
            ax.text(
                val + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%',
                va='center', fontsize=9
            )

        sns.despine()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Figure 03 — Biomarker distributions
    # -----------------------------------------------------------------------

    def plot_biomarker_distributions(
        self,
        df: pd.DataFrame,
        filename: str = '03_biomarker_distributions.png'
    ):
        """
        2×3 grid of histograms showing the distribution of key biomarkers
        and cognitive scores.

        Why histograms?
          They reveal whether data is normally distributed (bell-shaped),
          right-skewed (most values are small but a few are very large —
          common for biomarkers like NfL), bi-modal (two clusters), etc.
          Each shape implies different statistical treatment.

        The red dashed line marks the median — a robust location estimate
        that isn't pulled by extreme outliers like the mean sometimes is.

        Parameters
        ----------
        df : pd.DataFrame
            The UPENN plasma + cognitive dataset (or any merged DataFrame).
        """
        from config.settings import COGNITIVE_COLUMNS

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()

        # Build the list of (column, display_label) pairs to plot
        biomarkers = [
            ('pT217_F',     'p-tau217 (pg/mL)'),
            ('AB42_AB40_F', 'Aβ42/40 Ratio'),
            ('NfL_Q',       'NfL (pg/mL)'),
            ('GFAP_Q',      'GFAP (pg/mL)'),
        ]
        # Supplement with any cognitive columns that happen to be in the DataFrame
        for col, label in COGNITIVE_COLUMNS.items():
            if col in df.columns:
                biomarkers.append((col, label))

        for i, (col, title) in enumerate(biomarkers[:6]):
            if col not in df.columns:
                continue

            data = df[col].dropna()
            data = data[data >= 0]

            # Remove extreme top-1% outliers so the x-axis isn't stretched by
            # a handful of physiologically implausible values
            q99  = data.quantile(0.99)
            data = data[data <= q99]

            axes[i].hist(data, bins=50, color=COLORS['primary'],
                         edgecolor='white', alpha=0.7)
            axes[i].set_title(title, fontsize=12, fontweight='bold')
            axes[i].set_xlabel('Measurement value')
            axes[i].set_ylabel('Frequency (count)')

            # Median line — robust measure of the centre of the distribution
            axes[i].axvline(
                data.median(), color='red', linestyle='--', linewidth=2,
                label=f'Median: {data.median():.2f}'
            )
            axes[i].legend(fontsize=9)

        plt.suptitle('Distribution of Key Biomarkers and Cognitive Scores',
                     fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Figure 04 — Correlation heatmap
    # -----------------------------------------------------------------------

    def plot_correlation_heatmap(
        self,
        corr_matrix: pd.DataFrame,
        filename: str = '04_correlation_heatmap.png'
    ):
        """
        Colour-coded grid where each cell shows the Pearson correlation
        between two variables.

        Colour scale:
          Deep blue → strong negative correlation (−1)
          White     → no correlation (0)
          Deep red  → strong positive correlation (+1)

        Cell annotations show the exact r value so readers can assess
        effect sizes without interpreting colour alone.

        Parameters
        ----------
        corr_matrix : pd.DataFrame
            Square correlation matrix (e.g. from StatisticalAnalyzer).
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1)

        # Tick labels for axes
        n = len(corr_matrix.columns)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
        ax.set_yticklabels(corr_matrix.columns)
        ax.set_title('Multimodal Correlation Matrix', fontsize=14, fontweight='bold')

        # Annotate each cell with the r value
        for row in range(n):
            for col in range(n):
                val = corr_matrix.iloc[row, col]
                if not np.isnan(val):
                    # Use white text on dark cells, black on light ones
                    txt_color = 'white' if abs(val) > 0.5 else 'black'
                    ax.text(col, row, f'{val:.2f}',
                            ha='center', va='center',
                            fontsize=10, color=txt_color)

        plt.colorbar(im, ax=ax, label='Pearson r')
        plt.tight_layout()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Figure 05 — Study phase distribution
    # -----------------------------------------------------------------------

    def plot_study_phases(
        self,
        phase_distribution: pd.DataFrame,
        filename: str = '05_study_phases.png'
    ):
        """
        Pie chart showing the proportion of records from each ADNI phase.

        Useful for understanding whether results might be biased toward a
        particular cohort (e.g. if 80% of data comes from ADNI4, analyses
        may not generalise to earlier phases).

        Parameters
        ----------
        phase_distribution : pd.DataFrame
            Output of LongitudinalAnalyzer.get_study_phase_distribution().
            Must have 'Phase' and 'Count' columns.
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        colors = [COLORS['primary'], COLORS['secondary'], COLORS['tertiary'],
                  COLORS['warning'], COLORS['info']]

        ax.pie(
            phase_distribution['Count'],
            labels=phase_distribution['Phase'],
            autopct='%1.1f%%',
            colors=colors[:len(phase_distribution)],
            startangle=90
        )
        ax.set_title('Study Phase Distribution — Records per ADNI Phase',
                     fontsize=14, fontweight='bold')

        plt.tight_layout()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Figure 06 — Longitudinal visit patterns
    # -----------------------------------------------------------------------

    def plot_longitudinal_patterns(
        self,
        visit_summaries: Dict[str, Dict],
        filename: str = '06_longitudinal_patterns.png'
    ):
        """
        Three side-by-side bar charts comparing mean and max visit counts
        for the three most important datasets.

        Purpose: quickly verify that a meaningful fraction of participants
        returned for multiple visits — a requirement for longitudinal analysis.
        If mean visits ≈ 1, the dataset is essentially cross-sectional.

        Parameters
        ----------
        visit_summaries : Dict[str, Dict]
            Output of LongitudinalAnalyzer.analyze_all_datasets().
        """
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        for i, (name, summary) in enumerate(list(visit_summaries.items())[:3]):
            if 'error' in summary:
                axes[i].set_visible(False)
                continue

            mean_v = summary['mean_visits_per_participant']
            max_v  = summary['max_visits']

            axes[i].bar(['Mean', 'Max'], [mean_v, max_v],
                        color=COLORS['primary'], edgecolor='white')
            axes[i].set_ylabel('Visits per participant')
            axes[i].set_title(
                f"{name[:20]}…\n(Mean: {mean_v:.1f})",
                fontsize=11, fontweight='bold'
            )

        plt.suptitle('Longitudinal Visit Patterns by Dataset',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Figure 07 — CDR Global distribution
    # -----------------------------------------------------------------------

    def plot_cdr_distribution(
        self,
        cdr_distribution: Dict,
        filename: str = '07_cdr_distribution.png'
    ):
        """
        Vertical bar chart of CDR Global score frequencies.

        CDR (Clinical Dementia Rating) Global is the primary target variable
        for most ADNI machine learning studies:
          0   = cognitively normal (expected majority of participants)
          0.5 = mild cognitive impairment
          1   = mild dementia
          2   = moderate dementia
          3   = severe dementia

        Bars are colour-coded from green (normal) to red (severe) to
        visually convey clinical severity.  Each bar shows a count and
        percentage label so class imbalance is immediately obvious.

        Parameters
        ----------
        cdr_distribution : Dict
            {score_value: count} from CDR dataset — e.g. {0: 5000, 0.5: 1200, ...}
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        scores = sorted(cdr_distribution.keys())
        counts = [cdr_distribution[s] for s in scores]
        total  = sum(counts)

        severity_colors = [
            COLORS['success'],    # CDR 0   — normal
            COLORS['warning'],    # CDR 0.5 — MCI
            COLORS['secondary'],  # CDR 1   — mild
            COLORS['danger'],     # CDR 2   — moderate
            '#7030A0',            # CDR 3   — severe (purple)
        ]

        bars = ax.bar(
            [f'CDR {s}' for s in scores],
            counts,
            color=severity_colors[:len(scores)]
        )

        ax.set_xlabel('CDR Global Score', fontsize=12)
        ax.set_ylabel('Number of Assessments', fontsize=12)
        ax.set_title('CDR Global Score Distribution — ML Target Variable',
                     fontsize=14, fontweight='bold')

        # Add count + percentage labels above each bar
        for bar, val in zip(bars, counts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + max(counts) * 0.01,
                f'{val:,}\n({val / total * 100:.1f}%)',
                ha='center', va='bottom', fontsize=10
            )

        sns.despine()
        self.save_figure(fig, filename)

    # -----------------------------------------------------------------------
    # Run all figures in sequence
    # -----------------------------------------------------------------------

    def create_all_visualizations(
        self,
        datasets: Dict[str, Dict],
        schema_info: Dict[str, Dict],
        summary_df: pd.DataFrame
    ):
        """
        Generate all 7 standard ADNI EDA figures in order.

        Parameters
        ----------
        datasets : Dict[str, Dict]
            Loaded + preprocessed datasets dictionary.
        schema_info : Dict[str, Dict]
            Output of SchemaAnalyzer.analyze_all().
        summary_df : pd.DataFrame
            Output of SchemaAnalyzer.get_summary_table().
        """
        print("Creating visualizations...\n")

        # 01 — dataset record counts by category
        self.plot_dataset_overview(summary_df)

        # 02 — missing data rates per dataset
        self.plot_missing_data(schema_info)

        # 03 — biomarker histograms
        if 'UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026' in datasets:
            upenn_df = datasets['UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026']['df']
            self.plot_biomarker_distributions(upenn_df)

        # 04 — correlation heatmap is generated from StatisticalAnalyzer;
        #       the caller should pass the matrix directly if needed:
        #       viz.plot_correlation_heatmap(corr_df)

        # 05 — study phase pie chart
        from src.analysis.longitudinal_analyzer import LongitudinalAnalyzer
        long_analyzer = LongitudinalAnalyzer(datasets)

        phase_dist = long_analyzer.get_study_phase_distribution()
        if not phase_dist.empty:
            self.plot_study_phases(phase_dist)

        # 06 — visit pattern bars for each dataset
        visit_summaries = long_analyzer.analyze_all_datasets()
        self.plot_longitudinal_patterns(visit_summaries)

        # 07 — CDR target variable distribution
        if 'CDR_13Feb2026' in datasets:
            cdr_df = datasets['CDR_13Feb2026']['df']
            if 'CDGLOBAL' in cdr_df.columns:
                cdr_vals = cdr_df['CDGLOBAL'].dropna()
                cdr_vals = cdr_vals[cdr_vals >= 0]
                cdr_dist = cdr_vals.value_counts().sort_index().to_dict()
                self.plot_cdr_distribution(cdr_dist)

        print(f"\nAll visualizations saved to: {self.output_dir}")


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from src.data.loader import load_and_preprocess_adni_data
    from src.analysis.schema_analyzer import SchemaAnalyzer

    datasets, summary_df = load_and_preprocess_adni_data()
    schema_info = SchemaAnalyzer(datasets).analyze_all()

    viz = ADNIVisualizer()
    viz.create_all_visualizations(datasets, schema_info, summary_df)
