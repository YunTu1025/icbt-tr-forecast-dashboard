"""
Fee Forecast UI Generator - Creates complete forecast sections for each fee type
"""
import streamlit as st
from modules.fee_forecast_engine import (
    FEE_TYPE_CONFIG,
    load_and_aggregate_data,
    format_raw_data_for_display,
    build_forecast_table,
    calculate_baseline_row,
    build_index_table,
    update_forecast_2026_baseline,
    update_forecast_ml_predictions,
    create_forecast_chart,
    create_index_chart
)
from modules.ml_forecaster import forecast_variable_tr_2026, forecast_international_tr_2026


def render_fee_forecast_section(
    fee_type,
    fvf_data,
    control_panel_settings,
    week_date_map,
    budget_df=None,
    prior_forecast_df=None
):
    """
    Render a complete fee forecast section with all components

    Args:
        fee_type: Fee type name (e.g., 'Variable', 'BSTD', 'Fixed')
        fvf_data: Main FVF DataFrame
        control_panel_settings: Control panel settings from session state
        week_date_map: Dictionary mapping week numbers to dates
        budget_df: Optional Budget DataFrame from uploaded CSV
        prior_forecast_df: Optional Prior Forecast DataFrame from uploaded CSV

    Returns:
        DataFrame: The forecast table (df_forecast) for use in Tab4
    """
    # Get configuration
    if fee_type not in FEE_TYPE_CONFIG:
        st.error(f"Unknown fee type: {fee_type}")
        return

    config = FEE_TYPE_CONFIG[fee_type]
    fee_type_display = config['display_name']

    # Section header
    st.markdown("---")
    st.markdown(f"### 📈 {fee_type_display} Forecast")

    # Check if section should be displayed
    if fee_type not in control_panel_settings['fee_type_weights']:
        st.warning(f"{fee_type_display} not found in control panel settings")
        return

    st.markdown("---")
    st.markdown("##### Raw Data Preview")

    # Load and aggregate data
    df_agg, error_msg = load_and_aggregate_data(fvf_data, config, fee_type)

    if error_msg:
        st.error(f"❌ {error_msg}")
        st.info(f"Available columns: {', '.join(fvf_data.columns.tolist()[:20])}...")
        return

    # Format and display raw data
    df_display = format_raw_data_for_display(df_agg, config)
    st.dataframe(df_display, use_container_width=True, height=400)
    st.caption(f"Total Records: {len(df_agg):,} (aggregated by RETAIL_YEAR and RETAIL_WEEK)")

    # Get default year weights
    default_weights = control_panel_settings['fee_type_weights'][fee_type]['weights']

    # Year Weight Input Area
    st.markdown("---")
    st.markdown("##### Year Weights for Index Calculation")

    active_weights = {}
    cols = st.columns([0.5, 1.5, 0.3, 0.5, 1.5, 0.3, 0.5, 1.5, 0.3, 0.5, 1.5, 0.3])

    # 2022
    with cols[0]:
        st.markdown("<div style='margin-top: 8px;'>2022</div>", unsafe_allow_html=True)
    with cols[1]:
        active_weights[2022] = st.number_input(
            "2022", min_value=0.0, max_value=100.0,
            value=float(default_weights[2022]), step=1.0, format="%.2f",
            key=f"{fee_type.lower()}_weight_2022_input", label_visibility="collapsed"
        )
    with cols[2]:
        st.markdown("<div style='margin-top: 8px;'>%</div>", unsafe_allow_html=True)

    # 2023
    with cols[3]:
        st.markdown("<div style='margin-top: 8px;'>2023</div>", unsafe_allow_html=True)
    with cols[4]:
        active_weights[2023] = st.number_input(
            "2023", min_value=0.0, max_value=100.0,
            value=float(default_weights[2023]), step=1.0, format="%.2f",
            key=f"{fee_type.lower()}_weight_2023_input", label_visibility="collapsed"
        )
    with cols[5]:
        st.markdown("<div style='margin-top: 8px;'>%</div>", unsafe_allow_html=True)

    # 2024
    with cols[6]:
        st.markdown("<div style='margin-top: 8px;'>2024</div>", unsafe_allow_html=True)
    with cols[7]:
        active_weights[2024] = st.number_input(
            "2024", min_value=0.0, max_value=100.0,
            value=float(default_weights[2024]), step=1.0, format="%.2f",
            key=f"{fee_type.lower()}_weight_2024_input", label_visibility="collapsed"
        )
    with cols[8]:
        st.markdown("<div style='margin-top: 8px;'>%</div>", unsafe_allow_html=True)

    # 2025
    with cols[9]:
        st.markdown("<div style='margin-top: 8px;'>2025</div>", unsafe_allow_html=True)
    with cols[10]:
        active_weights[2025] = st.number_input(
            "2025", min_value=0.0, max_value=100.0,
            value=float(default_weights[2025]), step=1.0, format="%.2f",
            key=f"{fee_type.lower()}_weight_2025_input", label_visibility="collapsed"
        )
    with cols[11]:
        st.markdown("<div style='margin-top: 8px;'>%</div>", unsafe_allow_html=True)

    # Weight validation
    total_weight = sum(active_weights.values())
    if abs(total_weight - 100.0) > 0.01:
        st.warning(f"⚠️ Weights sum to {total_weight:.2f}% (should be 100%)")
    else:
        st.success(f"✅ Weights sum to {total_weight:.2f}%")

    # Build forecast table
    df_forecast = build_forecast_table(df_agg, config, week_date_map, budget_df, prior_forecast_df)

    # Calculate baseline/index values
    index_weeks = control_panel_settings['index_weeks']
    baseline_row = calculate_baseline_row(df_forecast, index_weeks)

    # Insert baseline row at the top
    import pandas as pd
    df_forecast = pd.concat([pd.DataFrame([baseline_row]), df_forecast], ignore_index=True)

    # Build index table
    df_index = build_index_table(df_forecast, active_weights, week_date_map)

    # Update 2026 Index Baseline in forecast
    baseline_values = {year: df_forecast.iloc[0][year] for year in ['2022', '2023', '2024', '2025', '2026']}
    baseline_2026 = baseline_values['2026']
    update_forecast_2026_baseline(df_forecast, df_index, baseline_2026)

    # === MACHINE LEARNING FORECASTING (Variable only) ===
    if fee_type == 'Variable':
        st.markdown("---")
        st.markdown("##### 🤖 Machine Learning Forecast")
        st.info("Training ensemble model (Prophet + XGBoost) on historical data (2022-2025)...")

        try:
            # Run ML forecaster
            ml_predictions = forecast_variable_tr_2026(df_agg, week_date_map)

            # Update forecast and index tables with ML predictions
            update_forecast_ml_predictions(df_forecast, df_index, ml_predictions, baseline_2026)

            st.success(f"✅ ML forecast completed! Predictions generated for 52 weeks.")

        except Exception as e:
            st.error(f"❌ ML forecasting failed: {str(e)}")
            st.info("Continuing with Index Baseline forecast only...")

    # === CHARTS SECTION ===
    st.markdown("---")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown(f"##### {fee_type_display} Forecast Chart")
        fig_forecast = create_forecast_chart(df_forecast, fee_type_display)
        st.plotly_chart(fig_forecast, use_container_width=True)

    with chart_col2:
        st.markdown(f"##### {fee_type_display} Index Chart")
        fig_index = create_index_chart(df_index)
        st.plotly_chart(fig_index, use_container_width=True)

    # === TABLES DISPLAY ===
    st.markdown("---")
    st.markdown(f"##### {fee_type_display} Forecast Table")

    # Format forecast table for display
    df_forecast_display = df_forecast.copy()
    df_forecast_display = df_forecast_display.reset_index(drop=True)
    for col in ['2022', '2023', '2024', '2025', '2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']:
        if col in df_forecast_display.columns:
            df_forecast_display[col] = df_forecast_display[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    st.dataframe(df_forecast_display, use_container_width=True, height=400, hide_index=True)

    # Display Index Table
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

    # Return the forecast DataFrame for Tab4
    return df_forecast


def render_fee_forecast_section_run_rate(
    fee_type,
    fvf_data,
    control_panel_settings,
    week_date_map,
    budget_df=None,
    prior_forecast_df=None
):
    """
    Render a fee forecast section using Run Rate methodology
    (Used for eTRS, Regulatory, Buyer Protection)

    Differences from Index Baseline methodology:
    - No Year Weights input
    - No Index Table
    - No Index Chart
    - 2026 Index Baseline = constant baseline value for all weeks without 2026 actual

    Args:
        fee_type: Fee type name (e.g., 'eTRS', 'Regulatory', 'Buyer Protection')
        fvf_data: Main FVF DataFrame
        control_panel_settings: Control panel settings from session state
        week_date_map: Dictionary mapping week numbers to dates
        budget_df: Optional Budget DataFrame from uploaded CSV
        prior_forecast_df: Optional Prior Forecast DataFrame from uploaded CSV

    Returns:
        DataFrame: The forecast table (df_forecast) for use in Tab4
    """
    # Get configuration
    if fee_type not in FEE_TYPE_CONFIG:
        st.error(f"Unknown fee type: {fee_type}")
        return

    config = FEE_TYPE_CONFIG[fee_type]
    fee_type_display = config['display_name']

    # Section header
    st.markdown("---")
    st.markdown(f"### 📈 {fee_type_display} Forecast")

    st.markdown("---")
    st.markdown("##### Raw Data Preview")

    # Load and aggregate data
    df_agg, error_msg = load_and_aggregate_data(fvf_data, config, fee_type)

    if error_msg:
        st.error(f"❌ {error_msg}")
        st.info(f"Available columns: {', '.join(fvf_data.columns.tolist()[:20])}...")
        return

    # Format and display raw data
    df_display = format_raw_data_for_display(df_agg, config)
    st.dataframe(df_display, use_container_width=True, height=400)
    st.caption(f"Total Records: {len(df_agg):,} (aggregated by RETAIL_YEAR and RETAIL_WEEK)")

    # Build forecast table
    df_forecast = build_forecast_table(df_agg, config, week_date_map, budget_df, prior_forecast_df)

    # Calculate baseline/index values
    index_weeks = control_panel_settings['index_weeks']
    baseline_row = calculate_baseline_row(df_forecast, index_weeks)

    # Insert baseline row at the top
    import pandas as pd
    df_forecast = pd.concat([pd.DataFrame([baseline_row]), df_forecast], ignore_index=True)

    # Get 2026 baseline value
    baseline_2026 = df_forecast.iloc[0]['2026']

    # Update 2026 Index Baseline: for all weeks without 2026 actual, use baseline value
    for i in range(1, len(df_forecast)):  # Skip row 0 (baseline)
        value_2026 = df_forecast.iloc[i]['2026']

        if pd.notna(value_2026):
            # Has 2026 actual data, leave Index Baseline as None
            df_forecast.at[i, '2026 Index Baseline'] = None
        else:
            # No 2026 actual data, use baseline value
            if pd.notna(baseline_2026):
                df_forecast.at[i, '2026 Index Baseline'] = baseline_2026
            else:
                df_forecast.at[i, '2026 Index Baseline'] = None

    # === CHART SECTION (Forecast only, no Index chart) ===
    st.markdown("---")
    st.markdown(f"##### {fee_type_display} Forecast Chart")
    fig_forecast = create_forecast_chart(df_forecast, fee_type_display)
    st.plotly_chart(fig_forecast, use_container_width=True)

    # === TABLE DISPLAY (Forecast only, no Index table) ===
    st.markdown("---")
    st.markdown(f"##### {fee_type_display} Forecast Table")

    # Format forecast table for display
    df_forecast_display = df_forecast.copy()
    df_forecast_display = df_forecast_display.reset_index(drop=True)
    for col in ['2022', '2023', '2024', '2025', '2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']:
        if col in df_forecast_display.columns:
            df_forecast_display[col] = df_forecast_display[col].apply(
                lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
            )

    st.dataframe(df_forecast_display, use_container_width=True, height=400, hide_index=True)

    # Return the forecast DataFrame for Tab4
    return df_forecast
