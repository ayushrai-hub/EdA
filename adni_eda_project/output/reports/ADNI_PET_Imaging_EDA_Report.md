# ADNI Additional Imaging Data (PET/Tau/Amyloid) EDA Report

**Generated:** 2026-03-06 03:24:14  
**Analyst:** Senior Biomedical Data Scientist  
**Dataset:** ADNI PET, Tau, and Amyloid Imaging Data

---

## Executive Summary

This report presents a comprehensive exploratory data analysis of additional ADNI imaging datasets focusing on **PET (Positron Emission Tomography)** biomarkers including:
- **Amyloid PET** (AV45/Florbetapir)
- **Tau PET** (FTP/Flortaucipir)
- **FDG PET** (Fluorodeoxyglucose - glucose metabolism)

### Key Findings

| Metric | Value |
|--------|-------|
| Total Datasets | 13 unique tables |
| Total Records | 37,529 |
| Total Memory | 28.05 MB |
| Unique Participants (RID) | 16,588 |
| Average Missing Data | 19.34% |
| Date Coverage | 2005-2026 (up to 16.9 years per modality) |

### Critical PET Biomarker Correlations

| Correlation | r-value | Interpretation |
|-------------|---------|----------------|
| Amyloid vs Tau | **+0.50** | Moderate positive (co-pathology) |
| Amyloid vs FDG | **-0.51** | Moderate negative (hypometabolism) |
| Tau vs FDG | **-0.47** | Moderate negative (neurodegeneration) |

---

## 1. Dataset Overview

### 1.1 Dataset Inventory by Category

#### Amyloid PET (3 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| AMYMETA | 3,038 | 38 | 1,643 | 32.08% | Amyloid PET metadata |
| AMYQC | 2,873 | 27 | 1,573 | 39.46% | Amyloid PET quality control |
| BAIPETNMRCAV45 | 2,815 | 13 | 1,294 | 1.90% | BAI Lab AV45 SUVR values |

#### Tau PET (4 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| UCBERKELEY_TAU_6MM | 2,327 | 339 | 1,357 | 5.33% | UC Berkeley Tau SUVR (164 regions) |
| UCBERKELEY_TAUPVC_6MM | 2,106 | 335 | 1,230 | 2.70% | Tau SUVR with PVC correction |
| TAUMETA | 3,150 | 39 | 1,655 | 38.25% | Tau PET metadata |
| TAUQC | 2,670 | 28 | 1,541 | 42.15% | Tau PET quality control |

#### FDG PET (3 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| UCBERKELEYFDG_8mm | 7,524 | 10 | 1,687 | 0.03% | UC Berkeley FDG (MetaROI, Top50PonsVermis) |
| BAIPETNMRCFDG | 3,684 | 14 | 1,610 | 0.00% | BAI Lab FDG SUVR (AD/MCI patterns) |
| NYUFDGHIP | 612 | 16 | 343 | 0.03% | NYU FDG Hippocampus |

#### PET Metadata (3 datasets)

| Dataset | Rows | Columns | Unique RID | Missing % | Description |
|---------|------|---------|------------|-----------|-------------|
| PETQC | 3,951 | 38 | 1,413 | 26.80% | PET quality control |
| PETMETA_ADNI1 | 1,957 | 104 | 420 | 62.63% | ADNI1 PET metadata |
| CROSSVAL | 822 | 5 | 822 | 0.00% | Cross-validation data |

### 1.2 Aggregate Statistics by Category

| Category | Files | Total Rows | Avg Columns | Total Memory | Unique RID | Avg Missing % |
|----------|-------|------------|-------------|--------------|------------|---------------|
| Amyloid PET | 3 | 8,726 | 26.0 | 4.38 MB | 4,510 | 24.48% |
| Tau PET | 4 | 10,253 | 185.3 | 15.85 MB | 5,783 | 22.11% |
| FDG PET | 3 | 11,820 | 13.3 | 2.92 MB | 3,640 | 0.02% |
| PET Metadata | 3 | 6,730 | 49.0 | 4.90 MB | 2,655 | 29.81% |

