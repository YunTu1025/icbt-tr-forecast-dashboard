"""
TR Walk Engine - Forecast Version Comparison
Handles calculations for TR Walk analysis comparing different forecast versions
"""

import pandas as pd
import numpy as np
from datetime import datetime


def calculate_walk_metrics(df_from, df_to, start_date, end_date, buffer_stretch=0.0):
    """
    Calculate TR Walk metrics comparing two forecast versions

    Parameters:
    - df_from: DataFrame for 'Walk From' version
    - df_to: DataFrame for 'Walk To' version
    - start_date: Start date for the comparison period
    - end_date: End date for the comparison period
    - buffer_stretch: Adjustment value for waterfall chart

    Returns:
    - Dictionary containing calculated metrics for all walk tables
    """

    # Convert dates to datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filter data by date range
    if not df_from.empty and 'Date' in df_from.columns:
        df_from_copy = df_from.copy()
        df_from_copy['Date'] = pd.to_datetime(df_from_copy['Date'])
        df_from_filtered = df_from_copy[(df_from_copy['Date'] >= start_date) & (df_from_copy['Date'] <= end_date)]
    else:
        df_from_filtered = df_from.copy() if not df_from.empty else pd.DataFrame()

    if not df_to.empty and 'Date' in df_to.columns:
        df_to_copy = df_to.copy()
        df_to_copy['Date'] = pd.to_datetime(df_to_copy['Date'])
        df_to_filtered = df_to_copy[(df_to_copy['Date'] >= start_date) & (df_to_copy['Date'] <= end_date)]
    else:
        df_to_filtered = df_to.copy() if not df_to.empty else pd.DataFrame()

    # Calculate TXN TR Walk metrics (Dollar Amounts)
    txn_tr_walk = calculate_txn_tr_walk(df_from_filtered, df_to_filtered)

    # Calculate Take Rate % metrics
    take_rate_pct = calculate_take_rate_pct(txn_tr_walk)

    # Calculate waterfall bridge data
    waterfall_data = calculate_waterfall_bridge(take_rate_pct, buffer_stretch)

    # Calculate FVF TR Walk data
    fvf_walk_data = calculate_fvf_walk(df_from_filtered, df_to_filtered)

    return {
        'txn_tr_walk': txn_tr_walk,
        'take_rate_pct': take_rate_pct,
        'waterfall_data': waterfall_data,
        'fvf_walk_data': fvf_walk_data
    }


def calculate_txn_tr_walk(df_from, df_to):
    """
    Calculate TXN TR Walk metrics (Dollar Amounts)
    Returns a dictionary with metrics for Walk From and Walk To
    Metrics: GMV, FVF, IF, FF non-PL, Store
    """

    # Define revenue columns mapping - try both column name patterns
    revenue_columns = {
        'GMV': ['GMV', 'GMV_PLAN'],
        'FVF': ['Net FVF', 'FVF', 'FVF_N_USD_PLAN', 'TTL_FVF_N_USD_PLAN'],
        'IF': ['IF', 'IF_N_USD_PLAN'],
        'FF non-PL': ['FF', 'FF_non_PL', 'FF_N_USD_PLAN', 'FIXED_FEE_N_USD_PLAN'],
        'Store': ['Store', 'STORE_FEE_N_USD_PLAN']
    }

    metrics = {}

    for metric_name, col_candidates in revenue_columns.items():
        walk_from_value = 0
        walk_to_value = 0

        # Try to find matching column in df_from
        for col_name in col_candidates:
            if not df_from.empty and col_name in df_from.columns:
                walk_from_value = df_from[col_name].sum()
                break

        # Try to find matching column in df_to
        for col_name in col_candidates:
            if not df_to.empty and col_name in df_to.columns:
                walk_to_value = df_to[col_name].sum()
                break

        change_dollar = walk_to_value - walk_from_value
        change_pct = (change_dollar / walk_from_value * 100) if walk_from_value != 0 else 0

        metrics[metric_name] = {
            'Walk From': walk_from_value,
            'Walk To': walk_to_value,
            'Change ($)': change_dollar,
            'Change (%)': change_pct
        }

    return metrics


def calculate_take_rate_pct(txn_tr_walk):
    """
    Calculate Take Rate percentages from TXN TR Walk data
    Returns dictionary with take rate metrics
    """

    gmv_from = txn_tr_walk['GMV']['Walk From']
    gmv_to = txn_tr_walk['GMV']['Walk To']

    take_rates = {}

    # Calculate TR for each metric (excluding GMV)
    for metric_name, values in txn_tr_walk.items():
        if metric_name == 'GMV':
            continue

        tr_from = (values['Walk From'] / gmv_from * 100) if gmv_from != 0 else 0
        tr_to = (values['Walk To'] / gmv_to * 100) if gmv_to != 0 else 0
        change_bps = (tr_to - tr_from) * 100  # Convert to basis points

        take_rates[f"{metric_name} TR"] = {
            'Walk From (%)': tr_from,
            'Walk To (%)': tr_to,
            'Change (bps)': change_bps
        }

    return take_rates


