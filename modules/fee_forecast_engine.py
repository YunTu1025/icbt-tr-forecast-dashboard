"""
Fee Forecast Engine - Reusable components for generating fee forecast sections
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# Fee Type Configurations
FEE_TYPE_CONFIG = {
    'Variable': {
        'display_name': 'Variable',
        'columns': ['CAL_P2_VAR_FEE_UP_DAILY', 'FVF_BASE_G_USD_PLAN', 'ETRS_CREDIT_USD_PLAN'],
        'tr_name': 'Variable TR',
        'calculation_type': 'year_dependent_subtract',
        'historical_col': 'CAL_P2_VAR_FEE_UP_DAILY',
        'future_col_1': 'FVF_BASE_G_USD_PLAN',
        'future_col_2': 'ETRS_CREDIT_USD_PLAN',  # Will be subtracted
    },
    'International': {
        'display_name': 'International',
        'columns': ['CAL_P2_CBT_FEE_UP_DAILY', 'CBT_FEE_G_USD_PLAN'],
        'tr_name': 'International TR',
        'calculation_type': 'year_dependent',
        'historical_col': 'CAL_P2_CBT_FEE_UP_DAILY',
        'future_col': 'CBT_FEE_G_USD_PLAN',
    },
    'BSTD': {
        'display_name': 'BSTD',
        'columns': ['CAL_BSTD_G_USD_PLAN_DAILY', 'FVF_BSTD_G_USD_PLAN'],
        'tr_name': 'BSTD TR',
        'calculation_type': 'year_dependent',
        'historical_col': 'CAL_BSTD_G_USD_PLAN_DAILY',
        'future_col': 'FVF_BSTD_G_USD_PLAN',
    },
    'eTRS': {
        'display_name': 'eTRS',
        'columns': ['ETRS_CREDIT_USD_PLAN'],
        'tr_name': 'eTRS TR',
        'calculation_type': 'simple',
        'value_col': 'ETRS_CREDIT_USD_PLAN',
    },
    'SNAD': {
        'display_name': 'SNAD',
        'columns': ['FVF_SNAD_G_USD_PLAN', 'FVF_SNAD_C_USD_PLAN'],
        'tr_name': 'SNAD TR',
        'calculation_type': 'sum',
        'value_col_1': 'FVF_SNAD_G_USD_PLAN',
        'value_col_2': 'FVF_SNAD_C_USD_PLAN',
    },
    'Fixed': {
        'display_name': 'Fixed',
        'columns': ['CAL_P2_FIXED_FEE_UP_DAILY', 'FIXED_FEE_G_USD_PLAN'],
        'tr_name': 'Fixed TR',
        'calculation_type': 'year_dependent',
        'historical_col': 'CAL_P2_FIXED_FEE_UP_DAILY',
        'future_col': 'FIXED_FEE_G_USD_PLAN',
    },
    'Credit': {
        'display_name': 'Credit',
        'columns': [
            'CAL_P2_VAR_CREDIT_UP_DAILY',
            'CAL_P2_CBT_CREDIT_UP_DAILY',
            'CAL_BSTD_C_USD_PLAN_DAILY',
            'CAL_P2_FIXED_CREDIT_UP_DAILY',
            'FVF_BASE_C_USD_PLAN',
            'CBT_FEE_C_USD_PLAN',
            'FVF_BSTD_C_USD_PLAN',
            'FIXED_FEE_C_USD_PLAN'
        ],
        'tr_name': 'Credit TR',
        'calculation_type': 'year_dependent_multi_sum',
        'historical_cols': [
            'CAL_P2_VAR_CREDIT_UP_DAILY',
            'CAL_P2_CBT_CREDIT_UP_DAILY',
            'CAL_BSTD_C_USD_PLAN_DAILY',
            'CAL_P2_FIXED_CREDIT_UP_DAILY'
        ],
        'future_cols': [
            'FVF_BASE_C_USD_PLAN',
            'CBT_FEE_C_USD_PLAN',
            'FVF_BSTD_C_USD_PLAN',
            'FIXED_FEE_C_USD_PLAN'
        ],
    },
    'Regulatory': {
        'display_name': 'Regulatory',
        'columns': ['FVF_REGULATORY_G_USD_PLAN', 'FVF_REGULATORY_C_USD_PLAN'],
        'tr_name': 'Regulatory TR',
        'calculation_type': 'sum',
        'value_col_1': 'FVF_REGULATORY_G_USD_PLAN',
        'value_col_2': 'FVF_REGULATORY_C_USD_PLAN',
    },
    'Buyer Protection': {
        'display_name': 'Buyer Protection',
        'columns': ['FVF_BuyerProtect_G_USD_PLAN', 'FVF_BuyerProtect_C_USD_PLAN'],
        'tr_name': 'Buyer Protection TR',
        'calculation_type': 'sum',
        'value_col_1': 'FVF_BuyerProtect_G_USD_PLAN',
        'value_col_2': 'FVF_BuyerProtect_C_USD_PLAN',
    },
}


def calculate_tr(row, config, gmv_col='GMV_PLAN_PAID'):
    """
    Calculate Take Rate based on fee type configuration

    Args:
        row: DataFrame row
        config: Fee type configuration dictionary
        gmv_col: GMV column name

    Returns:
        Calculated TR value or None
    """
    if row[gmv_col] == 0:
        return None

    calc_type = config['calculation_type']

    if calc_type == 'simple':
        # eTRS: same formula for all years
        return row[config['value_col']] / row[gmv_col]

    elif calc_type == 'sum':
        # SNAD: sum of two columns for all years
        return (row[config['value_col_1']] + row[config['value_col_2']]) / row[gmv_col]

    elif calc_type == 'year_dependent':
        # BSTD, International, Fixed: different columns for historical vs 2026
        if row['RETAIL_YEAR'] in [2022, 2023, 2024, 2025]:
            return row[config['historical_col']] / row[gmv_col]
        else:  # 2026
            return row[config['future_col']] / row[gmv_col]

    elif calc_type == 'year_dependent_subtract':
        # Variable: subtract ETRS from FVF for 2026
        if row['RETAIL_YEAR'] in [2022, 2023, 2024, 2025]:
            return row[config['historical_col']] / row[gmv_col]
        else:  # 2026
            return (row[config['future_col_1']] - row[config['future_col_2']]) / row[gmv_col]

    elif calc_type == 'year_dependent_multi_sum':
        # Credit: sum of multiple columns for historical vs 2026
        if row['RETAIL_YEAR'] in [2022, 2023, 2024, 2025]:
            return sum(row[col] for col in config['historical_cols']) / row[gmv_col]
        else:  # 2026
            return sum(row[col] for col in config['future_cols']) / row[gmv_col]

    return None


def get_tr_value_from_raw(value_row, config, year):
    """
    Recalculate TR from raw column values for a specific year

    Args:
        value_row: DataFrame row with raw values
        config: Fee type configuration
        year: Year to calculate for

    Returns:
        TR value or None
    """
    gmv_val = value_row.iloc[0]['GMV_PLAN_PAID']
    if gmv_val == 0:
        return None

    calc_type = config['calculation_type']

    if calc_type == 'simple':
        val = value_row.iloc[0][config['value_col']]
        return val / gmv_val

    elif calc_type == 'sum':
        val1 = value_row.iloc[0][config['value_col_1']]
        val2 = value_row.iloc[0][config['value_col_2']]
        return (val1 + val2) / gmv_val

    elif calc_type == 'year_dependent':
        if year in [2022, 2023, 2024, 2025]:
            val = value_row.iloc[0][config['historical_col']]
        else:
            val = value_row.iloc[0][config['future_col']]
        return val / gmv_val

    elif calc_type == 'year_dependent_subtract':
        if year in [2022, 2023, 2024, 2025]:
            val = value_row.iloc[0][config['historical_col']]
        else:
            val1 = value_row.iloc[0][config['future_col_1']]
            val2 = value_row.iloc[0][config['future_col_2']]
            val = val1 - val2
        return val / gmv_val

    elif calc_type == 'year_dependent_multi_sum':
        if year in [2022, 2023, 2024, 2025]:
            val = sum(value_row.iloc[0][col] for col in config['historical_cols'])
        else:
            val = sum(value_row.iloc[0][col] for col in config['future_cols'])
        return val / gmv_val

    return None


def load_and_aggregate_data(fvf_data, config, fee_type):
    """
    Load and aggregate fee data from the main FVF dataset

    Args:
        fvf_data: Main FVF DataFrame
        config: Fee type configuration
        fee_type: Fee type name (for error messages)

    Returns:
        Tuple of (df_agg, error_message) where error_message is None if successful
    """
    # Check required columns exist
    required_cols = ['RETAIL_YEAR', 'RETAIL_WEEK', 'GMV_PLAN_PAID'] + config['columns']

    # Get column names (case insensitive check)
    available_cols = fvf_data.columns.tolist()
    col_map = {}

    for req_col in required_cols:
        found = False
        for avail_col in available_cols:
            if req_col.upper() == avail_col.upper():
                col_map[req_col] = avail_col
                found = True
                break
        if not found:
            return None, f"Column '{req_col}' not found in data"

    # Filter and select columns
    selected_cols = [col_map[col] for col in required_cols]
    df = fvf_data[selected_cols].copy()

    # Rename columns to standard names
    df.columns = required_cols

    # Filter for years 2022-2026
    df = df[df['RETAIL_YEAR'].isin([2022, 2023, 2024, 2025, 2026])]

    # Build aggregation dictionary
    agg_dict = {'GMV_PLAN_PAID': 'sum'}
    for col in config['columns']:
        agg_dict[col] = 'sum'

    # Group by RETAIL_YEAR and RETAIL_WEEK and sum
    df_agg = df.groupby(['RETAIL_YEAR', 'RETAIL_WEEK']).agg(agg_dict).reset_index()

    # Calculate TR
    df_agg[config['tr_name']] = df_agg.apply(lambda row: calculate_tr(row, config), axis=1)

    # Sort by year and week
    df_agg = df_agg.sort_values(['RETAIL_YEAR', 'RETAIL_WEEK'])

    return df_agg, None


def format_raw_data_for_display(df_agg, config):
    """
    Format aggregated data for display in Raw Data Preview

    Args:
        df_agg: Aggregated DataFrame
        config: Fee type configuration

    Returns:
        Formatted DataFrame for display
    """
    df_display = df_agg.copy()
    df_display = df_display.reset_index(drop=True)
    df_display.index = df_display.index + 1

    # Format numeric columns with thousand separators
    for col in ['GMV_PLAN_PAID'] + config['columns']:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(
                lambda x: f"{x:,.0f}" if pd.notna(x) else ""
            )

    # Format TR as percentage with 2 decimals
    if config['tr_name'] in df_display.columns:
        df_display[config['tr_name']] = df_display[config['tr_name']].apply(
            lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
        )

    return df_display


def build_forecast_table(df_agg, config, week_date_map, budget_df=None, prior_forecast_df=None):
    """
    Build forecast table with week mapping for all years

    Args:
        df_agg: Aggregated DataFrame with raw data
        config: Fee type configuration
        week_date_map: Dictionary mapping week numbers to dates
        budget_df: Optional Budget DataFrame from uploaded CSV
        prior_forecast_df: Optional Prior Forecast DataFrame from uploaded CSV

    Returns:
        DataFrame with forecast data for weeks 1-52
    """
    forecast_table = []

    for week_num in range(1, 53):
        row_data = {
            'Week': week_num,
            'Date': week_date_map.get(week_num, 'N/A')
        }

        # For each year, map to the correct retail week
        for year in [2022, 2023, 2024, 2025, 2026]:
            if year in [2022, 2023, 2024]:
                # For 2022-2024: week 2-52 maps to 1-51, week 1 of next year maps to 52
                if week_num <= 51:
                    retail_week = week_num + 1
                    retail_year = year
                else:  # week 52
                    retail_week = 1
                    retail_year = year + 1
            elif year == 2025:
                # For 2025: retail_week 2-53 maps to week_num 1-52
                retail_week = week_num + 1
                retail_year = year
            else:  # 2026
                # Direct match
                retail_week = week_num
                retail_year = year

            # Get the value from the original aggregated data
            value_row = df_agg[
                (df_agg['RETAIL_YEAR'] == retail_year) &
                (df_agg['RETAIL_WEEK'] == retail_week)
            ]

            if not value_row.empty:
                row_data[str(year)] = get_tr_value_from_raw(value_row, config, retail_year)
            else:
                row_data[str(year)] = None

        # 2026 Index Baseline and Machine Learning columns (placeholders)
        row_data['2026 Index Baseline'] = None
        row_data['2026 Machine Learning'] = None

        # Add 2026 Budget column from uploaded Budget CSV
        row_data['2026 Budget'] = None
        if budget_df is not None and not budget_df.empty:
            # Try to find matching column (case-insensitive search for fee type TR name)
            tr_col_name = config.get('tr_name', '')
            matching_col = None
            for col in budget_df.columns:
                if tr_col_name.lower() in col.lower() or col.lower() in tr_col_name.lower():
                    matching_col = col
                    break

            if matching_col:
                # Find row with matching week
                budget_row = budget_df[budget_df['Week'] == week_num]
                if not budget_row.empty:
                    row_data['2026 Budget'] = budget_row.iloc[0][matching_col]

        # Add 2026 Prior Forecast column from uploaded Prior Forecast CSV
        row_data['2026 Prior Forecast'] = None
        if prior_forecast_df is not None and not prior_forecast_df.empty:
            # Try to find matching column (case-insensitive search for fee type TR name)
            tr_col_name = config.get('tr_name', '')
            matching_col = None
            for col in prior_forecast_df.columns:
                if tr_col_name.lower() in col.lower() or col.lower() in tr_col_name.lower():
                    matching_col = col
                    break

            if matching_col:
                # Find row with matching week
                prior_row = prior_forecast_df[prior_forecast_df['Week'] == week_num]
                if not prior_row.empty:
                    row_data['2026 Prior Forecast'] = prior_row.iloc[0][matching_col]

        forecast_table.append(row_data)

    return pd.DataFrame(forecast_table)


def calculate_baseline_row(df_forecast, index_weeks):
    """
    Calculate baseline/index row from forecast table

    Args:
        df_forecast: Forecast DataFrame
        index_weeks: List of week numbers to use for baseline

    Returns:
        Dictionary representing the baseline row
    """
    baseline_row = {
        'Week': 'Index/Baseline',
        'Date': f"Weeks {min(index_weeks)}-{max(index_weeks)}"
    }

    for year in ['2022', '2023', '2024', '2025', '2026']:
        values = df_forecast[df_forecast['Week'].isin(index_weeks)][year].dropna()
        if len(values) > 0:
            baseline_row[year] = values.mean()
        else:
            baseline_row[year] = None

    baseline_row['2026 Index Baseline'] = None
    baseline_row['2026 Machine Learning'] = None

    # Calculate baseline for 2026 Budget and 2026 Prior Forecast
    for col in ['2026 Budget', '2026 Prior Forecast']:
        if col in df_forecast.columns:
            values = df_forecast[df_forecast['Week'].isin(index_weeks)][col].dropna()
            if len(values) > 0:
                baseline_row[col] = values.mean()
            else:
                baseline_row[col] = None
        else:
            baseline_row[col] = None

    return baseline_row


def build_index_table(df_forecast, active_weights, week_date_map):
    """
    Build index table with index values and weighted 2026 baseline

    Args:
        df_forecast: Forecast DataFrame with baseline row at top
        active_weights: Dictionary of year weights {2022: weight, ...}
        week_date_map: Dictionary mapping week numbers to dates

    Returns:
        DataFrame with index values
    """
    # Get baseline values from forecast table (row 0)
    baseline_values = {}
    for year in ['2022', '2023', '2024', '2025', '2026']:
        baseline_values[year] = df_forecast.iloc[0][year]

    # Get baseline values for Budget and Prior Forecast
    for col in ['2026 Budget', '2026 Prior Forecast']:
        if col in df_forecast.columns:
            baseline_values[col] = df_forecast.iloc[0][col]

    index_table = []

    # Row 0: Year weights
    weights_row = {
        'Week': 'Year Weights',
        'Date': 'Weight %',
        '2022': active_weights[2022],
        '2023': active_weights[2023],
        '2024': active_weights[2024],
        '2025': active_weights[2025],
        '2026': None,
        '2026 Index Baseline': None,
        '2026 Machine Learning': None,
        '2026 Budget': None,
        '2026 Prior Forecast': None
    }
    index_table.append(weights_row)

    # Rows 1-52: Index values
    for week_num in range(1, 53):
        row_data = {
            'Week': week_num,
            'Date': week_date_map.get(week_num, 'N/A')
        }

        # For each year, calculate index = (value / baseline) * 100
        for year in ['2022', '2023', '2024', '2025', '2026']:
            week_row = df_forecast[df_forecast['Week'] == week_num]
            if not week_row.empty:
                value = week_row.iloc[0][year]
                baseline = baseline_values[year]

                if pd.notna(value) and pd.notna(baseline) and baseline != 0:
                    row_data[year] = (value / baseline) * 100
                else:
                    row_data[year] = None
            else:
                row_data[year] = None

        # Calculate 2026 Index Baseline = weighted average
        weighted_sum = 0
        total_weight = 0
        for year in [2022, 2023, 2024, 2025]:
            year_str = str(year)
            if pd.notna(row_data.get(year_str)):
                weight = active_weights[year]
                weighted_sum += row_data[year_str] * weight
                total_weight += weight

        if total_weight > 0:
            row_data['2026 Index Baseline'] = weighted_sum / total_weight
        else:
            row_data['2026 Index Baseline'] = None

        row_data['2026 Machine Learning'] = None

        # Calculate index for 2026 Budget and 2026 Prior Forecast
        for col in ['2026 Budget', '2026 Prior Forecast']:
            if col in df_forecast.columns:
                week_row = df_forecast[df_forecast['Week'] == week_num]
                if not week_row.empty:
                    value = week_row.iloc[0][col]
                    baseline = baseline_values.get(col)

                    if pd.notna(value) and pd.notna(baseline) and baseline != 0:
                        row_data[col] = (value / baseline) * 100
                    else:
                        row_data[col] = None
                else:
                    row_data[col] = None
            else:
                row_data[col] = None

        index_table.append(row_data)

    return pd.DataFrame(index_table)


def update_forecast_2026_baseline(df_forecast, df_index, baseline_2026):
    """
    Update 2026 Index Baseline values in forecast table

    Args:
        df_forecast: Forecast DataFrame (modified in place)
        df_index: Index DataFrame
        baseline_2026: 2026 baseline value
    """
    for i in range(1, len(df_forecast)):  # Skip row 0 (baseline)
        week_num = df_forecast.iloc[i]['Week']
        value_2026 = df_forecast.iloc[i]['2026']

        if pd.notna(value_2026):
            df_forecast.at[i, '2026 Index Baseline'] = None
        else:
            index_row = df_index[df_index['Week'] == week_num]
            if not index_row.empty:
                index_2026_baseline = index_row.iloc[0]['2026 Index Baseline']
                if pd.notna(index_2026_baseline) and pd.notna(baseline_2026):
                    df_forecast.at[i, '2026 Index Baseline'] = (index_2026_baseline * baseline_2026) / 100
                else:
                    df_forecast.at[i, '2026 Index Baseline'] = None
            else:
                df_forecast.at[i, '2026 Index Baseline'] = None


def update_forecast_ml_predictions(df_forecast, df_index, ml_predictions, baseline_2026):
    """
    Update 2026 Machine Learning values in forecast table and index table

    Args:
        df_forecast: Forecast DataFrame (modified in place)
        df_index: Index DataFrame (modified in place)
        ml_predictions: Dictionary mapping week number (1-52) to ML prediction (as decimal, e.g., 0.1234 for 12.34%)
        baseline_2026: 2026 baseline value for calculating index
    """
    if ml_predictions is None or not ml_predictions:
        return

    # Update forecast table (skip row 0 which is baseline row)
    for i in range(1, len(df_forecast)):
        week_num = df_forecast.iloc[i]['Week']
        if week_num in ml_predictions:
            df_forecast.at[i, '2026 Machine Learning'] = ml_predictions[week_num]

    # Calculate baseline for ML predictions (average of index weeks)
    ml_baseline_values = [ml_predictions[week] for week in ml_predictions if week in range(1, 53)]
    if ml_baseline_values:
        ml_baseline = sum(ml_baseline_values) / len(ml_baseline_values)
        # Update baseline row (row 0)
        df_forecast.at[0, '2026 Machine Learning'] = ml_baseline
    else:
        ml_baseline = None
        df_forecast.at[0, '2026 Machine Learning'] = None

    # Update index table (skip row 0 which is weights row)
    if df_index is not None and len(df_index) > 1:
        for i in range(1, len(df_index)):
            week_num = df_index.iloc[i]['Week']
            if week_num in ml_predictions and pd.notna(ml_baseline) and ml_baseline != 0:
                # Index = (value / baseline) * 100
                ml_value = ml_predictions[week_num]
                df_index.at[i, '2026 Machine Learning'] = (ml_value / ml_baseline) * 100
            else:
                df_index.at[i, '2026 Machine Learning'] = None

        # Update weights row (row 0) - set to None
        df_index.at[0, '2026 Machine Learning'] = None


def create_forecast_chart(df_forecast, fee_type_display):
    """
    Create Plotly forecast chart

    Args:
        df_forecast: Forecast DataFrame
        fee_type_display: Display name for the fee type

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    years_to_plot = ['2022', '2023', '2024', '2025', '2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']
    colors = ['#4472C4', '#ED7D31', '#70AD47', '#FFC000', '#000000', '#FF0000', '#B19CD9', '#A5A5A5', '#000000']

    df_chart = df_forecast[df_forecast['Week'] != 'Index/Baseline'].copy()

    for i, year in enumerate(years_to_plot):
        y_values = df_chart[year].values
        mask = pd.notna(y_values)
        x_values = df_chart['Week'].values[mask]
        y_values_filtered = y_values[mask]

        if len(y_values_filtered) > 0:
            line_style = dict(
                color=colors[i],
                width=2.5 if year in ['2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast'] else 2,
                shape='spline',
                smoothing=0.3
            )

            if year in ['2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']:
                line_style['dash'] = 'dot'

            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values_filtered * 100,
                mode='lines',
                name=year,
                line=line_style,
                hovertemplate=f'{year}<br>%{{y:.2f}}%<extra></extra>'
            ))

    fig.update_layout(
        xaxis_title="Week",
        yaxis_title=f"{fee_type_display} TR (%)",
        xaxis=dict(tickmode='linear', tick0=0, dtick=4),
        yaxis=dict(tickformat='.2f', ticksuffix='%'),
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=50)
    )

    return fig


