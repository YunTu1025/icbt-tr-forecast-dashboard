# Unreachable Code Analysis - fee_forecast_ui.py Lines 188-206

## Executive Summary

**CONFIRMED: Lines 190-206 in fee_forecast_ui.py are UNREACHABLE CODE**

The Index Table display section is never executed because the function returns at line 188, before the Index Table code can run.

---

## Evidence

### Code Structure

```python
# fee_forecast_ui.py - render_fee_forecast_section() function

# Line 150: Index table IS built
df_index = build_index_table(df_forecast, active_weights, week_date_map)

# Line 155: Index table IS used for calculations
update_forecast_2026_baseline(df_forecast, df_index, baseline_2026)

# Lines 167-170: Index chart IS displayed (uses df_index)
with chart_col2:
    st.markdown(f"##### {fee_type_display} Index Chart")
    fig_index = create_index_chart(df_index)
    st.plotly_chart(fig_index, use_container_width=True)

# Line 185: Forecast table displayed
st.dataframe(df_forecast_display, use_container_width=True, height=400, hide_index=True)

# Line 188: FUNCTION RETURNS HERE ⚠️
return df_forecast

# Lines 190-206: UNREACHABLE CODE ❌
# This section NEVER executes:
st.markdown("---")
st.markdown(f"##### {fee_type_display} Index Table")
df_index_display = df_index.copy()
# ... formatting code ...
st.dataframe(df_index_display, use_container_width=True, height=400, hide_index=True)

# Line 206: Duplicate return (also unreachable)
return df_forecast
```

---

## Impact Analysis

### What Gets Displayed
✅ **Displayed (works correctly):**
1. Year Weights input section
2. Raw Data Preview table
3. Forecast Chart (left side)
4. **Index Chart (right side)** ← Uses df_index successfully
5. Forecast Table

### What Does NOT Get Displayed
❌ **NOT Displayed (unreachable):**
1. **Index Table** ← The formatted data table for the index values

---

## Usage Analysis

### Where is render_fee_forecast_section() called?

**Called 9 times in app.py for different fee types:**

1. Line 518: Variable (Index Baseline method)
2. Line 530: International (Index Baseline method)
3. Line 542: BSTD (Index Baseline method)
4. Line 566: SNAD (Index Baseline method)
5. Line 578: Fixed (Index Baseline method)
6. Line 590: Credit (Index Baseline method)

