"""
Forecast Review Engine - Aggregate and prepare forecast data for Tab4 review
"""
import pandas as pd
import numpy as np


def aggregate_tab2_weekly_forecast(forecast_data_dict, week_date_map):
    """
    Aggregate Tab2 FVF forecast data by week

    Args:
        forecast_data_dict: Dictionary with fee type names as keys and forecast DataFrames as values
                           Expected keys: 'Variable', 'BSTD', 'Fixed', 'eTRS', 'Regulatory', 'Buyer Protection'
        week_date_map: Dictionary mapping week numbers to dates

    Returns:
        DataFrame with columns: Week, Variable, International, BSTD, eTRS, SNAD, Fixed, Credit, Regulatory, Buyer Protection, Net FVF
    """
    # Initialize result DataFrame for 52 weeks
    weeks = list(range(1, 53))
    result_df = pd.DataFrame({'Week': weeks})

    # Fee type mapping from Tab2 to Total Site columns (all 9 fee types)
    fee_type_mapping = {
        'Variable': 'Variable',
        'International': 'International',
        'BSTD': 'BSTD',
        'eTRS': 'eTRS',
        'SNAD': 'SNAD',
        'Fixed': 'Fixed',
        'Credit': 'Credit',
        'Regulatory': 'Regulatory',
        'Buyer Protection': 'Buyer Protection'
    }

    # Add columns from Tab2 forecast data
    for tab2_fee_type, column_name in fee_type_mapping.items():
        if tab2_fee_type in forecast_data_dict:
            df_forecast = forecast_data_dict[tab2_fee_type]

            # Skip the first row (baseline row with Week = 'Index/Baseline')
            df_data = df_forecast[df_forecast['Week'] != 'Index/Baseline'].copy()

            # Create week-value mapping
            week_values = {}
            for _, row in df_data.iterrows():
                week = row['Week']

                # Priority: 2026 actual data first, then 2026 Index Baseline forecast
                value_2026_actual = row.get('2026', np.nan)
                value_2026_forecast = row.get('2026 Index Baseline', np.nan)

                # Use actual if available, otherwise use forecast
                if pd.notna(value_2026_actual):
                    value = value_2026_actual
                else:
                    value = value_2026_forecast

                if pd.notna(week) and isinstance(week, (int, float)):
                    week_values[int(week)] = value

            # Map values to result DataFrame
            result_df[column_name] = result_df['Week'].map(week_values)
        else:
            # Fee type not found, fill with NaN
            result_df[column_name] = np.nan

    # Calculate Net FVF (sum of all 9 FVF components)
    fvf_components = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']

    # For each row, sum all non-NaN components
    result_df['Net FVF'] = result_df[fvf_components].sum(axis=1, skipna=True)

    # If all components are NaN, set Net FVF to NaN
    all_nan_mask = result_df[fvf_components].isna().all(axis=1)
    result_df.loc[all_nan_mask, 'Net FVF'] = np.nan

    # Reorder columns to match the reference format
    final_columns = ['Week', 'Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF']
    result_df = result_df[final_columns]

    return result_df


def build_fvf_weekly_table(forecast_data_dict, week_date_map, gmv_data=None):
    """
    Build the complete FVF weekly forecast table with GMV column

    Args:
        forecast_data_dict: Dictionary with fee type forecast data from Tab2
        week_date_map: Dictionary mapping week numbers to dates
        gmv_data: Optional DataFrame with GMV values (from data_editor)

    Returns:
        DataFrame with columns: Week, GMV, Variable, International, BSTD, eTRS, SNAD, Fixed, Credit, Regulatory, Buyer Protection, Net FVF
    """
    # Get FVF forecast data
    fvf_df = aggregate_tab2_weekly_forecast(forecast_data_dict, week_date_map)

    # Add GMV column (initially empty/NaN)
    fvf_df.insert(1, 'GMV', np.nan)

    # If GMV data is provided (from data_editor), merge it
    if gmv_data is not None and isinstance(gmv_data, pd.DataFrame):
        if 'GMV' in gmv_data.columns:
            # Update GMV values from the data editor
            fvf_df['GMV'] = gmv_data['GMV']

    return fvf_df


def format_fvf_weekly_table_for_display(fvf_df):
    """
    Format the FVF weekly table for Streamlit data_editor

    Args:
        fvf_df: DataFrame from build_fvf_weekly_table

    Returns:
        Formatted DataFrame with proper number/percentage formatting
    """
    display_df = fvf_df.copy()

    # GMV column remains as numeric (data_editor will handle editing)
    # No formatting needed for GMV

    # Format all FVF component columns as percentages (2 decimal places)
    fvf_columns = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF']
    for col in fvf_columns:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    return display_df


