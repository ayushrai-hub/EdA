# ADNI Comprehensive Exploratory Data Analysis (EDA) Report

**Generated:** 2026-03-05 23:13:33  
**Analyst:** Senior Biomedical Data Scientist  
**Dataset:** Alzheimer's Disease Neuroimaging Initiative (ADNI)

---

## Executive Summary

This report presents a comprehensive, research-grade exploratory data analysis of the ADNI dataset comprising **29 unique data tables** across three major domains:
- **Biospecimen/Biomarkers** (6 tables)
- **Neuropsychological Assessments** (10 tables)
- **Imaging (MRI)** (13 tables)

### Key Findings

| Metric | Value |
|--------|-------|
| Total Records | 235,524 |
| Total Memory | 167.34 MB |
| Unique Participants (RID) | 42,812 |
| Average Missing Data | 16.51% |
| Date Coverage | 2005-2026 (21 years) |

### Critical Data Quality Issues Identified

1. **APOERES dataset**: 46.5% missing data - primarily due to sparse VISCODE coverage
2. **NPI dataset**: 69.7% missing data - highly sparse instrument
3. **WATC dataset**: 73.3% missing data - ADNI4-specific instrument with limited adoption
4. **MRIQC dataset**: Missing RID/PTID identifiers - uses VISCODE2 only

---

## 1. Global Dataset Overview

### 1.1 Dataset Inventory by Category

#### Biospecimen/Biomarkers (6 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| UPENN_PLASMA_FUJIREBIO_QUANTERIX | 2,178 | 19 | 1,615 | 11.5% | Primary plasma biomarkers (p-tau217, Aβ42/40, NfL, GFAP) |
| APOERES | 3,253 | 16 | 3,253 | 46.5% | APOE genotyping results |
| batemanlab_20221118 | 742 | 36 | 358 | 10.6% | Bateman Lab plasma Aβ42/40 (LC-MS) |
| batemanlab_20190621 | 622 | 73 | 200 | 21.7% | Earlier Bateman Lab batch |
| YASSINE_PLASMA | 188 | 22 | 188 | 26.2% | Yassine Lab plasma biomarkers |
| YASSINE_CSF | 188 | 25 | 188 | 27.0% | CSF apolipoprotein E and glycation |

#### Neuropsychological Assessments (10 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| CDR | 14,705 | 25 | 4,398 | 16.6% | Clinical Dementia Rating (CDR-SB, CDGLOBAL) |
| GDSCALE | 13,783 | 32 | 4,587 | 13.1% | Geriatric Depression Scale |
| FAQ | 13,360 | 27 | 3,020 | 15.6% | Functional Activities Questionnaire |
| ADAS | 12,952 | 16 | 3,027 | 20.7% | ADAS-Cog total and 13-item scores |
| MOCA | 9,044 | 58 | 2,500 | 8.8% | Montreal Cognitive Assessment |
| NPI | 8,317 | 168 | 2,467 | 69.7% | Neuropsychiatric Inventory |
| ECOGSP | 8,107 | 59 | 1,913 | 13.6% | ECOG Study Partner |
| ECOGPT | 8,093 | 62 | 1,917 | 13.5% | ECOG Patient |
| WATC | 1,012 | 58 | 1,012 | 73.3% | Weekly Assessment (ADNI4) |
| IES | 698 | 29 | 585 | 0.3% | Impact of Events Scale |

