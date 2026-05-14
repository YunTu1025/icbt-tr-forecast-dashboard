"""
IF/FF/Store Forecast Engine - Core calculation logic for Tab 3 forecasts
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def build_monthly_data_table(
    data,
    metric_column,
    region_filter=None,
    current_date=None,
    baseline_phasing_table=None,
    budget_df=None,
    prior_forecast_df=None,
    region=None,
    fee_type=None,
    year_col='YEAR_ID',
    month_col='MONTH_OF_YEAR_ID'
):
    """
    Build monthly data table with actual and adjusted values

    Args:
        data: Source DataFrame (IF/FF/Store data)
        metric_column: Column to aggregate (e.g., 'IF_N_USD_PLAN')
        region_filter: Dictionary with filter conditions (e.g., {'slr_cntry_2': 'CN'})
        current_date: Current date for adjustment calculations
        baseline_phasing_table: Phasing table (raw values, not formatted) with 'Baseline' column
        budget_df: Optional Budget DataFrame from uploaded CSV
        prior_forecast_df: Optional Prior Forecast DataFrame from uploaded CSV
        region: Region name (e.g., 'ICBT', 'GC', 'HIS', 'JPKO')
        fee_type: Fee type name (e.g., 'IF', 'FF', 'Store')
        year_col: Year column name
        month_col: Month column name

    Returns:
        DataFrame with MONTH_OF_YEAR_ID as rows, years as columns, plus forecast columns
    """
    # Filter data by region if specified
    df = data.copy()
    if region_filter:
        for col, values in region_filter.items():
            if isinstance(values, list):
                df = df[df[col].isin(values)]
            else:
                df = df[df[col] == values]

    # Aggregate by year and month
    monthly_agg = df.groupby([year_col, month_col])[metric_column].sum().reset_index()

    # Pivot to get years as columns
    monthly_pivot = monthly_agg.pivot(
        index=month_col,
        columns=year_col,
        values=metric_column
    )

    # Ensure all months 1-12 are present
    all_months = pd.DataFrame({month_col: range(1, 13)})
    monthly_pivot = monthly_pivot.reset_index()
    monthly_pivot = all_months.merge(monthly_pivot, on=month_col, how='left')
    monthly_pivot = monthly_pivot.set_index(month_col)

    # Ensure columns for years 2022-2026
    for year in [2022, 2023, 2024, 2025, 2026]:
        if year not in monthly_pivot.columns:
            monthly_pivot[year] = np.nan

    # Sort columns
    monthly_pivot = monthly_pivot[[2022, 2023, 2024, 2025, 2026]]

    # Add 2026 Adjusted column
    monthly_pivot['2026 Adjusted'] = np.nan

    if current_date is not None and baseline_phasing_table is not None:
        current_month = current_date.month
        current_day = current_date.day

        # Get baseline phasing value for current day
        if current_day in baseline_phasing_table.index and 'Baseline' in baseline_phasing_table.columns:
            baseline_phasing_pct = baseline_phasing_table.loc[current_day, 'Baseline']

            # Only process if baseline is valid
            if pd.notna(baseline_phasing_pct) and baseline_phasing_pct > 0:
                # For months < current month: 2026 Adjusted = 2026 actual
                for month in range(1, current_month):
                    if pd.notna(monthly_pivot.loc[month, 2026]):
                        monthly_pivot.loc[month, '2026 Adjusted'] = monthly_pivot.loc[month, 2026]

                # For month = current month: 2026 Adjusted = 2026 actual / baseline phasing
                if pd.notna(monthly_pivot.loc[current_month, 2026]):
                    actual_2026 = monthly_pivot.loc[current_month, 2026]
                    adjusted_2026 = actual_2026 / (baseline_phasing_pct / 100.0)
                    monthly_pivot.loc[current_month, '2026 Adjusted'] = adjusted_2026

    # Add 4 additional forecast columns
    monthly_pivot['2026 Index Baseline'] = np.nan
    monthly_pivot['2026 Machine Learning'] = np.nan
    monthly_pivot['2026 Budget'] = np.nan
    monthly_pivot['2026 Prior Forecast'] = np.nan

    # Map prior forecast data if provided
    if prior_forecast_df is not None and region is not None and fee_type is not None:
        # Column name format: Region_FeeType (e.g., 'ICBT_IF', 'GC_FF', 'HIS_Store')
        prior_forecast_column = f"{region}_{fee_type}"

        if prior_forecast_column in prior_forecast_df.columns:
            # Check if Month or MONTH_OF_YEAR_ID column exists
            month_col_name = None
            if 'Month' in prior_forecast_df.columns:
                month_col_name = 'Month'
            elif 'MONTH_OF_YEAR_ID' in prior_forecast_df.columns:
                month_col_name = 'MONTH_OF_YEAR_ID'

            if month_col_name:
                # Map prior forecast values by month
                for month in range(1, 13):
                    # Find matching row in prior_forecast_df
                    matching_rows = prior_forecast_df[prior_forecast_df[month_col_name] == month]
                    if not matching_rows.empty:
                        prior_value = matching_rows.iloc[0][prior_forecast_column]
                        if pd.notna(prior_value):
                            monthly_pivot.loc[month, '2026 Prior Forecast'] = prior_value

    # Map budget data if provided
    if budget_df is not None and region is not None and fee_type is not None:
        # Column name format: Region_FeeType (e.g., 'ICBT_IF', 'GC_FF', 'HIS_Store')
        budget_column = f"{region}_{fee_type}"

        if budget_column in budget_df.columns:
            # Check if Month or MONTH_OF_YEAR_ID column exists
            month_col_name = None
            if 'Month' in budget_df.columns:
                month_col_name = 'Month'
            elif 'MONTH_OF_YEAR_ID' in budget_df.columns:
                month_col_name = 'MONTH_OF_YEAR_ID'

            if month_col_name:
                # Map budget values by month
                for month in range(1, 13):
                    # Find matching row in budget_df
                    matching_rows = budget_df[budget_df[month_col_name] == month]
                    if not matching_rows.empty:
                        budget_value = matching_rows.iloc[0][budget_column]
                        if pd.notna(budget_value):
                            monthly_pivot.loc[month, '2026 Budget'] = budget_value

    return monthly_pivot


def calculate_monthly_baseline_row(df_monthly, index_months):
    """
    Calculate baseline/index row from monthly data table

    Args:
        df_monthly: Monthly DataFrame with months as rows, years as columns
        index_months: List of month numbers to use for baseline (e.g., [1, 2, 3] for Jan-Mar)

    Returns:
        Dictionary representing the baseline row
    """
    baseline_row = {}
    baseline_row['MONTH_OF_YEAR_ID'] = 'Index/Baseline'

    # Calculate average for each year column
    for year in [2022, 2023, 2024, 2025, 2026]:
        if year in df_monthly.columns:
            values = df_monthly.loc[df_monthly.index.isin(index_months), year].dropna()
            if len(values) > 0:
                baseline_row[year] = values.mean()
            else:
                baseline_row[year] = np.nan
        else:
            baseline_row[year] = np.nan

    # Calculate baseline for 2026 Adjusted column
    if '2026 Adjusted' in df_monthly.columns:
        values = df_monthly.loc[df_monthly.index.isin(index_months), '2026 Adjusted'].dropna()
        if len(values) > 0:
            baseline_row['2026 Adjusted'] = values.mean()
        else:
            baseline_row['2026 Adjusted'] = np.nan
    else:
        baseline_row['2026 Adjusted'] = np.nan

    # Initialize other forecast columns
    baseline_row['2026 Index Baseline'] = np.nan
    baseline_row['2026 Machine Learning'] = np.nan

    # Calculate baseline for 2026 Budget and 2026 Prior Forecast if they exist
    for col in ['2026 Budget', '2026 Prior Forecast']:
        if col in df_monthly.columns:
            values = df_monthly.loc[df_monthly.index.isin(index_months), col].dropna()
            if len(values) > 0:
                baseline_row[col] = values.mean()
            else:
                baseline_row[col] = np.nan
        else:
            baseline_row[col] = np.nan

    return baseline_row


def format_monthly_data_for_display(monthly_data, format_type='number'):
    """
    Format monthly data table for Streamlit display

    Args:
        monthly_data: DataFrame from build_monthly_data_table
        format_type: 'number' for values with thousand separators, 'percentage' for percentages

    Returns:
        Formatted DataFrame
    """
    display_df = monthly_data.copy()

    if format_type == 'percentage':
        # Format as percentage
        for col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.2f}%" if pd.notna(x) else ""
            )
    else:
        # Format as number with thousand separators, no decimals
        for col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else ""
            )

    return display_df


# Region filter configurations
REGION_FILTERS = {
    'ICBT': None,  # No filter = all data
    'GC': {
        'slr_cntry_2': 'GC'
    },
    'HIS': {
        'slr_cntry_2': ['HIPO', 'INSEA']
    },
    'JPKO': {
        'slr_cntry_2': 'JPKO'
    }
}


def create_monthly_data_chart(df_monthly, fee_display_name):
    """
    Create Plotly chart for monthly data

    Args:
        df_monthly: Monthly DataFrame with months as index (including baseline row)
        fee_display_name: Display name for the fee type (e.g., 'IF (Insertion Fee)')

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Columns to plot
    columns_to_plot = [2022, 2023, 2024, 2025, '2026 Adjusted', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']
    colors = ['#4472C4', '#ED7D31', '#70AD47', '#FFC000', '#000000', '#FF0000', '#B19CD9', '#A5A5A5', '#000000']

    # Exclude baseline row for chart
    df_chart = df_monthly[df_monthly.index != 'Index/Baseline'].copy()

    # Get month labels (1-12)
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    for i, col in enumerate(columns_to_plot):
        if col in df_chart.columns:
            y_values = df_chart[col].values
            mask = pd.notna(y_values)
            x_indices = df_chart.index.values[mask]
            y_values_filtered = y_values[mask]

            if len(y_values_filtered) > 0:
                # Map month numbers to labels
                x_labels = [month_labels[idx - 1] for idx in x_indices if isinstance(idx, (int, np.integer)) and 1 <= idx <= 12]

                line_style = dict(
                    color=colors[i],
                    width=2.5 if col in ['2026 Adjusted', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast'] else 2,
                    shape='spline',
                    smoothing=0.3
                )

                # Dotted lines for forecast columns
                if col in ['2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']:
                    line_style['dash'] = 'dot'

                fig.add_trace(go.Scatter(
                    x=x_labels,
                    y=y_values_filtered,
                    mode='lines',
                    name=str(col),
                    line=line_style,
                    hovertemplate=f'{col}<br>%{{y:,.0f}}<extra></extra>'
                ))

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title=f"{fee_display_name}",
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=month_labels
        ),
        yaxis=dict(
            tickformat=',.0f',  # Thousand separators, no decimals
            separatethousands=True
        ),
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=50)
    )

    return fig
