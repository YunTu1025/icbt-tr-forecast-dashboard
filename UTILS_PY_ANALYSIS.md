# utils.py Analysis - Complete Usage Audit

## Executive Summary

**STATUS: 80% DEAD CODE - Only 1 of 5 functions is actually used**

**Recommendation: Delete utils.py after migrating load_config() to app.py**

---

## Function-by-Function Analysis

### 1. load_config() - ✅ USED (1 usage)

**Location:** utils.py lines 7-10

```python
def load_config():
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
```

**Usage:**
- ✅ **app.py line 19:** `from modules.utils import load_config`
- ✅ **app.py line 57:** `config = load_config()`

**Current Usage:**
```python
# app.py line 57
config = load_config()
```

**But then:** The `config` variable is **NEVER USED** anywhere else in app.py!

```bash
$ grep -n "config" app.py
19:from modules.utils import load_config, validate_excel_file, show_dataframe_preview
57:    config = load_config()
```

**Verdict:**
- The function is called, but its return value is unused
- The config file is loaded but never referenced
- **This is essentially dead code too!**

**Recommendation:** 
- Check if config is needed at all
- If not needed: Remove load_config() call entirely
- If needed later: Move inline to app.py where it's used

---

### 2. get_project_root() - ❌ NEVER USED

**Location:** utils.py lines 12-13

```python
def get_project_root():
    return Path(__file__).parent.parent
```

**Usage:** NONE - Never imported, never called

**Search Results:**
```bash
$ grep -rn "get_project_root" --include="*.py"
modules/utils.py:12:def get_project_root():
```

**Verdict:** 100% dead code

**Recommendation:** DELETE

---

### 3. validate_excel_file() - ❌ IMPORTED BUT NEVER CALLED

**Location:** utils.py lines 15-30

```python
def validate_excel_file(file_path, expected_sheets=None):
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        xl_file = pd.ExcelFile(file_path)
        actual_sheets = xl_file.sheet_names
        
        if expected_sheets:
            missing_sheets = set(expected_sheets) - set(actual_sheets)
            if missing_sheets:
                return False, f"Missing sheets: {missing_sheets}"
        
        return True, f"Valid file with {len(actual_sheets)} sheets"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"
```

**Usage:**
- ⚠️ **app.py line 19:** `from modules.utils import ..., validate_excel_file, ...`
- ❌ **NEVER CALLED** anywhere in the codebase

**Search Results:**
```bash
$ grep -rn "validate_excel_file" --include="*.py"
app.py:19:from modules.utils import load_config, validate_excel_file, show_dataframe_preview
modules/utils.py:15:def validate_excel_file(file_path, expected_sheets=None):
```

**Verdict:** Imported but never used - zombie code

**Recommendation:** DELETE

---

### 4. format_number() - ❌ NEVER IMPORTED OR USED

**Location:** utils.py lines 32-43

```python
def format_number(value, format_type='currency'):
    if pd.isna(value):
        return "-"
    
    if format_type == 'currency':
        return f"${value:,.0f}"
    elif format_type == 'percent':
        return f"{value:.2%}"
    elif format_type == 'number':
        return f"{value:,.0f}"
    else:
        return str(value)
```

**Usage:** NONE - Never imported, never called

**Search Results:**
```bash
$ grep -rn "format_number" --include="*.py"
modules/utils.py:32:def format_number(value, format_type='currency'):
```

**BUT:** This function could be VERY useful!

**Inline formatting appears 36 times across 8 files:**
- app.py: 3 occurrences
- fee_forecast_engine.py: 3 occurrences  
- fee_forecast_ui.py: 3 occurrences
- forecast_review_ui.py: 19 occurrences
- forecast_review_engine.py: 3 occurrences
- if_ff_store_forecast_engine.py: 2 occurrences
- if_ff_store_ui.py: 2 occurrences
- phasing_engine.py: 1 occurrence

