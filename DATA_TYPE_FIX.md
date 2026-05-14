# Data Type Fix for Hive String Columns

## Issue

When retrieving data from Hive database, numeric columns like `YEAR_ID`, `MONTH_OF_YEAR_ID`, and `DAY_OF_MONTH_ID` were being read as string types instead of integers. This caused a runtime error when the code tried to perform arithmetic operations on these columns.

## Error Message

```
TypeError: operation 'add' not supported for dtype 'str' with dtype 'int64'
```

**Location:** `modules/phasing_engine.py`, line 93  
**Operation:** `year_months['SORT_KEY'] = year_months[year_col] * 100 + year_months[month_col]`

## Root Cause

Hive database returns all columns as strings by default. When the code attempted to multiply and add these string values to create a sort key, Python raised a TypeError.

## Solution

Added explicit type conversions to integer in two functions in `modules/phasing_engine.py`:

### 1. `calculate_phasing_table()` - Lines 27-30

**Added:**
```python
# Convert to int to handle both string and int types from different data sources
df[year_col] = df[year_col].astype(int)
df[month_col] = df[month_col].astype(int)
df[day_col] = df[day_col].astype(int)
```

**Before line 32:**
```python
df['YEAR_MONTH'] = df[year_col].astype(str) + '-' + df[month_col].astype(str).str.zfill(2)
```

### 2. `get_trailing_12_months()` - Lines 97-99

**Added:**
```python
# Convert to int to handle both string and int types from different data sources
year_months[year_col] = year_months[year_col].astype(int)
year_months[month_col] = year_months[month_col].astype(int)
```

**Before line 101:**
```python
year_months['SORT_KEY'] = year_months[year_col] * 100 + year_months[month_col]
```

## Impact

This fix ensures the application works correctly with both:
- **Hive Database** - Columns come as strings, now converted to int
- **CSV File Upload** - Columns may be int or str, now always converted to int

The conversion is done early in the processing pipeline, ensuring all downstream operations work correctly regardless of the data source.

## Files Modified

- **modules/phasing_engine.py**
  - `calculate_phasing_table()` function - Added 3 type conversions
  - `get_trailing_12_months()` function - Added 2 type conversions

## Testing

After this fix, the application should:
- ✅ Load IF/FF/Store data from Hive without errors
- ✅ Load ALL REV data from Hive without errors
- ✅ Calculate phasing tables correctly
- ✅ Display Tab 3 (IF/FF/Store Forecast) without errors
- ✅ Handle both Hive and CSV data sources consistently

## Related Changes

This fix complements the addition of the ALL REV Data source, which uses the same `P_FPA_T.FEE_FORECAST2` table and encounters the same string type issue.

---

**Status:** Fixed ✅  
**Date:** 2026-05-07
