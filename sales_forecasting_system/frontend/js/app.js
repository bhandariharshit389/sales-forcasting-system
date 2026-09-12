// Main application controller
class SalesDashboard {
    constructor() {
        this.baseURL = 'http://localhost:5000/api';
        this.charts = {};
        this.init();
    }

    async init() {
        try {
            // Load all dashboard data
            await this.loadSummary();
            await this.loadCharts();
            await this.loadForecast();
            await this.loadInsights();
            await this.loadModelInfo();
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to load dashboard data. Please check if the backend server is running.');
        }
    }

    async loadSummary() {
        try {
            const response = await axios.get(`${this.baseURL}/dashboard/summary`);
            const data = response.data;
            
            document.getElementById('totalRevenue').textContent = this.formatCurrency(data.total_revenue);
            document.getElementById('totalOrders').textContent = data.total_orders.toLocaleString();
            document.getElementById('avgOrderValue').textContent = this.formatCurrency(data.average_order_value);
            document.getElementById('avgRating').textContent = data.average_rating.toFixed(1);
            document.getElementById('totalCustomers').textContent = data.unique_customers.toLocaleString();
            document.getElementById('totalProductsSold').textContent = data.total_products_sold.toLocaleString();
            
            // Remove loading state
            document.querySelectorAll('.card').forEach(card => {
                card.classList.remove('loading');
            });
        } catch (error) {
            console.error('Error loading summary:', error);
        }
    }

    async loadCharts() {
        try {
            // Load sales trend
            const trendResponse = await axios.get(`${this.baseURL}/analytics/sales-over-time?timeframe=monthly`);
            this.createSalesTrendChart(trendResponse.data);
            
            // Load category data
            const categoryResponse = await axios.get(`${this.baseURL}/analytics/sales-by-category`);
            this.createCategoryChart(categoryResponse.data);
            
            // Load payment methods
            const paymentResponse = await axios.get(`${this.baseURL}/analytics/payment-methods`);
            this.createPaymentChart(paymentResponse.data);
            
            // Load delivery status
            const deliveryResponse = await axios.get(`${this.baseURL}/analytics/delivery-status`);
            this.createDeliveryChart(deliveryResponse.data);
            
            // Load sentiment
            const sentimentResponse = await axios.get(`${this.baseURL}/sentiment/analysis`);
            this.createSentimentChart(sentimentResponse.data);
            
            // Load customer insights
            const customerResponse = await axios.get(`${this.baseURL}/analytics/customer-insights`);
            this.createCustomerChart(customerResponse.data);
            
            // Load top products
            this.createTopProductsChart();
        } catch (error) {
            console.error('Error loading charts:', error);
        }
    }

    async loadForecast() {
        try {
            const response = await axios.post(`${this.baseURL}/forecasting/predict`, {
                periods: 12
            });
            this.createForecastChart(response.data);
        } catch (error) {
            console.error('Error loading forecast:', error);
        }
    }

    async loadInsights() {
        try {
            const response = await axios.get(`${this.baseURL}/insights/generate`);
            this.displayInsights(response.data);
        } catch (error) {
            console.error('Error loading insights:', error);
        }
    }

    async loadModelInfo() {
        try {
            const response = await axios.get(`${this.baseURL}/forecasting/model-info`);
            this.displayModelInfo(response.data);
        } catch (error) {
            console.error('Error loading model info:', error);
        }
    }

