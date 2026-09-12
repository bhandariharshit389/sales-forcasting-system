import pandas as pd
import numpy as np

class InsightsGenerator:
    def generate_insights(self, summary, forecast, sentiment, df):
        """Generate business insights and recommendations"""
        insights = {
            'summary': self._generate_summary_insights(summary),
            'forecast_insights': self._generate_forecast_insights(forecast),
            'customer_insights': self._generate_customer_insights(df),
            'product_insights': self._generate_product_insights(df),
            'sentiment_insights': self._generate_sentiment_insights(sentiment),
            'recommendations': self._generate_recommendations(summary, forecast, sentiment, df)
        }
        
        return insights
    
    def _generate_summary_insights(self, summary):
        """Generate insights from summary data"""
        insights = []
        
        if summary['total_revenue'] > 0:
            insights.append(f"Total revenue is ₹{summary['total_revenue']:,.2f} from {summary['total_orders']} orders")
        
        if summary['average_order_value'] > 0:
            insights.append(f"Average order value is ₹{summary['average_order_value']:,.2f}")
        
        if summary['average_rating'] > 0:
            insights.append(f"Average customer rating is {summary['average_rating']:.1f} out of 5")
        
        # Top category insight
        if summary.get('top_categories'):
            top_cat = list(summary['top_categories'].keys())[0]
            insights.append(f"Top performing category: {top_cat}")
        
        return insights
    
    def _generate_forecast_insights(self, forecast):
        """Generate insights from forecast data"""
        if not forecast or 'forecast' not in forecast:
            return "No forecast data available"
        
        forecast_values = forecast['forecast']
        if not forecast_values:
            return "No forecast data available"
        
        insights = []
        
        # Calculate predicted total
        total_forecast = sum([f['yhat'] for f in forecast_values])
        avg_monthly = total_forecast / len(forecast_values)
        
        insights.append(f"Predicted total sales for next period: ₹{total_forecast:,.2f}")
        insights.append(f"Average monthly predicted sales: ₹{avg_monthly:,.2f}")
        
        # Trend analysis
        if len(forecast_values) > 1:
            first_value = forecast_values[0]['yhat']
            last_value = forecast_values[-1]['yhat']
            growth_rate = ((last_value - first_value) / first_value) * 100 if first_value > 0 else 0
            
            if growth_rate > 5:
                insights.append(f"📈 Growth trend: +{growth_rate:.1f}% increase expected")
            elif growth_rate < -5:
                insights.append(f"📉 Growth trend: {growth_rate:.1f}% decrease expected")
            else:
                insights.append("➡️ Stable growth trend expected")
        
        return insights
    
    def _generate_customer_insights(self, df):
        """Generate customer-related insights"""
        insights = []
        
        # Customer distribution
        total_customers = df['customerID'].nunique()
        total_orders = len(df)
        avg_orders_per_customer = total_orders / total_customers if total_customers > 0 else 0
        
        insights.append(f"Total unique customers: {total_customers}")
        insights.append(f"Average orders per customer: {avg_orders_per_customer:.2f}")
        
        # Repeat customers
        customer_orders = df.groupby('customerID')['orderID'].count()
        repeat_customers = len([x for x in customer_orders if x > 1])
        repeat_rate = (repeat_customers / total_customers) * 100 if total_customers > 0 else 0
        
        insights.append(f"Repeat customer rate: {repeat_rate:.1f}%")
        
        # Top states
        top_states = df['state'].value_counts().head(3)
        for state, count in top_states.items():
            insights.append(f"Top state: {state} with {count} orders")
        
        return insights
    
    def _generate_product_insights(self, df):
        """Generate product-related insights"""
        insights = []
        
        # Best selling products
        top_products = df.groupby('product_name')['quantity'].sum().sort_values(ascending=False).head(5)
        
        if not top_products.empty:
            insights.append("Top selling products:")
            for product, qty in top_products.items():
                insights.append(f"  - {product}: {qty} units sold")
        
        # Revenue by product
        top_revenue = df.groupby('product_name')['total_sales_inr'].sum().sort_values(ascending=False).head(3)
        
        if not top_revenue.empty:
            insights.append("Highest revenue products:")
            for product, revenue in top_revenue.items():
                insights.append(f"  - {product}: ₹{revenue:,.2f}")
        
        return insights
    
    def _generate_sentiment_insights(self, sentiment):
        """Generate insights from sentiment analysis"""
        if not sentiment or 'error' in sentiment:
            return ["Sentiment analysis data not available"]
        
        insights = []
        
        if 'sentiment_distribution' in sentiment:
            dist = sentiment['sentiment_distribution']
            total = sum(dist.values())
            
            positive_pct = (dist.get('positive', 0) / total) * 100
            negative_pct = (dist.get('negative', 0) / total) * 100
            neutral_pct = (dist.get('neutral', 0) / total) * 100
            
            insights.append(f"Positive reviews: {positive_pct:.1f}%")
            insights.append(f"Negative reviews: {negative_pct:.1f}%")
            insights.append(f"Neutral reviews: {neutral_pct:.1f}%")
            
            if positive_pct > 70:
                insights.append("😊 Overall customer sentiment is very positive!")
            elif positive_pct > 50:
                insights.append("👍 Overall customer sentiment is positive")
            else:
                insights.append("🔍 There may be opportunities to improve customer satisfaction")
        
        return insights
    
    def _generate_recommendations(self, summary, forecast, sentiment, df):
        """Generate actionable recommendations"""
        recommendations = []
        
        # Revenue-based recommendations
        if summary['average_order_value'] < 5000:
            recommendations.append("💡 Consider upselling strategies to increase average order value")
        
        # Customer-based recommendations
        customer_orders = df.groupby('customerID')['orderID'].count()
        repeat_rate = len([x for x in customer_orders if x > 1]) / len(customer_orders) if len(customer_orders) > 0 else 0
        if repeat_rate < 0.3:
            recommendations.append("💡 Implement customer loyalty programs to increase repeat purchases")
        
        # Product-based recommendations
        top_category = df.groupby('product_category')['total_sales_inr'].sum().sort_values(ascending=False)
        if not top_category.empty:
            top_cat = top_category.index[0]
            bottom_cat = top_category.index[-1]
            recommendations.append(f"💡 Focus on the {top_cat} category which shows highest performance")
            recommendations.append(f"💡 Consider marketing strategies for {bottom_cat} category to improve sales")
        
        # State-based recommendations
        top_state = df['state'].value_counts().index[0] if not df['state'].empty else None
        if top_state:
            recommendations.append(f"💡 Top performing state is {top_state} - consider targeted campaigns there")
        
        # Sentiment-based recommendations
        if sentiment and 'sentiment_distribution' in sentiment:
            negative_pct = sentiment['sentiment_distribution'].get('negative', 0) / sum(sentiment['sentiment_distribution'].values()) * 100
            if negative_pct > 20:
                recommendations.append("💡 Review negative feedback patterns to improve product quality")
        
        # Forecast-based recommendations
        if forecast and 'forecast' in forecast and forecast['forecast']:
            forecast_values = forecast['forecast']
            if len(forecast_values) > 1:
                growth_rate = ((forecast_values[-1]['yhat'] - forecast_values[0]['yhat']) / forecast_values[0]['yhat']) * 100 if forecast_values[0]['yhat'] > 0 else 0
                if growth_rate > 10:
                    recommendations.append("💡 Prepare for growth: increase inventory and staff accordingly")
                elif growth_rate < -5:
                    recommendations.append("💡 Develop new promotional strategies to counter expected decline")
        
        # Add some seasonal recommendations
        current_month = datetime.now().month
        if current_month in [11, 12]:
            recommendations.append("🎄 Holiday season approaching: ensure sufficient stock and promotions")
        elif current_month in [2, 3]:
            recommendations.append("🌸 Consider spring collection launch strategies")
        
        return recommendations