def calculate_waterfall_bridge(take_rate_pct, buffer_stretch=0.0):
    """
    Calculate waterfall bridge from Submission to Realistic

    Parameters:
    - take_rate_pct: Take rate percentage metrics
    - buffer_stretch: Adjustment value (calculated or provided)
    """

    # Get Total TXN TR
    if 'Total TXN Rev TR' in take_rate_pct:
        submission = take_rate_pct['Total TXN Rev TR']['Walk From (%)'] / 100
        realistic_target = take_rate_pct['Total TXN Rev TR']['Walk To (%)'] / 100
    else:
        submission = 0
        realistic_target = 0

    realistic = submission + buffer_stretch

    # Calculate individual component contributions
    components = {}
    for metric_name, values in take_rate_pct.items():
        if metric_name == 'Total TXN Rev TR':
            continue

        contribution = values['Change (bps)'] / 10000  # Convert bps to percentage
        components[metric_name.replace(' TR', '')] = contribution

    waterfall_data = {
        'Submission': submission,
        'Adjustment': buffer_stretch,
        'Realistic': realistic,
        'Components': components
    }

    return waterfall_data


def calculate_fvf_walk(df_from, df_to):
    """
    Calculate detailed FVF TR Walk breakdown
    """

    # FVF component columns mapping - try display name first, then internal column name
    fvf_components = {
        'Variable': ['Variable', 'FVF_BASE_G_USD_PLAN'],
        'International': ['International', 'CBT_FEE_G_USD_PLAN'],
        'BSTD': ['BSTD', 'FVF_BSTD_G_USD_PLAN'],
        'eTRS': ['eTRS', 'ETRS_CREDIT_PLAN'],
        'SNAD': ['SNAD', 'FVF_SNAD_N_USD_PLAN'],
        'Fixed': ['Fixed', 'FIXED_FEE_G_USD_PLAN'],
        'Credit': ['Credit', 'CBT_FEE_C_USD_PLAN'],
        'Regulatory': ['Regulatory', 'FVF_REGULATORY_N_USD_PLAN'],
        'Buyer Protection': ['Buyer Protection', 'FVF_BuyerProtect_N_USD_PLAN']
    }

    # Get GMV for TR calculation - try both GMV and GMV_PLAN
    gmv_from = 1
    gmv_to = 1

    if not df_from.empty:
        if 'GMV' in df_from.columns:
            gmv_from = df_from['GMV'].sum()
        elif 'GMV_PLAN' in df_from.columns:
            gmv_from = df_from['GMV_PLAN'].sum()
        if gmv_from == 0:
            gmv_from = 1

    if not df_to.empty:
        if 'GMV' in df_to.columns:
            gmv_to = df_to['GMV'].sum()
        elif 'GMV_PLAN' in df_to.columns:
            gmv_to = df_to['GMV_PLAN'].sum()
        if gmv_to == 0:
            gmv_to = 1

    fvf_data = {}

    for component_name, col_candidates in fvf_components.items():
        from_value = 0
        to_value = 0

        # Try to find matching column in df_from
        if not df_from.empty:
            for col_name in col_candidates:
                if col_name in df_from.columns:
                    from_value = df_from[col_name].sum()
                    break

        # Try to find matching column in df_to
        if not df_to.empty:
            for col_name in col_candidates:
                if col_name in df_to.columns:
                    to_value = df_to[col_name].sum()
                    break

        tr_from = (from_value / gmv_from * 100) if gmv_from != 0 else 0
        tr_to = (to_value / gmv_to * 100) if gmv_to != 0 else 0
        change_bps = (tr_to - tr_from) * 100

        fvf_data[component_name] = {
            'Walk From (%)': tr_from,
            'Walk To (%)': tr_to,
            'Change (bps)': change_bps
        }

    # Calculate Net FVF TR (sum of all components)
    net_fvf_from = sum([v['Walk From (%)'] for v in fvf_data.values()])
    net_fvf_to = sum([v['Walk To (%)'] for v in fvf_data.values()])
    net_fvf_change = (net_fvf_to - net_fvf_from) * 100

    fvf_data['Net FVF TR'] = {
        'Walk From (%)': net_fvf_from,
        'Walk To (%)': net_fvf_to,
        'Change (bps)': net_fvf_change
    }

    return fvf_data
