import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class AnalyticsGenerator:
    def generate_summary(self, df):
        """Generate summary statistics"""
        summary = {
            'total_orders': len(df),
            'total_revenue': df['total_sales_inr'].sum(),
            'average_order_value': df['total_sales_inr'].mean(),
            'total_products_sold': df['quantity'].sum(),
            'unique_customers': df['customerID'].nunique(),
            'unique_products': df['product_name'].nunique(),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d')
            },
            'average_rating': df['review_rating'].mean(),
            'top_categories': self._get_top_categories(df),
            'monthly_revenue': self._get_monthly_revenue(df)
        }
        return summary
    
    def _get_top_categories(self, df, n=5):
        """Get top performing categories"""
        category_revenue = df.groupby('product_category')['total_sales_inr'].sum().sort_values(ascending=False)
        return category_revenue.head(n).to_dict()
    
    def _get_monthly_revenue(self, df):
        """Get monthly revenue trends"""
        monthly = df.groupby(df['date'].dt.to_period('M'))['total_sales_inr'].sum()
        return monthly.to_dict()
    
    def sales_by_category(self, df):
        """Analyze sales by category"""
        category_analysis = df.groupby('product_category').agg({
            'total_sales_inr': ['sum', 'mean', 'count'],
            'quantity': 'sum',
            'review_rating': 'mean'
        }).round(2)
        
        # Format for JSON response
        result = {}
        for category in category_analysis.index:
            result[category] = {
                'total_revenue': float(category_analysis.loc[category, ('total_sales_inr', 'sum')]),
                'average_order_value': float(category_analysis.loc[category, ('total_sales_inr', 'mean')]),
                'order_count': int(category_analysis.loc[category, ('total_sales_inr', 'count')]),
                'total_quantity': int(category_analysis.loc[category, ('quantity', 'sum')]),
                'average_rating': float(category_analysis.loc[category, ('review_rating', 'mean')])
            }
        
        return result
    
    def sales_over_time(self, df, timeframe='monthly'):
        """Get sales trends over time"""
        if timeframe == 'daily':
            date_col = df['date'].dt.date
        elif timeframe == 'weekly':
            date_col = df['date'].dt.to_period('W').dt.start_time
        elif timeframe == 'quarterly':
            date_col = df['date'].dt.to_period('Q').dt.start_time
        else:  # monthly
            date_col = df['date'].dt.to_period('M').dt.start_time
        
        time_series = df.groupby(date_col).agg({
            'total_sales_inr': 'sum',
            'quantity': 'sum',
            'orderID': 'count'
        }).reset_index()
        
        time_series.columns = ['date', 'revenue', 'quantity', 'orders']
        time_series['date'] = time_series['date'].astype(str)
        
        return time_series.to_dict('records')
    
    def customer_insights(self, df):
        """Generate customer insights"""
        # Customer purchase patterns
        customer_orders = df.groupby('customerID')['orderID'].count()
        customer_spend = df.groupby('customerID')['total_sales_inr'].sum()
        customer_avg = df.groupby('customerID')['total_sales_inr'].mean()
        
        # Segment customers
        segments = {
            'new_customers': len([x for x in customer_orders if x == 1]),
            'regular_customers': len([x for x in customer_orders if 1 < x <= 5]),
            'frequent_customers': len([x for x in customer_orders if x > 5])
        }
        
        insights = {
            'total_customers': len(df['customerID'].unique()),
            'customer_segments': segments,
            'average_orders_per_customer': customer_orders.mean(),
            'average_spend_per_customer': customer_spend.mean(),
            'top_spenders': customer_spend.nlargest(5).to_dict(),
            'repeat_purchase_rate': len([x for x in customer_orders if x > 1]) / len(customer_orders) * 100 if len(customer_orders) > 0 else 0
        }
        
        return insights
    
    def payment_method_distribution(self, df):
        """Analyze payment method usage"""
        payment_counts = df['payment_method'].value_counts()
        payment_revenue = df.groupby('payment_method')['total_sales_inr'].sum()
        
        return {
            'counts': payment_counts.to_dict(),
            'revenue': payment_revenue.to_dict()
        }
    
    def delivery_status_distribution(self, df):
        """Analyze delivery status"""
        status_counts = df['delivery_status'].value_counts()
        status_revenue = df.groupby('delivery_status')['total_sales_inr'].sum()
        
        return {
            'counts': status_counts.to_dict(),
            'revenue': status_revenue.to_dict()
        }