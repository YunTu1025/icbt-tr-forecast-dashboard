"""
Machine Learning Forecasting Module
Implements Prophet + XGBoost ensemble for Variable Take Rate forecasting
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')


class VariableTRForecaster:
    """
    Ensemble forecaster combining Prophet and XGBoost for Variable Take Rate prediction

    Features used:
    - Historical Variable TR from 2022-2025
    - Seasonal indicators (derived from date)
    - Lagged values (previous weeks)
    - Rolling averages
    """

    def __init__(self, prophet_weight=0.2, xgboost_weight=0.8):
        """
        Initialize the ensemble forecaster

        Args:
            prophet_weight: Weight for Prophet predictions (0-1)
            xgboost_weight: Weight for XGBoost predictions (0-1)
        """
        self.prophet_weight = prophet_weight
        self.xgboost_weight = xgboost_weight
        self.prophet_model = None
        self.xgb_model = None
        self.feature_columns = None

    def create_features(self, df, is_training=True):
        """
        Create features for ML models - FOCUSED ON RECENT TRENDS

        Features (in order of importance):
        - Lagged values (1-8 weeks back) - EXPANDED
        - Rolling averages (2, 4, 8, 12, 16 weeks) - EXPANDED
        - Rolling std (4, 8, 12 weeks)
        - Trend indicators (rate of change)
        - Minimal seasonal indicators

        Args:
            df: DataFrame with columns ['ds' (date), 'y' (Variable TR)]
            is_training: If True, drops rows with NaN (for training). If False, fills NaN with forward fill.

        Returns:
            DataFrame with engineered features
        """
        df = df.copy()
        df = df.sort_values('ds').reset_index(drop=True)

        # EXPANDED: Lagged features (previous 1-8 weeks) - MORE EMPHASIS ON RECENT VALUES
        for lag in [1, 2, 3, 4, 5, 6, 7, 8]:
            df[f'lag_{lag}'] = df['y'].shift(lag)

        # EXPANDED: Rolling averages - MORE WINDOW SIZES
        for window in [2, 4, 8, 12, 16]:
            df[f'rolling_mean_{window}'] = df['y'].rolling(window=window, min_periods=1).mean()

        # Rolling standard deviations - FOCUS ON VOLATILITY
        for window in [4, 8, 12]:
            df[f'rolling_std_{window}'] = df['y'].rolling(window=window, min_periods=1).std()

        # NEW: Rolling min/max to capture range
        for window in [4, 8, 12]:
            df[f'rolling_min_{window}'] = df['y'].rolling(window=window, min_periods=1).min()
            df[f'rolling_max_{window}'] = df['y'].rolling(window=window, min_periods=1).max()

        # CRITICAL: Rate of change (week-over-week trend indicators for sharp drops)
        df['change_1w'] = df['y'].diff(1)  # 1-week change (captures sharp drops)
        df['change_2w'] = df['y'].diff(2)  # 2-week change
        df['change_3w'] = df['y'].diff(3)  # 3-week change
        df['change_4w'] = df['y'].diff(4)  # 4-week change
        df['pct_change_1w'] = df['y'].pct_change(1)  # 1-week % change (critical for Thanksgiving drop %)
        df['pct_change_2w'] = df['y'].pct_change(2)  # 2-week % change
        df['pct_change_3w'] = df['y'].pct_change(3)  # 3-week % change
        df['pct_change_4w'] = df['y'].pct_change(4)  # 4-week % change

        # Acceleration (change of change) - captures if drop is accelerating
        df['accel_1w'] = df['change_1w'].diff(1)  # Week-over-week acceleration

        # CRITICAL: Year-over-Year features (52-week lag for same week last year)
        df['lag_52'] = df['y'].shift(52)  # Same week last year
        df['yoy_change'] = df['y'] - df['lag_52']  # YoY absolute change
        df['yoy_pct_change'] = df['y'].pct_change(52)  # YoY % change
        df['rolling_mean_52'] = df['y'].rolling(window=52, min_periods=1).mean()  # Yearly average

        # Week number features (CRITICAL for capturing Thanksgiving and other week-specific patterns)
        df['week_of_year'] = pd.to_datetime(df['ds']).dt.isocalendar().week.astype(int)
        df['year'] = pd.to_datetime(df['ds']).dt.year

        # Cyclical encoding for week number (preserves continuity: week 52 is close to week 1)
        df['week_sin'] = np.sin(2 * np.pi * df['week_of_year'] / 52)
        df['week_cos'] = np.cos(2 * np.pi * df['week_of_year'] / 52)

        # THANKSGIVING WEEK INDICATORS - Calculate actual Thanksgiving week for each year
        # Thanksgiving = 4th Thursday of November
        def get_thanksgiving_week(year):
            """Get ISO week number for Thanksgiving (4th Thursday of November)"""
            november_1 = pd.Timestamp(f'{year}-11-01')
            # Find first Thursday in November
            days_until_thursday = (3 - november_1.weekday()) % 7
            first_thursday = november_1 + pd.Timedelta(days=days_until_thursday)
            # 4th Thursday is 3 weeks later
            thanksgiving = first_thursday + pd.Timedelta(weeks=3)
            return thanksgiving.isocalendar().week

        # Create Thanksgiving indicators for each year
        df['is_thanksgiving_week'] = 0
        df['is_pre_thanksgiving'] = 0  # Week before Thanksgiving
        df['is_post_thanksgiving'] = 0  # Week after Thanksgiving

        for year_val in df['year'].unique():
            thanksgiving_week = get_thanksgiving_week(int(year_val))
            year_mask = df['year'] == year_val
            df.loc[year_mask & (df['week_of_year'] == thanksgiving_week), 'is_thanksgiving_week'] = 1
            df.loc[year_mask & (df['week_of_year'] == thanksgiving_week - 1), 'is_pre_thanksgiving'] = 1
            df.loc[year_mask & (df['week_of_year'] == thanksgiving_week + 1), 'is_post_thanksgiving'] = 1

        # CRITICAL: Historical Thanksgiving drop magnitude feature
        # Calculate average drop from historical data to give model a reference
        thanksgiving_drops = []
        for year_val in df['year'].unique():
            if year_val < df['year'].max():  # Only historical years
                thanksgiving_week = get_thanksgiving_week(int(year_val))
                year_mask = df['year'] == year_val

                pre_val = df.loc[year_mask & (df['week_of_year'] == thanksgiving_week - 1), 'y']
                thanks_val = df.loc[year_mask & (df['week_of_year'] == thanksgiving_week), 'y']

                if len(pre_val) > 0 and len(thanks_val) > 0:
                    drop = pre_val.iloc[0] - thanks_val.iloc[0]
                    thanksgiving_drops.append(drop)

        # Store average historical drop as a feature (helps model learn the scale)
        if len(thanksgiving_drops) > 0:
            avg_drop = np.mean(thanksgiving_drops)
            df['historical_thanksgiving_drop'] = avg_drop
        else:
            df['historical_thanksgiving_drop'] = 0.0


        # SHORT-TERM rolling features (1-3 weeks) - CRITICAL for week-over-week sharp drops
        df['rolling_mean_1'] = df['y'].shift(1)  # Last week value
        df['rolling_mean_2_wk'] = df['y'].rolling(window=2, min_periods=1).mean()
        df['rolling_mean_3_wk'] = df['y'].rolling(window=3, min_periods=1).mean()
        df['rolling_std_2'] = df['y'].rolling(window=2, min_periods=1).std()
        df['rolling_std_3'] = df['y'].rolling(window=3, min_periods=1).std()
        df['rolling_min_2'] = df['y'].rolling(window=2, min_periods=1).min()
        df['rolling_max_2'] = df['y'].rolling(window=2, min_periods=1).max()
        df['rolling_min_3'] = df['y'].rolling(window=3, min_periods=1).min()
        df['rolling_max_3'] = df['y'].rolling(window=3, min_periods=1).max()

        # Quarter features (for quarter-over-quarter patterns)
        df['quarter'] = pd.to_datetime(df['ds']).dt.quarter
        quarter_dummies = pd.get_dummies(df['quarter'], prefix='quarter', drop_first=True)
        df = pd.concat([df, quarter_dummies], axis=1)

        # CRITICAL: Quarter-over-Quarter change features
        # Use rolling calculation that works during prediction
        df['quarter_rolling_avg'] = df['y'].rolling(window=13, min_periods=1).mean()  # ~13 weeks = 1 quarter
        df['qoq_change'] = df['quarter_rolling_avg'].diff(13)  # Quarter-over-quarter change
        df['qoq_pct_change'] = df['quarter_rolling_avg'].pct_change(13)  # Quarter-over-quarter % change

        if is_training:
            # For training, drop rows with NaN (from lagging)
            df = df.dropna()
        else:
            # For prediction, fill NaN with forward fill
            df = df.ffill().bfill()

        return df

    def fit(self, train_df):
        """
        Train both Prophet and XGBoost models

        Args:
            train_df: DataFrame with columns ['ds' (date), 'y' (Variable TR)]
        """
        # Train Prophet with seasonality enabled
        print("Training Prophet model...")
        self.prophet_model = Prophet(
            yearly_seasonality=True,  # Enable yearly seasonality
            weekly_seasonality=True,  # Enable weekly seasonality
            daily_seasonality=True,  # Enable daily seasonality
            seasonality_mode='additive',  # Additive seasonality
            changepoint_prior_scale=0.05,  # Moderate flexibility for trend changes
            seasonality_prior_scale=10.0,  # Higher seasonality impact
            n_changepoints=25  # More changepoints for flexible trend
        )
        self.prophet_model.fit(train_df[['ds', 'y']])

        # Create features for XGBoost
        print("Creating features for XGBoost...")
        train_features = self.create_features(train_df, is_training=True)

        # Define feature columns (exclude ds, y, quarter, week_of_year, year - use cyclical encoding and indicators instead)
        self.feature_columns = [col for col in train_features.columns
                                if col not in ['ds', 'y', 'quarter', 'week_of_year', 'year']]

        X_train = train_features[self.feature_columns]
        y_train = train_features['y']

        # Train XGBoost - TUNED FOR CAPTURING SUBTLE CHANGES (2+ bps) AND SHARP DROPS (10+ bps)
        print("Training XGBoost model...")
        self.xgb_model = xgb.XGBRegressor(
            n_estimators=300,  # Increased for better pattern learning (was 200)
            max_depth=6,  # Deeper trees to capture complex interactions (was 5)
            learning_rate=0.03,  # Lower rate for precision on small changes (was 0.05)
            subsample=0.9,  # Higher subsample for stability (was 0.85)
            colsample_bytree=0.85,  # Higher feature sampling (was 0.8)
            min_child_weight=1,  # CRITICAL: Allow learning from small changes (was 2)
            gamma=0.0,  # NO gamma regularization - allow fitting small changes (was 0.05)
            reg_alpha=0.0,  # NO L1 regularization - preserve all features (was 0.05)
            reg_lambda=0.1,  # Minimal L2 regularization (was 0.5)
            random_state=42,
            objective='reg:squarederror',
            tree_method='hist'  # Faster and more precise for small changes
        )
        self.xgb_model.fit(X_train, y_train)

        print("Training complete!")

        # Show top 10 feature importances
        feature_importance = self.xgb_model.feature_importances_
        importance_df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': feature_importance
        }).sort_values('importance', ascending=False)

        print("\n=== TOP 10 MOST IMPORTANT FEATURES ===")
        print(importance_df.head(10).to_string(index=False))

        return self

    def predict(self, future_df):
        """
        Generate ensemble predictions

        Args:
            future_df: DataFrame with column 'ds' (dates to predict)

        Returns:
            DataFrame with columns ['ds', 'prophet_pred', 'xgb_pred', 'ensemble_pred']
        """
        # Prophet predictions
        prophet_forecast = self.prophet_model.predict(future_df[['ds']])
        prophet_pred = prophet_forecast['yhat'].values

        # Prepare features for XGBoost
        # Need to combine historical data with future dates
        future_features = self.create_features(future_df, is_training=False)

        # XGBoost predictions
        X_future = future_features[self.feature_columns]
        xgb_pred = self.xgb_model.predict(X_future)

        # Ensemble prediction
        ensemble_pred = (self.prophet_weight * prophet_pred +
                        self.xgboost_weight * xgb_pred)

        result = pd.DataFrame({
            'ds': future_df['ds'],
            'prophet_pred': prophet_pred,
            'xgb_pred': xgb_pred,
            'ensemble_pred': ensemble_pred
        })

        return result

    def predict_weekly(self, train_df, num_weeks=52):
        """
        Predict weekly values for the next period

        Args:
            train_df: Historical data with columns ['ds' (date), 'y' (Variable TR)]
            num_weeks: Number of weeks to forecast

        Returns:
            Array of predictions (length = num_weeks)
        """
        # Get the last date in training data
        last_date = pd.to_datetime(train_df['ds'].max())

        # Generate future dates (weekly)
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=7),
                                     periods=num_weeks,
                                     freq='W')

        future_df = pd.DataFrame({'ds': future_dates})

        # For XGBoost, we need historical context for lagged features
        # Combine train data with future dates
        combined_df = pd.concat([
            train_df[['ds', 'y']],
            pd.DataFrame({'ds': future_dates, 'y': np.nan})
        ], ignore_index=True)

        # Make predictions iteratively for XGBoost (to use previous predictions as lags)
        predictions = []

        for i in range(num_weeks):
            # Current date to predict
            current_date = future_dates[i]
            current_df = pd.DataFrame({'ds': [current_date]})

            # Prophet prediction
            prophet_forecast = self.prophet_model.predict(current_df)
            prophet_pred = prophet_forecast['yhat'].values[0]

            # For XGBoost, create features from combined data up to current point
            temp_combined = combined_df[combined_df['ds'] <= current_date].copy()
            temp_features = self.create_features(temp_combined, is_training=False)

            # Get the last row (current prediction point)
            current_features = temp_features.iloc[-1:][self.feature_columns]
            xgb_pred = self.xgb_model.predict(current_features)[0]

            # Ensemble prediction
            ensemble_pred = (self.prophet_weight * prophet_pred +
                           self.xgboost_weight * xgb_pred)

            predictions.append(ensemble_pred)

            # Update combined_df with prediction for next iteration
            combined_df.loc[combined_df['ds'] == current_date, 'y'] = ensemble_pred

        return np.array(predictions)


def forecast_variable_tr_2026(df_variable_agg, year_mapping):
    """
    Forecast Variable TR for 2026 using ML ensemble - INDEPENDENT methodology
    Uses YoY calibration from actual 2026 data (not Index Baseline parameters)

    Args:
        df_variable_agg: Aggregated Variable TR data with columns
                        ['RETAIL_YEAR', 'RETAIL_WEEK', 'GMV_PLAN_PAID',
                         'CAL_P2_VAR_FEE_UP_DAILY', 'FVF_BASE_G_USD_PLAN',
                         'ETRS_CREDIT_USD_PLAN', 'Variable TR']
        year_mapping: Dictionary mapping week numbers to retail year/week
                     Format: {week_num: {'year': year, 'week': retail_week}}

    Returns:
        Dictionary mapping week number (1-52) to ML prediction
    """
    # Prepare training data from 2022-2025 and collect actual 2026 data for calibration
    train_data = []
    data_2025 = []
    data_2026_actual = []

    for week_num in range(1, 53):
        for year in [2022, 2023, 2024, 2025, 2026]:
            # Get retail year/week mapping
            if year in [2022, 2023, 2024]:
                if week_num <= 51:
                    retail_week = week_num + 1
                    retail_year = year
                else:
                    retail_week = 1
                    retail_year = year + 1
            elif year == 2025:
                retail_week = week_num + 1
                retail_year = year
            elif year == 2026:
                retail_week = week_num
                retail_year = year

            # Find corresponding data
            row = df_variable_agg[
                (df_variable_agg['RETAIL_YEAR'] == retail_year) &
                (df_variable_agg['RETAIL_WEEK'] == retail_week)
            ]

            if not row.empty:
                gmv = row.iloc[0]['GMV_PLAN_PAID']

                if year == 2026:
                    # Collect actual 2026 data for YoY calibration
                    fvf = row.iloc[0]['FVF_BASE_G_USD_PLAN']
                    etrs = row.iloc[0]['ETRS_CREDIT_USD_PLAN']
                    if gmv != 0:
                        variable_tr = (fvf - etrs) / gmv
                        data_2026_actual.append(variable_tr)
                else:
                    # Training data: 2022-2025
                    cal_p2 = row.iloc[0]['CAL_P2_VAR_FEE_UP_DAILY']
                    if gmv != 0:
                        variable_tr = cal_p2 / gmv

                        # Create a pseudo-date for weekly data
                        date_str = f"{year}-W{week_num:02d}-1"
                        date = pd.to_datetime(date_str, format='%Y-W%W-%w')

                        train_data.append({
                            'ds': date,
                            'y': variable_tr,
                            'year': year,
                            'week': week_num
                        })

                        if year == 2025:
                            data_2025.append(variable_tr)

    train_df = pd.DataFrame(train_data)
    train_df = train_df.sort_values('ds').reset_index(drop=True)

    print(f"\n=== TRAINING DATA (2022-2025) ===")
    print(f"Total data points: {len(train_df)}")
    print(f"\nAverage Variable TR by year:")
    for year in [2022, 2023, 2024, 2025]:
        year_data = train_df[train_df['year'] == year]['y']
        if len(year_data) > 0:
            print(f"  {year}: mean={year_data.mean():.4f} ({year_data.mean()*100:.2f}%), std={year_data.std():.4f}, range=[{year_data.min():.4f}, {year_data.max():.4f}]")

    print(f"\nQuarter averages across all years:")
    for q in [1, 2, 3, 4]:
        q_data = train_df[train_df['ds'].dt.quarter == q]['y']
        if len(q_data) > 0:
            print(f"  Q{q}: {q_data.mean():.4f} ({q_data.mean()*100:.2f}%)")

    # Check Thanksgiving patterns in historical data
    print(f"\nThanksgiving week patterns (historical):")
    for year in [2022, 2023, 2024, 2025]:
        year_data = train_df[train_df['year'] == year]
        if len(year_data) > 0:
            november_1 = pd.Timestamp(f'{year}-11-01')
            days_until_thursday = (3 - november_1.weekday()) % 7
            first_thursday = november_1 + pd.Timedelta(days=days_until_thursday)
            thanksgiving = first_thursday + pd.Timedelta(weeks=3)
            thanksgiving_week = thanksgiving.isocalendar().week

            pre_thanks = year_data[year_data['ds'].dt.isocalendar().week == thanksgiving_week - 1]['y']
            thanks = year_data[year_data['ds'].dt.isocalendar().week == thanksgiving_week]['y']
            post_thanks = year_data[year_data['ds'].dt.isocalendar().week == thanksgiving_week + 1]['y']

            if len(pre_thanks) > 0 and len(thanks) > 0:
                drop = pre_thanks.iloc[0] - thanks.iloc[0]
                print(f"  {year} (week {thanksgiving_week}): pre={pre_thanks.iloc[0]:.4f}, thanks={thanks.iloc[0]:.4f}, drop={drop:.4f} ({drop*100:+.2f}%)")

    # Calculate YoY calibration from actual 2026 data - USE PARTIAL CALIBRATION to preserve variations
    yoy_ratio = 1.0
    yoy_adjustment = 0.0
    if len(data_2025) > 0 and len(data_2026_actual) > 0:
        avg_2025 = np.mean(data_2025)
        avg_2026_actual = np.mean(data_2026_actual)
        yoy_ratio = avg_2026_actual / avg_2025
        yoy_adjustment = avg_2026_actual - avg_2025  # Absolute adjustment
        print(f"\nYoY Calibration from actual data:")
        print(f"  2025 average: {avg_2025:.4f} ({avg_2025*100:.2f}%)")
        print(f"  2026 actual average: {avg_2026_actual:.4f} ({avg_2026_actual*100:.2f}%)")
        print(f"  YoY ratio: {yoy_ratio:.4f} ({(yoy_ratio-1)*100:+.2f}%)")
        print(f"  YoY absolute adjustment: {yoy_adjustment:.4f} ({yoy_adjustment*100:+.2f}%)")
    else:
        print("\nNo YoY calibration - insufficient 2026 actual data")

    # Train the ensemble model - Prophet + XGBoost
    forecaster = VariableTRForecaster(prophet_weight=0.2, xgboost_weight=0.8)
    forecaster.fit(train_df[['ds', 'y']])

    # Predict for 2026 (52 weeks)
    predictions_raw = forecaster.predict_weekly(train_df[['ds', 'y']], num_weeks=52)

    print(f"\n=== RAW ML PREDICTIONS (before calibration) ===")
    print(f"Mean: {predictions_raw.mean():.4f} ({predictions_raw.mean()*100:.2f}%)")
    print(f"Std dev: {predictions_raw.std():.4f} ({predictions_raw.std()*100:.2f}%)")
    print(f"Range: {predictions_raw.min():.4f} to {predictions_raw.max():.4f}")
    print(f"Max drop (any week-over-week): {(predictions_raw[:-1] - predictions_raw[1:]).max():.4f} ({(predictions_raw[:-1] - predictions_raw[1:]).max()*100:.2f}%)")

    # Show predictions for specific quarters and Thanksgiving
    print(f"\n=== QUARTER AVERAGES (Raw predictions) ===")
    print(f"Q1 avg: {predictions_raw[0:13].mean():.4f} ({predictions_raw[0:13].mean()*100:.2f}%)")
    print(f"Q2 avg: {predictions_raw[13:26].mean():.4f} ({predictions_raw[13:26].mean()*100:.2f}%)")
    print(f"Q3 avg: {predictions_raw[26:39].mean():.4f} ({predictions_raw[26:39].mean()*100:.2f}%)")
    print(f"Q4 avg: {predictions_raw[39:52].mean():.4f} ({predictions_raw[39:52].mean()*100:.2f}%)")
    print(f"Q2→Q3 change: {(predictions_raw[26:39].mean() - predictions_raw[13:26].mean()):.4f} ({(predictions_raw[26:39].mean() - predictions_raw[13:26].mean())*100:+.2f}%)")

    # Thanksgiving week (week 48 for 2026)
    thanksgiving_week_2026 = 48
    if thanksgiving_week_2026 > 1:
        print(f"\n=== THANKSGIVING PATTERN (Week {thanksgiving_week_2026}) ===")
        print(f"Week {thanksgiving_week_2026-1}: {predictions_raw[thanksgiving_week_2026-2]:.4f} ({predictions_raw[thanksgiving_week_2026-2]*100:.2f}%)")
        print(f"Week {thanksgiving_week_2026} (Thanksgiving): {predictions_raw[thanksgiving_week_2026-1]:.4f} ({predictions_raw[thanksgiving_week_2026-1]*100:.2f}%)")
        print(f"Week {thanksgiving_week_2026+1}: {predictions_raw[thanksgiving_week_2026]:.4f} ({predictions_raw[thanksgiving_week_2026]*100:.2f}%)")
        print(f"Thanksgiving drop: {(predictions_raw[thanksgiving_week_2026-2] - predictions_raw[thanksgiving_week_2026-1]):.4f} ({(predictions_raw[thanksgiving_week_2026-2] - predictions_raw[thanksgiving_week_2026-1])*100:+.2f}%)")

    # CRITICAL: Use ADDITIVE calibration instead of MULTIPLICATIVE to preserve variations
    # Calibration purpose: Align forecast level with actual 2026 YoY trend
    # Multiplicative (old): predictions * yoy_ratio → smooths variations by scaling
    # Additive (new): predictions + yoy_adjustment → shifts level but preserves drops
    if yoy_adjustment != 0.0:
        predictions = predictions_raw + yoy_adjustment
        print(f"\n{'='*80}")
        print(f"CALIBRATION: Adding {yoy_adjustment:.4f} ({yoy_adjustment*100:+.2f}%) to all predictions")
        print(f"Purpose: Align with 2025→2026 YoY trend while preserving variations")
        print(f"{'='*80}")
    else:
        predictions = predictions_raw
        print(f"\nNo calibration applied (insufficient 2026 actual data)")

    print(f"\n=== AFTER CALIBRATION ===")
    print(f"Mean: {predictions.mean():.4f} ({predictions.mean()*100:.2f}%)")
    print(f"Std dev: {predictions.std():.4f} ({predictions.std()*100:.2f}%)")
    print(f"Range: {predictions.min():.4f} to {predictions.max():.4f}")

    print(f"\nQuarter averages (AFTER calibration):")
    print(f"  Q1: {predictions[0:13].mean():.4f} ({predictions[0:13].mean()*100:.2f}%)")
    print(f"  Q2: {predictions[13:26].mean():.4f} ({predictions[13:26].mean()*100:.2f}%)")
    print(f"  Q3: {predictions[26:39].mean():.4f} ({predictions[26:39].mean()*100:.2f}%)")
    print(f"  Q4: {predictions[39:52].mean():.4f} ({predictions[39:52].mean()*100:.2f}%)")
    print(f"  Q2→Q3 change: {(predictions[26:39].mean() - predictions[13:26].mean()):.4f} ({(predictions[26:39].mean() - predictions[13:26].mean())*100:+.2f}%)")

    if thanksgiving_week_2026 > 1:
        print(f"\nThanksgiving pattern (AFTER calibration):")
        print(f"  Week {thanksgiving_week_2026-1}: {predictions[thanksgiving_week_2026-2]:.4f} ({predictions[thanksgiving_week_2026-2]*100:.2f}%)")
        print(f"  Week {thanksgiving_week_2026} (Thanksgiving): {predictions[thanksgiving_week_2026-1]:.4f} ({predictions[thanksgiving_week_2026-1]*100:.2f}%)")
        print(f"  Drop: {(predictions[thanksgiving_week_2026-2] - predictions[thanksgiving_week_2026-1]):.4f} ({(predictions[thanksgiving_week_2026-2] - predictions[thanksgiving_week_2026-1])*100:+.2f}%)")

    # Show sample weeks before/after calibration
    print(f"\n=== SAMPLE WEEKS: BEFORE vs AFTER CALIBRATION ===")
    print(f"{'Week':<6} {'Before':<12} {'After':<12} {'Difference':<12}")
    print(f"{'-'*50}")
    sample_weeks = [1, 13, 26, 39, thanksgiving_week_2026-1, thanksgiving_week_2026, thanksgiving_week_2026+1, 52]
    for week in sample_weeks:
        if 1 <= week <= 52:
            idx = week - 1
            before = predictions_raw[idx]
            after = predictions[idx]
            diff = after - before
            print(f"{week:<6} {before*100:>10.2f}%  {after*100:>10.2f}%  {diff*100:>+10.2f}%")

    # Create result dictionary
    ml_predictions = {}
    for week_num in range(1, 53):
        ml_predictions[week_num] = predictions[week_num - 1]

    return ml_predictions


def forecast_international_tr_2026(df_variable_agg, year_mapping):
    """
    Forecast International TR for 2026 using ML ensemble - INDEPENDENT methodology
    Uses YoY calibration from actual 2026 data (not Index Baseline parameters)

    Args:
        df_variable_agg: Aggregated data with columns
                        ['RETAIL_YEAR', 'RETAIL_WEEK', 'GMV_PLAN_PAID',
                         'CAL_P2_CBT_FEE_UP_DAILY', 'CBT_FEE_G_USD_PLAN']
        year_mapping: Dictionary mapping week numbers to retail year/week

    Returns:
        Dictionary mapping week number (1-52) to ML prediction
    """
    # Prepare training data from 2022-2025 and collect actual 2026 data for calibration
    train_data = []
    data_2025 = []
    data_2026_actual = []

    for week_num in range(1, 53):
        for year in [2022, 2023, 2024, 2025, 2026]:
            # Get retail year/week mapping
            if year in [2022, 2023, 2024]:
                if week_num <= 51:
                    retail_week = week_num + 1
                    retail_year = year
                else:
                    retail_week = 1
                    retail_year = year + 1
            elif year == 2025:
                retail_week = week_num + 1
                retail_year = year
            elif year == 2026:
                retail_week = week_num
                retail_year = year

            # Find corresponding data
            row = df_variable_agg[
                (df_variable_agg['RETAIL_YEAR'] == retail_year) &
                (df_variable_agg['RETAIL_WEEK'] == retail_week)
            ]

            if not row.empty:
                gmv = row.iloc[0]['GMV_PLAN_PAID']

                if year == 2026:
                    # For 2026: International TR = CBT_FEE_G_USD_PLAN / GMV_PLAN_PAID
                    cbt_fee = row.iloc[0]['CBT_FEE_G_USD_PLAN']
                    if gmv != 0:
                        international_tr = cbt_fee / gmv
                        data_2026_actual.append(international_tr)
                else:
                    # For 2022-2025: International TR = CAL_P2_CBT_FEE_UP_DAILY / GMV_PLAN_PAID
                    cal_p2_cbt = row.iloc[0]['CAL_P2_CBT_FEE_UP_DAILY']
                    if gmv != 0:
                        international_tr = cal_p2_cbt / gmv

                        # Create a pseudo-date for weekly data
                        date_str = f"{year}-W{week_num:02d}-1"
                        date = pd.to_datetime(date_str, format='%Y-W%W-%w')

                        train_data.append({
                            'ds': date,
                            'y': international_tr,
                            'year': year,
                            'week': week_num
                        })

                        if year == 2025:
                            data_2025.append(international_tr)

    train_df = pd.DataFrame(train_data)
    train_df = train_df.sort_values('ds').reset_index(drop=True)

    print(f"Training International ML model on {len(train_df)} historical data points (2022-2025)")
    print(f"Average International TR by year:")
    for year in [2022, 2023, 2024, 2025]:
        year_data = train_df[train_df['year'] == year]['y']
        if len(year_data) > 0:
            print(f"  {year}: {year_data.mean():.4f} ({year_data.mean()*100:.2f}%)")

    # Calculate YoY calibration from actual 2026 data - USE PARTIAL CALIBRATION to preserve variations
    yoy_ratio = 1.0
    yoy_adjustment = 0.0
    if len(data_2025) > 0 and len(data_2026_actual) > 0:
        avg_2025 = np.mean(data_2025)
        avg_2026_actual = np.mean(data_2026_actual)
        yoy_ratio = avg_2026_actual / avg_2025
        yoy_adjustment = avg_2026_actual - avg_2025  # Absolute adjustment
        print(f"\nInternational YoY Calibration from actual data:")
        print(f"  2025 average: {avg_2025:.4f} ({avg_2025*100:.2f}%)")
        print(f"  2026 actual average: {avg_2026_actual:.4f} ({avg_2026_actual*100:.2f}%)")
        print(f"  YoY ratio: {yoy_ratio:.4f} ({(yoy_ratio-1)*100:+.2f}%)")
        print(f"  YoY absolute adjustment: {yoy_adjustment:.4f} ({yoy_adjustment*100:+.2f}%)")
    else:
        print("\nNo YoY calibration - insufficient 2026 actual data")

    # Train the ensemble model - Prophet + XGBoost
    forecaster = VariableTRForecaster(prophet_weight=0.2, xgboost_weight=0.8)
    forecaster.fit(train_df[['ds', 'y']])

    # Predict for 2026 (52 weeks)
    predictions_raw = forecaster.predict_weekly(train_df[['ds', 'y']], num_weeks=52)

    print(f"\nRaw International ML predictions: mean={predictions_raw.mean():.4f} ({predictions_raw.mean()*100:.2f}%)")
    print(f"Raw International ML std dev: {predictions_raw.std():.4f} ({predictions_raw.std()*100:.2f}%)")
    print(f"Raw International ML range: {predictions_raw.min():.4f} to {predictions_raw.max():.4f}")

    # CRITICAL: Use ADDITIVE calibration instead of MULTIPLICATIVE to preserve variations
    if yoy_adjustment != 0.0:
        predictions = predictions_raw + yoy_adjustment
        print(f"\nUsing ADDITIVE calibration to preserve variations")
    else:
        predictions = predictions_raw

    print(f"Calibrated International ML predictions: mean={predictions.mean():.4f} ({predictions.mean()*100:.2f}%)")
    print(f"Calibrated International ML std dev: {predictions.std():.4f} ({predictions.std()*100:.2f}%)")
    print(f"Calibrated International ML range: {predictions.min():.4f} to {predictions.max():.4f}")

    # Create result dictionary
    ml_predictions = {}
    for week_num in range(1, 53):
        ml_predictions[week_num] = predictions[week_num - 1]

    return ml_predictions