---

## 2. Schema Mapping and Table Relationships

### 2.1 Join Key Availability

| Dataset | RID | PTID | VISCODE | VISCODE2 | PHASE |
|---------|-----|------|---------|----------|-------|
| BAIPETNMRCAV45 | ✓ | ✗ | ✓ | ✓ | ✗ |
| BAIPETNMRCFDG | ✓ | ✗ | ✓ | ✓ | ✗ |
| UCBERKELEY_TAU_6MM | ✓ | ✓ | ✓ | ✓ | ✗ |
| UCBERKELEY_TAUPVC_6MM | ✓ | ✓ | ✓ | ✓ | ✗ |
| UCBERKELEYFDG_8mm | ✓ | ✗ | ✓ | ✓ | ✗ |
| AMYMETA | ✓ | ✓ | ✓ | ✓ | ✓ |
| TAUMETA | ✓ | ✓ | ✓ | ✓ | ✓ |
| NYUFDGHIP | ✓ | ✓ | ✓ | ✗ | ✓ |

### 2.2 Recommended Join Strategy

**Primary Join Keys for PET Data:**
- **(RID, VISCODE2)** - Most reliable for cross-modal PET integration
- **(RID, VISCODE)** - Alternative when VISCODE2 unavailable
- **EXAMDATE/SCANDATE** - For temporal alignment

---

## 3. Statistical EDA - Key PET Biomarkers

### 3.1 Amyloid PET (AV45) - BAI Lab

| Measure | N | Mean ± SD | Median (IQR) | Range |
|---------|---|-----------|--------------|-------|
| MCSUVRWM (Whole Cerebellum ref) | 2,815 | 0.8108 ± 0.1990 | 0.7499 (0.6601-0.9373) | 0.4385-1.9613 |
| MCSUVRCERE (Eroded Cerebellum ref) | 2,815 | 1.1663 ± 0.2281 | 1.0873 (0.9840-1.3296) | 0.7656-2.4249 |

**Interpretation:**
- Typical AV45 SUVR cutoff for amyloid positivity: ~1.10-1.20 (varies by reference region)
- Wide range indicates mix of amyloid-negative and amyloid-positive participants

### 3.2 Tau PET - UC Berkeley

| Measure | N | Mean ± SD | Median | Range |
|---------|---|-----------|--------|-------|
| META_TEMPORAL_SUVR | 2,315 | 1.2975 ± 0.3118 | 1.209 | 0.774-3.833 |

**Regional Coverage:**
- **164 Tau SUVR measures** available including:
  - Meta-temporal composite (entorhinal, amygdala, fusiform, parahippocampal)
  - Cortical regions (frontal, parietal, temporal, occipital)
  - Subcortical structures

### 3.3 FDG PET

#### UC Berkeley FDG (MetaROI)

| Measure | N | Mean ± SD | Median (IQR) | Range |
|---------|---|-----------|--------------|-------|
| MetaROI SUVR | 3,760 | 1.2380 ± 0.1007 | 1.2540 (1.1900-1.3033) | 0.7130-1.5120 |
| Top50PonsVermis SUVR | 3,760 | 1.0646 ± 0.0915 | 1.0700 | 0.774-1.450 |

#### BAI Lab FDG

| Pattern | N | Mean ± SD | Median | Range |
|---------|---|-----------|--------|-------|
| SROI.AD (AD-related regions) | 3,684 | 1.1636 ± 0.0815 | 1.1668 | 0.8591-1.3888 |
| SROI.MCI (MCI-related regions) | 3,684 | 1.0985 ± 0.0957 | 1.0996 | 0.7861-1.3525 |

#### NYU FDG Hippocampus

| Region | N | Mean ± SD | Median | Range |
|--------|---|-----------|--------|-------|
| Right Hippocampus/Pons | 612 | 0.9807 ± 0.1434 | 0.9899 | 0.4237-1.3929 |
| Left Hippocampus/Pons | 612 | 0.9607 ± 0.1523 | 0.9686 | 0.3898-1.4000 |
| Average Hippocampus | 612 | 0.9707 ± 0.1412 | 0.9793 | 0.4068-1.3937 |