#### Imaging - MRI (13 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| MRIQC | 91,309 | 26 | N/A | 4.0% | MRI Quality Control (scan-level) |
| MRIMPRANK | 9,412 | 17 | 859 | 5.8% | MRI Scan Ranking |
| MRI3META | 9,371 | 42 | 2,872 | 40.3% | 3T MRI Metadata |
| TBM | 9,354 | 17 | 1,921 | 5.9% | Tensor-Based Morphometry |
| ADNI_PICSLASHS | 4,184 | 67 | 1,965 | 2.8% | PICSL ASHS Hippocampal Segmentation |
| UASPMVBM | 4,091 | 127 | 829 | 0.0% | Voxel-Based Morphometry |
| BSI | 3,594 | 20 | 842 | 15.0% | Boundary Shift Integral |
| UCSFSNTVOL | 1,874 | 15 | 587 | 0.0% | UCSF SNT Hippocampal Volumes |
| UCSFATRPHY | 1,721 | 12 | 765 | 0.0% | UCSF Atrophy Measures |
| UCSFFSL51Y1 | 1,356 | 364 | 357 | 0.7% | FSL 5.1 Longitudinal |
| UCSFASLQC | 1,011 | 7 | N/A | 6.8% | ASL QC |
| UCSFASLFS | 675 | 701 | 257 | 3.5% | ASL Flow Measures |
| UPENNSPARE_MCI | 330 | 13 | 330 | 5.2% | SPARE-MCI Score |

---

## 2. Schema Mapping and Table Relationships

### 2.1 Join Key Availability

| Dataset | RID | PTID | VISCODE | VISCODE2 | PHASE |
|---------|-----|------|---------|----------|-------|
| UPENN_PLASMA | ✓ | ✓ | ✓ | ✓ | ✓ |
| ADAS | ✓ | ✓ | ✓ | ✓ | ✓ |
| CDR | ✓ | ✓ | ✓ | ✓ | ✓ |
| MOCA | ✓ | ✓ | ✓ | ✓ | ✓ |
| UCSFSNTVOL | ✓ | ✗ | ✓ | ✗ | ✗ |
| MRIQC | ✗ | ✗ | ✗ | ✓ | ✗ |

### 2.2 Recommended Join Strategy

**Primary Join Keys:**
- **(RID, VISCODE2)** - Most reliable for cross-modal integration
- **(RID, VISCODE)** - Alternative when VISCODE2 unavailable
- **RID only** - For cross-sectional analysis (latest visit per participant)

**Join Coverage:**
- 24 datasets joinable on (RID, VISCODE)
- 20 datasets joinable on (RID, VISCODE2)

---

## 3. Statistical EDA - Key Biomarkers

### 3.1 UPENN Plasma Biomarkers (Fujirebio/Quanterix)

| Biomarker | N | Mean ± SD | Median (IQR) | Range | Skewness |
|-----------|---|-----------|--------------|-------|----------|
| p-tau217 (pg/mL) | 2,178 | 0.31 ± 0.35 | 0.17 (0.10-0.39) | 0.03-5.56 | 3.55 |
| Aβ42 (pg/mL) | 2,172 | 27.15 ± 22.02 | 26.24 (22.35-30.21) | 2.25-1000 | 39.84 |
| Aβ40 (pg/mL) | 2,173 | 313.71 ± 130.08 | 303.36 (268.57-342.46) | 26.89-5000 | 22.89 |
| Aβ42/40 Ratio | 2,172 | 0.087 ± 0.014 | 0.085 (0.077-0.095) | 0.010-0.663 | 13.25 |
| NfL (pg/mL) | 1,727 | 22.75 ± 16.46 | 19.00 (13.40-27.50) | 3.07-278 | 5.04 |
| GFAP (pg/mL) | 1,727 | 195.90 ± 121.98 | 169.10 (113.55-245.60) | 10.56-1783 | 2.78 |

**Outlier Analysis (IQR 1.5× Rule):**
- p-tau217: 8.6% outliers (high values)
- Aβ42/40: 1.5% outliers
- NfL: 4.7% outliers (high values)
- GFAP: 3.9% outliers (high values)

### 3.2 Cognitive Assessment Scores

| Assessment | N | Mean ± SD | Median (IQR) | Range | Skewness |
|------------|---|-----------|--------------|-------|----------|
| MoCA Total | 3,785 | 23.72 ± 4.69 | 24.0 (22.0-27.0) | 1-30 | -1.33 |
| ADAS-Cog Total | 12,749 | 10.69 ± 8.22 | 8.3 (5.0-13.7) | 0-70 | 1.99 |
| ADAS-Cog 13 | 12,646 | 16.51 ± 11.29 | 13.7 (8.3-22.3) | 0-85 | 1.38 |
| CDR-SB | 14,456 | 1.94 ± 2.78 | 1.0 (0.0-2.5) | 0-18 | 2.45 |

