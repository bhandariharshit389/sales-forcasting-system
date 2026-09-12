import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FeatureEngineer:
    def __init__(self):
        self.aggregated_features = {}
        
    def engineer_features(self, df):
        """Create additional features for modeling"""
        df = df.copy()
        
        # 1. Time-based features
        df = self.create_time_features(df)
        
        # 2. Price-based features
        df = self.create_price_features(df)
        
        # 3. Customer-based features
        df = self.create_customer_features(df)
        
        # 4. Product-based features
        df = self.create_product_features(df)
        
        # 5. Rating-based features
        df = self.create_rating_features(df)
        
        # 6. Rolling statistics
        df = self.create_rolling_features(df)
        
        return df
    
    def create_time_features(self, df):
        """Create time-based features"""
        # Day of year
        df['day_of_year'] = df['date'].dt.dayofyear
        
        # Week of year
        df['week_of_year'] = df['date'].dt.isocalendar().week
        
        # Is weekend
        df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)
        
        # Is holiday season (simplified)
        df['is_holiday_season'] = df['month'].isin([11, 12, 1]).astype(int)
        
        return df
    
    def create_price_features(self, df):
        """Create price-related features"""
        # Discount indicator (if any price variation exists)
        # For now, we'll create a simple price tier feature
        df['price_tier'] = pd.cut(df['unit_price_inr'], 
                                 bins=[0, 500, 2000, 5000, 10000, float('inf')],
                                 labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
        
        # Total value tier
        df['order_value_tier'] = pd.cut(df['total_sales_inr'],
                                       bins=[0, 1000, 5000, 10000, 30000, float('inf')],
                                       labels=['Small', 'Medium', 'Large', 'Very Large', 'Huge'])
        
        return df
    
    def create_customer_features(self, df):
        """Create customer-based features"""
        # Customer purchase frequency
        customer_purchase_count = df.groupby('customerID').size()
        df['customer_purchase_count'] = df['customerID'].map(customer_purchase_count)
        
        # Customer total spend
        customer_total_spend = df.groupby('customerID')['total_sales_inr'].sum()
        df['customer_total_spend'] = df['customerID'].map(customer_total_spend)
        
        # Customer average order value
        customer_avg_order = df.groupby('customerID')['total_sales_inr'].mean()
        df['customer_avg_order_value'] = df['customerID'].map(customer_avg_order)
        
        return df
    
    def create_product_features(self, df):
        """Create product-based features"""
        # Product popularity
        product_sales = df.groupby('product_name')['quantity'].sum()
        df['product_total_sold'] = df['product_name'].map(product_sales)
        
        # Category popularity
        category_sales = df.groupby('product_category')['quantity'].sum()
        df['category_total_sold'] = df['product_category'].map(category_sales)
        
        return df
    
    def create_rating_features(self, df):
        """Create rating-based features"""
        # Rating category
        df['rating_category'] = pd.cut(df['review_rating'],
                                      bins=[0, 2, 3, 4, 4.5, 5],
                                      labels=['Very Poor', 'Poor', 'Average', 'Good', 'Excellent'])
        
        # High rating indicator
        df['high_rating'] = (df['review_rating'] >= 4.5).astype(int)
        
        return df
    
    def create_rolling_features(self, df):
        """Create rolling statistics for time series"""
        # Sort by date
        df = df.sort_values('date')
        
        # 7-day rolling average of sales
        df['sales_7d_rolling_avg'] = df['total_sales_inr'].rolling(window=7, min_periods=1).mean()
        
        # 30-day rolling average
        df['sales_30d_rolling_avg'] = df['total_sales_inr'].rolling(window=30, min_periods=1).mean()
        
        # Cumulative sales
        df['cumulative_sales'] = df['total_sales_inr'].cumsum()
        
        return df