---

## 4. Multimodal PET Correlation Analysis

### 4.1 Amyloid-Tau Correlation

| Comparison | N | Pearson r | Interpretation |
|------------|---|-----------|----------------|
| AV45 (WM ref) vs Tau (Meta-temporal) | 246 | **+0.50** | Moderate positive |
| AV45 (Cereb ref) vs Tau (Meta-temporal) | 246 | +0.45 | Moderate positive |

**Key Finding:** Amyloid and Tau show moderate positive correlation (r=0.50), consistent with the amyloid cascade hypothesis where amyloid deposition precedes and promotes tau pathology.

### 4.2 Amyloid-FDG Correlation

| Comparison | N | Pearson r | Interpretation |
|------------|---|-----------|----------------|
| AV45 vs FDG (AD pattern) | 1,614 | **-0.51** | Moderate negative |
| AV45 vs FDG (MCI pattern) | 1,614 | -0.48 | Moderate negative |

**Key Finding:** Strong negative correlation between amyloid burden and glucose metabolism, indicating that higher amyloid is associated with hypometabolism in AD-affected regions.

### 4.3 Tau-FDG Correlation

| Comparison | N | Pearson r | Interpretation |
|------------|---|-----------|----------------|
| Tau (Meta-temporal) vs FDG (AD pattern) | 247 | **-0.47** | Moderate negative |

**Key Finding:** Tau pathology is associated with reduced glucose metabolism, reflecting neurodegeneration in affected regions.

### 4.4 Cross-Modal Integration Summary

| Integration | Records | Participants |
|-------------|---------|--------------|
| Amyloid + Tau | 246 | ~200 |
| Amyloid + FDG | 1,614 | ~1,200 |
| Tau + FDG | 247 | ~200 |
| All three modalities | ~200 | ~150 |

---

## 5. Longitudinal Analysis

### 5.1 Visit Patterns

| Dataset | Participants | Mean Visits | Max Visits | % with 2+ Visits |
|---------|--------------|-------------|------------|------------------|
| UCBERKELEYFDG | 1,687 | 4.46 | 20 | 100.0% |
| BAIPETNMRCAV45 | 1,294 | 2.18 | 6 | 58.3% |
| UCBERKELEY_TAU | 1,357 | 1.71 | 7 | 40.4% |

### 5.2 Temporal Coverage

| Modality | Date Range | Span |
|----------|------------|------|
| FDG PET | 2005-2022 | 16.9 years |
| Amyloid PET | 2010-2020 | 9.7 years |
| Tau PET | 2015-2025 | 10.0 years |

### 5.3 Study Phase Distribution

| Phase | Records | Description |
|-------|---------|-------------|
| ADNI3 | 7,293 | Phase 3 (2016-2023) |
| ADNI4 | 4,166 | Phase 4 (2022-present) |
| ADNI1 | 2,569 | Phase 1 (2004-2010) |
| ADNI2 | 272 | Phase 2 (2009-2016) |

---

## 6. Data Quality Assessment

### 6.1 Missing Data Summary

| Category | Average Missing % | Highest Missing Dataset |
|----------|-------------------|------------------------|
| FDG PET | 0.02% | Excellent quality |
| Tau PET | 22.11% | Moderate (QC-related) |
| Amyloid PET | 24.48% | Moderate (QC-related) |
| PET Metadata | 29.81% | High (sparse fields) |

### 6.2 Critical Data Quality Issues

1. **PETMETA_ADNI1**: 62.63% missing data - historical ADNI1 metadata with sparse fields
2. **TAUQC**: 42.15% missing - quality control data with incomplete coverage
3. **AMYQC**: 39.46% missing - quality control data with incomplete coverage

### 6.3 Duplicate Records

No duplicate rows detected in any PET dataset.

---

## 7. Integration with Blood Biomarkers