**CDR Global Distribution:**
- CDR 0 (Normal): 5,434 (37.6%)
- CDR 0.5 (Questionable): 6,925 (47.9%)
- CDR 1.0 (Mild): 1,601 (11.1%)
- CDR 2.0 (Moderate): 395 (2.7%)
- CDR 3.0 (Severe): 99 (0.7%)

### 3.3 Hippocampal Volumes (UCSF SNT)

| Region | N | Mean ± SD (mm³) | Median (IQR) | Range |
|--------|---|-----------------|--------------|-------|
| Left Hippocampus | 1,874 | 1,830 ± 399 | 1,839 (1,539-2,102) | 817-2,875 |
| Right Hippocampus | 1,874 | 1,881 ± 415 | 1,896 (1,571-2,173) | 593-3,078 |
| Total Hippocampus | 1,874 | 3,711 ± 805 | 3,736 (3,126-4,269) | 1,410-5,953 |

---

## 4. Multimodal Correlation Analysis

### 4.1 Biomarker-Cognitive Correlations

| Biomarker | MoCA | ADAS-Total | CDR-SB |
|-----------|------|------------|--------|
| p-tau217 | **-0.496** | **0.515** | **0.498** |
| Aβ42/40 | 0.121 | -0.195 | -0.120 |
| NfL | -0.257 | 0.298 | **0.316** |
| GFAP | -0.325 | 0.329 | 0.297 |

**Key Findings:**
- p-tau217 shows strongest correlations with cognitive impairment
- NfL and GFAP (neurodegeneration markers) correlate with cognitive decline
- Aβ42/40 ratio shows weaker but expected negative correlations

### 4.2 Biomarker-Imaging Correlations

| Biomarker | Total Hippocampal Volume |
|-----------|-------------------------|
| p-tau217 | **-0.337** (n=146) |
| NfL | -0.135 (n=145) |
| GFAP | -0.194 (n=145) |
| Aβ42/40 | 0.030 (n=146) |

### 4.3 Integrated Data Coverage

| Integration Level | Records | Unique Participants |
|-------------------|---------|---------------------|
| Biomarkers only | 2,178 | 1,615 |
| Biomarkers + Cognitive | 1,946 | 1,503 |
| Biomarkers + Imaging | 26 | 26 |
| Cross-sectional (latest visit) | 146 | 146 |

---

## 5. Longitudinal Analysis

### 5.1 Visit Patterns

| Dataset | Mean Visits/Participant | Max Visits | 2+ Visits | 3+ Visits |
|---------|------------------------|------------|-----------|-----------|
| UPENN Plasma | 1.35 | 4 | 29.9% | 4.8% |
| MoCA | 3.62 | 15 | 69.7% | 56.8% |
| CDR | 3.34 | 21 | 52.3% | 45.3% |

### 5.2 Study Phase Distribution

| Phase | Records | Description |
|-------|---------|-------------|
| ADNI2 | 43,769 | Phase 2 (2009-2016) |
| ADNI3 | 29,393 | Phase 3 (2016-2023) |
| ADNI1 | 17,361 | Phase 1 (2004-2010) |
| ADNI4 | 14,332 | Phase 4 (2022-present) |
| ADNIGO | 4,202 | Grand Opportunity (2009-2012) |

### 5.3 Temporal Coverage

- **Biomarkers (UPENN Plasma):** 2005-2025 (19.9 years)
- **Cognitive (MoCA):** 2010-2026 (15.8 years)
- **Cognitive (CDR):** 2005-2026 (20.5 years)

---

## 6. Machine Learning Readiness Assessment

### 6.1 Feature Variance Analysis