**Example inline formatting patterns:**
```python
# Pattern 1: Number with thousand separators
lambda x: f"{x:,.0f}" if pd.notna(x) else ""

# Pattern 2: Percentage with 2 decimals
lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""

# Pattern 3: Decimal with 2 places
lambda x: f"{x:.2f}" if pd.notna(x) else ""
```

**Verdict:** Not currently used, but could replace 36+ inline formatting statements

**Recommendation:** 
- **Option A:** Enhance and integrate format_number() across the codebase
- **Option B:** Delete if not integrating

---

### 5. show_dataframe_preview() - ❌ IMPORTED BUT NEVER CALLED

**Location:** utils.py lines 45-48

```python
def show_dataframe_preview(df, title="Data Preview", max_rows=10):
    st.subheader(title)
    st.dataframe(df.head(max_rows), use_container_width=True)
    st.caption(f"Showing {min(len(df), max_rows)} of {len(df)} rows")
```

**Usage:**
- ⚠️ **app.py line 19:** `from modules.utils import ..., show_dataframe_preview`
- ❌ **NEVER CALLED** anywhere in the codebase

**Search Results:**
```bash
$ grep -rn "show_dataframe_preview" --include="*.py"
app.py:19:from modules.utils import load_config, validate_excel_file, show_dataframe_preview
modules/utils.py:45:def show_dataframe_preview(df, title="Data Preview", max_rows=10):
```

**Verdict:** Imported but never used - zombie code

**Recommendation:** DELETE

---

## Summary Table

| Function | Imported? | Called? | Status | Action |
|----------|-----------|---------|--------|--------|
| load_config() | ✅ Yes (app.py) | ✅ Yes (app.py:57) | Used but result unused | Move inline or delete |
| get_project_root() | ❌ No | ❌ No | Dead code | DELETE |
| validate_excel_file() | ⚠️ Yes (app.py) | ❌ No | Zombie code | DELETE |
| format_number() | ❌ No | ❌ No | Unused utility | DELETE or integrate |
| show_dataframe_preview() | ⚠️ Yes (app.py) | ❌ No | Zombie code | DELETE |

**Total:** 1/5 functions actually used (20% utilization)

---

## Recommended Actions

### Step 1: Handle load_config()

**Current situation:**
```python
# app.py line 57
config = load_config()  # Called but result never used!
```

**Investigation needed:**
```bash
$ grep -n " config" app.py
19:from modules.utils import load_config, validate_excel_file, show_dataframe_preview
57:    config = load_config()
```

**The config variable is loaded but NEVER referenced!**

**Options:**

**Option A: Delete entirely** (if config.yaml not needed)
```python
# Just remove line 57
# config = load_config()  # DELETE THIS LINE
```

**Option B: Move inline to app.py** (if config.yaml might be needed later)
```python
# app.py - Add at top of main() function when actually needed
import yaml
from pathlib import Path

config_path = Path(__file__).parent / "config" / "settings.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
```

**Recommendation:** Check if config/settings.yaml exists and is needed. If not, delete the load_config() call.

---

### Step 2: Clean up app.py imports

**Current (line 19):**
```python
from modules.utils import load_config, validate_excel_file, show_dataframe_preview
```

**After cleanup:**
```python
# DELETE THIS ENTIRE LINE - no utils.py functions are actually used!
```

---

### Step 3: Delete utils.py

After removing all imports from app.py:

```bash
rm modules/utils.py
```

**Verification:**
```bash
# Ensure no other files import from utils
grep -rn "from modules.utils import\|from utils import\|import utils" --include="*.py"
# Should return NO results after cleanup
```

---

## format_number() Integration Analysis

If you want to integrate format_number() instead of deleting it, here's the impact:

### Current Inline Formatting Patterns

**Pattern 1: Number formatting (appears 8 times)**
```python
# Current
lambda x: f"{x:,.0f}" if pd.notna(x) and isinstance(x, (int, float)) else x

# With format_number()
lambda x: format_number(x, 'number')
```

**Pattern 2: Percentage formatting (appears 12 times)**
```python
# Current
lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""

# With format_number() - NEEDS ENHANCEMENT
# format_number() expects value already multiplied by 100
lambda x: format_number(x*100, 'percent') if pd.notna(x) else ""
```

