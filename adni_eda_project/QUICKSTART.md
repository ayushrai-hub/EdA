# ADNI EDA — Quick Start

## Prerequisites

```bash
pip install -r requirements.txt
```

## 1. Run the full pipeline

```bash
# From inside adni_eda_project/
python run_eda.py --data-dir /path/to/adni/csv/files
```

This runs all six phases and produces:
- `output/tables/`         — CSV summary files
- `output/visualizations/` — PNG figures

## 2. Run individual modules

```python
# Load all datasets
from src.data.loader import load_and_preprocess_adni_data
datasets, summary = load_and_preprocess_adni_data('/path/to/data')

# Schema analysis
from src.analysis.schema_analyzer import SchemaAnalyzer
schema = SchemaAnalyzer(datasets)
schema.print_detailed_report()

# Statistical analysis
from src.analysis.statistical_analyzer import StatisticalAnalyzer
stats = StatisticalAnalyzer(datasets)
print(stats.analyze_biomarkers()['descriptive_stats'])

# Longitudinal analysis
from src.analysis.longitudinal_analyzer import LongitudinalAnalyzer
long = LongitudinalAnalyzer(datasets)
print(long.get_visit_summary_table())

# ML readiness
from src.analysis.ml_readiness import MLReadinessAnalyzer
ml = MLReadinessAnalyzer(datasets)
ml.print_ml_report()
```

## 3. Generate specific figures

```python
from src.visualization.plots import ADNIVisualizer
viz = ADNIVisualizer()

# Individual figures (pass the relevant data)
viz.plot_dataset_overview(summary_df)
viz.plot_missing_data(schema_info)
viz.plot_biomarker_distributions(datasets['UPENN_...']['df'])
viz.plot_cdr_distribution(cdr_dist_dict)
```

## 4. Access a specific dataset

```python
# Datasets are keyed by filename stem (no .csv extension)
moca_df  = datasets['MOCA_13Feb2026']['df']
upenn_df = datasets['UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026']['df']

# All biospecimen datasets
bio = {
    name: data['df']
    for name, data in datasets.items()
    if data['category'] == 'biospecimen'
}
```

## Module reference

| Module | Import path | Primary class / function |
|--------|-------------|-------------------------|
| Data loading | `src.data.loader` | `load_and_preprocess_adni_data()` |
| Schema analysis | `src.analysis.schema_analyzer` | `SchemaAnalyzer` |
| Statistical EDA | `src.analysis.statistical_analyzer` | `StatisticalAnalyzer` |
| Longitudinal EDA | `src.analysis.longitudinal_analyzer` | `LongitudinalAnalyzer` |
| ML readiness | `src.analysis.ml_readiness` | `MLReadinessAnalyzer` |
| Figures | `src.visualization.plots` | `ADNIVisualizer` |
| PET analysis | `adni_pet_analysis` (top-level) | `load_pet_data()`, `analyze_pet_biomarkers()` |

## Configuration

Edit `config/settings.py` to change:
- `DATA_DIR` — where your ADNI CSV files live
- `OUTPUT_DIR` — where outputs are written
- `OUTLIER_IQR_MULTIPLIER` — outlier detection sensitivity
- `MISSING_HIGH_THRESHOLD` — threshold for "sparse" column warning

## Troubleshooting

**ImportError: No module named 'src'**
Make sure you are running from inside `adni_eda_project/`, or add it to PYTHONPATH:
```bash
export PYTHONPATH=$PYTHONPATH:/path/to/adni_eda_project
```

**FileNotFoundError: data files not found**
Check that `DATA_DIR` in `config/settings.py` matches where your ADNI CSVs are,
or pass `--data-dir` explicitly.

**MemoryError**
The full dataset is ~170 MB in memory. Close other applications, or analyse
datasets one category at a time using `get_datasets_by_category()`.