| Feature | N | Mean | Std | CV | Assessment |
|---------|---|------|-----|----|------------|
| p-tau217 | 1,946 | 0.30 | 0.34 | 1.13 | ✓ Good variance |
| Aβ42/40 | 1,942 | 0.087 | 0.014 | 0.16 | ✓ Acceptable |
| NfL | 1,501 | 21.96 | 15.01 | 0.68 | ✓ Good variance |
| GFAP | 1,501 | 193.17 | 122.94 | 0.64 | ✓ Good variance |
| MoCA | 1,689 | 23.71 | 4.62 | 0.19 | ✓ Acceptable |
| ADAS-Total | 1,904 | 9.68 | 7.45 | 0.77 | ✓ Good variance |

### 6.2 Multicollinearity Assessment

**High Correlation Detected:**
- MoCA vs ADAS-Total: r = -0.77 (expected - cognitive measures are inversely related)

**Recommendation:** Use either MoCA OR ADAS-Total in models, not both, or apply regularization.

### 6.3 Missing Data Pattern

| Feature | Missing | Missing % | Impact |
|---------|---------|-----------|--------|
| p-tau217 | 0 | 0.0% | ✓ Complete |
| Aβ42/40 | 4 | 0.2% | ✓ Near-complete |
| NfL | 445 | 22.9% | ⚠ Moderate |
| GFAP | 445 | 22.9% | ⚠ Moderate |
| MoCA | 257 | 13.2% | ⚠ Moderate |
| ADAS-Total | 42 | 2.2% | ✓ Near-complete |

**Complete Cases:** 1,231 (63.3% of integrated dataset)

### 6.4 Target Variable Analysis

| Target | N Positive | % Positive | Imbalance Ratio |
|--------|------------|------------|-----------------|
| CDR > 0 (any impairment) | 445 | 22.9% | 3.37:1 |
| CDR ≥ 0.5 (MCI/Dementia) | 445 | 22.9% | 3.37:1 |
| MoCA < 26 (impaired) | 1,009 | 51.8% | 1.07:1 |

**Recommendation:** Moderate class imbalance - use stratified sampling and appropriate metrics (AUC-ROC, F1).

### 6.5 ML Recommendations

**✓ Ready for ML:**
- Adequate sample size (n=1,231 complete cases)
- Good feature variance
- Biologically meaningful correlations
- Clear target variables

**⚠ Considerations:**
- Handle 22.9% missing in NfL/GFAP (imputation or separate models)
- Address MoCA/ADAS collinearity
- Use stratified sampling for class imbalance
- Consider domain-specific feature engineering

---

## 7. Data Quality Issues and Recommendations

### 7.1 Critical Issues

1. **MRIQC Dataset:** Missing RID/PTID identifiers
   - **Impact:** Cannot join with other datasets
   - **Recommendation:** Use VISCODE2 for manual mapping or request RID from ADNI

2. **APOERES Dataset:** 64.4% missing VISCODE
   - **Impact:** Limited longitudinal joinability
   - **Recommendation:** Use USERDATE for temporal alignment

3. **NPI Dataset:** 69.7% missing data
   - **Impact:** Limited utility for analysis
   - **Recommendation:** Consider exclusion or domain-specific imputation

### 7.2 Sentinel Value Handling

All datasets have been normalized to treat the following as missing:
- Numeric: -4, -999
- String: '', 'NA', 'N/A', 'NULL', 'None'

### 7.3 Duplicate Records

No duplicate rows detected in any dataset.

---

## 8. Proposed Cleaned Schema for ML Pipeline

### 8.1 Core Tables

**1. BIOMARKER_MASTER**
```
Primary Key: (RID, VISCODE2, EXAMDATE)
Columns:
  - RID (int): Participant identifier
  - VISCODE2 (str): Visit code (bl, m06, m12, etc.)
  - EXAMDATE (date): Examination date
  - PHASE (str): ADNI phase
  - PTau217 (float): p-tau217 (pg/mL)
  - AB42_40_Ratio (float): Aβ42/40 ratio
  - NfL (float): Neurofilament light (pg/mL)
  - GFAP (float): Glial fibrillary acidic protein (pg/mL)
```

