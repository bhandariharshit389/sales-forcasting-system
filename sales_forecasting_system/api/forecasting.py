import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

class SalesForecaster:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.forecast_models = {
            'prophet': self._prophet_forecast,
            'xgboost': self._xgboost_forecast,
            'arima': self._arima_forecast,
            'linear': self._linear_forecast
        }
        
    def forecast_sales(self, df, periods=12):
        """Generate sales forecast for next 'periods' months"""
        # Prepare daily sales data
        daily_sales = df.groupby('date')['total_sales_inr'].sum().reset_index()
        daily_sales.columns = ['ds', 'y']
        
        # Monthly aggregation
        monthly_sales = df.groupby(df['date'].dt.to_period('M'))['total_sales_inr'].sum().reset_index()
        monthly_sales['date'] = monthly_sales['date'].dt.to_timestamp()
        monthly_sales.columns = ['ds', 'y']
        
        # Generate forecasts from different models
        forecasts = {}
        for model_name, model_func in self.forecast_models.items():
            try:
                if model_name == 'prophet':
                    forecast = model_func(monthly_sales, periods)
                else:
                    forecast = model_func(df, periods)
                forecasts[model_name] = forecast
            except Exception as e:
                print(f"Error in {model_name} forecast: {str(e)}")
                continue
        
        # Combine forecasts (ensemble)
        ensemble_forecast = self._ensemble_forecast(forecasts)
        
        # Generate metadata about models used
        model_info = self._get_model_info(forecasts)
        
        result = {
            'forecast': ensemble_forecast,
            'individual_forecasts': forecasts,
            'model_info': model_info,
            'metrics': self._calculate_metrics(daily_sales, ensemble_forecast)
        }
        
        return result
    
    def _prophet_forecast(self, df, periods):
        """Facebook Prophet forecasting"""
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=periods, freq='M')
        forecast = model.predict(future)
        
        # Extract forecast values
        forecast_values = forecast[['ds', 'yhat']].tail(periods)
        forecast_values['yhat'] = forecast_values['yhat'].clip(lower=0)  # No negative sales
        
        return forecast_values.to_dict('records')
    
    def _xgboost_forecast(self, df, periods):
        """XGBoost forecasting with features"""
        # Prepare features
        df_features = df.copy()
        
        # Create lag features
        for lag in [1, 3, 7, 14, 30]:
            df_features[f'lag_{lag}'] = df_features['total_sales_inr'].shift(lag)
        
        # Create rolling averages
        for window in [7, 14, 30]:
            df_features[f'rolling_avg_{window}'] = df_features['total_sales_inr'].rolling(window=window).mean()
        
        # Drop NaN values
        df_features = df_features.dropna()
        
        # Select features for modeling
        feature_cols = ['quantity', 'unit_price_inr', 'review_rating', 'month', 'weekday', 
                       'is_weekend'] + [f'lag_{i}' for i in [1, 3, 7, 14, 30]] + [f'rolling_avg_{i}' for i in [7, 14, 30]]
        
        X = df_features[feature_cols]
        y = df_features['total_sales_inr']
        
        # Train XGBoost model
        model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        model.fit(X, y)
        self.models['xgboost'] = model
        
        # Generate future predictions
        last_known = df_features.iloc[-1:].copy()
        predictions = []
        
        for i in range(periods):
            pred = model.predict(last_known[feature_cols])[0]
            predictions.append(pred)
            
            # Update features for next prediction
            new_row = last_known.copy()
            for lag in [30, 14, 7, 3, 1]:
                if lag == 1:
                    new_row[f'lag_{lag}'] = pred
                else:
                    new_row[f'lag_{lag}'] = last_known[f'lag_{lag-1}'].values[0]
            
            for window in [7, 14, 30]:
                # Simplified rolling average update
                new_row[f'rolling_avg_{window}'] = pred
            
            last_known = new_row
        
        # Create dates for predictions
        last_date = df['date'].max()
        pred_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods, freq='M')
        
        return [{'ds': date, 'yhat': max(0, pred)} for date, pred in zip(pred_dates, predictions)]
    
    def _arima_forecast(self, df, periods):
        """ARIMA time series forecasting"""
        # Prepare time series data
        ts_data = df.groupby(df['date'].dt.to_period('M'))['total_sales_inr'].sum()
        ts_data.index = ts_data.index.to_timestamp()
        
        # Fit ARIMA model
        model = ARIMA(ts_data, order=(2, 1, 2), seasonal_order=(1, 1, 1, 12))
        model_fit = model.fit()
        
        # Generate forecast
        forecast = model_fit.forecast(steps=periods)
        
        # Create dates for predictions
        last_date = ts_data.index[-1]
        pred_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq='M')
        
        return [{'ds': date, 'yhat': max(0, pred)} for date, pred in zip(pred_dates, forecast)]
    
    def _linear_forecast(self, df, periods):
        """Linear regression forecasting"""
        # Prepare data
        df['date_numeric'] = (df['date'] - df['date'].min()).dt.days
        
        # Create features
        features = ['date_numeric', 'month', 'weekday', 'quarter']
        X = df[features]
        y = df['total_sales_inr']
        
        # Train model
        model = LinearRegression()
        model.fit(X, y)
        self.models['linear'] = model
        
        # Generate future predictions
        last_date = df['date'].max()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods * 30, freq='D')
        
        future_df = pd.DataFrame({
            'date_numeric': [(date - df['date'].min()).days for date in future_dates],
            'month': [date.month for date in future_dates],
            'weekday': [date.weekday() for date in future_dates],
            'quarter': [date.quarter for date in future_dates]
        })
        
        predictions = model.predict(future_df)
        
        # Aggregate to monthly
        future_df['date'] = future_dates
        future_df['prediction'] = predictions
        monthly_preds = future_df.groupby(pd.Grouper(key='date', freq='M'))['prediction'].sum()
        
        # Create monthly forecast
        pred_dates = monthly_preds.index
        pred_values = monthly_preds.values
        
        return [{'ds': date, 'yhat': max(0, pred)} for date, pred in zip(pred_dates, pred_values)]
    
    def _ensemble_forecast(self, forecasts):
        """Combine forecasts using weighted average"""
        if not forecasts:
            return []
        
        # Simple average of all available forecasts
        forecast_values = []
        dates = None
        
        for model_name, forecast in forecasts.items():
            if dates is None:
                dates = [f['ds'] for f in forecast]
            values = [f['yhat'] for f in forecast]
            forecast_values.append(values)
        
        # Calculate average
        ensemble_values = np.mean(forecast_values, axis=0)
        
        return [{'ds': date, 'yhat': value} for date, value in zip(dates, ensemble_values)]
    
    def _get_model_info(self, forecasts):
        """Get information about models used"""
        model_info = []
        
        for model_name in forecasts.keys():
            model_info.append({
                'name': model_name,
                'type': {
                    'prophet': 'Time Series',
                    'xgboost': 'Machine Learning',
                    'arima': 'Statistical',
                    'linear': 'Regression'
                }.get(model_name, 'Unknown'),
                'status': 'Active'
            })
        
        return model_info
    
    def _calculate_metrics(self, actual, forecast):
        """Calculate forecast accuracy metrics"""
        if len(actual) == 0 or len(forecast) == 0:
            return {}
        
        # Align data
        actual_dates = actual['ds'].values
        forecast_dates = [f['ds'] for f in forecast]
        
        # For metrics, we'll use the last N actual values that align with forecast
        min_len = min(len(actual), len(forecast))
        if min_len == 0:
            return {}
        
        actual_values = actual['y'].iloc[-min_len:].values
        forecast_values = [f['yhat'] for f in forecast[:min_len]]
        
        metrics = {
            'mae': mean_absolute_error(actual_values, forecast_values),
            'rmse': np.sqrt(mean_squared_error(actual_values, forecast_values)),
            'mape': np.mean(np.abs((actual_values - forecast_values) / actual_values)) * 100,
            'r2': r2_score(actual_values, forecast_values)
        }
        
        return metrics