"""
TR Walk Section - Reusable component for displaying TR Walk analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from modules import tr_walk_engine, tr_walk_ui


def display_walk_section(
    walk_number,
    walk_title_default="",
    from_version_default="Prior Forecast",
    to_version_default="Current Forecast",
    start_date_default=None,
    end_date_default=None,
    tab4_daily_data=None,
    tab5_budget_df=None,
    tab5_prior_forecast_df=None
):
    """
    Display a complete TR Walk section with configuration and results

    Parameters:
    - walk_number: Integer (1, 2, 3, etc.) for unique keys
    - walk_title_default: Default value for Walk Title
    - from_version_default: Default selection for Walk From Version
    - to_version_default: Default selection for Walk To Version
    - start_date_default: Default start date (datetime object)
    - end_date_default: Default end date (datetime object)
    - tab4_daily_data: DataFrame from Tab4 daily revenue table
    - tab5_budget_df: DataFrame from Budget CSV
    - tab5_prior_forecast_df: DataFrame from Prior Forecast CSV
    """

    # Generate unique keys for this walk
    key_prefix = f"walk{walk_number}_"

    # Section header
    st.markdown("---")
    st.markdown(f"### 📊 Walk {walk_number}")
    st.markdown("#### ⚙️ Configuration")

    # Configuration inputs - Row 1
    row1_col1, row1_col2, row1_col3 = st.columns(3)

    with row1_col1:
        walk_title = st.text_input("Walk Title", value=walk_title_default, key=f"{key_prefix}title")

    with row1_col2:
        walk_from_version = st.selectbox(
            "Walk From Version",
            options=["Current Forecast", "Budget", "Prior Forecast"],
            index=["Current Forecast", "Budget", "Prior Forecast"].index(from_version_default),
            key=f"{key_prefix}from_version"
        )

    with row1_col3:
        walk_to_version = st.selectbox(
            "Walk To Version",
            options=["Current Forecast", "Budget", "Prior Forecast"],
            index=["Current Forecast", "Budget", "Prior Forecast"].index(to_version_default),
            key=f"{key_prefix}to_version"
        )

    # Configuration inputs - Row 2
    row2_col1, row2_col2, row2_col3 = st.columns(3)

    with row2_col1:
        walk_start_date = st.date_input(
            "Start Date",
            value=start_date_default if start_date_default else datetime.now(),
            key=f"{key_prefix}start_date"
        )

    with row2_col2:
        walk_end_date = st.date_input(
            "End Date",
            value=end_date_default if end_date_default else datetime.now(),
            key=f"{key_prefix}end_date"
        )

    with row2_col3:
        # Calculate and display Adjustment
        walk_buffer_stretch, buffer_msg = calculate_buffer_stretch(
            walk_from_version,
            walk_start_date,
            walk_end_date,
            tab5_budget_df,
            tab5_prior_forecast_df
        )

        st.markdown("<p style='font-size: 0.9em;'>Adjustment</p>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='font-weight: bold; text-decoration: underline; font-size: 1.4em;'>{walk_buffer_stretch*100:.3f}%</p>",
            unsafe_allow_html=True
        )
        if buffer_msg:
            st.caption(buffer_msg)

    # Get data sources for Walk From and Walk To
    walk_from_df = get_data_source(walk_from_version, tab4_daily_data, tab5_budget_df, tab5_prior_forecast_df)
    walk_to_df = get_data_source(walk_to_version, tab4_daily_data, tab5_budget_df, tab5_prior_forecast_df)

    # Check if both data sources are available
    if walk_from_df is None:
        st.error(f"⚠️ Data not available for '{walk_from_version}'. Please upload the required data.")
        return

    if walk_to_df is None:
        st.error(f"⚠️ Data not available for '{walk_to_version}'. Please upload the required data.")
        return

    # Calculate metrics
    try:
        walk_metrics = tr_walk_engine.calculate_walk_metrics(
            walk_from_df,
            walk_to_df,
            walk_start_date,
            walk_end_date,
            walk_buffer_stretch
        )

        # Display results
        display_walk_results(walk_metrics, walk_title)

    except Exception as e:
        st.error(f"⚠️ Error calculating Walk {walk_number} metrics: {str(e)}")


def calculate_buffer_stretch(from_version, start_date, end_date, budget_df, prior_forecast_df):
    """
    Calculate Adjustment value

    Returns:
    - buffer_stretch: Float value (percentage as decimal, e.g., 0.05 for 5%)
    - message: String message for user
    """

    if from_version == "Current Forecast":
        return 0.0, "Walk From is Current Forecast"

    # Determine data source
    data_df = None
    if from_version == "Budget" and budget_df is not None:
        data_df = budget_df
    elif from_version == "Prior Forecast" and prior_forecast_df is not None:
        data_df = prior_forecast_df

    if data_df is None:
        return 0.0, f"⚠️ No data available for {from_version}"

    # Check required columns
    if 'Date' not in data_df.columns:
        return 0.0, "⚠️ 'Date' column not found in data"
    if 'PLUG' not in data_df.columns:
        return 0.0, "⚠️ 'PLUG' column not found in data"
    if 'GMV' not in data_df.columns:
        return 0.0, "⚠️ 'GMV' column not found in data"

    try:
        # Filter by date range
        df_copy = data_df.copy()
        df_copy['Date'] = pd.to_datetime(df_copy['Date'])
        filtered_df = df_copy[
            (df_copy['Date'] >= pd.to_datetime(start_date)) &
            (df_copy['Date'] <= pd.to_datetime(end_date))
        ]

        if filtered_df.empty:
            return 0.0, "⚠️ No data in selected date range"

        # Calculate: -sum(PLUG) / sum(GMV)
        total_plug = filtered_df['PLUG'].sum()
        total_gmv = filtered_df['GMV'].sum()

        if total_gmv == 0:
            return 0.0, "⚠️ GMV is zero in selected date range"

        buffer_stretch = -total_plug / total_gmv
        return buffer_stretch, ""

    except Exception as e:
        return 0.0, f"⚠️ Error calculating: {str(e)}"


def get_data_source(version_name, tab4_daily_data, budget_df, prior_forecast_df):
    """
    Get the appropriate DataFrame based on version selection

    Returns:
    - DataFrame or None if not available
    """

    if version_name == "Current Forecast":
        return tab4_daily_data
    elif version_name == "Budget":
        return budget_df
    elif version_name == "Prior Forecast":
        return prior_forecast_df
    else:
        return None


def display_walk_results(walk_metrics, walk_title=""):
    """
    Display all Walk results: TXN TR Walk Table, Waterfall, and FVF Walk Section
    """

    # Display TXN TR Walk Table and Waterfall side by side
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 📊 TXN TR Walk Table")
        tr_walk_ui.display_txn_tr_walk_table(walk_metrics['txn_tr_walk'])

    with col2:
        st.markdown("#### 🌊 TXN TR Walk Waterfall")
        tr_walk_ui.display_waterfall_chart(
            walk_metrics['txn_tr_walk'],
            walk_metrics['waterfall_data']['Adjustment'],
            walk_title
        )

    # FVF TR Walk Section (Table + Waterfall side by side)
    tr_walk_ui.display_fvf_walk_section(
        walk_metrics['fvf_walk_data'],
        walk_metrics['txn_tr_walk'],
        walk_metrics['waterfall_data']['Adjustment'],
        walk_title
    )