def build_date_to_week_mapping():
    """
    Build mapping from date to retail week number for 2026

    Returns:
        DataFrame with columns: Date, Week (retail week number)
    """
    import datetime

    # Date to week mapping for 2026 retail calendar
    # Week 53 (2025 carryover): Jan 1-3
    # Week 1: Jan 4-10
    # Week 2: Jan 11-17
    # And so on...

    date_week_map = []

    # Week 53: Jan 1-3, 2026
    for day in range(1, 4):
        date_week_map.append({
            'Date': datetime.date(2026, 1, day),
            'Week': 53
        })

    # Weeks 1-52: Starting from Jan 4, 2026
    week_num = 1
    current_date = datetime.date(2026, 1, 4)
    end_date = datetime.date(2026, 12, 31)

    while current_date <= end_date:
        date_week_map.append({
            'Date': current_date,
            'Week': week_num
        })

        current_date += datetime.timedelta(days=1)

        # Each retail week has 7 days
        # Check if we need to increment week (every 7 days from Jan 4)
        days_since_week1_start = (current_date - datetime.date(2026, 1, 4)).days
        week_num = min((days_since_week1_start // 7) + 1, 52)

    return pd.DataFrame(date_week_map)


def build_fvf_daily_table(weekly_df, date_week_df=None):
    """
    Build FVF daily forecast table from weekly forecast data

    Args:
        weekly_df: Weekly forecast DataFrame (raw numeric data with GMV and 9 fee types)
        date_week_df: Optional DataFrame with Date-Week mapping. If None, will generate default mapping.

    Returns:
        DataFrame with columns: Date, Week, GMV, Variable, International, BSTD, eTRS, SNAD, Fixed, Credit, Regulatory, Buyer Protection, Net FVF
    """
    # Get date-week mapping
    if date_week_df is None:
        date_week_df = build_date_to_week_mapping()

    # Initialize result list
    daily_data = []

    # For each date, look up the retail week and get values from weekly_df
    for _, date_row in date_week_df.iterrows():
        date_val = date_row['Date']
        week_num = date_row['Week']

        # Find matching week in weekly_df
        week_match = weekly_df[weekly_df['Week'] == week_num]

        if not week_match.empty:
            week_data = week_match.iloc[0]

            daily_row = {
                'Date': date_val,
                'Week': week_num,
                'GMV': week_data.get('GMV', np.nan),
                'Variable': week_data.get('Variable', np.nan),
                'International': week_data.get('International', np.nan),
                'BSTD': week_data.get('BSTD', np.nan),
                'eTRS': week_data.get('eTRS', np.nan),
                'SNAD': week_data.get('SNAD', np.nan),
                'Fixed': week_data.get('Fixed', np.nan),
                'Credit': week_data.get('Credit', np.nan),
                'Regulatory': week_data.get('Regulatory', np.nan),
                'Buyer Protection': week_data.get('Buyer Protection', np.nan),
                'Net FVF': week_data.get('Net FVF', np.nan)
            }
        else:
            # No matching week data
            daily_row = {
                'Date': date_val,
                'Week': week_num,
                'GMV': np.nan,
                'Variable': np.nan,
                'International': np.nan,
                'BSTD': np.nan,
                'eTRS': np.nan,
                'SNAD': np.nan,
                'Fixed': np.nan,
                'Credit': np.nan,
                'Regulatory': np.nan,
                'Buyer Protection': np.nan,
                'Net FVF': np.nan
            }

        daily_data.append(daily_row)

    return pd.DataFrame(daily_data)


def build_fvf_daily_tables(weekly_df, if_daily_breakdown_df=None, tab3_monthly_data=None, date_week_df=None, all_rev_data=None):
    """
    Build FVF daily forecast tables in two formats: dollar amount and take rate %

    Args:
        weekly_df: Weekly forecast DataFrame with GMV and 9 fee type take rates
        if_daily_breakdown_df: Daily breakdown table with IF forecasts
        tab3_monthly_data: Dictionary with Tab3 monthly forecasts {'IF': df, 'FF': df, 'Store': df}
        date_week_df: Optional DataFrame with Date-Week mapping
        all_rev_data: Optional DataFrame with ALL REV data for actual values

    Returns:
        tuple: (dollar_df, pct_df) - Two DataFrames with same columns
    """
    # Get date-week mapping
    if date_week_df is None:
        # Load static Date-Week-Month mapping from CSV
        import os
        mapping_path = os.path.join('data', 'date_week_month_mapping.csv')
        if os.path.exists(mapping_path):
            date_week_df = pd.read_csv(mapping_path)
            date_week_df['Date'] = pd.to_datetime(date_week_df['Date'])
        else:
            # Fallback to dynamic generation
            date_week_df = build_date_to_week_mapping()

    # Determine current date from ALL REV data
    current_date = None
    if all_rev_data is not None and 'DT' in all_rev_data.columns:
        current_date = pd.to_datetime(all_rev_data['DT']).max()

    # Build ALL REV data lookup dictionary by date - sum to daily level
    all_rev_dict = {}
    if all_rev_data is not None and 'DT' in all_rev_data.columns:
        all_rev_data_copy = all_rev_data.copy()
        all_rev_data_copy['DT'] = pd.to_datetime(all_rev_data_copy['DT'])

        # Group by date and sum all numeric columns
        all_rev_data_copy['Date_Key'] = all_rev_data_copy['DT'].dt.date

        # Define columns to sum
        sum_columns = [
            'GMV_PLAN',
            'FVF_BASE_G_USD_PLAN', 'ETRS_CREDIT_PLAN', 'CBT_FEE_G_USD_PLAN',
            'FVF_BSTD_G_USD_PLAN', 'FVF_SNAD_N_USD_PLAN', 'FIXED_FEE_G_USD_PLAN',
            'FVF_BASE_C_USD_PLAN', 'CBT_FEE_C_USD_PLAN', 'FVF_BSTD_C_USD_PLAN',
            'FIXED_FEE_C_USD_PLAN', 'FVF_REGULATORY_N_USD_PLAN', 'FVF_BuyerProtect_N_USD_PLAN',
            'IF_N_USD_PLAN', 'FF_N_USD_PLAN', 'TTL_PL_FEE_N_USD_PLAN', 'STORE_FEE_N_USD_PLAN'
        ]

        # Filter to only columns that exist in the dataframe
        existing_sum_columns = [col for col in sum_columns if col in all_rev_data_copy.columns]

        # Group by date and sum
        daily_agg = all_rev_data_copy.groupby('Date_Key')[existing_sum_columns].sum().reset_index()

        # Convert to dictionary
        for _, row in daily_agg.iterrows():
            date_key = row['Date_Key']
            all_rev_dict[date_key] = row

    # Fee type columns
    fee_types = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']

    # Initialize result lists
    daily_dollar_data = []
    daily_pct_data = []

    # Build IF daily lookup dict (convert to date for consistent matching)
    if_daily_dict = {}
    if if_daily_breakdown_df is not None:
        for _, row in if_daily_breakdown_df.iterrows():
            date_val = row['Date']
            # Convert pandas Timestamp to date
            if hasattr(date_val, 'date'):
                date_key = date_val.date()
            else:
                date_key = date_val
            if_daily_dict[date_key] = row['IF Daily Forecast']

    # Build FF monthly revenue lookup dict
    ff_monthly_revenue = {}
    if tab3_monthly_data and 'FF' in tab3_monthly_data:
        ff_monthly_df = tab3_monthly_data['FF']

        # Safety check: ensure MONTH_OF_YEAR_ID is index, not column
        if 'MONTH_OF_YEAR_ID' in ff_monthly_df.columns:
            ff_monthly_df = ff_monthly_df.set_index('MONTH_OF_YEAR_ID')

        # Monthly data has MONTH_OF_YEAR_ID as index
        for month in range(1, 13):
            if month in ff_monthly_df.index:
                # Try different column names for 2026 forecast
                revenue_value = np.nan
                for col in ['2026 Adjusted', '2026 Index Baseline', '2026']:
                    if col in ff_monthly_df.columns:
                        val = ff_monthly_df.loc[month, col]
                        if pd.notna(val):
                            revenue_value = val
                            break
                ff_monthly_revenue[month] = revenue_value

    # Build Store monthly revenue lookup dict (all revenue on 1st day of month)
    store_monthly_revenue = {}
    if tab3_monthly_data and 'Store' in tab3_monthly_data:
        store_monthly_df = tab3_monthly_data['Store']

        # Safety check: ensure MONTH_OF_YEAR_ID is index, not column
        if 'MONTH_OF_YEAR_ID' in store_monthly_df.columns:
            store_monthly_df = store_monthly_df.set_index('MONTH_OF_YEAR_ID')

        # Monthly data has MONTH_OF_YEAR_ID as index
        for month in range(1, 13):
            if month in store_monthly_df.index:
                # Try different column names for 2026 forecast
                revenue_value = np.nan
                for col in ['2026 Adjusted', '2026 Index Baseline', '2026']:
                    if col in store_monthly_df.columns:
                        val = store_monthly_df.loc[month, col]
                        if pd.notna(val):
                            revenue_value = val
                            break
                store_monthly_revenue[month] = revenue_value

    # For each date, calculate dollar and take rate
    rows_with_weekly_data = 0
    rows_without_weekly_data = 0

    for idx, date_row in date_week_df.iterrows():
        date_val = date_row['Date']
        week_num = date_row['Week']
        month_num = date_val.month
        day_of_month = date_val.day

        # GMV - initialize as NaN, will be editable
        gmv = np.nan

        # IF dollar - retrieve from daily breakdown table (for Revenue table display)
        # This is NOT restricted by date-week mapping
        # Convert date_val to date object for consistent lookup
        date_key = date_val.date() if hasattr(date_val, 'date') else date_val
        if_dollar = if_daily_dict.get(date_key, np.nan)

        # Store dollar - all revenue on 1st day of month (for Revenue table display)
        # This is NOT restricted by date-week mapping
        if day_of_month == 1:
            store_dollar = store_monthly_revenue.get(month_num, np.nan)
        else:
            store_dollar = 0.0 if month_num in store_monthly_revenue else np.nan

        # Find matching week in weekly_df to get FVF take rates
        week_match = weekly_df[weekly_df['Week'] == week_num]

        if not week_match.empty:
            week_data = week_match.iloc[0]
            # Get FVF take rates from weekly data (for TR table display)
            fvf_trs = {fee_type: week_data.get(fee_type, np.nan) for fee_type in fee_types}
            net_fvf_tr = week_data.get('Net FVF', np.nan)
            rows_with_weekly_data += 1
        else:
            # No matching week data - use NaN for FVF take rates
            fvf_trs = {fee_type: np.nan for fee_type in fee_types}
            net_fvf_tr = np.nan
            rows_without_weekly_data += 1

        # Determine A/F status
        af_status = 'F'  # Default to Forecast
        if current_date is not None and date_val <= current_date:
            af_status = 'A'  # Actual

        # Check if we have actual data for this date
        date_key = date_val.date() if hasattr(date_val, 'date') else date_val
        actual_row = all_rev_dict.get(date_key, None)

        # Initialize values
        actual_gmv = np.nan
        actual_variable = np.nan
        actual_international = np.nan
        actual_bstd = np.nan
        actual_etrs = np.nan
        actual_snad = np.nan
        actual_fixed = np.nan
        actual_credit = np.nan
        actual_regulatory = np.nan
        actual_buyer_protection = np.nan
        actual_net_fvf = np.nan
        actual_if = np.nan
        actual_ff = np.nan
        actual_net_xot = np.nan
        actual_store = np.nan

        # If A/F = 'A', retrieve actual values from ALL REV Data
        if af_status == 'A' and actual_row is not None:
            actual_gmv = actual_row.get('GMV_PLAN', np.nan)
            # Calculate fee types from actual data
            fvf_base_g = actual_row.get('FVF_BASE_G_USD_PLAN', 0) if pd.notna(actual_row.get('FVF_BASE_G_USD_PLAN')) else 0
            etrs_credit = actual_row.get('ETRS_CREDIT_PLAN', 0) if pd.notna(actual_row.get('ETRS_CREDIT_PLAN')) else 0
            actual_variable = fvf_base_g - etrs_credit
            actual_international = actual_row.get('CBT_FEE_G_USD_PLAN', np.nan)
            actual_bstd = actual_row.get('FVF_BSTD_G_USD_PLAN', np.nan)
            actual_etrs = etrs_credit
            actual_snad = actual_row.get('FVF_SNAD_N_USD_PLAN', np.nan)
            actual_fixed = actual_row.get('FIXED_FEE_G_USD_PLAN', np.nan)
            # Credit = sum of credit columns
            fvf_base_c = actual_row.get('FVF_BASE_C_USD_PLAN', 0) if pd.notna(actual_row.get('FVF_BASE_C_USD_PLAN')) else 0
            cbt_fee_c = actual_row.get('CBT_FEE_C_USD_PLAN', 0) if pd.notna(actual_row.get('CBT_FEE_C_USD_PLAN')) else 0
            fvf_bstd_c = actual_row.get('FVF_BSTD_C_USD_PLAN', 0) if pd.notna(actual_row.get('FVF_BSTD_C_USD_PLAN')) else 0
            fixed_fee_c = actual_row.get('FIXED_FEE_C_USD_PLAN', 0) if pd.notna(actual_row.get('FIXED_FEE_C_USD_PLAN')) else 0
            actual_credit = fvf_base_c + cbt_fee_c + fvf_bstd_c + fixed_fee_c
            actual_regulatory = actual_row.get('FVF_REGULATORY_N_USD_PLAN', np.nan)
            actual_buyer_protection = actual_row.get('FVF_BuyerProtect_N_USD_PLAN', np.nan)
            # Net FVF = sum of all fee types
            actual_net_fvf = sum([x for x in [actual_variable, actual_international, actual_bstd, actual_etrs,
                                              actual_snad, actual_fixed, actual_credit, actual_regulatory,
                                              actual_buyer_protection] if pd.notna(x)])
            actual_if = actual_row.get('IF_N_USD_PLAN', np.nan)
            # FF = FF_N_USD_PLAN - TTL_PL_FEE_N_USD_PLAN
            ff_n_usd = actual_row.get('FF_N_USD_PLAN', 0) if pd.notna(actual_row.get('FF_N_USD_PLAN')) else 0
            ttl_pl_fee = actual_row.get('TTL_PL_FEE_N_USD_PLAN', 0) if pd.notna(actual_row.get('TTL_PL_FEE_N_USD_PLAN')) else 0
            actual_ff = ff_n_usd - ttl_pl_fee
            # Net XOT = Net FVF + IF + FF
            actual_net_xot = sum([x for x in [actual_net_fvf, actual_if, actual_ff] if pd.notna(x)])
            actual_store = actual_row.get('STORE_FEE_N_USD_PLAN', np.nan)

        # Dollar row - use actual data if A/F = 'A', otherwise use forecast logic
        if af_status == 'A' and actual_row is not None:
            dollar_row = {
                'Date': date_val,
                'Week': week_num,
                'Month': month_num,
                'A/F': af_status,
                'GMV': actual_gmv,
                'Variable': actual_variable,
                'International': actual_international,
                'BSTD': actual_bstd,
                'eTRS': actual_etrs,
                'SNAD': actual_snad,
                'Fixed': actual_fixed,
                'Credit': actual_credit,
                'Regulatory': actual_regulatory,
                'Buyer Protection': actual_buyer_protection,
                'Net FVF': actual_net_fvf,
                'IF': actual_if,
                'FF': actual_ff,
                'Net XOT Rev (excl. PL)': actual_net_xot,
                'Store': actual_store
            }
        else:
            dollar_row = {
                'Date': date_val,
                'Week': week_num,
                'Month': month_num,
                'A/F': af_status,
                'GMV': gmv,
                'Variable': np.nan,
                'International': np.nan,
                'BSTD': np.nan,
                'eTRS': np.nan,
                'SNAD': np.nan,
                'Fixed': np.nan,
                'Credit': np.nan,
                'Regulatory': np.nan,
                'Buyer Protection': np.nan,
                'Net FVF': np.nan,
                'IF': if_dollar,
                'FF': np.nan,
                'Net XOT Rev (excl. PL)': np.nan,
                'Store': store_dollar
            }

        # Take rate row - calculate from actual data if A/F = 'A', otherwise use forecast TR
        if af_status == 'A' and actual_row is not None and pd.notna(actual_gmv) and actual_gmv > 0:
            pct_row = {
                'Date': date_val,
                'Week': week_num,
                'Month': month_num,
                'A/F': af_status,
                'GMV': actual_gmv,
                'Variable': actual_variable / actual_gmv if pd.notna(actual_variable) else np.nan,
                'International': actual_international / actual_gmv if pd.notna(actual_international) else np.nan,
                'BSTD': actual_bstd / actual_gmv if pd.notna(actual_bstd) else np.nan,
                'eTRS': actual_etrs / actual_gmv if pd.notna(actual_etrs) else np.nan,
                'SNAD': actual_snad / actual_gmv if pd.notna(actual_snad) else np.nan,
                'Fixed': actual_fixed / actual_gmv if pd.notna(actual_fixed) else np.nan,
                'Credit': actual_credit / actual_gmv if pd.notna(actual_credit) else np.nan,
                'Regulatory': actual_regulatory / actual_gmv if pd.notna(actual_regulatory) else np.nan,
                'Buyer Protection': actual_buyer_protection / actual_gmv if pd.notna(actual_buyer_protection) else np.nan,
                'Net FVF': actual_net_fvf / actual_gmv if pd.notna(actual_net_fvf) else np.nan,
                'IF': actual_if / actual_gmv if pd.notna(actual_if) else np.nan,
                'FF': actual_ff / actual_gmv if pd.notna(actual_ff) else np.nan,
                'Net XOT Rev (excl. PL)': actual_net_xot / actual_gmv if pd.notna(actual_net_xot) else np.nan,
                'Store': actual_store / actual_gmv if pd.notna(actual_store) else np.nan
            }
        else:
            pct_row = {
                'Date': date_val,
                'Week': week_num,
                'Month': month_num,
                'A/F': af_status,
                'GMV': gmv,
                'Variable': fvf_trs.get('Variable', np.nan),
                'International': fvf_trs.get('International', np.nan),
                'BSTD': fvf_trs.get('BSTD', np.nan),
                'eTRS': fvf_trs.get('eTRS', np.nan),
                'SNAD': fvf_trs.get('SNAD', np.nan),
                'Fixed': fvf_trs.get('Fixed', np.nan),
                'Credit': fvf_trs.get('Credit', np.nan),
                'Regulatory': fvf_trs.get('Regulatory', np.nan),
                'Buyer Protection': fvf_trs.get('Buyer Protection', np.nan),
                'Net FVF': net_fvf_tr,
                'IF': np.nan,
                'FF': np.nan,
                'Store': np.nan,
                'Net XOT Rev (excl. PL)': np.nan
            }

        # Append rows regardless of whether week match exists
        daily_dollar_data.append(dollar_row)
        daily_pct_data.append(pct_row)

    dollar_df = pd.DataFrame(daily_dollar_data)
    pct_df = pd.DataFrame(daily_pct_data)

    # Reset index to ensure clean DataFrames
    dollar_df = dollar_df.reset_index(drop=True)
    pct_df = pct_df.reset_index(drop=True)

    # Ensure Date column is datetime type (not object)
    dollar_df['Date'] = pd.to_datetime(dollar_df['Date'])
    pct_df['Date'] = pd.to_datetime(pct_df['Date'])

    # Fill week 53 with week 52 data for Take Rate % columns (only for forecast rows)
    week_53_mask = pct_df['Week'] == 53
    week_52_mask = pct_df['Week'] == 52

    if week_53_mask.any() and week_52_mask.any():
        # Get average of week 52 data for FVF fee types
        fee_types_to_fill = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF']
        week_52_avg = {}
        for fee_type in fee_types_to_fill:
            week_52_values = pct_df.loc[week_52_mask, fee_type]
            avg_value = week_52_values.mean() if not week_52_values.empty else np.nan
            week_52_avg[fee_type] = avg_value

        # Fill week 53 with week 52 averages ONLY for forecast rows (A/F = 'F')
        # For actual rows (A/F = 'A'), keep the actual data
        for idx in pct_df.index[week_53_mask]:
            af_status = pct_df.loc[idx, 'A/F']
            if af_status == 'F':  # Only fill forecast rows
                for fee_type in fee_types_to_fill:
                    pct_df.loc[idx, fee_type] = week_52_avg[fee_type]

    # Note: Actual data (A/F = 'A') already contains daily sums from the aggregated ALL REV Data
    # Note: FF TR and other calculated values will be computed after GMV input (in the refresh button)
    return dollar_df, pct_df


def parse_gmv_paste_input(paste_text):
    """
    Parse pasted GMV data (tab-separated or comma-separated)
    Expected format: Week<tab/comma>GMV or just GMV values (one per line)

    Args:
        paste_text: String with pasted data

    Returns:
        DataFrame with columns: Week, GMV
    """
    if not paste_text or paste_text.strip() == "":
        return pd.DataFrame(columns=['Week', 'GMV'])

    lines = paste_text.strip().split('\n')
    data = []

    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        # Try tab-separated first, then comma-separated
        if '\t' in line:
            parts = line.split('\t')
        elif ',' in line:
            parts = line.split(',')
        else:
            # Single value, assume it's GMV and use line number as week
            parts = [str(i), line]

        if len(parts) >= 2:
            try:
                week = int(parts[0].strip())
                gmv = float(parts[1].strip().replace(',', ''))
                data.append({'Week': week, 'GMV': gmv})
            except (ValueError, IndexError):
                continue
        elif len(parts) == 1:
            # Single value, use line number as week
            try:
                gmv = float(parts[0].strip().replace(',', ''))
                data.append({'Week': i, 'GMV': gmv})
            except ValueError:
                continue

    return pd.DataFrame(data)


def build_fvf_monthly_table(daily_df, tab3_monthly_data=None):
    """
    Build FVF monthly forecast table from daily data and Tab3 forecasts

    Args:
        daily_df: Daily forecast DataFrame (raw numeric data with GMV and 9 fee types)
        tab3_monthly_data: Optional dictionary with Tab3 monthly forecasts
                          Format: {'IF': monthly_df, 'FF': monthly_df, 'Store': monthly_df}
                          Each monthly_df should have MONTH_OF_YEAR_ID as index and 2026 forecast values

    Returns:
        DataFrame with columns: Month, GMV, 9 fee types ($), IF, FF, Store, 9 fee types (%)
    """
    import datetime

    # Add Month column to daily data
    daily_with_month = daily_df.copy()
    daily_with_month['Month'] = daily_with_month['Date'].apply(lambda x: x.month if pd.notna(x) else np.nan)

    # Initialize result list
    monthly_data = []

    fee_types = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']

    for month in range(1, 13):
        month_rows = daily_with_month[daily_with_month['Month'] == month]

        # Calculate GMV (sum of daily GMV)
        gmv_sum = month_rows['GMV'].sum()
        gmv_sum = gmv_sum if pd.notna(gmv_sum) and gmv_sum > 0 else np.nan

        monthly_row = {
            'Month': month,
            'GMV': gmv_sum
        }

        # Calculate Dollar Amount for each fee type
        # Dollar Amount = sum of daily dollar amounts (daily_df already has dollar values, not TRs)
        for fee_type in fee_types:
            dollar_sum = month_rows[fee_type].sum()
            # Check if we have any valid values
            has_value = month_rows[fee_type].notna().any()
            monthly_row[fee_type] = dollar_sum if has_value and pd.notna(dollar_sum) else np.nan

        # Calculate Net FVF (sum of all 9 fee type dollar amounts)
        net_fvf_dollar = 0
        has_net_fvf = False
        for fee_type in fee_types:
            if pd.notna(monthly_row.get(fee_type)):
                net_fvf_dollar += monthly_row[fee_type]
                has_net_fvf = True
        monthly_row['Net FVF'] = net_fvf_dollar if has_net_fvf else np.nan

        # Add IF, FF, Store from Tab3 if provided
        if tab3_monthly_data is not None:
            for fee_name in ['IF', 'FF', 'Store']:
                if fee_name in tab3_monthly_data:
                    tab3_df = tab3_monthly_data[fee_name]

                    # Safety check: ensure MONTH_OF_YEAR_ID is index, not column
                    if 'MONTH_OF_YEAR_ID' in tab3_df.columns:
                        tab3_df = tab3_df.set_index('MONTH_OF_YEAR_ID')

                    # Look for month value in the dataframe
                    # Check if index contains the month
                    if month in tab3_df.index:
                        # Get the 2026 forecast value (could be in different columns)
                        # Try '2026 Adjusted', '2026 Index Baseline', '2026' in order
                        value = np.nan
                        for col in ['2026 Adjusted', '2026 Index Baseline', '2026']:
                            if col in tab3_df.columns:
                                val = tab3_df.loc[month, col]
                                if pd.notna(val):
                                    value = val
                                    break
                        monthly_row[fee_name] = value
                    else:
                        monthly_row[fee_name] = np.nan
                else:
                    monthly_row[fee_name] = np.nan
        else:
            monthly_row['IF'] = np.nan
            monthly_row['FF'] = np.nan
            monthly_row['Store'] = np.nan

        # Calculate Net XOT Rev (excl. PL) = Net FVF + IF + FF
        net_xot_dollar = 0
        has_net_xot = False
        if pd.notna(monthly_row.get('Net FVF')):
            net_xot_dollar += monthly_row['Net FVF']
            has_net_xot = True
        if pd.notna(monthly_row.get('IF')):
            net_xot_dollar += monthly_row['IF']
            has_net_xot = True
        if pd.notna(monthly_row.get('FF')):
            net_xot_dollar += monthly_row['FF']
            has_net_xot = True
        monthly_row['Net XOT Rev (excl. PL)'] = net_xot_dollar if has_net_xot else np.nan

        # Note: Percentage values will be calculated in the percentage table

        monthly_data.append(monthly_row)

    # Build DataFrame with proper column order
    columns = ['Month', 'GMV']
    for fee_type in fee_types:
        columns.append(fee_type)
    columns.extend(['Net FVF', 'IF', 'FF', 'Net XOT Rev (excl. PL)', 'Store'])

    monthly_df = pd.DataFrame(monthly_data)
    monthly_df = monthly_df[columns]

    # Create percentage DataFrame by dividing dollar amounts by GMV
    pct_df = monthly_df.copy()
    for col in columns:
        if col not in ['Month', 'GMV']:
            pct_df[col] = pct_df.apply(
                lambda row: row[col] / row['GMV'] if pd.notna(row[col]) and pd.notna(row['GMV']) and row['GMV'] > 0 else np.nan,
                axis=1
            )

    return monthly_df, pct_df


def build_if_monthly_daily_phasing_tables(if_ff_store_data):
    """
    Build 12 monthly daily phasing tables for IF

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store historical data

    Returns:
        Dictionary with month numbers (1-12) as keys and phasing DataFrames as values
        Each DataFrame has:
        - Rows: Day of month ID (1-31)
        - Columns: Baseline (average of 3 years), 2023, 2024, 2025
        - Values: % of column total for IF_N_USD_PLAN
    """
    from modules.phasing_engine import calculate_phasing_table

    # Calculate phasing table for IF
    phasing_table = calculate_phasing_table(if_ff_store_data, metric_column='IF_N_USD_PLAN')

    # Dictionary to store monthly tables
    monthly_tables = {}

    # For each month (1-12), create a table with past 3 matured years
    for month in range(1, 13):
        # Filter columns for this month from 2023, 2024, 2025
        month_str = str(month).zfill(2)
        year_month_cols = [f'2023-{month_str}', f'2024-{month_str}', f'2025-{month_str}']

        # Filter to available columns
        available_cols = [col for col in year_month_cols if col in phasing_table.columns]

        if available_cols:
            month_table = phasing_table[available_cols].copy()

            # Rename columns to just year names for cleaner display
            rename_map = {col: col.split('-')[0] for col in available_cols}
            month_table = month_table.rename(columns=rename_map)

            # Calculate Baseline as the average of the 3 years
            year_cols = [rename_map[col] for col in available_cols]
            month_table.insert(0, 'Baseline', month_table[year_cols].mean(axis=1))
        else:
            # No data available, create empty table
            month_table = pd.DataFrame(index=range(1, 32))
            month_table['Baseline'] = np.nan

        monthly_tables[month] = month_table

    return monthly_tables


def build_if_daily_breakdown_table(if_ff_store_data, tab3_monthly_data=None):
    """
    Build IF daily breakdown table from monthly forecasts and daily phasing

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store historical data
        tab3_monthly_data: Optional dictionary with Tab3 monthly forecasts
                          Format: {'IF': monthly_df, 'FF': monthly_df, 'Store': monthly_df}

    Returns:
        DataFrame with columns: Date, Month, IF Daily Phasing, IF Monthly Forecast, IF Daily Forecast
    """
    import datetime

    # Get phasing tables with baseline values (cumulative %)
    monthly_phasing_tables = build_if_monthly_daily_phasing_tables(if_ff_store_data)

    # Convert cumulative % to incremental daily % for each month
    monthly_daily_pct = {}
    for month, phasing_table in monthly_phasing_tables.items():
        if 'Baseline' in phasing_table.columns:
            baseline_cumulative = phasing_table['Baseline'].copy()

            # Calculate incremental daily % (difference between consecutive days)
            baseline_incremental = baseline_cumulative.copy()
            baseline_incremental.iloc[0] = baseline_cumulative.iloc[0]  # Day 1 = cumulative value
            for i in range(1, len(baseline_incremental)):
                if pd.notna(baseline_cumulative.iloc[i]) and pd.notna(baseline_cumulative.iloc[i-1]):
                    baseline_incremental.iloc[i] = baseline_cumulative.iloc[i] - baseline_cumulative.iloc[i-1]
                else:
                    baseline_incremental.iloc[i] = np.nan

            monthly_daily_pct[month] = baseline_incremental
        else:
            monthly_daily_pct[month] = pd.Series([np.nan] * 31)

    # Build date range for 2026
    start_date = datetime.date(2026, 1, 1)
    end_date = datetime.date(2026, 12, 31)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    # Initialize result list
    daily_data = []

    for date in date_range:
        month = date.month
        day = date.day

        # Get daily phasing % (incremental) for this month and day
        daily_pct_series = monthly_daily_pct.get(month)
        if daily_pct_series is not None and day - 1 < len(daily_pct_series):
            daily_phasing_pct = daily_pct_series.iloc[day - 1]
        else:
            daily_phasing_pct = np.nan

        # Get monthly forecast for IF from Tab3
        if_monthly_forecast = np.nan
        if tab3_monthly_data is not None and 'IF' in tab3_monthly_data:
            if_df = tab3_monthly_data['IF']

            # Safety check: ensure MONTH_OF_YEAR_ID is index, not column
            if 'MONTH_OF_YEAR_ID' in if_df.columns:
                if_df = if_df.set_index('MONTH_OF_YEAR_ID')

            # Check if month exists in the index
            if month in if_df.index:
                # Try different column names for 2026 forecast
                for col in ['2026 Adjusted', '2026 Index Baseline', '2026']:
                    if col in if_df.columns:
                        val = if_df.loc[month, col]
                        if pd.notna(val):
                            if_monthly_forecast = val
                            break

        # Calculate daily forecast = daily phasing (%) * monthly forecast ($)
        if pd.notna(daily_phasing_pct) and pd.notna(if_monthly_forecast):
            # Convert phasing from % to proportion (divide by 100)
            if_daily_forecast = (daily_phasing_pct / 100.0) * if_monthly_forecast
        else:
            if_daily_forecast = np.nan

        daily_data.append({
            'Date': date,
            'Month': month,
            'IF Daily Phasing': daily_phasing_pct,
            'IF Monthly Forecast': if_monthly_forecast,
            'IF Daily Forecast': if_daily_forecast
        })

    return pd.DataFrame(daily_data)
