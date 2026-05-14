# ALL REV Data Source Addition

## Summary

Added a third data source option "ALL REV Data" to the application with support for both Hive Database retrieval and CSV file upload.

---

## Changes Made

### 1. Added Query to `modules/hive_queries.py`

**New Method:** `get_all_rev_data()`

```python
@staticmethod
def get_all_rev_data():
    return """
    SELECT *
    FROM P_FPA_T.FEE_FORECAST2
    WHERE YEAR_ID >= 2021
    """
```

**Location:** Lines 35-40

---

### 2. Updated `app.py`

#### Session State Initialization (Line 62)
Added new session state variable:
```python
st.session_state.all_rev_data = None
```

#### Hive Database Retrieval (Lines 106, 143-158)

**Added success flag:**
```python
all_rev_success = False
```

**Added data retrieval block:**
```python
try:
    with st.spinner("Retrieving ALL REV data from P_FPA_T.FEE_FORECAST2..."):
        all_rev_results = hive_conn.execute_query(HiveQueries.get_all_rev_data())
        all_rev_columns = hive_conn.get_column_names()
        st.session_state.all_rev_data = pd.DataFrame(all_rev_results, columns=all_rev_columns)
        all_rev_success = True
        st.sidebar.success(f"✅ ALL REV Data: {len(all_rev_results):,} rows")
except Exception as e:
    error_msg = str(e)
    if "access" in error_msg.lower() or "permission" in error_msg.lower() or "denied" in error_msg.lower():
        error_tables.append("P_FPA_T.FEE_FORECAST2 (ALL REV)")
        st.sidebar.error(f"❌ Access denied to P_FPA_T.FEE_FORECAST2 (ALL REV)")
    else:
        st.sidebar.error(f"❌ ALL REV query error: {error_msg[:100]}")
```

**Updated success condition:**
```python
if fvf_success or if_ff_success or all_rev_success:
    st.session_state.data_loaded = True
    st.session_state.data_source = 'Hive Database'
```

#### CSV File Upload (Lines 177, 193-239)

**Updated description:**
```python
st.sidebar.markdown("Upload CSV files for FVF, IF/FF/Store, and ALL REV data")
```

**Added file uploader:**
```python
all_rev_csv_file = st.sidebar.file_uploader(
    "Upload ALL REV Data (CSV)",
    type=['csv'],
    accept_multiple_files=False,
    key='all_rev_csv_uploader'
)
```

**Updated validation:**
```python
if not fvf_csv_file and not if_ff_csv_file and not all_rev_csv_file:
    st.sidebar.error("❌ Please upload at least one CSV file")
```

**Added success flag and CSV loading:**
```python
all_rev_success = False

# Load ALL REV CSV
if all_rev_csv_file:
    try:
        st.session_state.all_rev_data = pd.read_csv(all_rev_csv_file)
        all_rev_success = True
        st.sidebar.success(f"✅ ALL REV Data: {len(st.session_state.all_rev_data):,} rows")
    except Exception as e:
        st.sidebar.error(f"❌ ALL REV CSV error: {str(e)[:100]}")
```

**Updated success condition:**
```python
if fvf_success or if_ff_success or all_rev_success:
    st.session_state.data_loaded = True
    st.session_state.data_source = 'CSV File Upload'
    st.sidebar.success("✅ CSV files loaded successfully!")
```

---

## Usage

### Option 1: Hive Database

1. Select "Hive Database" in the sidebar
2. Enter NT Username and PET Password
3. Click "📊 Retrieve Data"
4. The system will retrieve three data sources:
   - FVF Data from `P_FPA_T.BUDGET_DATA_OUTPUT`
   - IF/FF/Store Data from `P_FPA_T.FEE_FORECAST2` (aggregated)
   - **ALL REV Data from `P_FPA_T.FEE_FORECAST2` (all columns, YEAR_ID >= 2021)**

### Option 2: CSV File Upload

1. Select "CSV File Upload" in the sidebar
2. Upload CSV files for one or more data sources:
   - Upload FVF Data (CSV) - optional
   - Upload IF/FF/Store Data (CSV) - optional
   - **Upload ALL REV Data (CSV) - optional**
3. Click "📊 Load CSV Data"
4. The system will load all uploaded files

---

## Data Access

After loading, the ALL REV data is available in session state as:

```python
st.session_state.all_rev_data
```

This DataFrame contains all columns from `P_FPA_T.FEE_FORECAST2` where `YEAR_ID >= 2021`.

---

## Query Details

**Table:** `P_FPA_T.FEE_FORECAST2`  
**Filter:** `WHERE YEAR_ID >= 2021`  
**Columns:** All columns (SELECT *)

This is different from the IF/FF/Store query which:
- Filters by `DT >= '2021-01-01'`
- Aggregates specific columns with SUM()
- Groups by multiple dimensions

The ALL REV query retrieves the full raw data without aggregation.

---

## Files Modified

1. **modules/hive_queries.py**
   - Added `get_all_rev_data()` method

2. **app.py**
   - Added session state variable `all_rev_data`
   - Added Hive retrieval for ALL REV data
   - Added CSV uploader for ALL REV data
   - Updated success conditions to include ALL REV data
   - Updated sidebar messages to mention ALL REV data

---

## Testing Checklist

### Hive Database Mode
- [ ] Connect to Hive with valid credentials
- [ ] Click "Retrieve Data"
- [ ] Verify ALL REV data is retrieved successfully
- [ ] Check sidebar shows "✅ ALL REV Data: X rows"
- [ ] Verify `st.session_state.all_rev_data` contains data
- [ ] Test error handling for access denied scenarios

### CSV Upload Mode
- [ ] Select "CSV File Upload"
- [ ] Upload a CSV file for ALL REV Data
- [ ] Click "Load CSV Data"
- [ ] Verify CSV loads successfully
- [ ] Check sidebar shows "✅ ALL REV Data: X rows"
- [ ] Verify `st.session_state.all_rev_data` contains data
- [ ] Test error handling for invalid CSV files

### Combined Testing
- [ ] Test loading only ALL REV data (no FVF or IF/FF/Store)
- [ ] Test loading ALL REV data alongside other data sources
- [ ] Verify session state persists across page interactions
- [ ] Test switching between Hive and CSV modes

---

## Implementation Complete

✅ Query added to `hive_queries.py`  
✅ Session state initialized  
✅ Hive retrieval implemented  
✅ CSV upload implemented  
✅ Error handling added  
✅ Success messages configured  
✅ Data accessible via `st.session_state.all_rev_data`

**Status:** Ready for testing
