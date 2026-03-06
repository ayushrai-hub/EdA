# ADNI Exploratory Data Analysis (EDA) Project

A data analysis pipeline for the **Alzheimer's Disease Neuroimaging Initiative (ADNI)** dataset.
It loads 30+ raw CSV files, cleans them, analyses them across four dimensions,
and produces tables and figures — all from a single command.

---

## What is ADNI?

ADNI is a long-running multi-site study that tracks participants across five phases
(ADNI1, ADNIGO, ADNI2, ADNI3, ADNI4) with the goal of finding biomarkers that
detect Alzheimer's disease before clinical symptoms appear.

Each participant is measured repeatedly over years across three domains:

| Domain | What it measures | Example files |
|--------|-----------------|---------------|
| **Biospecimen** | Blood-based protein markers | UPENN plasma (p-tau217, Aβ42/40, NfL, GFAP) |
| **Neuropsychological** | Cognitive and behavioural test scores | MoCA, ADAS-Cog, CDR |
| **MRI** | Brain structure (volumes, atrophy) | Hippocampal volumes (UCSFSNTVOL) |

There is also a separate **PET imaging** dataset (amyloid, tau, FDG) handled by
`adni_pet_analysis.py`.

---

## Project Structure

```
ADNI EDA Code 2/
│
├── adni_pet_analysis.py          ← Standalone PET analysis (runs independently)
│
└── adni_eda_project/             ← Main project package
    │
    ├── run_eda.py                ← Entry point — run this to start the pipeline
    ├── requirements.txt          ← Python packages needed
    ├── setup.py                  ← Package installation config
    │
    ├── config/
    │   └── settings.py           ← ALL configuration: paths, thresholds, colors, column names
    │
    └── src/
        ├── data/
        │   └── loader.py         ← Loads CSVs, deduplicates, cleans sentinels, parses dates
        │
        ├── analysis/
        │   ├── schema_analyzer.py      ← Dataset structure: keys, missing data, join ability
        │   ├── statistical_analyzer.py ← Descriptive stats, outlier detection, correlations
        │   ├── longitudinal_analyzer.py← Visit patterns, temporal coverage, study phases
        │   └── ml_readiness.py         ← Feature variance, collinearity, complete-case counts
        │
        └── visualization/
            └── plots.py          ← Generates and saves all 7 standard EDA figures
```

### What each file is for — at a glance

| File | Who needs it | What it does |
|------|-------------|--------------|
| `config/settings.py` | Everyone | Change paths and parameters here first |
| `src/data/loader.py` | Called by run_eda.py | Finds, loads, and cleans all CSVs |
| `src/analysis/schema_analyzer.py` | Phase 2 of pipeline | Dataset health-check: keys, missingness, join capability |
| `src/analysis/statistical_analyzer.py` | Phase 3 | Descriptive statistics, outlier detection, cross-domain correlations |
| `src/analysis/longitudinal_analyzer.py` | Phase 4 | Visit counts, temporal span, study-phase breakdown |
| `src/analysis/ml_readiness.py` | Phase 5 | Variance, multicollinearity, complete cases, class imbalance |
| `src/visualization/plots.py` | Phase 6 | All 7 figures (histograms, heatmaps, bar charts, pie charts) |
| `adni_pet_analysis.py` | Optional | PET-specific: amyloid, tau, FDG analysis |

---

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) install the package in editable mode so 'adni-eda' works as a command
pip install -e .
```

---

## Usage

### Run the full pipeline

```bash
python run_eda.py --data-dir /path/to/adni/csv/files
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--data-dir` | `/mnt/okcomputer/upload` | Folder of ADNI CSV files |
| `--output-dir` | `./output` | Where to write tables and figures |
| `--skip-viz` | off | Skip figure generation (faster) |

### Use individual modules in Python

```python
from src.data.loader import load_and_preprocess_adni_data
from src.analysis.schema_analyzer import SchemaAnalyzer
from src.analysis.statistical_analyzer import StatisticalAnalyzer

# Step 1 — load all datasets
datasets, summary = load_and_preprocess_adni_data('/path/to/data')

# Step 2 — check dataset structure
schema = SchemaAnalyzer(datasets)
schema.print_detailed_report()

