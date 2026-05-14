"""
Common Utilities - Shared helper functions across modules
Contains reusable baseline calculation and chart creation utilities
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def calculate_baseline(
    data,
    index_selection,
    index_column_name='Week',
    data_columns=None,
    baseline_label='Index/Baseline',
    date_range_format=None
):
    """
    Generic baseline calculation utility for both weekly and monthly data

    Args:
        data: DataFrame containing the data (weekly or monthly)
        index_selection: List of indices to use for baseline (e.g., [1, 2, 3] for weeks/months)
        index_column_name: Name of the index column (e.g., 'Week', 'MONTH_OF_YEAR_ID')
        data_columns: List of column names to calculate baseline for (e.g., ['2022', '2023', ...])
                     If None, defaults to ['2022', '2023', '2024', '2025', '2026']
        baseline_label: Label for the baseline row (e.g., 'Index/Baseline')
        date_range_format: Optional string format for date range display
                          If None, uses "Weeks/Months {min}-{max}" format

    Returns:
        Dictionary representing the baseline row

    Examples:
        # Weekly baseline (for fee_forecast_engine)
        baseline_row = calculate_baseline(
            data=df_forecast,
            index_selection=[1, 2, 3, 4],
            index_column_name='Week',
            baseline_label='Index/Baseline'
        )

        # Monthly baseline (for if_ff_store_forecast_engine)
        baseline_row = calculate_baseline(
            data=monthly_data,
            index_selection=[1, 2, 3],
            index_column_name='MONTH_OF_YEAR_ID',
            baseline_label='Index/Baseline'
        )
    """
    if data_columns is None:
        data_columns = ['2022', '2023', '2024', '2025', '2026']

    # Initialize baseline row
    baseline_row = {index_column_name: baseline_label}

    # Add date range if applicable
    if 'Date' in data.columns or date_range_format is not None:
        if date_range_format:
            baseline_row['Date'] = date_range_format
        else:
            unit = 'Weeks' if index_column_name == 'Week' else 'Months'
            baseline_row['Date'] = f"{unit} {min(index_selection)}-{max(index_selection)}"

    # Calculate baseline for each data column
    for col in data_columns:
        if col in data.columns:
            # Filter by index selection
            if index_column_name in data.columns:
                values = data[data[index_column_name].isin(index_selection)][col].dropna()
            else:
                # If index is already set, use index directly
                values = data.loc[data.index.isin(index_selection), col].dropna()

            if len(values) > 0:
                baseline_row[col] = values.mean()
            else:
                baseline_row[col] = None
        else:
            baseline_row[col] = None

    # Handle forecast columns
    baseline_row['2026 Index Baseline'] = None
    baseline_row['2026 Machine Learning'] = None

    # Calculate baseline for optional columns (2026 Adjusted, Budget, Prior Forecast)
    optional_columns = ['2026 Adjusted', '2026 Budget', '2026 Prior Forecast']
    for col in optional_columns:
        if col in data.columns:
            if index_column_name in data.columns:
                values = data[data[index_column_name].isin(index_selection)][col].dropna()
            else:
                values = data.loc[data.index.isin(index_selection), col].dropna()

            if len(values) > 0:
                baseline_row[col] = values.mean()
            else:
                baseline_row[col] = None
        else:
            baseline_row[col] = None

    return baseline_row


def create_plotly_line_chart(
    data,
    x_column,
    chart_type='forecast',
    title=None,
    x_title=None,
    y_title=None,
    skip_rows_with_value=None,
    y_multiplier=1.0,
    y_format='number',
    x_axis_config=None,
    height=500
):
    """
    Generic Plotly line chart creator for forecast and index charts

    Args:
        data: DataFrame with data to plot
        x_column: Name of the column to use for x-axis (e.g., 'Week', month index)
        chart_type: 'forecast', 'index', or 'monthly' - determines default settings
        title: Optional chart title
        x_title: X-axis title (default: "Week" or "Month")
        y_title: Y-axis title (default based on chart_type)
        skip_rows_with_value: Skip rows where x_column equals this value (e.g., 'Index/Baseline')
        y_multiplier: Multiply y values by this (e.g., 100 for percentage)
        y_format: 'percentage', 'number', or 'decimal' - determines tick format
        x_axis_config: Optional dict for x-axis configuration (e.g., {'tickmode': 'linear', 'dtick': 4})
        height: Chart height in pixels (default: 500)

    Returns:
        Plotly Figure object

    Examples:
        # Weekly forecast chart (fee_forecast_engine)
        fig = create_plotly_line_chart(
            data=df_forecast,
            x_column='Week',
            chart_type='forecast',
            y_title='Variable TR (%)',
            skip_rows_with_value='Index/Baseline',
            y_multiplier=100,
            y_format='percentage'
        )

        # Index chart (fee_forecast_engine)
        fig = create_plotly_line_chart(
            data=df_index,
            x_column='Week',
            chart_type='index',
            skip_rows_with_value='Year Weights',
            y_format='decimal'
        )

        # Monthly chart (if_ff_store_forecast_engine)
        fig = create_plotly_line_chart(
            data=monthly_data,
            x_column='MONTH_OF_YEAR_ID',
            chart_type='monthly',
            y_title='IF (Insertion Fee)',
            skip_rows_with_value='Index/Baseline',
            y_format='number'
        )
    """
    # Data columns to plot
    data_columns = ['2022', '2023', '2024', '2025', '2026', '2026 Index Baseline',
                    '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']

    # Handle 2026 Adjusted for monthly charts
    if chart_type == 'monthly' and '2026 Adjusted' in data.columns:
        # Insert '2026 Adjusted' after '2025'
        data_columns = ['2022', '2023', '2024', '2025', '2026 Adjusted', '2026 Index Baseline',
                       '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']

    # Color scheme
    colors = ['#4472C4', '#ED7D31', '#70AD47', '#FFC000', '#000000', '#FF0000',
              '#B19CD9', '#A5A5A5', '#000000']

    # Forecast columns that should be dotted lines
    forecast_columns = ['2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']

    # Thick lines columns
    thick_lines = ['2026', '2026 Adjusted', '2026 Index Baseline', '2026 Machine Learning',
                   '2026 Budget', '2026 Prior Forecast']

    # Filter data - skip baseline/header rows
    df_chart = data.copy()
    if skip_rows_with_value is not None:
        if x_column in df_chart.columns:
            df_chart = df_chart[df_chart[x_column] != skip_rows_with_value].copy()
        else:
            df_chart = df_chart[df_chart.index != skip_rows_with_value].copy()

    # Create figure
    fig = go.Figure()

    # Add traces
    for i, col in enumerate(data_columns):
        if col not in df_chart.columns:
            continue

        y_values = df_chart[col].values
        mask = pd.notna(y_values)

        # Get x values
        if x_column in df_chart.columns:
            x_values_raw = df_chart[x_column].values[mask]
        else:
            x_values_raw = df_chart.index.values[mask]

        y_values_filtered = y_values[mask] * y_multiplier

        if len(y_values_filtered) == 0:
            continue

        # Convert month numbers to names for monthly charts
        if chart_type == 'monthly':
            month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            x_values = [month_labels[idx - 1] for idx in x_values_raw
                       if isinstance(idx, (int, np.integer)) and 1 <= idx <= 12]
        else:
            x_values = x_values_raw

        # Line style
        line_style = dict(
            color=colors[i % len(colors)],
            width=2.5 if col in thick_lines else 2,
            shape='spline',
            smoothing=0.3
        )

        # Dotted lines for forecast columns
        if col in forecast_columns:
            line_style['dash'] = 'dot'

        # Hover template based on format
        if y_format == 'percentage':
            hover_template = f'{col}<br>%{{y:.2f}}%<extra></extra>'
        elif y_format == 'decimal':
            hover_template = f'{col}<br>%{{y:.1f}}<extra></extra>'
        else:  # number
            hover_template = f'{col}<br>%{{y:,.0f}}<extra></extra>'

        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values_filtered,
            mode='lines',
            name=col,
            line=line_style,
            hovertemplate=hover_template
        ))

    # Configure x-axis
    if x_axis_config is None:
        if chart_type == 'monthly':
            x_axis_config = {
                'type': 'category',
                'categoryorder': 'array',
                'categoryarray': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            }
        else:
            x_axis_config = {'tickmode': 'linear', 'tick0': 0, 'dtick': 4}

    # Configure y-axis
    if y_format == 'percentage':
        y_axis_config = {'tickformat': '.2f', 'ticksuffix': '%'}
    elif y_format == 'decimal':
        y_axis_config = {'tickformat': '.1f'}
    else:  # number
        y_axis_config = {'tickformat': ',.0f', 'separatethousands': True}

    # Set default titles
    if x_title is None:
        x_title = "Month" if chart_type == 'monthly' else "Week"

    if y_title is None:
        if chart_type == 'index':
            y_title = "Index"
        elif chart_type == 'monthly':
            y_title = "Value"
        else:
            y_title = "TR (%)"

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        xaxis=x_axis_config,
        yaxis=y_axis_config,
        hovermode='x unified',
        height=height,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=50)
    )

    return fig