def create_index_chart(df_index):
    """
    Create Plotly index chart

    Args:
        df_index: Index DataFrame

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    years_to_plot = ['2022', '2023', '2024', '2025', '2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']
    colors = ['#4472C4', '#ED7D31', '#70AD47', '#FFC000', '#000000', '#FF0000', '#B19CD9', '#A5A5A5', '#000000']

    df_chart = df_index[df_index['Week'] != 'Year Weights'].copy()

    for i, year in enumerate(years_to_plot):
        y_values = df_chart[year].values
        mask = pd.notna(y_values)
        x_values = df_chart['Week'].values[mask]
        y_values_filtered = y_values[mask]

        if len(y_values_filtered) > 0:
            line_style = dict(
                color=colors[i],
                width=2.5 if year in ['2026', '2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast'] else 2,
                shape='spline',
                smoothing=0.3
            )

            if year in ['2026 Index Baseline', '2026 Machine Learning', '2026 Budget', '2026 Prior Forecast']:
                line_style['dash'] = 'dot'

            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values_filtered,
                mode='lines',
                name=year,
                line=line_style,
                hovertemplate=f'{year}<br>%{{y:.1f}}<extra></extra>'
            ))

    fig.update_layout(
        xaxis_title="Week",
        yaxis_title="Index",
        xaxis=dict(tickmode='linear', tick0=0, dtick=4),
        yaxis=dict(tickformat='.1f'),
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=50)
    )

    return fig