**2. COGNITIVE_MASTER**
```
Primary Key: (RID, VISCODE2, VISDATE)
Columns:
  - RID (int): Participant identifier
  - VISCODE2 (str): Visit code
  - VISDATE (date): Assessment date
  - MoCA_Total (int): MoCA total score (0-30)
  - ADAS_Total (float): ADAS-Cog total score
  - ADAS_13 (float): ADAS-Cog 13-item score
  - CDR_SB (float): CDR Sum of Boxes
  - CDR_Global (float): CDR Global score
```

**3. IMAGING_MASTER**
```
Primary Key: (RID, VISCODE, EXAMDATE)
Columns:
  - RID (int): Participant identifier
  - VISCODE (str): Visit code
  - EXAMDATE (date): Scan date
  - Left_Hippo_Vol (float): Left hippocampal volume (mm³)
  - Right_Hippo_Vol (float): Right hippocampal volume (mm³)
  - Total_Hippo_Vol (float): Total hippocampal volume (mm³)
```

**4. PARTICIPANT_MASTER**
```
Primary Key: (RID)
Columns:
  - RID (int): Participant identifier
  - PTID (str): Public participant ID
  - First_Visit_Date (date): Date of first visit
  - Last_Visit_Date (date): Date of last visit
  - Total_Visits (int): Number of visits
  - Has_Biomarker (bool): Has biomarker data
  - Has_Cognitive (bool): Has cognitive assessment
  - Has_Imaging (bool): Has imaging data
```

### 8.2 Recommended Feature Set for Risk Assessment Model

**Input Features (Blood Biomarkers):**
- p-tau217 (continuous)
- Aβ42/40 ratio (continuous)
- NfL (continuous)
- GFAP (continuous)

**Input Features (Cognitive):**
- MoCA total score (continuous, 0-30)
- OR ADAS-Cog total score (continuous)

**Target Variables:**
- CDR Global (multiclass: 0, 0.5, 1, 2, 3)
- Binary impairment (CDR > 0)
- MCI/Dementia (CDR ≥ 0.5)

**Derived Features (Recommended):**
- p-tau217 / Aβ42 ratio
- Biomarker z-score composite
- Age × biomarker interactions (when demographics available)

---

## 9. Conclusions

### 9.1 Data Suitability Summary

| Criterion | Assessment | Notes |
|-----------|------------|-------|
| Sample Size | ✓ Excellent | 1,615+ participants with biomarkers |
| Data Quality | ⚠ Good | 16.5% average missing, manageable |
| Longitudinal | ✓ Excellent | Up to 21 years follow-up |
| Multimodal | ✓ Good | Biomarkers + Cognitive + Imaging |
| ML Ready | ✓ Yes | 1,231 complete cases, good variance |

### 9.2 Key Statistical Findings

1. **p-tau217** is the strongest individual biomarker predictor of cognitive impairment (r = -0.50 with MoCA, r = 0.52 with ADAS)

2. **NfL and GFAP** show moderate correlations with cognitive decline, supporting their role as neurodegeneration markers

3. **Hippocampal atrophy** correlates with elevated p-tau217 (r = -0.34), validating the AT(N) framework

4. **Aβ42/40 ratio** shows expected but weaker correlations, possibly due to assay variability

### 9.3 Recommendations for AI Risk Assessment System

1. **Primary Model:** Use p-tau217 + Aβ42/40 + NfL + GFAP + MoCA for risk stratification

2. **Feature Engineering:** Create composite biomarker scores and handle MoCA/ADAS collinearity

3. **Missing Data:** Implement imputation for NfL/GFAP or train separate models

4. **Validation:** Use CDR Global as gold standard, with binary impairment as secondary target

5. **Deployment:** Implement RID-based lookup service with VISCODE2 alignment for real-time assessment

---

*Report generated by automated EDA pipeline. All statistics derived directly from provided ADNI CSV files.*
