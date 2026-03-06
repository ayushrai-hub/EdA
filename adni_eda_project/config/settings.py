"""
config/settings.py
------------------
Central configuration file for the ADNI EDA project.

Everything that might need to change — file paths, biomarker names, thresholds,
colors — lives here in one place. Edit this file before running anything else.

Beginner tip: pathlib.Path is like os.path but cleaner.
  Path(__file__) = this file's location
  .parent        = the folder it lives in
  / 'foo'        = append 'foo' to the path (works on Mac/Linux/Windows)
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# DIRECTORY PATHS
# ---------------------------------------------------------------------------

# The root of the project folder (one level up from config/)
PROJECT_ROOT = Path(__file__).parent.parent

# Where the raw ADNI CSV files are stored.
# Change this to wherever you downloaded the data.
DATA_DIR = Path('/mnt/okcomputer/upload')

# Where all output (tables, figures, reports) is written
OUTPUT_DIR = PROJECT_ROOT / 'output'

# Sub-folders inside output/
REPORTS_DIR        = OUTPUT_DIR / 'reports'
TABLES_DIR         = OUTPUT_DIR / 'tables'
VISUALIZATIONS_DIR = OUTPUT_DIR / 'visualizations'

# Create the output folders automatically when this module is imported
for _dir in [REPORTS_DIR, TABLES_DIR, VISUALIZATIONS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# SENTINEL / MISSING VALUES
# ---------------------------------------------------------------------------
# ADNI uses several special codes to indicate "value not recorded".
# We convert all of these to NaN (pandas not-a-number) so that statistical
# functions skip them automatically.

SENTINEL_VALUES = [
    -4, -4.0, '-4',          # ADNI's standard "missing" numeric code
    -999, -999.0,            # Alternative missing code used in some files
    '', ' ',                 # Empty strings (blank cells in the CSV)
    'NA', 'N/A', 'na', 'n/a',
    'NULL', 'null',
    'None', 'none',
    'nan', 'NaN',
]


# ---------------------------------------------------------------------------
# FILE CATEGORIES
# ---------------------------------------------------------------------------
# ADNI data spans several domains. We group each CSV file into one of three
# categories so we can process or report on them as a group.

FILE_CATEGORIES = {

    # Blood / plasma biomarker measurements
    'biospecimen': [
        'UPENN_PLASMA_FUJIREBIO_QUANTERIX_13Feb2026.csv',  # p-tau217, Aβ, NfL, GFAP
        'APOERES_13Feb2026.csv',                           # APOE genotyping
        'batemanlab_20190621_13Feb2026.csv',               # Bateman lab plasma (2019)
        'batemanlab_20221118_13Feb2026.csv',               # Bateman lab plasma (2022)
        'YASSINE_PLASMA_13Feb2026.csv',                    # Yassine lab plasma
        'YASSINE_CSF_13Feb2026.csv',                       # Yassine lab CSF
    ],

    # Cognitive / psychiatric tests given to participants at each visit
    'neuropsychological': [
        'ADAS_13Feb2026.csv',     # Alzheimer's Disease Assessment Scale
        'CDR_13Feb2026.csv',      # Clinical Dementia Rating
        'MOCA_13Feb2026.csv',     # Montreal Cognitive Assessment
        'FAQ_13Feb2026.csv',      # Functional Activities Questionnaire
        'NPI_13Feb2026.csv',      # Neuropsychiatric Inventory
        'ECOGPT_13Feb2026.csv',   # Everyday Cognition (participant-reported)
        'ECOGSP_13Feb2026.csv',   # Everyday Cognition (study-partner-reported)
        'GDSCALE_13Feb2026.csv',  # Geriatric Depression Scale
        'IES_13Feb2026.csv',      # Impact of Event Scale
        'WATC_13Feb2026.csv',     # Word Association Test Completion
    ],

    # Structural MRI-derived brain measurements
    'imaging_mri': [
        'ADNI_PICSLASHS_13Feb2026.csv',
        'BSI_13Feb2026.csv',
        'MRI3META_13Feb2026.csv',
        'MRIMPRANK_13Feb2026.csv',
        'MRIQC_13Feb2026.csv',
        'TBM_03_17_2022_13Feb2026.csv',
        'UASPMVBM_13Feb2026.csv',
        'UCSFASLFS_11_02_15_V2_13Feb2026.csv',
        'UCSFASLQC_13Feb2026.csv',
        'UCSFATRPHY_13Feb2026.csv',
        'UCSFFSL51Y1_08_01_16_13Feb2026.csv',
        'UCSFSNTVOL_13Feb2026.csv',    # Subcortical volumes (hippocampus etc.)
        'UPENNSPARE_MCI_08_12_16_13Feb2026.csv',
    ],
}

# Duplicate file names to skip — ADNI sometimes delivers files with
# a "(1)", "(2)" suffix that are identical byte-for-byte to the original.
FILES_TO_EXCLUDE = [
    'APOERES_13Feb2026(1).csv',
    'APOERES_13Feb2026(2).csv',
    'YASSINE_CSF_13Feb2026(1).csv',
    'YASSINE_CSF_13Feb2026(2).csv',
    'YASSINE_PLASMA_13Feb2026(1).csv',
    'YASSINE_PLASMA_13Feb2026(2).csv',
    'batemanlab_20190621_13Feb2026(1).csv',
    'batemanlab_20221118_13Feb2026(1).csv',
]


# ---------------------------------------------------------------------------
# ANALYSIS PARAMETERS
# ---------------------------------------------------------------------------

# IQR-based outlier detection: a point is an outlier if it falls more than
# 1.5 × IQR below Q1 or above Q3. Increase to 3.0 for a looser threshold.
OUTLIER_IQR_MULTIPLIER = 1.5

# Z-score outlier threshold: flag points more than 3 standard deviations
# from the mean.
OUTLIER_ZSCORE_THRESHOLD = 3.0

# Correlation methods supported by statistical_analyzer.py
CORRELATION_METHODS = ['pearson', 'spearman']

# A column where > 50% of values are missing is considered "sparse"
MISSING_HIGH_THRESHOLD = 0.50

# A column where > 30% of values are missing is flagged as "moderate concern"
MISSING_MODERATE_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# VISUALIZATION SETTINGS
# ---------------------------------------------------------------------------

FIGURE_DPI    = 150          # Dots-per-inch — 150 is good for screen; use 300 for print
FIGURE_FORMAT = 'png'        # Output format ('png', 'pdf', 'svg')
FIGURE_SIZE   = (12, 8)     # Default (width, height) in inches

# Named color palette used across all plots for visual consistency
COLORS = {
    'primary':   '#4472C4',  # Blue — main bars, lines
    'secondary': '#ED7D31',  # Orange — secondary series
    'tertiary':  '#A5A5A5',  # Grey — background / reference
    'success':   '#70AD47',  # Green — low-missingness, good status
    'warning':   '#FFC000',  # Amber — moderate-missingness, caution
    'danger':    '#C5504B',  # Red — high-missingness, alert
    'info':      '#5B9BD5',  # Light blue — supplementary info
}


# ---------------------------------------------------------------------------
# KEY COLUMN DEFINITIONS
# ---------------------------------------------------------------------------
# ADNI uses consistent column names across datasets for linking records.
# These are the "join keys" — think of them like a primary key in a database.

ID_COLUMNS = [
    'RID',       # Participant Research ID — unique identifier per person
    'PTID',      # Participant ID — alternate identifier (used by some files)
    'VISCODE',   # Visit code (e.g. 'bl' = baseline, 'm06' = 6 months)
    'VISCODE2',  # Harmonised visit code used in later ADNI phases
    'PHASE',     # ADNI study phase (ADNI1, ADNIGO, ADNI2, ADNI3, ADNI4)
]

# Column name patterns that suggest a column holds date information.
# Used by detect_date_columns() to auto-detect dateable fields.
DATE_COLUMN_PATTERNS = ['date', 'stamp', 'time', 'DATE', 'STAMP', 'TIME']


# ---------------------------------------------------------------------------
# BIOMARKER COLUMNS
# ---------------------------------------------------------------------------
# Blood-based Alzheimer's biomarkers from the UPENN plasma dataset.
# Keys = column names in the CSV; Values = human-readable labels for plots.

BIOMARKER_COLUMNS = {
    'pT217_F':      'p-tau217 (Fujirebio, pg/mL)',
    'AB42_F':       'Aβ42 (Fujirebio, pg/mL)',
    'AB40_F':       'Aβ40 (Fujirebio, pg/mL)',
    'AB42_AB40_F':  'Aβ42/40 Ratio (Fujirebio)',  # Lower ratio = more amyloid burden
    'NfL_Q':        'NfL (Quanterix, pg/mL)',       # Neurofilament light — marker of axonal injury
    'GFAP_Q':       'GFAP (Quanterix, pg/mL)',      # Glial fibrillary acidic protein — astrocyte damage
    'NfL_F':        'NfL (Fujirebio, pg/mL)',
    'GFAP_F':       'GFAP (Fujirebio, pg/mL)',
}


# ---------------------------------------------------------------------------
# COGNITIVE ASSESSMENT COLUMNS
# ---------------------------------------------------------------------------
# Key scores extracted from neuropsychological test datasets.

COGNITIVE_COLUMNS = {
    'MOCA':     'MoCA Total Score (0–30, higher = better)',
    'TOTSCORE': 'ADAS-Cog Total Score (higher = worse)',
    'TOTAL13':  'ADAS-Cog 13-Item Score (higher = worse)',
    'CDRSB':    'CDR Sum of Boxes (0–18, higher = worse)',
    'CDGLOBAL': 'CDR Global Score (0=normal, 0.5=MCI, 1–3=dementia)',
}


# ---------------------------------------------------------------------------
# IMAGING COLUMNS
# ---------------------------------------------------------------------------
# Hippocampal and sub-region volumes from the FreeSurfer segmentation
# pipeline (UCSFSNTVOL dataset). Volumes are in mm³.

IMAGING_COLUMNS = {
    'LEFTHIPPO':    'Left Hippocampal Volume (mm³)',
    'RIGHTHIPPO':   'Right Hippocampal Volume (mm³)',
    'LEFT_CA1_VOL': 'Left CA1 Sub-region Volume (mm³)',
    'LEFT_DG_VOL':  'Left Dentate Gyrus Volume (mm³)',
    'RIGHT_CA1_VOL':'Right CA1 Sub-region Volume (mm³)',
    'RIGHT_DG_VOL': 'Right Dentate Gyrus Volume (mm³)',
}