**These 3 use the _run_rate variant (doesn't have Index Table anyway):**
7. Line 554: eTRS (Run Rate - uses render_fee_forecast_section_run_rate)
8. Line 602: Regulatory (Run Rate - uses render_fee_forecast_section_run_rate)
9. Line 614: Buyer Protection (Run Rate - uses render_fee_forecast_section_run_rate)

**All callers expect only the return value (df_forecast), NOT the UI display**

The function's purpose is to:
1. Display UI components (side effect)
2. Return df_forecast DataFrame for use in Tab4

**None of the callers depend on the Index Table being displayed** - they only use the returned DataFrame.

---

## df_index Usage Verification

### Where df_index IS used (before the return):

1. **Line 155:** `update_forecast_2026_baseline(df_forecast, df_index, baseline_2026)`
   - ✅ This executes successfully
   - Updates the 2026 Index Baseline column in df_forecast

2. **Line 169:** `fig_index = create_index_chart(df_index)`
   - ✅ This executes successfully
   - Creates and displays the Index Chart

**Conclusion:** The Index Chart is displayed, but the Index Table (raw data) is not.

---

## Run Rate Variant Analysis

The `render_fee_forecast_section_run_rate()` function (lines 209-316) intentionally:
- Does NOT build an index table (no df_index variable)
- Does NOT display an Index Chart
- Does NOT display an Index Table

**From the docstring (line 223):**
```python
"""
Differences from Index Baseline methodology:
- No Year Weights input
- No Index Table        ← Explicitly states no Index Table
- No Index Chart        ← Explicitly states no Index Chart
- 2026 Index Baseline = constant baseline value
"""
```

This confirms that the Index Table was **intentionally designed** for the Index Baseline method, but the code bug prevents it from being displayed.

---

## Original Design Intent

Based on the code structure, the **original design intent** was:

### Index Baseline Fee Types (Variable, International, BSTD, SNAD, Fixed, Credit):
1. Year Weights input
2. Raw Data Preview table
3. **Side-by-side:** Forecast Chart (left) + Index Chart (right)
4. Forecast Table
5. **Index Table** ← Currently missing due to bug

### Run Rate Fee Types (eTRS, Regulatory, Buyer Protection):
1. Raw Data Preview table
2. Forecast Chart (full width, no Index Chart)
3. Forecast Table
4. No Index Table (by design)

---

## Fix Required

### Current Code (BROKEN):
```python
st.dataframe(df_forecast_display, use_container_width=True, height=400, hide_index=True)

# Return the forecast DataFrame for Tab4
return df_forecast  # ← Line 188: EARLY RETURN

# Display Index Table
st.markdown("---")
st.markdown(f"##### {fee_type_display} Index Table")
# ... unreachable code ...
```

### Fixed Code:
```python
st.dataframe(df_forecast_display, use_container_width=True, height=400, hide_index=True)

# Display Index Table (MOVE BEFORE RETURN)
st.markdown("---")
st.markdown(f"##### {fee_type_display} Index Table")

# Format index table for display
df_index_display = df_index.copy()
df_index_display = df_index_display.reset_index(drop=True)
for col in ['2022', '2023', '2024', '2025', '2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']:
    if col in df_index_display.columns:
        df_index_display[col] = df_index_display[col].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else ""
        )

st.dataframe(df_index_display, use_container_width=True, height=400, hide_index=True)

# Return the forecast DataFrame for Tab4 (SINGLE RETURN AT END)
return df_forecast
```

---

## Risk Assessment

### Risk of Fixing This Bug: **LOW**

**Why it's safe to fix:**
1. ✅ All callers only use the return value (df_forecast) - they don't depend on UI display
2. ✅ df_index is already calculated and used successfully (for chart and calculations)
3. ✅ No external dependencies on the current broken behavior
4. ✅ The fix simply moves existing code to an executable location
5. ✅ No logic changes - just reordering statements

**What changes after the fix:**
- Users will see the Index Table for Index Baseline fee types (Variable, International, BSTD, SNAD, Fixed, Credit)
- This matches the original design intent
- Run Rate fee types remain unchanged (no Index Table, as designed)

**No breaking changes expected.**

---

## Testing Checklist

After fixing:

- [ ] Variable fee forecast displays Index Table
- [ ] International fee forecast displays Index Table
- [ ] BSTD fee forecast displays Index Table
- [ ] SNAD fee forecast displays Index Table
- [ ] Fixed fee forecast displays Index Table
- [ ] Credit fee forecast displays Index Table
- [ ] eTRS fee forecast does NOT display Index Table (Run Rate method)
- [ ] Regulatory fee forecast does NOT display Index Table (Run Rate method)
- [ ] Buyer Protection fee forecast does NOT display Index Table (Run Rate method)
- [ ] Tab4 still receives df_forecast correctly from all fee types
- [ ] All forecast calculations remain unchanged

---

## Recommendation

**Fix this bug immediately.**

**Why:**
1. This is a clear defect - unreachable code serving no purpose
2. The Index Table was part of the original design (evidenced by df_index calculation)
3. Users are missing important data visualization (index values in table format)
4. Zero risk of breaking existing functionality
5. Improves feature completeness and user experience

**Estimated fix time:** 2 minutes
**Testing time:** 10 minutes
**Total impact time:** 12 minutes

---

## Conclusion

**Lines 190-206 are definitively unreachable code that should be moved before the return statement.**

The df_index table is already calculated and used (for Index Chart), but the raw data table display is hidden due to premature return. Moving this code before the return statement will complete the intended feature without any breaking changes.