# Step 3 — biomarker statistics
stats = StatisticalAnalyzer(datasets)
bio = stats.analyze_biomarkers()
print(bio['descriptive_stats'])
```

### PET analysis (separate)

```python
from adni_pet_analysis import load_pet_data, analyze_pet_biomarkers

datasets = load_pet_data('/path/to/pet/csvs')
results  = analyze_pet_biomarkers(datasets)
```

---

## Output Files

All outputs go into `output/` (or the folder you specify with `--output-dir`):

### Tables (`output/tables/`)

| File | Contents |
|------|----------|
| `dataset_summary.csv` | File name, category, rows, columns, memory for every dataset |
| `schema_analysis.csv` | Per-dataset: key columns present, missing %, sparse column count |
| `biomarker_statistics.csv` | Descriptive stats for p-tau217, Aβ42/40, NfL, GFAP |
| `biomarker_outliers.csv` | IQR outlier counts per biomarker |
| `correlation_matrix.csv` | Biomarker × cognitive Pearson correlation matrix |
| `visit_patterns.csv` | Participant count, visit count, mean visits for key datasets |
| `ml_feature_variance.csv` | Feature variance and CV for ML feature set |

### Visualizations (`output/visualizations/`)

| File | What it shows |
|------|--------------|
| `01_dataset_overview.png` | Total records per domain (bar chart) |
| `02_missing_data.png` | Missing data % for the 15 datasets with most missingness |
| `03_biomarker_distributions.png` | Histograms of p-tau217, Aβ42/40, NfL, GFAP, MoCA |
| `04_correlation_heatmap.png` | Biomarker × cognitive correlation matrix |
| `05_study_phases.png` | Pie chart of ADNI1/2/3/4 phase contributions |
| `06_longitudinal_patterns.png` | Mean and max visits per participant |
| `07_cdr_distribution.png` | CDR Global score distribution (ML target) |

---

## Key Findings from the Data

### Dataset scale
- **29 unique datasets** across 3 domains
- **235,524 total records** with **21 years** of follow-up (2005–2026)

### Biomarker–cognitive correlations (Pearson r)

| Biomarker | vs MoCA | vs ADAS-Cog | vs CDR-SB |
|-----------|---------|-------------|-----------|
| p-tau217  | −0.50   | +0.51       | +0.50     |
| NfL       | −0.26   | +0.30       | +0.32     |
| GFAP      | −0.33   | +0.33       | +0.30     |

(Negative vs MoCA = higher biomarker → lower cognitive score, as expected)

### ML readiness summary
- ✓ **1,231 complete cases** (biomarker + cognitive data at same visit)
- ✓ Good feature variance across all biomarkers
- ⚠ NfL/GFAP have ~23% missing — consider imputation before modelling
- ⚠ MoCA and ADAS-Cog are strongly collinear (r = −0.77) — use one, not both
- ⚠ CDR class imbalance ratio 3.37:1 — use class-weighted loss or oversampling

### Data quality notes
- **WATC** (73.3% missing) — ADNI4-specific instrument, sparse by design
- **NPI** (69.7% missing) — neuropsychiatric inventory, collected infrequently
- **MRIQC** — missing RID/PTID; links via VISCODE2 only

---

## Recommended ML Feature Set

**Input features:** `pT217_F`, `AB42_AB40_F`, `NfL_Q`, `GFAP_Q`, `MOCA`

**Target variable:** `CDGLOBAL` (CDR Global score)
- Multi-class: 0, 0.5, 1, 2, 3
- Binary (impaired vs normal): CDR > 0
- Binary (MCI or worse): CDR ≥ 0.5

**Derived features worth trying:**
- p-tau217 / Aβ42 ratio (ATN framework)
- Biomarker composite z-score

---

## Configuring the Project

All tunable parameters live in `config/settings.py`:
- `DATA_DIR` — path to your ADNI CSV folder
- `OUTLIER_IQR_MULTIPLIER` — fence tightness for outlier detection (default 1.5)
- `MISSING_HIGH_THRESHOLD` — "sparse" column cutoff (default 50%)
- `COLORS` — plot colour palette
- `BIOMARKER_COLUMNS` / `COGNITIVE_COLUMNS` / `IMAGING_COLUMNS` — which columns to analyse

---

## License

This project is for research purposes.
All ADNI data use is subject to the ADNI Data Use Agreement —
see [adni.loni.usc.edu](https://adni.loni.usc.edu) for access instructions.