    createSalesTrendChart(data) {
        const ctx = document.getElementById('salesTrendChart').getContext('2d');
        const labels = data.map(d => d.date);
        const values = data.map(d => d.revenue);
        
        this.charts.salesTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Revenue (₹)',
                    data: values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    createCategoryChart(data) {
        const ctx = document.getElementById('categoryChart').getContext('2d');
        const categories = Object.keys(data);
        const values = categories.map(cat => data[cat].total_revenue);
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'];
        
        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: categories,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, categories.length),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ₹${context.parsed.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        });
    }

    createForecastChart(data) {
        const ctx = document.getElementById('forecastChart').getContext('2d');
        
        // Extract forecast data
        const forecastData = data.forecast || [];
        const labels = forecastData.map(d => {
            const date = new Date(d.ds);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        });
        const values = forecastData.map(d => d.yhat);
        
        this.charts.forecast = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predicted Sales (₹)',
                    data: values,
                    backgroundColor: 'rgba(118, 75, 162, 0.7)',
                    borderColor: '#764ba2',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    createPaymentChart(data) {
        const ctx = document.getElementById('paymentChart').getContext('2d');
        const methods = Object.keys(data.counts);
        const values = methods.map(m => data.counts[m]);
        const colors = ['#4facfe', '#43e97b', '#fa709a', '#fee140'];
        
        this.charts.payment = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: methods,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, methods.length),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createDeliveryChart(data) {
        const ctx = document.getElementById('deliveryChart').getContext('2d');
        const statuses = Object.keys(data.counts);
        const values = statuses.map(s => data.counts[s]);
        const colors = ['#43e97b', '#fa709a', '#fee140'];
        
        this.charts.delivery = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: statuses,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, statuses.length),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createSentimentChart(data) {
        const ctx = document.getElementById('sentimentChart').getContext('2d');
        
        if (data.error) {
            document.getElementById('sentimentChart').parentElement.innerHTML = 
                '<p style="text-align:center;color:#999;">No review data available</p>';
            return;
        }
        
        const distribution = data.sentiment_distribution || {};
        const labels = Object.keys(distribution);
        const values = labels.map(l => distribution[l]);
        const colors = ['#43e97b', '#fa709a', '#fee140'];
        
        this.charts.sentiment = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of Reviews',
                    data: values,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    createCustomerChart(data) {
        const ctx = document.getElementById('customerChart').getContext('2d');
        const segments = data.customer_segments || {};
        const labels = Object.keys(segments).map(key => {
            return key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        });
        const values = Object.values(segments);
        const colors = ['#667eea', '#764ba2', '#f093fb'];
        
        this.charts.customer = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of Customers',
                    data: values,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    createTopProductsChart() {
        // Since we don't have a specific API endpoint for top products,
        // we'll get it from the summary data or skip this chart
        // For now, we'll show a placeholder
        const ctx = document.getElementById('topProductsChart').getContext('2d');
        
        // Placeholder data - in a real implementation, this would come from an API
        const placeholderData = {
            labels: ['Product A', 'Product B', 'Product C', 'Product D', 'Product E'],
            values: [100, 80, 60, 40, 20]
        };
        
        this.charts.topProducts = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: placeholderData.labels,
                datasets: [{
                    label: 'Units Sold',
                    data: placeholderData.values,
                    backgroundColor: 'rgba(245, 87, 108, 0.7)',
                    borderColor: '#f5576c',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    displayInsights(data) {
        const container = document.getElementById('insightsContainer');
        
        let html = '';
        
        // Summary insights
        if (data.summary && data.summary.length > 0) {
            html += `<div class="insight-card">
                <h4>📊 Summary</h4>
                <ul>
                    ${data.summary.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        // Customer insights
        if (data.customer_insights && data.customer_insights.length > 0) {
            html += `<div class="insight-card">
                <h4>👥 Customer Insights</h4>
                <ul>
                    ${data.customer_insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        // Product insights
        if (data.product_insights && data.product_insights.length > 0) {
            html += `<div class="insight-card">
                <h4>📦 Product Insights</h4>
                <ul>
                    ${data.product_insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        // Sentiment insights
        if (data.sentiment_insights && data.sentiment_insights.length > 0) {
            html += `<div class="insight-card">
                <h4>💬 Sentiment Insights</h4>
                <ul>
                    ${data.sentiment_insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        // Forecast insights
        if (data.forecast_insights && data.forecast_insights.length > 0) {
            html += `<div class="insight-card">
                <h4>🔮 Forecast Insights</h4>
                <ul>
                    ${data.forecast_insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        // Recommendations
        if (data.recommendations && data.recommendations.length > 0) {
            html += `<div class="recommendations">
                <h3>💡 Recommendations</h3>
                <ul>
                    ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>`;
        }
        
        container.innerHTML = html;
    }

    displayModelInfo(data) {
        const container = document.getElementById('modelInfoContainer');
        
        let html = '';
        
        if (data.models) {
            data.models.forEach(model => {
                html += `
                    <div class="model-card">
                        <h4>${model.name}</h4>
                        <span class="model-type">${model.type}</span>
                        <p>${model.description}</p>
                        <p style="margin-top: 8px; color: #333;">
                            <strong>Use Case:</strong> ${model.use_case}
                        </p>
                    </div>
                `;
            });
        }
        
        if (data.metrics_used) {
            html += `
                <div class="model-card" style="grid-column: span 2;">
                    <h4>📈 Evaluation Metrics</h4>
                    <p><strong>Metrics:</strong> ${data.metrics_used.join(', ')}</p>
                    <p style="margin-top: 8px;"><strong>Ensemble Method:</strong> ${data.ensemble_method}</p>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }

    formatCurrency(value) {
        if (value >= 10000000) {
            return (value / 10000000).toFixed(1) + ' Cr';
        } else if (value >= 100000) {
            return (value / 100000).toFixed(1) + ' L';
        } else {
            return value.toLocaleString();
        }
    }

    showError(message) {
        const container = document.querySelector('.container');
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            background: #f8d7da;
            color: #721c24;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid #f5c6cb;
        `;
        errorDiv.innerHTML = `
            <h3>⚠️ Error</h3>
            <p>${message}</p>
        `;
        container.prepend(errorDiv);
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SalesDashboard();
});