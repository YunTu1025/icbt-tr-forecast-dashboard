import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Dict, Tuple, Optional

class FVFDataLoader:
    """
    Data loader for FVF (Final Value Fee) Excel files.

    Handles loading and caching of FVF forecast data from Excel workbooks.
    """

    def __init__(self, file_path: str):
        """
        Initialize FVF data loader.

        Args:
            file_path: Path to the FVF Excel file
        """
        self.file_path = file_path
        self.xl_file = None
        self.data = {}

    @st.cache_data(ttl=3600)
    def load_all_sheets(_self) -> Dict[str, pd.DataFrame]:
        """
        Load all required sheets from the FVF Excel file.

        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        _self.xl_file = pd.ExcelFile(_self.file_path)

        sheets_to_load = [
            'raw data',
            'Control Panel',
            'PV_reinstate',
            'working progress'
        ]

        for sheet_name in sheets_to_load:
            if sheet_name in _self.xl_file.sheet_names:
                _self.data[sheet_name] = pd.read_excel(_self.file_path, sheet_name=sheet_name)

        return _self.data

    def get_raw_data(self) -> pd.DataFrame:
        """Get the raw FVF data sheet."""
        if 'raw data' not in self.data:
            self.load_all_sheets()
        return self.data.get('raw data')

    def get_control_panel(self) -> pd.DataFrame:
        """Get the control panel configuration sheet."""
        if 'Control Panel' not in self.data:
            self.load_all_sheets()
        return self.data.get('Control Panel')

    def validate_data(self) -> Tuple[bool, str]:
        """
        Validate that required columns exist in the raw data.

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        required_columns = [
            'RETAIL_YEAR', 'RETAIL_WEEK', 'ICBT_FLAG', 'SLR_CNTRY',
            'GMV_PLAN', 'IF_G_USD_PLAN', 'FF_G_USD_PLAN', 'FVF_G_USD_PLAN'
        ]

        raw_data = self.get_raw_data()
        if raw_data is None:
            return False, "Raw data sheet not found"

        missing_cols = [col for col in required_columns if col not in raw_data.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"

        return True, "Data validation passed"


class IFFFFXDataLoader:
    """
    Data loader for IF (Insertion Fee) and FF (Fixed Fee) Excel files.

    Handles loading of fee modeling data across different regions.
    """

    def __init__(self, file_path: str):
        """
        Initialize IF/FF data loader.

        Args:
            file_path: Path to the IF/FF Excel file
        """
        self.file_path = file_path
        self.xl_file = None
        self.data = {}

    @st.cache_data(ttl=3600)
    def load_all_sheets(_self) -> Dict[str, pd.DataFrame]:
        """
        Load all required sheets from the IF/FF Excel file.

        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        _self.xl_file = pd.ExcelFile(_self.file_path)

        sheets_to_load = [
            'All_Fee_raw_data',
            'Control Panel',
            '1. IF_modeling_ICBT',
            '1. IF_modeling_GC',
            '1. IF_modeling_HIS',
            '1. IF_modeling_JPKO',
            '2. FFnon-PL_modeling_ICBT',
            '2. FFnon-PL_modeling_GC',
            '2. FFnon-PL_modeling_HIS',
            '2. FFnon-PL_modeling_JPKO'
        ]

        for sheet_name in sheets_to_load:
            if sheet_name in _self.xl_file.sheet_names:
                _self.data[sheet_name] = pd.read_excel(_self.file_path, sheet_name=sheet_name)

        return _self.data

    def get_modeling_data(self, region: str, fee_type: str) -> Optional[pd.DataFrame]:
        """
        Get modeling data for a specific region and fee type.

        Args:
            region: Region code (e.g., 'ICBT', 'GC', 'HIS', 'JPKO')
            fee_type: Fee type ('IF' or 'FF')

        Returns:
            DataFrame with modeling data, or None if not found
        """
        if fee_type == 'IF':
            sheet_name = f'1. IF_modeling_{region}'
        elif fee_type == 'FF':
            sheet_name = f'2. FFnon-PL_modeling_{region}'
        else:
            return None

        if sheet_name not in self.data:
            self.load_all_sheets()

        return self.data.get(sheet_name)

    def get_control_panel(self) -> pd.DataFrame:
        """Get the control panel configuration sheet."""
        if 'Control Panel' not in self.data:
            self.load_all_sheets()
        return self.data.get('Control Panel')


class TRSummaryDataLoader:
    """
    Data loader for TR (Take Rate) summary Excel files.

    Handles loading of TR summary and walk analysis data.
    """

    def __init__(self, file_path: str):
        """
        Initialize TR summary data loader.

        Args:
            file_path: Path to the TR summary Excel file
        """
        self.file_path = file_path
        self.xl_file = None
        self.data = {}

    @st.cache_data(ttl=3600)
    def load_all_sheets(_self) -> Dict[str, pd.DataFrame]:
        """
        Load all required sheets from the TR summary Excel file.

        Returns:
            Dictionary mapping sheet names to DataFrames
        """
        _self.xl_file = pd.ExcelFile(_self.file_path)

        sheets_to_load = [
            'Summary',
            'Total Site',
            'TR Walk',
            'Q2M1 - Aggregation',
            'GC',
            'HIS',
            'JPKO'
        ]

        for sheet_name in sheets_to_load:
            if sheet_name in _self.xl_file.sheet_names:
                _self.data[sheet_name] = pd.read_excel(_self.file_path, sheet_name=sheet_name)

        return _self.data

    def get_summary(self) -> pd.DataFrame:
        """Get the summary sheet."""
        if 'Summary' not in self.data:
            self.load_all_sheets()
        return self.data.get('Summary')

    def get_tr_walk(self) -> pd.DataFrame:
        """Get the TR Walk analysis sheet."""
        if 'TR Walk' not in self.data:
            self.load_all_sheets()
        return self.data.get('TR Walk')

    def get_regional_data(self, region: str) -> Optional[pd.DataFrame]:
        """
        Get regional data sheet.

        Args:
            region: Region name (e.g., 'GC', 'HIS', 'JPKO')

        Returns:
            DataFrame with regional data, or None if not found
        """
        if region not in self.data:
            self.load_all_sheets()
        return self.data.get(region)


def load_all_data(fvf_path: str, if_ff_path: str, tr_path: str) -> Tuple[FVFDataLoader, IFFFFXDataLoader, TRSummaryDataLoader]:
    """
    Load all data sources from Excel files.

    Args:
        fvf_path: Path to FVF Excel file
        if_ff_path: Path to IF/FF Excel file
        tr_path: Path to TR summary Excel file

    Returns:
        Tuple of (FVFDataLoader, IFFFFXDataLoader, TRSummaryDataLoader)
    """
    fvf_loader = FVFDataLoader(fvf_path)
    if_ff_loader = IFFFFXDataLoader(if_ff_path)
    tr_loader = TRSummaryDataLoader(tr_path)

    fvf_loader.load_all_sheets()
    if_ff_loader.load_all_sheets()
    tr_loader.load_all_sheets()

    return fvf_loader, if_ff_loader, tr_loader
