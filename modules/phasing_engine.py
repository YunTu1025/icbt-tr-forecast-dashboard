"""
Phasing Engine - Calculate monthly phasing percentages for incomplete month extrapolation
"""
import pandas as pd
import numpy as np
from datetime import datetime


def calculate_phasing_table(data, metric_column, year_col='YEAR_ID', month_col='MONTH_OF_YEAR_ID', day_col='DAY_OF_MONTH_ID'):
    """
    Calculate phasing table showing cumulative % contribution by day of month

    Args:
        data: DataFrame with daily fee data
        metric_column: Column name for the metric to calculate phasing (e.g., 'IF_N_USD_PLAN')
        year_col: Year column name
        month_col: Month column name
        day_col: Day of month column name

    Returns:
        DataFrame with DAY_OF_MONTH_ID as rows, months as columns, values as cumulative %
    """
    # Filter to valid data
    df = data[[year_col, month_col, day_col, metric_column]].copy()
    df = df[df[metric_column].notna()].copy()

    # Convert to int to handle both string and int types from different data sources
    df[year_col] = df[year_col].astype(int)
    df[month_col] = df[month_col].astype(int)
    df[day_col] = df[day_col].astype(int)

    # Create year-month identifier
    df['YEAR_MONTH'] = df[year_col].astype(str) + '-' + df[month_col].astype(str).str.zfill(2)

    # Group by year-month-day and sum the metric
    daily_sum = df.groupby(['YEAR_MONTH', year_col, month_col, day_col])[metric_column].sum().reset_index()

    # Calculate monthly totals
    monthly_total = daily_sum.groupby('YEAR_MONTH')[metric_column].sum().reset_index()
    monthly_total.columns = ['YEAR_MONTH', 'MONTH_TOTAL']

    # Merge monthly totals back
    daily_sum = daily_sum.merge(monthly_total, on='YEAR_MONTH', how='left')

    # Sort by year-month and day
    daily_sum = daily_sum.sort_values(['YEAR_MONTH', day_col])

    # Calculate cumulative sum within each month
    daily_sum['CUMULATIVE_SUM'] = daily_sum.groupby('YEAR_MONTH')[metric_column].cumsum()

    # Calculate cumulative percentage
    daily_sum['CUMULATIVE_PCT'] = (daily_sum['CUMULATIVE_SUM'] / daily_sum['MONTH_TOTAL']) * 100
    daily_sum['CUMULATIVE_PCT'] = daily_sum['CUMULATIVE_PCT'].fillna(0)

    # Pivot to create the phasing table
    phasing_table = daily_sum.pivot(
        index=day_col,
        columns='YEAR_MONTH',
        values='CUMULATIVE_PCT'
    )

    # Ensure all days 1-31 are present
    all_days = pd.DataFrame({day_col: range(1, 32)})
    phasing_table = phasing_table.reset_index()
    phasing_table = all_days.merge(phasing_table, on=day_col, how='left')
    phasing_table = phasing_table.set_index(day_col)

    # Forward fill missing values (e.g., day 31 for Feb)
    phasing_table = phasing_table.ffill(axis=0)

    # Fill remaining NaN with 100% (end of month)
    phasing_table = phasing_table.fillna(100.0)

    return phasing_table


def get_trailing_12_months(data, year_col='YEAR_ID', month_col='MONTH_OF_YEAR_ID', exclude_current=True):
    """
    Get the trailing 12 complete months from the data

    Args:
        data: DataFrame with year and month columns
        year_col: Year column name
        month_col: Month column name
        exclude_current: If True, exclude the current incomplete month

    Returns:
        List of year-month strings in format 'YYYY-MM'
    """
    # Get current date
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month

    # Get all unique year-months from data
    year_months = data[[year_col, month_col]].drop_duplicates()
    # Convert to int to handle both string and int types from different data sources
    year_months[year_col] = year_months[year_col].astype(int)
    year_months[month_col] = year_months[month_col].astype(int)
    year_months['YEAR_MONTH'] = year_months[year_col].astype(str) + '-' + year_months[month_col].astype(str).str.zfill(2)
    year_months['SORT_KEY'] = year_months[year_col] * 100 + year_months[month_col]
    year_months = year_months.sort_values('SORT_KEY', ascending=False)

    # Exclude current month if requested
    if exclude_current:
        current_sort_key = current_year * 100 + current_month
        year_months = year_months[year_months['SORT_KEY'] < current_sort_key]

    # Get trailing 12 months
    trailing_12 = year_months.head(12)['YEAR_MONTH'].tolist()

    return trailing_12


def get_phasing_table_for_display(data, metric_column, num_months=12, selected_months=None):
    """
    Get phasing table formatted for display with trailing N months and baseline column

    Args:
        data: DataFrame with daily fee data
        metric_column: Column name for the metric
        num_months: Number of trailing months to display (default 12)
        selected_months: List of selected month strings (e.g., ['2026-03', '2026-02']) for baseline calculation

    Returns:
        DataFrame ready for Streamlit display
    """
    # Calculate full phasing table
    phasing_table = calculate_phasing_table(data, metric_column)

    # Get trailing months
    trailing_months = get_trailing_12_months(data, exclude_current=True)

    # Filter to trailing months
    available_cols = [col for col in trailing_months if col in phasing_table.columns]
    phasing_table_filtered = phasing_table[available_cols[:num_months]].copy()

    # Calculate Baseline column (average of selected months)
    if selected_months and len(selected_months) > 0:
        # Filter to only selected months that exist in the table
        valid_selected = [m for m in selected_months if m in phasing_table_filtered.columns]

        if valid_selected:
            # Calculate mean across selected months
            phasing_table_filtered.insert(0, 'Baseline', phasing_table_filtered[valid_selected].mean(axis=1))
        else:
            # No valid selections, create empty baseline
            phasing_table_filtered.insert(0, 'Baseline', np.nan)
    else:
        # No selections, create empty baseline
        phasing_table_filtered.insert(0, 'Baseline', np.nan)

    # Sort month columns in descending order (most recent first), but keep Baseline first
    month_cols = [col for col in phasing_table_filtered.columns if col != 'Baseline']
    sorted_month_cols = sorted(month_cols, reverse=True)
    phasing_table_filtered = phasing_table_filtered[['Baseline'] + sorted_month_cols]

    # Format display
    phasing_table_display = phasing_table_filtered.copy()

    # Round to 2 decimal places and add % sign
    for col in phasing_table_display.columns:
        phasing_table_display[col] = phasing_table_display[col].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else ""
        )

    return phasing_table_display


def apply_phasing_to_incomplete_month(actual_value, day_of_month, phasing_pct):
    """
    Extrapolate incomplete month value to full month using phasing

    Args:
        actual_value: Actual value accumulated so far in the month
        day_of_month: Current day of the month
        phasing_pct: Phasing percentage for that day (e.g., 48.5 means 48.5%)

    Returns:
        Extrapolated full month value
    """
    if phasing_pct == 0 or phasing_pct is None:
        return actual_value

    full_month_estimate = actual_value / (phasing_pct / 100.0)
    return full_month_estimate
