"""
IF/FF/Store Forecast UI - Tab 3 components
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import SeriesLabel
from modules.phasing_engine import (
    get_phasing_table_for_display,
    get_trailing_12_months,
    calculate_phasing_table
)
from modules.if_ff_store_forecast_engine import (
    build_monthly_data_table,
    calculate_monthly_baseline_row,
    format_monthly_data_for_display,
    create_monthly_data_chart,
    REGION_FILTERS
)


def prepare_tab3_data_for_session(if_ff_store_data):
    """
    Prepare and cache Tab3 data in session state before tab rendering.
    This ensures IF daily breakdown data is available to Tab4 even if Tab3 hasn't been viewed yet.

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store data

    Returns:
        None (stores data in session state)
    """
    if if_ff_store_data is None or if_ff_store_data.empty:
        return

    # Only build if not already cached or if data has changed
    if 'tab3_data_prepared' not in st.session_state or not st.session_state['tab3_data_prepared']:
        # Import necessary function
        from modules.forecast_review_engine import build_if_daily_breakdown_table

        # Build and cache IF daily breakdown table
        # Note: tab3_monthly_data will be None here, but will be updated when Tab3 renders
        daily_breakdown_df = build_if_daily_breakdown_table(if_ff_store_data, tab3_monthly_data=None)
        st.session_state['if_daily_breakdown_data'] = daily_breakdown_df
        st.session_state['tab3_data_prepared'] = True


def render_control_panel_and_phasing_tables(if_ff_store_data):
    """
    Render control panel and phasing tables for Tab 3 - IF/FF/Store Forecast

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store data

    Returns:
        Dictionary with control panel settings
    """
    st.markdown("### ⚙️ Control Panel")

    # Current Date Display - from maximum date in the data
    max_date = pd.to_datetime(if_ff_store_data['DT']).max()
    st.markdown(f"##### Current Date: {max_date.strftime('%Y/%m/%d')}")

    st.markdown("##### Daily Phasing - Baseline Month Selection")

    # Get available months for selection (exclude unmatured month - matured only)
    trailing_months = get_trailing_12_months(if_ff_store_data, exclude_current=True)

    # Convert to readable format for display
    month_options = []
    month_map = {}
    for ym in trailing_months:
        year, month = ym.split('-')
        month_name = datetime.strptime(month, '%m').strftime('%B')
        display_name = f"{month_name} {year}"
        month_options.append(display_name)
        month_map[display_name] = ym

    # Default to most recent 4 matured months
    default_months = month_options[:4] if len(month_options) >= 4 else month_options

    # === IF Section ===
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("<div style='margin-top: 8px;'><strong>IF:</strong></div>", unsafe_allow_html=True)
    with col2:
        if_phasing_months = st.multiselect(
            "Select baseline months for IF",
            options=month_options,
            default=default_months,
            key="if_phasing_month_selector",
            label_visibility="collapsed"
        )

    if_phasing_table = get_phasing_table_for_display(
        if_ff_store_data,
        metric_column='IF_N_USD_PLAN',
        num_months=12,
        selected_months=[month_map.get(m) for m in if_phasing_months]
    )
    st.dataframe(if_phasing_table, use_container_width=True, height=400)

    # === FF Section ===
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("<div style='margin-top: 8px;'><strong>FF:</strong></div>", unsafe_allow_html=True)
    with col2:
        ff_phasing_months = st.multiselect(
            "Select baseline months for FF",
            options=month_options,
            default=default_months,
            key="ff_phasing_month_selector",
            label_visibility="collapsed"
        )

    # Calculate FF non-PL (FF - TTL_PL_FEE)
    if_ff_store_data_ff = if_ff_store_data.copy()
    if_ff_store_data_ff['FF_NON_PL'] = (
        if_ff_store_data_ff['FF_N_USD_PLAN'] - if_ff_store_data_ff['TTL_PL_FEE_N_USD_PLAN']
    )

    ff_phasing_table = get_phasing_table_for_display(
        if_ff_store_data_ff,
        metric_column='FF_NON_PL',
        num_months=12,
        selected_months=[month_map.get(m) for m in ff_phasing_months]
    )
    st.dataframe(ff_phasing_table, use_container_width=True, height=400)

    # === Store Section ===
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("<div style='margin-top: 8px;'><strong>Store:</strong></div>", unsafe_allow_html=True)
    with col2:
        store_phasing_months = st.multiselect(
            "Select baseline months for Store",
            options=month_options,
            default=default_months,
            key="store_phasing_month_selector",
            label_visibility="collapsed"
        )

    store_phasing_table = get_phasing_table_for_display(
        if_ff_store_data,
        metric_column='STORE_FEE_N_USD_PLAN',
        num_months=12,
        selected_months=[month_map.get(m) for m in store_phasing_months]
    )
    st.dataframe(store_phasing_table, use_container_width=True, height=400)

    # ===== PREVIOUS FORECAST VERSION SECTION =====
    st.markdown("---")
    st.markdown("### 📂 Previous Forecast Version")

    # Upload areas in a single row with 4 columns
    upload_col1, upload_col2, upload_col3, upload_col4 = st.columns([0.5, 1.5, 0.7, 1.5])

    with upload_col1:
        st.markdown("<div style='margin-top: 16px;'>Budget</div>", unsafe_allow_html=True)

    with upload_col2:
        budget_file = st.file_uploader(
            "Upload Budget CSV",
            type=['csv'],
            accept_multiple_files=False,
            key="tab3_budget_csv_upload",
            label_visibility="collapsed"
        )

    with upload_col3:
        st.markdown("<div style='margin-top: 16px;'>Prior Forecast</div>", unsafe_allow_html=True)

    with upload_col4:
        prior_forecast_file = st.file_uploader(
            "Upload Prior Forecast CSV",
            type=['csv'],
            accept_multiple_files=False,
            key="tab3_prior_forecast_csv_upload",
            label_visibility="collapsed"
        )

    # Success messages in second row
    success_col1, success_col2 = st.columns(2)

    with success_col1:
        if budget_file is not None:
            st.success(f"✅ {budget_file.name} uploaded")

    with success_col2:
        if prior_forecast_file is not None:
            st.success(f"✅ {prior_forecast_file.name} uploaded")

    # Read uploaded CSV files
    budget_df = None
    prior_forecast_df = None

    # Display uploaded file contents in tables
    table_col1, table_col2 = st.columns(2)

    with table_col1:
        if budget_file is not None:
            try:
                budget_df = pd.read_csv(budget_file)
                # Format all columns except Month/MONTH_OF_YEAR_ID as number
                budget_df_display = budget_df.copy()
                budget_df_display = budget_df_display.reset_index(drop=True)
                for col in budget_df_display.columns:
                    if col not in ['Month', 'MONTH_OF_YEAR_ID']:
                        budget_df_display[col] = budget_df_display[col].apply(
                            lambda x: f"{x:,.0f}" if pd.notna(x) and isinstance(x, (int, float)) else x
                        )
                st.markdown("##### Budget Data Preview")
                st.dataframe(budget_df_display, use_container_width=True, height=480, hide_index=True)
                st.caption(f"Total Records: {len(budget_df):,}")
            except Exception as e:
                st.error(f"Error reading Budget CSV: {str(e)}")
                budget_df = None

    with table_col2:
        if prior_forecast_file is not None:
            try:
                prior_forecast_df = pd.read_csv(prior_forecast_file)
                # Format all columns except Month/MONTH_OF_YEAR_ID as number
                prior_forecast_df_display = prior_forecast_df.copy()
                prior_forecast_df_display = prior_forecast_df_display.reset_index(drop=True)
                for col in prior_forecast_df_display.columns:
                    if col not in ['Month', 'MONTH_OF_YEAR_ID']:
                        prior_forecast_df_display[col] = prior_forecast_df_display[col].apply(
                            lambda x: f"{x:,.0f}" if pd.notna(x) and isinstance(x, (int, float)) else x
                        )
                st.markdown("##### Prior Forecast Data Preview")
                st.dataframe(prior_forecast_df_display, use_container_width=True, height=480, hide_index=True)
                st.caption(f"Total Records: {len(prior_forecast_df):,}")
            except Exception as e:
                st.error(f"Error reading Prior Forecast CSV: {str(e)}")
                prior_forecast_df = None

    # Return settings
    settings = {
        'current_date': max_date,
        'if_phasing_months': [month_map.get(m) for m in if_phasing_months],
        'ff_phasing_months': [month_map.get(m) for m in ff_phasing_months],
        'store_phasing_months': [month_map.get(m) for m in store_phasing_months],
        'if_phasing_months_display': if_phasing_months,
        'ff_phasing_months_display': ff_phasing_months,
        'store_phasing_months_display': store_phasing_months,
        'budget_df': budget_df,
        'prior_forecast_df': prior_forecast_df
    }

    return settings


def render_fee_forecast_section(
    fee_type,
    if_ff_store_data,
    control_panel_settings,
    metric_column,
    fee_display_name,
    region='ICBT',
    icbt_index_months=None,
    budget_df=None,
    prior_forecast_df=None
):
    """
    Render a fee forecast section for a specific region

    Args:
        fee_type: Fee type identifier ('IF', 'FF', 'Store')
        if_ff_store_data: DataFrame with IF/FF/Store data
        control_panel_settings: Settings from control panel
        metric_column: Column name for the metric (e.g., 'IF_N_USD_PLAN')
        fee_display_name: Display name for the fee type (e.g., 'IF (Insertion Fee)')
        region: Region to forecast ('ICBT', 'GC', 'HIS', 'JPKO')
        icbt_index_months: List of index months from ICBT (for non-ICBT regions)
        budget_df: Optional Budget DataFrame from uploaded CSV
        prior_forecast_df: Optional Prior Forecast DataFrame from uploaded CSV

    Returns:
        List of index months selected (for ICBT) or None (for other regions)
    """
    st.markdown(f"#### {fee_display_name} Forecast")

    # Create month options for 2026
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_options = [f"{name} 2026" for name in month_names]
    month_values = list(range(1, 13))  # 1-12

    # Calculate default months based on current month in CSV data (including unmatured)
    # Get the current month from IF/FF/Store data (including unmatured)
    trailing_months_with_current = get_trailing_12_months(if_ff_store_data, exclude_current=False)
    if trailing_months_with_current:
        latest_month_ym = trailing_months_with_current[0]  # Most recent month including unmatured in format 'YYYY-MM'
        latest_month = int(latest_month_ym.split('-')[1])  # Extract month number
    else:
        latest_month = 5  # Fallback to May if no data

    current_month = latest_month
    default_start_month_index = max(0, current_month - 2)  # current month - 1, 0-indexed
    default_end_month_index = max(0, current_month - 1)  # current month, 0-indexed

    if region == 'ICBT':
        # ICBT: Show selectbox for user input with header
        st.markdown("##### Index Month Selection")

        col1, col2, col3, col4 = st.columns([1, 2, 1, 2])

        with col1:
            st.markdown("<div style='margin-top: 8px;'><strong>Start Month</strong></div>", unsafe_allow_html=True)

        with col2:
            start_month_display = st.selectbox(
                "Start Month",
                options=month_options,
                index=default_start_month_index,
                key=f"{fee_type.lower()}_{region.lower()}_start_month",
                label_visibility="collapsed"
            )
            start_month = month_values[month_options.index(start_month_display)]

        with col3:
            st.markdown("<div style='margin-top: 8px;'><strong>End Month</strong></div>", unsafe_allow_html=True)

        with col4:
            end_month_display = st.selectbox(
                "End Month",
                options=month_options,
                index=default_end_month_index,
                key=f"{fee_type.lower()}_{region.lower()}_end_month",
                label_visibility="collapsed"
            )
            end_month = month_values[month_options.index(end_month_display)]

        # Calculate number of selected months
        if end_month >= start_month:
            num_months = end_month - start_month + 1
            index_months = list(range(start_month, end_month + 1))
        else:
            num_months = 0
            index_months = []

        # Display selection info message
        st.info(f"Selected {num_months} months for index selection")

    else:
        # Other regions (GC, HIS, JPKO): Display only, copy from ICBT
        if icbt_index_months and len(icbt_index_months) > 0:
            start_month = icbt_index_months[0]
            end_month = icbt_index_months[-1]
            num_months = len(icbt_index_months)
            index_months = icbt_index_months

            # Display the selection (read-only) in 1 row, 5 columns
            start_month_display = month_options[start_month - 1]
            end_month_display = month_options[end_month - 1]

            col1, col2, col3, col4, col5 = st.columns([3, 1, 1.5, 1, 1.5])

            with col1:
                st.markdown("<div style='margin-top: 8px; font-size: 1.2rem;'><strong>Index Month Selection (Copied from ICBT):</strong></div>", unsafe_allow_html=True)

            with col2:
                st.markdown("<div style='margin-top: 8px; font-size: 1.2rem;'><strong>Start Month</strong></div>", unsafe_allow_html=True)

            with col3:
                st.markdown(f"<div style='margin-top: 8px; font-size: 1.2rem;'>{start_month_display}</div>", unsafe_allow_html=True)

            with col4:
                st.markdown("<div style='margin-top: 8px; font-size: 1.2rem;'><strong>End Month</strong></div>", unsafe_allow_html=True)

            with col5:
                st.markdown(f"<div style='margin-top: 8px; font-size: 1.2rem;'>{end_month_display}</div>", unsafe_allow_html=True)

        else:
            # Fallback if no ICBT index months provided
            index_months = list(range(1, 13))
            st.warning("⚠️ No ICBT index months provided, using full year")

    # Get phasing baseline table (raw values, not formatted)
    phasing_months_key = f'{fee_type.lower()}_phasing_months'
    selected_months = control_panel_settings.get(phasing_months_key, [])

    # Calculate raw phasing table for baseline extraction
    if fee_type == 'FF':
        # FF needs special calculation (FF - TTL_PL_FEE)
        data_for_phasing = if_ff_store_data.copy()
        data_for_phasing['FF_NON_PL'] = (
            data_for_phasing['FF_N_USD_PLAN'] - data_for_phasing['TTL_PL_FEE_N_USD_PLAN']
        )
        phasing_column = 'FF_NON_PL'
    else:
        data_for_phasing = if_ff_store_data
        phasing_column = metric_column

    baseline_phasing_table_raw = calculate_phasing_table(data_for_phasing, phasing_column)

    # Calculate baseline column (average of selected months)
    if selected_months and len(selected_months) > 0:
        valid_selected = [m for m in selected_months if m in baseline_phasing_table_raw.columns]
        if valid_selected:
            baseline_phasing_table_raw.insert(0, 'Baseline', baseline_phasing_table_raw[valid_selected].mean(axis=1))
        else:
            baseline_phasing_table_raw.insert(0, 'Baseline', pd.NA)
    else:
        baseline_phasing_table_raw.insert(0, 'Baseline', pd.NA)

    current_date = control_panel_settings['current_date']

    # Build data table
    # Handle FF special case (FF - TTL_PL_FEE)
    if fee_type == 'FF':
        data_for_monthly = if_ff_store_data.copy()
        data_for_monthly['FF_NON_PL'] = (
            data_for_monthly['FF_N_USD_PLAN'] - data_for_monthly['TTL_PL_FEE_N_USD_PLAN']
        )
        monthly_metric_column = 'FF_NON_PL'
    else:
        data_for_monthly = if_ff_store_data
        monthly_metric_column = metric_column

    monthly_data = build_monthly_data_table(
        data=data_for_monthly,
        metric_column=monthly_metric_column,
        region_filter=REGION_FILTERS[region],
        current_date=current_date,
        baseline_phasing_table=baseline_phasing_table_raw,
        budget_df=budget_df,
        prior_forecast_df=prior_forecast_df,
        region=region,
        fee_type=fee_type
    )

    # Calculate baseline row from selected index months
    baseline_row = calculate_monthly_baseline_row(monthly_data, index_months)

    # Insert baseline row at the top (Row 0)
    baseline_df = pd.DataFrame([baseline_row])
    baseline_df = baseline_df.set_index('MONTH_OF_YEAR_ID')
    monthly_data = pd.concat([baseline_df, monthly_data])

    # Apply Run Rate logic: Fill 2026 Index Baseline where no 2026 actual exists
    # Use the baseline value from "2026 Adjusted" column (Row 0)
    baseline_2026_adjusted = baseline_row['2026 Adjusted']

    for month in monthly_data.index:
        if month != 'Index/Baseline':  # Skip the baseline row itself
            value_2026 = monthly_data.loc[month, 2026]

            if pd.notna(value_2026):
                # Has 2026 actual data, leave Index Baseline as None
                monthly_data.loc[month, '2026 Index Baseline'] = None
            else:
                # No 2026 actual data, use baseline value from 2026 Adjusted
                if pd.notna(baseline_2026_adjusted):
                    monthly_data.loc[month, '2026 Index Baseline'] = baseline_2026_adjusted
                else:
                    monthly_data.loc[month, '2026 Index Baseline'] = None

    # Chart Section (between Index Month Selection and Data)
    st.markdown("---")
    st.markdown(f"##### {fee_display_name} Forecast Chart")
    fig_monthly = create_monthly_data_chart(monthly_data, fee_display_name)
    st.plotly_chart(fig_monthly, use_container_width=True, key=f"chart_{fee_type}_{region}")

    # Data Section
    st.markdown("---")
    st.markdown("##### Data")

    # Format for display (number format with thousand separators, no decimals)
    monthly_data_display = format_monthly_data_for_display(monthly_data, format_type='number')

    st.dataframe(monthly_data_display, use_container_width=True, height=500)

    # Return index_months for ICBT (so other regions can copy) and monthly_data
    if region == 'ICBT':
        return index_months, monthly_data
    else:
        return None, monthly_data


def render_tab3(if_ff_store_data):
    """
    Main render function for Tab 3 - IF/FF/Store Forecast

    Args:
        if_ff_store_data: DataFrame with IF/FF/Store data

    Returns:
        Dictionary with monthly forecast data for IF, FF, Store (ICBT region)
    """
    if if_ff_store_data is None:
        st.warning("⚠️ IF/FF/Store data not available. Please retrieve data first.")
        return None

    # Render Control Panel and Phasing Tables
    control_panel_settings = render_control_panel_and_phasing_tables(if_ff_store_data)

    # === ICBT Region ===
    st.markdown("---")
    st.markdown("### 🌍 ICBT")
    st.markdown("---")

    # IF Forecast
    icbt_if_index_months, icbt_if_monthly_data = render_fee_forecast_section(
        fee_type='IF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='IF_N_USD_PLAN',
        fee_display_name='IF (Insertion Fee)',
        region='ICBT',
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # FF Forecast
    st.markdown("---")
    icbt_ff_index_months, icbt_ff_monthly_data = render_fee_forecast_section(
        fee_type='FF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='FF_N_USD_PLAN',
        fee_display_name='FF (Feature Fee)',
        region='ICBT',
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # Store Forecast
    st.markdown("---")
    icbt_store_index_months, icbt_store_monthly_data = render_fee_forecast_section(
        fee_type='Store',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='STORE_FEE_N_USD_PLAN',
        fee_display_name='Store Fee',
        region='ICBT',
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # === GC Region ===
    st.markdown("---")
    st.markdown("### 🌏 GC")
    st.markdown("---")

    # IF Forecast
    render_fee_forecast_section(
        fee_type='IF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='IF_N_USD_PLAN',
        fee_display_name='IF (Insertion Fee)',
        region='GC',
        icbt_index_months=icbt_if_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # FF Forecast
    st.markdown("---")
    render_fee_forecast_section(
        fee_type='FF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='FF_N_USD_PLAN',
        fee_display_name='FF (Feature Fee)',
        region='GC',
        icbt_index_months=icbt_ff_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # Store Forecast
    st.markdown("---")
    render_fee_forecast_section(
        fee_type='Store',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='STORE_FEE_N_USD_PLAN',
        fee_display_name='Store Fee',
        region='GC',
        icbt_index_months=icbt_store_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # === HIS Region ===
    st.markdown("---")
    st.markdown("### 🌏 HIS")
    st.markdown("---")

    # IF Forecast
    render_fee_forecast_section(
        fee_type='IF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='IF_N_USD_PLAN',
        fee_display_name='IF (Insertion Fee)',
        region='HIS',
        icbt_index_months=icbt_if_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # FF Forecast
    st.markdown("---")
    render_fee_forecast_section(
        fee_type='FF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='FF_N_USD_PLAN',
        fee_display_name='FF (Feature Fee)',
        region='HIS',
        icbt_index_months=icbt_ff_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # Store Forecast
    st.markdown("---")
    render_fee_forecast_section(
        fee_type='Store',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='STORE_FEE_N_USD_PLAN',
        fee_display_name='Store Fee',
        region='HIS',
        icbt_index_months=icbt_store_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # === JPKO Region ===
    st.markdown("---")
    st.markdown("### 🌏 JPKO")
    st.markdown("---")

    # IF Forecast
    render_fee_forecast_section(
        fee_type='IF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='IF_N_USD_PLAN',
        fee_display_name='IF (Insertion Fee)',
        region='JPKO',
        icbt_index_months=icbt_if_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # FF Forecast
    st.markdown("---")
    render_fee_forecast_section(
        fee_type='FF',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='FF_N_USD_PLAN',
        fee_display_name='FF (Feature Fee)',
        region='JPKO',
        icbt_index_months=icbt_ff_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # Store Forecast
    st.markdown("---")
    render_fee_forecast_section(
        fee_type='Store',
        if_ff_store_data=if_ff_store_data,
        control_panel_settings=control_panel_settings,
        metric_column='STORE_FEE_N_USD_PLAN',
        fee_display_name='Store Fee',
        region='JPKO',
        icbt_index_months=icbt_store_index_months,
        budget_df=control_panel_settings.get('budget_df'),
        prior_forecast_df=control_panel_settings.get('prior_forecast_df')
    )

    # === IF Monthly to Daily Phasing and Breakdown Table ===
    st.markdown("---")

    # Import the necessary functions from forecast_review_ui
    from modules.forecast_review_ui import render_if_monthly_daily_phasing_section, render_if_daily_breakdown_table

    # Render IF Monthly to Daily Phasing section
    render_if_monthly_daily_phasing_section(
        if_ff_store_data=if_ff_store_data
    )

    # Prepare tab3_monthly_data for IF Daily Breakdown Table
    if icbt_if_monthly_data is not None:
        if 'MONTH_OF_YEAR_ID' in icbt_if_monthly_data.columns:
            icbt_if_monthly_data = icbt_if_monthly_data.set_index('MONTH_OF_YEAR_ID')
    if icbt_ff_monthly_data is not None:
        if 'MONTH_OF_YEAR_ID' in icbt_ff_monthly_data.columns:
            icbt_ff_monthly_data = icbt_ff_monthly_data.set_index('MONTH_OF_YEAR_ID')
    if icbt_store_monthly_data is not None:
        if 'MONTH_OF_YEAR_ID' in icbt_store_monthly_data.columns:
            icbt_store_monthly_data = icbt_store_monthly_data.set_index('MONTH_OF_YEAR_ID')

    tab3_monthly_data_temp = {
        'IF': icbt_if_monthly_data,
        'FF': icbt_ff_monthly_data,
        'Store': icbt_store_monthly_data
    }

    # Render IF Daily Breakdown Table
    render_if_daily_breakdown_table(
        if_ff_store_data=if_ff_store_data,
        tab3_monthly_data=tab3_monthly_data_temp
    )

    # === Download Button ===
    st.markdown("---")

    if st.button("📥 Download Forecast Process", type="primary", key="download_if_ff_store_forecast"):
        with st.spinner("Generating Excel file..."):
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:

                # 1. Create Control Panel sheet
                control_panel_data = {
                    'Setting': ['Current Date', 'IF Phasing Months', 'FF Phasing Months', 'Store Phasing Months'],
                    'Value': [
                        control_panel_settings['current_date'].strftime('%Y-%m-%d'),
                        ', '.join(control_panel_settings['if_phasing_months_display']),
                        ', '.join(control_panel_settings['ff_phasing_months_display']),
                        ', '.join(control_panel_settings['store_phasing_months_display'])
                    ]
                }
                pd.DataFrame(control_panel_data).to_excel(writer, sheet_name='Control_Panel', index=False)

                # 2. Add ICBT Index Month Selection sheet
                month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                index_selection_data = {
                    'Fee Type': ['IF', 'FF', 'Store'],
                    'Start Month': [
                        month_names[icbt_if_index_months[0] - 1] if icbt_if_index_months else '',
                        month_names[icbt_ff_index_months[0] - 1] if icbt_ff_index_months else '',
                        month_names[icbt_store_index_months[0] - 1] if icbt_store_index_months else ''
                    ],
                    'End Month': [
                        month_names[icbt_if_index_months[-1] - 1] if icbt_if_index_months else '',
                        month_names[icbt_ff_index_months[-1] - 1] if icbt_ff_index_months else '',
                        month_names[icbt_store_index_months[-1] - 1] if icbt_store_index_months else ''
                    ],
                    'Number of Months': [
                        len(icbt_if_index_months) if icbt_if_index_months else 0,
                        len(icbt_ff_index_months) if icbt_ff_index_months else 0,
                        len(icbt_store_index_months) if icbt_store_index_months else 0
                    ]
                }
                pd.DataFrame(index_selection_data).to_excel(writer, sheet_name='ICBT_Index_Selection', index=False)

                # 3. Add Daily Phasing Tables
                # IF Phasing Table
                if_phasing_table = get_phasing_table_for_display(
                    if_ff_store_data,
                    metric_column='IF_N_USD_PLAN',
                    num_months=12,
                    selected_months=control_panel_settings.get('if_phasing_months', [])
                )
                if_phasing_table.to_excel(writer, sheet_name='IF_Daily_Phasing')

                # FF Phasing Table
                if_ff_store_data_ff = if_ff_store_data.copy()
                if_ff_store_data_ff['FF_NON_PL'] = (
                    if_ff_store_data_ff['FF_N_USD_PLAN'] - if_ff_store_data_ff['TTL_PL_FEE_N_USD_PLAN']
                )
                ff_phasing_table = get_phasing_table_for_display(
                    if_ff_store_data_ff,
                    metric_column='FF_NON_PL',
                    num_months=12,
                    selected_months=control_panel_settings.get('ff_phasing_months', [])
                )
                ff_phasing_table.to_excel(writer, sheet_name='FF_Daily_Phasing')

                # Store Phasing Table
                store_phasing_table = get_phasing_table_for_display(
                    if_ff_store_data,
                    metric_column='STORE_FEE_N_USD_PLAN',
                    num_months=12,
                    selected_months=control_panel_settings.get('store_phasing_months', [])
                )
                store_phasing_table.to_excel(writer, sheet_name='Store_Daily_Phasing')

                # 4. Create sheets for each region and fee type
                regions = ['ICBT', 'GC', 'HIS', 'JPKO']
                fee_types = [
                    ('IF', 'IF_N_USD_PLAN', 'IF (Insertion Fee)', icbt_if_index_months),
                    ('FF', 'FF_N_USD_PLAN', 'FF (Feature Fee)', icbt_ff_index_months),
                    ('Store', 'STORE_FEE_N_USD_PLAN', 'Store Fee', icbt_store_index_months)
                ]

                for region in regions:
                    for fee_type, metric_column, fee_display_name, index_months in fee_types:
                        # Build monthly data table
                        if fee_type == 'FF':
                            data_for_monthly = if_ff_store_data.copy()
                            data_for_monthly['FF_NON_PL'] = (
                                data_for_monthly['FF_N_USD_PLAN'] - data_for_monthly['TTL_PL_FEE_N_USD_PLAN']
                            )
                            monthly_metric_column = 'FF_NON_PL'
                        else:
                            data_for_monthly = if_ff_store_data
                            monthly_metric_column = metric_column

                        # Get baseline phasing table
                        phasing_months_key = f'{fee_type.lower()}_phasing_months'
                        selected_months = control_panel_settings.get(phasing_months_key, [])

                        if fee_type == 'FF':
                            data_for_phasing = if_ff_store_data.copy()
                            data_for_phasing['FF_NON_PL'] = (
                                data_for_phasing['FF_N_USD_PLAN'] - data_for_phasing['TTL_PL_FEE_N_USD_PLAN']
                            )
                            phasing_column = 'FF_NON_PL'
                        else:
                            data_for_phasing = if_ff_store_data
                            phasing_column = metric_column

                        baseline_phasing_table_raw = calculate_phasing_table(data_for_phasing, phasing_column)

                        if selected_months and len(selected_months) > 0:
                            valid_selected = [m for m in selected_months if m in baseline_phasing_table_raw.columns]
                            if valid_selected:
                                baseline_phasing_table_raw.insert(0, 'Baseline', baseline_phasing_table_raw[valid_selected].mean(axis=1))
                            else:
                                baseline_phasing_table_raw.insert(0, 'Baseline', pd.NA)
                        else:
                            baseline_phasing_table_raw.insert(0, 'Baseline', pd.NA)

                        monthly_data = build_monthly_data_table(
                            data=data_for_monthly,
                            metric_column=monthly_metric_column,
                            region_filter=REGION_FILTERS[region],
                            current_date=control_panel_settings['current_date'],
                            baseline_phasing_table=baseline_phasing_table_raw,
                            budget_df=control_panel_settings.get('budget_df'),
                            prior_forecast_df=control_panel_settings.get('prior_forecast_df'),
                            region=region,
                            fee_type=fee_type
                        )

                        # Calculate baseline row
                        baseline_row = calculate_monthly_baseline_row(monthly_data, index_months)
                        baseline_df = pd.DataFrame([baseline_row])
                        baseline_df = baseline_df.set_index('MONTH_OF_YEAR_ID')
                        monthly_data = pd.concat([baseline_df, monthly_data])

                        # Apply Run Rate logic
                        baseline_2026_adjusted = baseline_row['2026 Adjusted']
                        for month in monthly_data.index:
                            if month != 'Index/Baseline':
                                value_2026 = monthly_data.loc[month, 2026]
                                if pd.notna(value_2026):
                                    monthly_data.loc[month, '2026 Index Baseline'] = None
                                else:
                                    if pd.notna(baseline_2026_adjusted):
                                        monthly_data.loc[month, '2026 Index Baseline'] = baseline_2026_adjusted
                                    else:
                                        monthly_data.loc[month, '2026 Index Baseline'] = None

                        # Write to Excel
                        sheet_name = f"{region}_{fee_type}_Data"
                        monthly_data.to_excel(writer, sheet_name=sheet_name)

                # Get the workbook to add charts
                workbook = writer.book

                # 5. Add charts for each region and fee type
                for region in regions:
                    for fee_type, _, fee_display_name, _ in fee_types:
                        sheet_name = f"{region}_{fee_type}_Data"

                        if sheet_name in workbook.sheetnames:
                            ws = workbook[sheet_name]

                            # Create Chart
                            chart = LineChart()
                            chart.title = f"{region} - {fee_display_name} Forecast"
                            chart.style = 2
                            chart.y_axis.title = fee_display_name
                            chart.x_axis.title = "Month"
                            chart.height = 15
                            chart.width = 30

                            # Data columns: 2022, 2023, 2024, 2025, 2026 Adjusted, 2026 Index Baseline, 2026 Machine Learning, 2026 Budget, 2026 Prior Forecast
                            # Columns B-J (2-10), skip row 2 (baseline)
                            year_cols = ['2022', '2023', '2024', '2025', '2026 Adjusted', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']

                            for idx in range(len(year_cols)):
                                values = Reference(ws, min_col=2+idx, min_row=3, max_row=14)  # Skip baseline row (row 2)
                                chart.add_data(values, titles_from_data=False)

                            # Set series titles
                            for idx, series in enumerate(chart.series):
                                series.title = SeriesLabel(v=year_cols[idx])

                            # Set categories (Month numbers 1-12)
                            cats = Reference(ws, min_col=1, min_row=3, max_row=14)
                            chart.set_categories(cats)

                            ws.add_chart(chart, "L2")

            # Prepare download
            output.seek(0)
            st.download_button(
                label="📥 Download Excel File",
                data=output,
                file_name="IF_FF_Store_Forecast_Process.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.success("✅ Excel file generated successfully!")

    # Return monthly forecast data for Tab4
    # Ensure MONTH_OF_YEAR_ID is set as index, not a column
    if icbt_if_monthly_data is not None:
        if 'MONTH_OF_YEAR_ID' in icbt_if_monthly_data.columns:
            icbt_if_monthly_data = icbt_if_monthly_data.set_index('MONTH_OF_YEAR_ID')
    if icbt_ff_monthly_data is not None:
        if 'MONTH_OF_YEAR_ID' in icbt_ff_monthly_data.columns:
            icbt_ff_monthly_data = icbt_ff_monthly_data.set_index('MONTH_OF_YEAR_ID')
    if icbt_store_monthly_data is not None:
        if 'MONTH_OF_YEAR_ID' in icbt_store_monthly_data.columns:
            icbt_store_monthly_data = icbt_store_monthly_data.set_index('MONTH_OF_YEAR_ID')

    tab3_monthly_data = {
        'IF': icbt_if_monthly_data,
        'FF': icbt_ff_monthly_data,
        'Store': icbt_store_monthly_data
    }

    return tab3_monthly_data
