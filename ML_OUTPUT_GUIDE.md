# Machine Learning Forecast Output Guide

## What You'll See When Running Variable Forecast

### 1. TRAINING DATA ANALYSIS
Shows the historical data (2022-2025) the model learns from:
- **Year-by-year statistics**: mean, std dev, range for each year
- **Quarter averages**: Average TR for Q1, Q2, Q3, Q4 across all years
- **Thanksgiving patterns**: Actual Thanksgiving week drops from historical years

**Purpose**: Verify that historical data HAS the patterns we want to learn (QoQ drops, Thanksgiving drops)

---

### 2. FEATURE IMPORTANCE
Shows which features XGBoost finds most useful:
- **Lagged values** (lag_1, lag_2, etc.): Recent week values
- **Rolling averages** (rolling_mean_4, rolling_mean_8, etc.): Smoothed trends
- **Seasonal indicators** (is_thanksgiving_week, quarter_2, etc.): Time-based patterns
- **Change features** (change_1w, pct_change_1w, etc.): Week-over-week movements
- **YoY features** (lag_52, yoy_change, etc.): Year-over-year comparisons

**Purpose**: See if Thanksgiving indicators and QoQ features are being used

---

### 3. RAW ML PREDICTIONS (Before Calibration)
Shows the pure model output before any adjustments:
- **Overall stats**: Mean, std dev, range, max week-over-week drop
- **Quarter averages**: Q1, Q2, Q3, Q4 averages
- **Q2→Q3 change**: The quarter-over-quarter drop
- **Thanksgiving pattern**: Week 47, 48, 49 values and drop magnitude

**Purpose**: See if the model LEARNED the patterns (before calibration affects them)

---

### 4. CALIBRATION
Shows the adjustment applied to align with 2026 actual data:

```
CALIBRATION: Adding +0.0015 (+0.15%) to all predictions
Purpose: Align with 2025→2026 YoY trend while preserving variations
```

**What is Calibration?**
- Compares your partial 2026 actual data to 2025 average
- Calculates a level adjustment (additive, not multiplicative)
- Shifts all predictions by the same amount
- **PRESERVES** the shape (QoQ drops, Thanksgiving drops stay the same)

**Before Calibration**: Pure model predictions based on 2022-2025 patterns
**After Calibration**: Adjusted to match 2026 YoY trend level

---

### 5. AFTER CALIBRATION
Shows final predictions with calibration applied:
- Same statistics as "before" but shifted to 2026 level
- Quarter averages and Q2→Q3 change
- Thanksgiving pattern and drop

**Purpose**: Final forecast that goes into your charts and tables

---

### 6. SAMPLE WEEKS COMPARISON
Side-by-side view of before/after calibration:

```
Week   Before       After        Difference
--------------------------------------------------
1      11.25%      11.40%       +0.15%
13     11.30%      11.45%       +0.15%
26     11.22%      11.37%       +0.15%
...
```

**Purpose**: Verify calibration is additive (same difference for all weeks)

---

## What to Look For

### If Q2→Q3 Drop is Missing:
1. Check TRAINING DATA: Do historical years show a Q2→Q3 pattern?
2. Check FEATURE IMPORTANCE: Is `qoq_change` or `quarter_3` important?
3. Check RAW PREDICTIONS: Is the drop there before calibration?

### If Thanksgiving Drop is Too Subtle:
1. Check TRAINING DATA: What is the actual historical Thanksgiving drop magnitude?
2. Check FEATURE IMPORTANCE: Are `is_thanksgiving_week`, `is_pre_thanksgiving` important?
3. Check RAW PREDICTIONS: Is the drop magnitude correct before calibration?

### If Forecast is Too Flat:
1. Check RAW PREDICTIONS std dev: Should be similar to historical std dev
2. If raw predictions have variation but output is flat → Calibration might be wrong
3. If raw predictions are already flat → Model isn't learning patterns (check features)

---

## Key Metrics to Compare

| Metric | Historical (2022-2025) | Raw 2026 Prediction | After Calibration |
|--------|------------------------|---------------------|-------------------|
| Mean TR | ~11.25% | Should be similar | Adjusted to match 2026 actuals |
| Std Dev | ~0.15% | **Should be similar** | **Should be same as raw** |
| Q2→Q3 Drop | ~-0.05% | Should match | Should match |
| Thanksgiving Drop | ~-0.10% | Should match | Should match |

**Critical**: Std dev should be preserved through calibration!
