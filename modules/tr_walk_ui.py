"""
TR Walk UI - Display components for TR Walk analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def display_txn_tr_walk_table(txn_tr_walk):
    """
    Display TXN TR Walk Table
    Rows: GMV, FVF, IF, FF Non-PL, Store, Subtotal
    Columns: Walk From ($), Walk To ($), Walk From (%), Walk To (%), Delta (%)
    """

    # Define the metrics we want to display in order
    metric_order = ['GMV', 'FVF', 'IF', 'FF non-PL', 'Store', 'Subtotal']

    # Prepare data for display
    rows = []

    # Get GMV values first for percentage calculation
    gmv_from = txn_tr_walk.get('GMV', {}).get('Walk From', 1)
    gmv_to = txn_tr_walk.get('GMV', {}).get('Walk To', 1)

    # Prevent division by zero
    if gmv_from == 0:
        gmv_from = 1
    if gmv_to == 0:
        gmv_to = 1

    # Calculate Subtotal (sum of FVF, IF, FF non-PL, Store)
    subtotal_from = 0
    subtotal_to = 0
    for key in ['FVF', 'IF', 'FF non-PL', 'Store']:
        if key in txn_tr_walk:
            subtotal_from += txn_tr_walk[key].get('Walk From', 0)
            subtotal_to += txn_tr_walk[key].get('Walk To', 0)

    # Build rows in specified order
    for metric_name in metric_order:
        if metric_name == 'Subtotal':
            walk_from_dollar = subtotal_from
            walk_to_dollar = subtotal_to
        elif metric_name in txn_tr_walk:
            walk_from_dollar = txn_tr_walk[metric_name].get('Walk From', 0)
            walk_to_dollar = txn_tr_walk[metric_name].get('Walk To', 0)
        else:
            walk_from_dollar = 0
            walk_to_dollar = 0

        # Calculate percentages (TR)
        if metric_name == 'GMV':
            # GMV percentage - no values needed
            walk_from_pct = None
            walk_to_pct = None
            delta_pct = None
        else:
            walk_from_pct = (walk_from_dollar / gmv_from * 100) if gmv_from != 0 else 0
            walk_to_pct = (walk_to_dollar / gmv_to * 100) if gmv_to != 0 else 0
            delta_pct = walk_to_pct - walk_from_pct

        rows.append({
            'Metric': metric_name,
            'Walk From ($)': walk_from_dollar,
            'Walk To ($)': walk_to_dollar,
            'Walk From (%)': walk_from_pct,
            'Walk To (%)': walk_to_pct,
            'Delta (%)': delta_pct
        })

    df_display = pd.DataFrame(rows)

    # Format numbers
    df_display_formatted = df_display.copy()
    df_display_formatted['Walk From ($)'] = df_display_formatted['Walk From ($)'].apply(lambda x: f"${x:,.0f}")
    df_display_formatted['Walk To ($)'] = df_display_formatted['Walk To ($)'].apply(lambda x: f"${x:,.0f}")
    df_display_formatted['Walk From (%)'] = df_display_formatted['Walk From (%)'].apply(
        lambda x: '' if pd.isna(x) or x is None else f"{x:.2f}%")
    df_display_formatted['Walk To (%)'] = df_display_formatted['Walk To (%)'].apply(
        lambda x: '' if pd.isna(x) or x is None else f"{x:.2f}%")
    df_display_formatted['Delta (%)'] = df_display_formatted['Delta (%)'].apply(
        lambda x: '' if pd.isna(x) or x is None else f"{x:.2f}%")

    st.dataframe(df_display_formatted, use_container_width=True, hide_index=True)


def display_waterfall_chart(txn_tr_walk, buffer_stretch, walk_title=""):
    """
    Display Waterfall Chart

    Structure:
    - Submission (= Subtotal of Walk From (%))
    - Adjustment (= Adjustment in configuration)
    - Realistic (= Submission + Adjustment)
    - FVF (= FVF Delta (%) - Adjustment)
    - IF (= IF Delta (%))
    - FF non-PL (= FF non-PL Delta (%))
    - Store (= Store Delta (%))
    - Current Forecast (= Subtotal of Walk To (%))
    """

    # Get GMV values
    gmv_from = txn_tr_walk.get('GMV', {}).get('Walk From', 1)
    gmv_to = txn_tr_walk.get('GMV', {}).get('Walk To', 1)
    if gmv_from == 0:
        gmv_from = 1
    if gmv_to == 0:
        gmv_to = 1

    # Calculate Submission as Subtotal of Walk From (%)
    subtotal_from = 0
    for key in ['FVF', 'IF', 'FF non-PL', 'Store']:
        if key in txn_tr_walk:
            subtotal_from += txn_tr_walk[key].get('Walk From', 0)

    submission = (subtotal_from / gmv_from * 100)  # percentage

    # Calculate Realistic = Submission + Adjustment
    realistic = submission + (buffer_stretch * 100)  # Convert buffer_stretch to percentage

    # Calculate Walk From (%) and Walk To (%) for each component
    fvf_from_pct = (txn_tr_walk.get('FVF', {}).get('Walk From', 0) / gmv_from * 100) if gmv_from != 0 else 0
    fvf_to_pct = (txn_tr_walk.get('FVF', {}).get('Walk To', 0) / gmv_to * 100) if gmv_to != 0 else 0

    if_from_pct = (txn_tr_walk.get('IF', {}).get('Walk From', 0) / gmv_from * 100) if gmv_from != 0 else 0
    if_to_pct = (txn_tr_walk.get('IF', {}).get('Walk To', 0) / gmv_to * 100) if gmv_to != 0 else 0

    ff_from_pct = (txn_tr_walk.get('FF non-PL', {}).get('Walk From', 0) / gmv_from * 100) if gmv_from != 0 else 0
    ff_to_pct = (txn_tr_walk.get('FF non-PL', {}).get('Walk To', 0) / gmv_to * 100) if gmv_to != 0 else 0

    store_from_pct = (txn_tr_walk.get('Store', {}).get('Walk From', 0) / gmv_from * 100) if gmv_from != 0 else 0
    store_to_pct = (txn_tr_walk.get('Store', {}).get('Walk To', 0) / gmv_to * 100) if gmv_to != 0 else 0

    # Calculate deltas
    fvf_delta = fvf_to_pct - fvf_from_pct
    if_delta = if_to_pct - if_from_pct
    ff_delta = ff_to_pct - ff_from_pct
    store_delta = store_to_pct - store_from_pct

    # FVF delta needs to subtract adjustment
    fvf_delta_adjusted = fvf_delta - (buffer_stretch * 100)

    # Calculate Current Forecast as Subtotal of Walk To (%)
    subtotal_to = 0
    for key in ['FVF', 'IF', 'FF non-PL', 'Store']:
        if key in txn_tr_walk:
            subtotal_to += txn_tr_walk[key].get('Walk To', 0)

    current_forecast = (subtotal_to / gmv_to * 100)  # percentage

    # Build waterfall data
    x_labels = ['Submission', 'Adjustment', 'Realistic', 'FVF', 'IF', 'FF non-PL', 'Store', 'Current Forecast']
    measures = ['absolute', 'relative', 'total', 'relative', 'relative', 'relative', 'relative', 'total']
    values = [submission, buffer_stretch * 100, realistic, fvf_delta_adjusted, if_delta, ff_delta, store_delta, current_forecast]

    # Create waterfall chart
    # Colors: Submission, Realistic, Current Forecast (absolute/total) = black
    #         Positive changes (increasing) = green
    #         Negative changes (decreasing) = red
    fig = go.Figure(go.Waterfall(
        name="TR Walk",
        orientation="v",
        measure=measures,
        x=x_labels,
        textposition="outside",
        text=[f"{v:.2f}%" for v in values],
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},  # Green for positive
        decreasing={"marker": {"color": "#e74c3c"}},  # Red for negative
        totals={"marker": {"color": "#000000"}}  # Black for totals and absolute
    ))

    # Calculate axis bounds: min - 0.1%, max + 0.1%
    # For waterfall, we need to consider cumulative values
    cumulative = 0
    heights = [submission]  # Start with submission

    # Track cumulative heights for each bar
    cumulative = submission
    for i, (measure, value) in enumerate(zip(measures[1:], values[1:]), 1):
        if measure == 'relative':
            cumulative += value
            heights.append(cumulative)
        elif measure == 'total':
            heights.append(value)

    min_height = min(heights)
    max_height = max(heights)

    y_min = min_height - 0.1
    y_max = max_height + 0.1

    # Update layout
    chart_title = walk_title if walk_title else "TXN TR Walk Waterfall"

    fig.update_layout(
        title=chart_title,
        showlegend=False,
        height=500,
        yaxis_title="Take Rate (%)",
        xaxis_title="",
        yaxis=dict(
            tickformat=".2f",
            ticksuffix="%",
            range=[y_min, y_max]
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def display_fvf_walk_section(fvf_walk_data, txn_tr_walk, buffer_stretch, walk_title=""):
    """
    Display FVF TR Walk section with table and waterfall side by side

    Structure:
    - Left: FVF TR Walk Table (same format as TXN TR Walk Table)
    - Right: FVF TR Walk Waterfall (similar to TXN TR Walk Waterfall)
    """

    # Create two columns for side-by-side layout
    fvf_col1, fvf_col2 = st.columns([1, 1])

    with fvf_col1:
        st.markdown("#### 📊 FVF TR Walk Table")
        display_fvf_walk_table(fvf_walk_data, txn_tr_walk)

    with fvf_col2:
        st.markdown("#### 🌊 FVF TR Walk Waterfall")
        display_fvf_walk_waterfall(fvf_walk_data, txn_tr_walk, buffer_stretch, walk_title)


def display_fvf_walk_table(fvf_walk_data, txn_tr_walk):
    """
    Display FVF TR Walk Table
    Rows: GMV, Variable, International, BSTD, eTRS, SNAD, Fixed, Credit, Regulatory, Buyer Protection, Net FVF
    Columns: Walk From ($), Walk To ($), Walk From (%), Walk To (%), Delta (%)
    """

    # Define the metrics in order
    fvf_components = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']

    # Get GMV values
    gmv_from = txn_tr_walk.get('GMV', {}).get('Walk From', 1)
    gmv_to = txn_tr_walk.get('GMV', {}).get('Walk To', 1)
    if gmv_from == 0:
        gmv_from = 1
    if gmv_to == 0:
        gmv_to = 1

    # Prepare rows
    rows = []

    # GMV row (no percentages)
    rows.append({
        'Metric': 'GMV',
        'Walk From ($)': gmv_from,
        'Walk To ($)': gmv_to,
        'Walk From (%)': None,
        'Walk To (%)': None,
        'Delta (%)': None
    })

    # FVF component rows
    for component_name in fvf_components:
        if component_name in fvf_walk_data:
            values = fvf_walk_data[component_name]
            walk_from_pct = values.get('Walk From (%)', 0)
            walk_to_pct = values.get('Walk To (%)', 0)

            # Calculate dollar amounts from percentages
            walk_from_dollar = walk_from_pct / 100 * gmv_from if walk_from_pct else 0
            walk_to_dollar = walk_to_pct / 100 * gmv_to if walk_to_pct else 0

            delta_pct = walk_to_pct - walk_from_pct

            rows.append({
                'Metric': component_name,
                'Walk From ($)': walk_from_dollar,
                'Walk To ($)': walk_to_dollar,
                'Walk From (%)': walk_from_pct,
                'Walk To (%)': walk_to_pct,
                'Delta (%)': delta_pct
            })
        else:
            # Add placeholder if component not found
            rows.append({
                'Metric': component_name,
                'Walk From ($)': 0,
                'Walk To ($)': 0,
                'Walk From (%)': 0,
                'Walk To (%)': 0,
                'Delta (%)': 0
            })

    # Add Net FVF row (sum of all components)
    if 'Net FVF TR' in fvf_walk_data:
        net_fvf_values = fvf_walk_data['Net FVF TR']
        net_fvf_from_pct = net_fvf_values.get('Walk From (%)', 0)
        net_fvf_to_pct = net_fvf_values.get('Walk To (%)', 0)

        # Calculate dollar amounts from percentages
        net_fvf_from_dollar = net_fvf_from_pct / 100 * gmv_from if net_fvf_from_pct else 0
        net_fvf_to_dollar = net_fvf_to_pct / 100 * gmv_to if net_fvf_to_pct else 0

        net_fvf_delta_pct = net_fvf_to_pct - net_fvf_from_pct

        rows.append({
            'Metric': 'Net FVF',
            'Walk From ($)': net_fvf_from_dollar,
            'Walk To ($)': net_fvf_to_dollar,
            'Walk From (%)': net_fvf_from_pct,
            'Walk To (%)': net_fvf_to_pct,
            'Delta (%)': net_fvf_delta_pct
        })

    df_display = pd.DataFrame(rows)

    # Format numbers
    df_display_formatted = df_display.copy()
    df_display_formatted['Walk From ($)'] = df_display_formatted['Walk From ($)'].apply(lambda x: f"${x:,.0f}")
    df_display_formatted['Walk To ($)'] = df_display_formatted['Walk To ($)'].apply(lambda x: f"${x:,.0f}")
    df_display_formatted['Walk From (%)'] = df_display_formatted['Walk From (%)'].apply(
        lambda x: '' if pd.isna(x) or x is None else f"{x:.2f}%")
    df_display_formatted['Walk To (%)'] = df_display_formatted['Walk To (%)'].apply(
        lambda x: '' if pd.isna(x) or x is None else f"{x:.2f}%")
    df_display_formatted['Delta (%)'] = df_display_formatted['Delta (%)'].apply(
        lambda x: '' if pd.isna(x) or x is None else f"{x:.2f}%")

    st.dataframe(df_display_formatted, use_container_width=True, hide_index=True, height=430)


def display_fvf_walk_waterfall(fvf_walk_data, txn_tr_walk, buffer_stretch, walk_title=""):
    """
    Display FVF TR Walk Waterfall

    Structure (similar to TXN TR Walk Waterfall):
    - Submission (FVF Walk From (%))
    - Adjustment
    - Realistic (= Submission + Adjustment)
    - Variable (= Variable Delta (%) - Adjustment)  **Special calculation**
    - International, BSTD, eTRS, SNAD, Fixed, Credit, Regulatory, Buyer Protection (= Delta (%))
    - Current Forecast (FVF Walk To (%))
    """

    # Get GMV values
    gmv_from = txn_tr_walk.get('GMV', {}).get('Walk From', 1)
    gmv_to = txn_tr_walk.get('GMV', {}).get('Walk To', 1)
    if gmv_from == 0:
        gmv_from = 1
    if gmv_to == 0:
        gmv_to = 1

    # Calculate Submission as sum of all FVF components Walk From (%)
    fvf_components = ['Variable', 'International', 'BSTD', 'eTRS', 'SNAD', 'Fixed', 'Credit', 'Regulatory', 'Buyer Protection']

    submission = 0
    for comp in fvf_components:
        if comp in fvf_walk_data:
            submission += fvf_walk_data[comp].get('Walk From (%)', 0)

    # Calculate Realistic = Submission + Adjustment
    realistic = submission + (buffer_stretch * 100)

    # Calculate Current Forecast as sum of all FVF components Walk To (%)
    current_forecast = 0
    for comp in fvf_components:
        if comp in fvf_walk_data:
            current_forecast += fvf_walk_data[comp].get('Walk To (%)', 0)

    # Get deltas for each component
    deltas = {}
    for comp in fvf_components:
        if comp in fvf_walk_data:
            walk_from_pct = fvf_walk_data[comp].get('Walk From (%)', 0)
            walk_to_pct = fvf_walk_data[comp].get('Walk To (%)', 0)
            delta = walk_to_pct - walk_from_pct

            # Special handling for Variable: subtract adjustment
            if comp == 'Variable':
                delta = delta - (buffer_stretch * 100)

            deltas[comp] = delta
        else:
            deltas[comp] = 0

    # Build waterfall data
    x_labels = ['Submission', 'Adjustment', 'Realistic']
    measures = ['absolute', 'relative', 'total']
    values = [submission, buffer_stretch * 100, realistic]

    # Add component deltas
    for comp in fvf_components:
        x_labels.append(comp)
        measures.append('relative')
        values.append(deltas[comp])

    # Add Current Forecast
    x_labels.append('Current Forecast')
    measures.append('total')
    values.append(current_forecast)

    # Create waterfall chart
    fig = go.Figure(go.Waterfall(
        name="FVF TR Walk",
        orientation="v",
        measure=measures,
        x=x_labels,
        textposition="outside",
        text=[f"{v:.2f}%" for v in values],
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},  # Green for positive
        decreasing={"marker": {"color": "#e74c3c"}},  # Red for negative
        totals={"marker": {"color": "#000000"}}  # Black for totals and absolute
    ))

    # Calculate axis bounds
    cumulative = 0
    heights = [submission]
    cumulative = submission
    for i, (measure, value) in enumerate(zip(measures[1:], values[1:]), 1):
        if measure == 'relative':
            cumulative += value
            heights.append(cumulative)
        elif measure == 'total':
            heights.append(value)

    min_height = min(heights)
    max_height = max(heights)
    y_min = min_height - 0.1
    y_max = max_height + 0.1

    # Update layout
    chart_title = walk_title if walk_title else "FVF TR Walk Waterfall"

    fig.update_layout(
        title=chart_title,
        showlegend=False,
        height=500,
        yaxis_title="Take Rate (%)",
        xaxis_title="",
        yaxis=dict(
            tickformat=".2f",
            ticksuffix="%",
            range=[y_min, y_max]
        )
    )

    st.plotly_chart(fig, use_container_width=True)
