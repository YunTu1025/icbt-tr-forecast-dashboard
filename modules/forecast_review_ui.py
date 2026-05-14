"""
Forecast Review UI - Render Tab4 components for forecast result review
"""
import streamlit as st
import pandas as pd
import numpy as np
from modules.forecast_review_engine import (
    build_fvf_weekly_table,
    format_fvf_weekly_table_for_display,
    build_fvf_daily_table,
    build_fvf_daily_tables,
    build_fvf_monthly_table,
    build_if_monthly_daily_phasing_tables,
    build_if_daily_breakdown_table
)


def render_fvf_weekly_table_tab2(forecast_data_dict, week_date_map):
    """
    Render the FVF Weekly Forecast Table in Tab2 (without GMV column)

    Args:
        forecast_data_dict: Dictionary with fee type forecast data from Tab2
        week_date_map: Dictionary mapping week numbers to dates

    Returns:
        None (renders Streamlit UI components)
    """
    st.markdown("### 📊 FVF Weekly Forecast Summary Table")

    # Build FVF weekly table from Tab2 data
    fvf_weekly_df = build_fvf_weekly_table(forecast_data_dict, week_date_map, gmv_data=None)

    # Prepare formatted display data - remove GMV column
    display_columns = ['Week', 'Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF']
    formatted_display = fvf_weekly_df[display_columns].copy()

    # Format percentage columns (2 decimals)
    fvf_columns = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF']
    for col in fvf_columns:
        if col in formatted_display.columns:
            formatted_display[col] = formatted_display[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    # Configure column settings (all read-only)
    column_config = {
        "Week": st.column_config.NumberColumn("Week", disabled=True),
        "Variable": st.column_config.TextColumn("Variable", disabled=True),
        "International": st.column_config.TextColumn("International", disabled=True),
        "BSTD": st.column_config.TextColumn("BSTD", disabled=True),
        "eTRS": st.column_config.TextColumn("eTRS", disabled=True),
        "SNAD": st.column_config.TextColumn("SNAD", disabled=True),
        "Fixed": st.column_config.TextColumn("Fixed", disabled=True),
        "Credit": st.column_config.TextColumn("Credit", disabled=True),
        "Regulatory": st.column_config.TextColumn("Regulatory", disabled=True),
        "Buyer Protection": st.column_config.TextColumn("Buyer Protection", disabled=True),
        "Net FVF": st.column_config.TextColumn("Net FVF", disabled=True)
    }

    # Display table with formatted values
    st.data_editor(
        formatted_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=column_config,
        key="fvf_weekly_tab2_data_editor"
    )


def render_fvf_weekly_section(forecast_data_dict, week_date_map):
    """
    Render the FVF Forecast - Weekly section in Tab4

    Args:
        forecast_data_dict: Dictionary with fee type forecast data from Tab2
        week_date_map: Dictionary mapping week numbers to dates

    Returns:
        None (renders Streamlit UI components)
    """
    st.markdown("### 📊 FVF Forecast - Weekly")

    # Initialize session state for editable table data
    if 'fvf_weekly_table_data' not in st.session_state:
        st.session_state['fvf_weekly_table_data'] = None

    # Build FVF weekly table (or get from session state)
    if st.session_state['fvf_weekly_table_data'] is None:
        # First time: build from Tab2 data
        fvf_weekly_df = build_fvf_weekly_table(forecast_data_dict, week_date_map, gmv_data=None)
        st.session_state['fvf_weekly_table_data'] = fvf_weekly_df
    else:
        # Update FVF values from Tab2
        fvf_weekly_df = build_fvf_weekly_table(
            forecast_data_dict,
            week_date_map,
            gmv_data=st.session_state['fvf_weekly_table_data']
        )

    # Aggregate GMV from daily table if available
    if 'fvf_daily_table_data' in st.session_state and st.session_state['fvf_daily_table_data'] is not None:
        daily_df = st.session_state['fvf_daily_table_data']
        # Aggregate daily GMV by week
        for week in range(1, 53):
            week_gmv_sum = daily_df[daily_df['Week'] == week]['GMV'].sum()
            fvf_weekly_df.loc[fvf_weekly_df['Week'] == week, 'GMV'] = week_gmv_sum if pd.notna(week_gmv_sum) and week_gmv_sum > 0 else np.nan

        # Update session state
        st.session_state['fvf_weekly_table_data'] = fvf_weekly_df

    # Display table
    st.markdown("---")
    st.markdown("#### FVF Weekly Forecast Table")
    st.caption("💡 GMV values are calculated from the Daily Forecast Table below.")

    # Prepare formatted display data
    formatted_display = fvf_weekly_df.copy()

    # Format GMV with thousand separators, no decimals
    formatted_display['GMV'] = formatted_display['GMV'].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Format percentage columns (2 decimals)
    fvf_columns = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF']
    for col in fvf_columns:
        if col in formatted_display.columns:
            formatted_display[col] = formatted_display[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    # Configure column settings for data_editor
    column_config = {
        "Week": st.column_config.TextColumn("Week", disabled=True),
        "GMV": st.column_config.TextColumn("GMV", disabled=True, help="Aggregated from Daily Forecast Table"),
        "Variable": st.column_config.TextColumn("Variable", disabled=True),
        "International": st.column_config.TextColumn("International", disabled=True),
        "BSTD": st.column_config.TextColumn("BSTD", disabled=True),
        "eTRS": st.column_config.TextColumn("eTRS", disabled=True),
        "SNAD": st.column_config.TextColumn("SNAD", disabled=True),
        "Fixed": st.column_config.TextColumn("Fixed", disabled=True),
        "Credit": st.column_config.TextColumn("Credit", disabled=True),
        "Regulatory": st.column_config.TextColumn("Regulatory", disabled=True),
        "Buyer Protection": st.column_config.TextColumn("Buyer Protection", disabled=True),
        "Net FVF": st.column_config.TextColumn("Net FVF", disabled=True)
    }

    # Display table with formatted values
    st.data_editor(
        formatted_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=column_config,
        key="fvf_weekly_data_editor"
    )


def render_fvf_daily_section(forecast_data_dict, week_date_map, tab3_monthly_data=None, all_rev_data=None):
    """
    Render the Daily Consolidation section in Tab4 with two tables

    Args:
        forecast_data_dict: Dictionary with fee type forecast data from Tab2
        week_date_map: Dictionary mapping week numbers to dates
        tab3_monthly_data: Optional dictionary with Tab3 monthly forecasts
        all_rev_data: Optional DataFrame with ALL REV data for current date display

    Returns:
        None (renders Streamlit UI components)
    """
    st.markdown("### 📅 Daily Consolidation")

    # Current Date Display - from maximum date in ALL REV data
    if all_rev_data is not None and 'DT' in all_rev_data.columns:
        max_date = pd.to_datetime(all_rev_data['DT']).max()
        st.markdown(f"##### Current Date: {max_date.strftime('%Y/%m/%d')}")

    # Action buttons below section title
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🗑️ Clear Cache", key="clear_daily_cache_btn_top"):
            st.session_state['fvf_daily_dollar_data'] = None
            st.session_state['fvf_daily_pct_data'] = None
            st.success("✅ Cleared cached daily data")
            st.rerun()

    with col2:
        refresh_clicked = st.button("📖 Read Input", type="primary", key="daily_read_input_btn_top")

    # Get weekly table data from session state (built from Tab2 forecast data)
    if 'fvf_weekly_table_data' not in st.session_state or st.session_state['fvf_weekly_table_data'] is None:
        st.warning("⚠️ Please generate forecasts in Tab2 first. The FVF Weekly Forecast Summary Table in Tab2 provides the data needed for this section.")
        return

    weekly_df = st.session_state['fvf_weekly_table_data']

    # Get IF daily breakdown table from session state
    if_daily_breakdown_df = None
    if 'if_daily_breakdown_data' in st.session_state:
        if_daily_breakdown_df = st.session_state['if_daily_breakdown_data']

    # Initialize session state for daily tables
    if 'fvf_daily_dollar_data' not in st.session_state:
        st.session_state['fvf_daily_dollar_data'] = None
    if 'fvf_daily_pct_data' not in st.session_state:
        st.session_state['fvf_daily_pct_data'] = None

    # Build daily tables
    if st.session_state['fvf_daily_dollar_data'] is None:
        dollar_df, pct_df = build_fvf_daily_tables(weekly_df, if_daily_breakdown_df, tab3_monthly_data, all_rev_data=all_rev_data)
        st.session_state['fvf_daily_dollar_data'] = dollar_df
        st.session_state['fvf_daily_pct_data'] = pct_df
        st.session_state['fvf_daily_table_data'] = dollar_df  # For monthly section
    else:
        # Use existing calculated data from session state
        # Do NOT rebuild, as that would erase calculated 9 fee types revenue
        dollar_df = st.session_state['fvf_daily_dollar_data'].copy()
        pct_df = st.session_state['fvf_daily_pct_data'].copy()

    # Ensure clean DataFrames - reset index and check for unwanted columns
    dollar_df = dollar_df.reset_index(drop=True)
    pct_df = pct_df.reset_index(drop=True)

    # Remove any unwanted columns that might have snuck in
    expected_cols = ['Date', 'Week', 'Month', 'A/F', 'GMV', 'Variable', 'International', 'BSTD', 'eTRS', 'SNAD',
                     'Fixed', 'Credit', 'Regulatory', 'Buyer Protection', 'Net FVF', 'IF', 'FF',
                     'Net XOT Rev (excl. PL)', 'Store']

    # Keep only expected columns
    dollar_df = dollar_df[[col for col in expected_cols if col in dollar_df.columns]]
    pct_df = pct_df[[col for col in expected_cols if col in pct_df.columns]]

    # Fee type columns
    fee_types = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']

    # === TABLE 1: Revenue Dollar Amount ===
    st.markdown("---")
    st.markdown("#### Revenue Dollar Amount")

    # Prepare formatted display data for dollar table
    dollar_display = dollar_df.copy()

    # Safety check: ensure we only have expected columns
    if 'MONTH_OF_YEAR_ID' in dollar_display.columns:
        dollar_display = dollar_display.drop(columns=['MONTH_OF_YEAR_ID'])

    # Format Date
    dollar_display['Date'] = dollar_display['Date'].apply(
        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ""
    )

    # Format GMV with thousand separators, no decimals
    dollar_display['GMV'] = dollar_display['GMV'].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Format all dollar columns
    dollar_columns = fee_types + ['Net FVF', 'IF', 'FF', 'Net XOT Rev (excl. PL)', 'Store']
    for col in dollar_columns:
        if col in dollar_display.columns:
            dollar_display[col] = dollar_display[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else ""
            )

    # Apply styling - light grey background for A/F = "A" rows
    def highlight_actual_rows(row):
        """Apply light grey background to Actual rows (A/F=A)."""
        if row.get('A/F') == 'A':
            return ['background-color: #f0f0f0'] * len(row)
        else:
            return [''] * len(row)

    styled_dollar_display = dollar_display.style.apply(highlight_actual_rows, axis=1)

    # Configure column settings for dollar table
    dollar_column_config = {
        "Date": st.column_config.TextColumn("Date", disabled=True),
        "Week": st.column_config.NumberColumn("Week", disabled=True),
        "Month": st.column_config.NumberColumn("Month", disabled=True),
        "A/F": st.column_config.TextColumn("A/F", disabled=True, help="A = Actual, F = Forecast"),
        "GMV": st.column_config.TextColumn("GMV", help="Editable for Forecast rows only. Actual rows (A/F=A) are protected."),
    }
    for col in dollar_columns:
        dollar_column_config[col] = st.column_config.TextColumn(col, disabled=True)

    # Display editable dollar table with styling
    edited_dollar_df = st.data_editor(
        styled_dollar_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=dollar_column_config,
        key="fvf_daily_dollar_editor"
    )

    # Handle Read Input button click
    if refresh_clicked:
        # Parse and store edited GMV values
        if edited_dollar_df is not None:
            # Extract and update all GMV values first
            updated_dollar_df = dollar_df.copy()
            updated_pct_df = pct_df.copy()

            for idx in range(len(edited_dollar_df)):
                # Skip GMV update for rows with A/F = 'A' (Actual data - not editable)
                af_status = updated_dollar_df.iloc[idx].get('A/F', 'F')
                if af_status == 'A':
                    continue  # Keep actual GMV as-is

                gmv_str = edited_dollar_df.iloc[idx]['GMV']
                if gmv_str and str(gmv_str).strip():
                    try:
                        # Remove commas and convert to float
                        gmv_value = float(str(gmv_str).replace(',', '').strip())
                        updated_dollar_df.iloc[idx, updated_dollar_df.columns.get_loc('GMV')] = gmv_value
                        updated_pct_df.iloc[idx, updated_pct_df.columns.get_loc('GMV')] = gmv_value
                    except ValueError:
                        # Keep original value if parsing fails
                        pass

            # STEP 2: Calculate Daily Revenue for 9 FVF fee types and Net FVF
            for idx in range(len(updated_dollar_df)):
                # Skip calculation for rows with A/F = 'A' (Actual data)
                af_status = updated_dollar_df.iloc[idx].get('A/F', 'F')
                if af_status == 'A':
                    continue  # Keep actual data as-is

                gmv_value = updated_dollar_df.iloc[idx]['GMV']

                if pd.notna(gmv_value) and gmv_value > 0:
                    # Calculate FVF fee type dollars (9 fee types) using TR% from Tab2
                    for fee_type in fee_types:
                        tr_value = updated_pct_df.iloc[idx][fee_type]
                        if pd.notna(tr_value):
                            dollar_value = gmv_value * tr_value
                            updated_dollar_df.iloc[idx, updated_dollar_df.columns.get_loc(fee_type)] = dollar_value

                    # Calculate Net FVF dollar
                    net_fvf_tr = updated_pct_df.iloc[idx]['Net FVF']
                    if pd.notna(net_fvf_tr):
                        net_fvf_dollar = gmv_value * net_fvf_tr
                        updated_dollar_df.iloc[idx, updated_dollar_df.columns.get_loc('Net FVF')] = net_fvf_dollar

                    # Calculate IF TR%
                    if_dollar = updated_dollar_df.iloc[idx]['IF']
                    if pd.notna(if_dollar):
                        if_tr = if_dollar / gmv_value
                        updated_pct_df.iloc[idx, updated_pct_df.columns.get_loc('IF')] = if_tr

                    # Calculate Store TR%
                    store_dollar = updated_dollar_df.iloc[idx]['Store']
                    if pd.notna(store_dollar):
                        store_tr = store_dollar / gmv_value
                        updated_pct_df.iloc[idx, updated_pct_df.columns.get_loc('Store')] = store_tr

            # STEP 3: Calculate Monthly Section (aggregating from daily with revenue calculated)
            from modules.forecast_review_engine import build_fvf_monthly_table

            # Build monthly tables (this aggregates daily GMV and revenue to monthly)
            # This gives us monthly revenue for all 9 fee types
            # Calculates monthly TR% including FF TR%
            monthly_dollar_df, monthly_pct_df = build_fvf_monthly_table(updated_dollar_df, tab3_monthly_data)

            # Store monthly tables in session state for display
            st.session_state['fvf_monthly_dollar_data'] = monthly_dollar_df
            st.session_state['fvf_monthly_pct_data'] = monthly_pct_df

            # STEP 4: Update Daily FF TR% from Monthly TR% table
            for idx in range(len(updated_dollar_df)):
                # Skip calculation for rows with A/F = 'A' (Actual data)
                af_status = updated_dollar_df.iloc[idx].get('A/F', 'F')
                if af_status == 'A':
                    continue  # Keep actual data as-is

                gmv_value = updated_dollar_df.iloc[idx]['GMV']
                month_num = updated_dollar_df.iloc[idx]['Month']

                if pd.notna(gmv_value) and gmv_value > 0:
                    # Each day gets the FF TR% from its month
                    monthly_row = monthly_pct_df[monthly_pct_df['Month'] == month_num]
                    if not monthly_row.empty:
                        ff_tr = monthly_row.iloc[0]['FF']
                        updated_pct_df.iloc[idx, updated_pct_df.columns.get_loc('FF')] = ff_tr

                        # Recalculate daily FF revenue with updated FF TR% in REV table
                        ff_dollar = gmv_value * ff_tr
                        updated_dollar_df.iloc[idx, updated_dollar_df.columns.get_loc('FF')] = ff_dollar

                    # Calculate Net XOT Rev dollar and TR%
                    net_fvf_dollar = updated_dollar_df.iloc[idx]['Net FVF']
                    if_dollar = updated_dollar_df.iloc[idx]['IF']
                    ff_dollar = updated_dollar_df.iloc[idx]['FF']
                    if all(pd.notna(x) for x in [net_fvf_dollar, if_dollar, ff_dollar]):
                        net_xot_dollar = net_fvf_dollar + if_dollar + ff_dollar
                        updated_dollar_df.iloc[idx, updated_dollar_df.columns.get_loc('Net XOT Rev (excl. PL)')] = net_xot_dollar
                        # Calculate Net XOT Rev take rate
                        net_xot_tr = net_xot_dollar / gmv_value
                        updated_pct_df.iloc[idx, updated_pct_df.columns.get_loc('Net XOT Rev (excl. PL)')] = net_xot_tr

            # STEP 5: Saving updated data to session state
            st.session_state['fvf_daily_dollar_data'] = updated_dollar_df
            st.session_state['fvf_daily_pct_data'] = updated_pct_df
            st.session_state['fvf_daily_table_data'] = updated_dollar_df  # For monthly section

            st.success("✅ Calculations complete - Daily and Monthly tables updated")
            st.rerun()

    # === TABLE 2: Take Rate % ===
    st.markdown("---")
    st.markdown("#### Take Rate %")

    # Prepare formatted display data for percentage table
    pct_display = pct_df.copy()

    # Format Date
    pct_display['Date'] = pct_display['Date'].apply(
        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ""
    )

    # Format GMV with thousand separators, no decimals
    pct_display['GMV'] = pct_display['GMV'].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Format all percentage columns (2 decimals)
    pct_columns = fee_types + ['Net FVF', 'IF', 'FF', 'Net XOT Rev (excl. PL)', 'Store']
    for col in pct_columns:
        if col in pct_display.columns:
            pct_display[col] = pct_display[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    # Apply styling - light grey background for A/F = "A" rows
    styled_pct_display = pct_display.style.apply(highlight_actual_rows, axis=1)

    # Configure column settings for percentage table (all read-only)
    pct_column_config = {
        "Date": st.column_config.TextColumn("Date", disabled=True),
        "Week": st.column_config.NumberColumn("Week", disabled=True),
        "Month": st.column_config.NumberColumn("Month", disabled=True),
        "A/F": st.column_config.TextColumn("A/F", disabled=True, help="A = Actual, F = Forecast"),
        "GMV": st.column_config.TextColumn("GMV", disabled=True),
    }
    for col in pct_columns:
        pct_column_config[col] = st.column_config.TextColumn(col, disabled=True)

    # Display percentage table with styling
    st.data_editor(
        styled_pct_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=pct_column_config,
        key="fvf_daily_pct_editor"
    )


def render_fvf_monthly_section(tab3_monthly_data=None):
    """
    Render the Monthly Consolidation section in Tab4

    Args:
        tab3_monthly_data: Optional dictionary with Tab3 monthly forecasts
                          Format: {'IF': monthly_df, 'FF': monthly_df, 'Store': monthly_df}

    Returns:
        None (renders Streamlit UI components)
    """
    st.markdown("### 📅 Monthly Consolidation")

    # Get monthly table data from session state (calculated after daily GMV input)
    # If not available yet, build from daily data
    if 'fvf_monthly_dollar_data' in st.session_state and st.session_state['fvf_monthly_dollar_data'] is not None:
        # Use cached monthly data (already calculated in daily section refresh)
        dollar_df = st.session_state['fvf_monthly_dollar_data']
        pct_df = st.session_state['fvf_monthly_pct_data']
    else:
        # Initial build from daily data (before any GMV input)
        if 'fvf_daily_table_data' not in st.session_state or st.session_state['fvf_daily_table_data'] is None:
            st.warning("⚠️ Please generate daily forecast data first.")
            return

        daily_df = st.session_state['fvf_daily_table_data']
        # Build monthly tables from daily data (returns two DataFrames: dollar and percentage)
        dollar_df, pct_df = build_fvf_monthly_table(daily_df, tab3_monthly_data)
        # Cache for future use
        st.session_state['fvf_monthly_dollar_data'] = dollar_df
        st.session_state['fvf_monthly_pct_data'] = pct_df

    # === TABLE 1: Revenue Dollar Amount ===
    st.markdown("---")
    st.markdown("#### Revenue Dollar Amount")

    # Prepare formatted display data for dollar table
    dollar_display = dollar_df.copy()

    # Format Month as month name
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    dollar_display['Month'] = dollar_display['Month'].apply(
        lambda x: month_names[int(x) - 1] if pd.notna(x) and 1 <= x <= 12 else ""
    )

    # Format all dollar columns (thousand separators, no decimals)
    fee_types = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']
    dollar_columns = ['GMV'] + fee_types + ['Net FVF', 'IF', 'FF', 'Net XOT Rev (excl. PL)', 'Store']

    for col in dollar_columns:
        if col in dollar_display.columns:
            dollar_display[col] = dollar_display[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else ""
            )

    # Configure column settings for dollar table (all read-only)
    dollar_column_config = {
        "Month": st.column_config.TextColumn("Month", disabled=True),
    }
    for col in dollar_columns:
        dollar_column_config[col] = st.column_config.TextColumn(col, disabled=True)

    # Display dollar table
    st.data_editor(
        dollar_display,
        use_container_width=True,
        height=470,
        hide_index=True,
        column_config=dollar_column_config,
        key="fvf_monthly_dollar_editor"
    )

    # === TABLE 2: Take Rate % ===
    st.markdown("---")
    st.markdown("#### Take Rate %")

    # Prepare formatted display data for percentage table
    pct_display = pct_df.copy()

    # Format Month as month name
    pct_display['Month'] = pct_display['Month'].apply(
        lambda x: month_names[int(x) - 1] if pd.notna(x) and 1 <= x <= 12 else ""
    )

    # Format GMV with thousand separators, no decimals
    pct_display['GMV'] = pct_display['GMV'].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Format all percentage columns (2 decimals)
    pct_columns = fee_types + ['Net FVF', 'IF', 'FF', 'Net XOT Rev (excl. PL)', 'Store']

    for col in pct_columns:
        if col in pct_display.columns:
            pct_display[col] = pct_display[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    # Configure column settings for percentage table (all read-only)
    pct_column_config = {
        "Month": st.column_config.TextColumn("Month", disabled=True),
        "GMV": st.column_config.TextColumn("GMV", disabled=True),
    }
    for col in pct_columns:
        pct_column_config[col] = st.column_config.TextColumn(col, disabled=True)

    # Display percentage table
    st.data_editor(
        pct_display,
        use_container_width=True,
        height=470,
        hide_index=True,
        column_config=pct_column_config,
        key="fvf_monthly_pct_editor"
    )


def render_if_monthly_daily_phasing_section(if_ff_store_data):
    """
    Render the IF Monthly to Daily Phasing section in Tab3

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store historical data

    Returns:
        None (renders Streamlit UI components)
    """
    st.markdown("### 📊 IF Forecast Monthly to Daily Phasing Reference")

    if if_ff_store_data is None or if_ff_store_data.empty:
        st.warning("⚠️ No IF/FF/Store data available.")
        return

    # Build phasing tables for all 12 months
    monthly_tables = build_if_monthly_daily_phasing_tables(if_ff_store_data)

    # Month names for display
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']

    # Display 12 months in 4 rows (3 months per row)
    for quarter in range(4):
        # Create 3 columns for the 3 months in this quarter
        cols = st.columns(3)

        # Display 3 months in this row
        for i in range(3):
            month = quarter * 3 + i + 1  # Calculate month number (1-12)

            with cols[i]:
                st.markdown(f"#### {month_names[month - 1]}")

                # Get phasing table for this month
                phasing_table = monthly_tables[month]

                # Format for display
                phasing_display = phasing_table.copy()

                # Format all columns as percentages (2 decimal places)
                for col in phasing_display.columns:
                    phasing_display[col] = phasing_display[col].apply(
                        lambda x: f"{x:.2f}%" if pd.notna(x) else ""
                    )

                # Reset index to show Day of Month ID
                phasing_display.index.name = 'Day of Month'
                phasing_display = phasing_display.reset_index()

                # Configure column settings (all read-only)
                column_config = {
                    "Day of Month": st.column_config.NumberColumn("Day of Month", disabled=True),
                    "Baseline": st.column_config.TextColumn("Baseline", disabled=True)
                }
                for col in phasing_table.columns:
                    if col != 'Baseline':
                        column_config[col] = st.column_config.TextColumn(col, disabled=True)

                # Display table
                st.dataframe(
                    phasing_display,
                    use_container_width=True,
                    height=400,
                    hide_index=True,
                    column_config=column_config
                )


def render_if_daily_breakdown_table(if_ff_store_data, tab3_monthly_data=None):
    """
    Render the IF Forecast Monthly to Daily Breakdown Table in Tab4

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store historical data
        tab3_monthly_data: Optional dictionary with Tab3 monthly forecasts

    Returns:
        None (renders Streamlit UI components)
    """
    st.markdown("---")
    st.markdown("### 📊 IF Forecast Monthly to Daily Breakdown Table")

    if if_ff_store_data is None or if_ff_store_data.empty:
        st.warning("⚠️ No IF/FF/Store data available.")
        return

    # Build daily breakdown table
    daily_breakdown_df = build_if_daily_breakdown_table(if_ff_store_data, tab3_monthly_data)

    # Save to session state for use in FVF daily section
    st.session_state['if_daily_breakdown_data'] = daily_breakdown_df

    # Format for display
    display_df = daily_breakdown_df.copy()

    # Format Date
    display_df['Date'] = display_df['Date'].apply(
        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else ""
    )

    # Format IF Daily Phasing as percentage (2 decimals)
    display_df['IF Daily Phasing'] = display_df['IF Daily Phasing'].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else ""
    )

    # Format IF Monthly Forecast with thousand separators, no decimals
    display_df['IF Monthly Forecast'] = display_df['IF Monthly Forecast'].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Format IF Daily Forecast with thousand separators, no decimals
    display_df['IF Daily Forecast'] = display_df['IF Daily Forecast'].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Configure column settings (all read-only)
    column_config = {
        "Date": st.column_config.TextColumn("Date", disabled=True),
        "Month": st.column_config.NumberColumn("Month", disabled=True),
        "IF Daily Phasing": st.column_config.TextColumn("IF Daily Phasing", disabled=True),
        "IF Monthly Forecast": st.column_config.TextColumn("IF Monthly Forecast", disabled=True),
        "IF Daily Forecast": st.column_config.TextColumn("IF Daily Forecast", disabled=True)
    }

    # Display table
    st.data_editor(
        display_df,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=column_config,
        key="if_daily_breakdown_editor"
    )