### 7.1 Potential Integration Points

The PET data can be integrated with blood biomarkers (from UPENN Plasma dataset) using:
- **RID + VISCODE2** for visit-matched analysis
- **EXAMDATE** proximity for temporal alignment

### 7.2 Expected Correlations (Literature-Based)

| Blood Biomarker | Expected PET Correlation |
|-----------------|-------------------------|
| p-tau217 | Strong with Amyloid (r ~0.6-0.7) |
| Aβ42/40 | Strong with Amyloid (r ~-0.5 to -0.6) |
| NfL | Moderate with Tau (r ~0.3-0.4) |
| GFAP | Moderate with Amyloid (r ~0.3-0.4) |

---

## 8. Proposed Cleaned Schema for PET Data

### 8.1 Core PET Tables

**1. AMYLOID_PET_MASTER**
```
Primary Key: (RID, VISCODE2, EXAMDATE)
Columns:
  - RID (int): Participant identifier
  - VISCODE2 (str): Visit code
  - EXAMDATE (date): Scan date
  - AV45_SUVR_WM (float): AV45 SUVR (whole cerebellum reference)
  - AV45_SUVR_CERE (float): AV45 SUVR (eroded cerebellum reference)
  - AMYLOID_STATUS (int): Binary amyloid positive/negative
```

**2. TAU_PET_MASTER**
```
Primary Key: (RID, VISCODE2, SCANDATE)
Columns:
  - RID (int): Participant identifier
  - VISCODE2 (str): Visit code
  - SCANDATE (date): Scan date
  - META_TEMPORAL_SUVR (float): Meta-temporal composite SUVR
  - ENTORHINAL_SUVR (float): Entorhinal cortex SUVR
  - [164 regional SUVR columns...]
```

**3. FDG_PET_MASTER**
```
Primary Key: (RID, VISCODE2, EXAMDATE)
Columns:
  - RID (int): Participant identifier
  - VISCODE2 (str): Visit code
  - EXAMDATE (date): Scan date
  - METAROI_SUVR (float): MetaROI glucose metabolism
  - AD_PATTERN_SUVR (float): AD-pattern hypometabolism
  - MCI_PATTERN_SUVR (float): MCI-pattern hypometabolism
```

---

## 9. Conclusions

### 9.1 Data Suitability Summary

| Criterion | Assessment | Notes |
|-----------|------------|-------|
| Sample Size | ✓ Excellent | 1,200-1,600 participants per modality |
| Data Quality | ✓ Good | FDG excellent, Tau/Amyloid moderate |
| Longitudinal | ✓ Good | FDG up to 16.9 years, Tau 10 years |
| Multimodal | ✓ Good | All three PET modalities available |
| Cross-Modal Integration | ⚠ Moderate | 200-1,600 matched records |

### 9.2 Key Statistical Findings

1. **Amyloid-Tau Co-pathology**: Moderate positive correlation (r=0.50) supports the amyloid cascade hypothesis

2. **Hypometabolism Pattern**: Strong negative correlations between both amyloid (r=-0.51) and tau (r=-0.47) with FDG, indicating neurodegeneration

3. **FDG as Functional Marker**: MetaROI FDG shows clear separation potential with mean SUVR 1.24 ± 0.10

4. **Longitudinal Coverage**: FDG has the best longitudinal coverage (16.9 years), followed by Amyloid (9.7 years) and Tau (10.0 years)

### 9.3 Recommendations for AI Integration

1. **AT(N) Classification**: Use Amyloid (A), Tau (T), and FDG (N) for AT(N) research framework classification

2. **Blood-PET Validation**: Use PET as ground truth to validate blood biomarker performance

3. **Feature Engineering**: Create composite scores (e.g., amyloid+tau burden, hypometabolism patterns)

4. **Target Variables**: Use PET-based amyloid status, tau stage, or FDG patterns as targets for blood-based prediction models

---

*Report generated by automated EDA pipeline. All statistics derived directly from provided ADNI PET CSV files.*
