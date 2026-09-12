import pandas as pd
import numpy as np
from datetime import datetime
import re

class DataPreprocessor:
    def __init__(self):
        self.numeric_cols = ['quantity', 'unit_price_inr', 'total_sales_inr', 'review_rating']
        self.categorical_cols = ['product_category', 'payment_method', 'delivery_status', 'state', 'country']
        
    def preprocess(self, df):
        """Main preprocessing pipeline"""
        df = df.copy()
        
        # Convert date
        df['date'] = pd.to_datetime(df['date'])
        
        # Handle missing values
        df = self.handle_missing_values(df)
        
        # Convert data types
        df = self.convert_data_types(df)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['orderID'])
        
        # Extract additional date features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['weekday'] = df['date'].dt.weekday
        df['quarter'] = df['date'].dt.quarter
        
        return df
    
    def handle_missing_values(self, df):
        """Handle missing values in the dataset"""
        # Numeric columns - fill with median
        for col in self.numeric_cols:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())
        
        # Categorical columns - fill with mode
        for col in self.categorical_cols:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown')
        
        # Text columns - fill with empty string
        if 'reviews_text' in df.columns:
            df['reviews_text'] = df['reviews_text'].fillna('')
        
        return df
    
    def convert_data_types(self, df):
        """Convert columns to appropriate data types"""
        # Convert orderID to string
        if 'orderID' in df.columns:
            df['orderID'] = df['orderID'].astype(str)
        
        # Convert customerID to string
        if 'customerID' in df.columns:
            df['customerID'] = df['customerID'].astype(str)
        
        # Convert numeric columns
        for col in ['quantity', 'unit_price_inr', 'total_sales_inr', 'review_rating']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def remove_outliers(self, df, column, method='iqr'):
        """Remove outliers from numeric columns"""
        if method == 'iqr':
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
        return df