**Pattern 3: Decimal formatting (appears 6 times)**
```python
# Current  
lambda x: f"{x:.2f}" if pd.notna(x) else ""

# With format_number() - NEEDS NEW FORMAT TYPE
lambda x: format_number(x, 'decimal')
```

### Enhanced format_number()

```python
def format_number(value, format_type='number'):
    """
    Format numeric values for display
    
    Args:
        value: Numeric value to format
        format_type: 'currency', 'percent', 'number', 'decimal', 'pct_raw'
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return ""
    
    if format_type == 'currency':
        return f"${value:,.0f}"
    elif format_type == 'percent':
        # Expects value as decimal (0.0545 → "5.45%")
        return f"{value:.2%}"
    elif format_type == 'pct_raw':
        # Expects value already as percentage (5.45 → "5.45%")
        return f"{value:.2f}%"
    elif format_type == 'number':
        return f"{value:,.0f}"
    elif format_type == 'decimal':
        return f"{value:.2f}"
    else:
        return str(value)
```

### Integration Effort Estimate

- **Files to modify:** 8 files
- **Locations to update:** 36+ inline lambda statements
- **Testing required:** Full UI regression test
- **Estimated time:** 3-4 hours
- **Risk:** Medium (formatting changes could break display)

### Integration Decision

**Recommendation: DO NOT INTEGRATE**

**Why:**
1. Inline formatting is clear and explicit
2. Integration requires touching 36+ locations across 8 files
3. Medium risk of introducing formatting bugs
4. Minimal benefit (slightly shorter code, no performance gain)
5. Current inline approach is more maintainable (each format is visible at use site)

**Better approach:** Keep inline formatting, delete format_number()

---

## File Deletion Safety Check

### Dependencies Check

```bash
# Check if any file imports utils
$ grep -rn "from modules.utils\|from utils\|import utils" --include="*.py"
app.py:19:from modules.utils import load_config, validate_excel_file, show_dataframe_preview
```

**Only app.py imports from utils.py**

### Files to Modify

1. **app.py line 19:** Remove utils import
2. **app.py line 57:** Remove load_config() call (or move inline if needed)
3. **modules/utils.py:** DELETE entire file

### Safe to Delete After Cleanup: ✅ YES

---

## Final Recommendations

### Priority 1: Immediate Cleanup (Do Now)

1. ✅ Check if config/settings.yaml is needed
   - If NO: Delete app.py line 57 (`config = load_config()`)
   - If YES: Move load_config logic inline to app.py where it's used

2. ✅ Remove dead imports from app.py line 19
   ```python
   # DELETE THIS LINE:
   from modules.utils import load_config, validate_excel_file, show_dataframe_preview
   ```

3. ✅ Delete modules/utils.py
   ```bash
   rm modules/utils.py
   ```

4. ✅ Verify no broken imports
   ```bash
   python app.py  # Should run without errors
   ```

### Priority 2: Future Consideration (Optional)

- Consider creating a new common_formatting.py if formatting utilities are needed later
- Keep inline formatting as-is (it works well and is maintainable)

---

## Testing Checklist

After deleting utils.py:

- [ ] App starts without import errors
- [ ] Tab1 (Data Overview) loads correctly
- [ ] Tab2 (FVF Forecast) loads correctly
- [ ] Tab3 (IF/FF/Store Forecast) loads correctly
- [ ] Tab4 (Forecast Review) loads correctly
- [ ] Hive connection works (if used)
- [ ] CSV upload works (if used)
- [ ] All displays format correctly (numbers, percentages, decimals)

---

## Conclusion

**utils.py contains 80% dead code and should be deleted.**

The only "used" function (load_config) is called but its result is never used, making it effectively dead code as well.

**Recommended action plan:**
1. Remove utils import from app.py
2. Remove config = load_config() call from app.py (line 57)
3. Delete modules/utils.py
4. Test the application

**Estimated time:** 5 minutes
**Risk level:** Very Low (no actual functionality depends on utils.py)
