class HiveQueries:
    """
    Repository of SQL queries for Hive database access.

    Contains static methods that return SQL query strings for different data sources.
    """

    @staticmethod
    def get_fvf_data():
        """
        Get FVF (Final Value Fee) budget data from Hive.

        Returns:
            SQL query string for FVF data (years >= 2021)
        """
        return """
        SELECT *
        FROM P_FPA_T.BUDGET_DATA_OUTPUT
        WHERE RETAIL_YEAR >= 2021
        """

    @staticmethod
    def get_if_ff_store_data():
        """
        Get Insertion Fee, Fixed Fee, and Store Fee data from Hive.

        Returns:
            SQL query string aggregating fee data by date, week, and country
        """
        return """
        SELECT
            DT
            , YEAR_ID
            , MONTH_OF_YEAR_ID
            , DAY_OF_MONTH_ID
            , MONTH_BEG_DT
            , RTL_WEEK_BEG_DT
            , RETAIL_WEEK
            , RETAIL_YEAR
            , slr_cntry_2
            , SUM(GMV_PLAN) AS GMV_PLAN
            , SUM(IF_N_USD_PLAN) AS IF_N_USD_PLAN
            , SUM(FF_N_USD_PLAN) AS FF_N_USD_PLAN
            , SUM(TTL_PL_FEE_N_USD_PLAN) AS TTL_PL_FEE_N_USD_PLAN
            , SUM(STORE_FEE_N_USD_PLAN) AS STORE_FEE_N_USD_PLAN
        FROM P_FPA_T.FEE_FORECAST2
        WHERE DT >= '2021-01-01'
        GROUP BY 1,2,3,4,5,6,7,8,9
        """

    @staticmethod
    def get_all_rev_data():
        """
        Get all revenue forecast data for 2026.

        Returns:
            SQL query string for complete 2026 revenue data
        """
        return """
        SELECT *
        FROM P_FPA_T.FEE_FORECAST2
        WHERE YEAR_ID = 2026
        """

    @staticmethod
    def parse_access_error(error_msg):
        """
        Parse database access error messages to identify inaccessible tables.

        Args:
            error_msg: Error message string from database

        Returns:
            Table name that caused the access error, or "Unknown table"
        """
        if "P_FPA_T.BUDGET_DATA_OUTPUT" in error_msg:
            return "P_FPA_T.BUDGET_DATA_OUTPUT"
        elif "P_FPA_T.FEE_FORECAST2" in error_msg:
            return "P_FPA_T.FEE_FORECAST2"
        else:
            return "Unknown table"
