// Forecasting-specific functionality

class ForecastingManager {
    constructor() {
        this.baseURL = 'http://localhost:5000/api';
        this.forecastData = null;
        this.forecastChart = null;
        this.modelMetrics = {};
        this.periods = 12;
        this.selectedModel = 'ensemble';
        this.modelColors = {
            'ensemble': '#764ba2',
            'prophet': '#4facfe',
            'xgboost': '#43e97b',
            'arima': '#fa709a',
            'linear': '#fee140'
        };
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Add model selector if it exists
        const modelSelector = document.getElementById('modelSelector');
        if (modelSelector) {
            modelSelector.addEventListener('change', (e) => {
                this.selectedModel = e.target.value;
                this.updateForecastDisplay();
            });
        }

        // Add period selector if it exists
        const periodSelector = document.getElementById('periodSelector');
        if (periodSelector) {
            periodSelector.addEventListener('change', (e) => {
                this.periods = parseInt(e.target.value);
                this.generateForecast(this.periods);
            });
        }
    }

    async generateForecast(periods = 12) {
        try {
            const response = await axios.post(`${this.baseURL}/forecasting/predict`, {
                periods: periods
            });
            this.forecastData = response.data;
            this.modelMetrics = response.data.metrics || {};
            
            // Display forecast details and charts
            this.displayForecastDetails(response.data);
            this.displayModelComparison(response.data);
            this.displayForecastMetrics(response.data);
            
            // Update the main forecast chart (managed by main app)
            if (window.dashboard && window.dashboard.charts) {
                this.updateMainForecastChart(response.data);
            }
            
            return response.data;
        } catch (error) {
            console.error('Error generating forecast:', error);
            this.showError('Failed to generate forecast. Please try again.');
            throw error;
        }
    }

    updateMainForecastChart(data) {
        // This method will be called to update the main forecast chart
        // The main app will handle the chart update
        if (window.dashboard && window.dashboard.charts.forecast) {
            const forecastData = data.forecast || [];
            const labels = forecastData.map(d => {
                const date = new Date(d.ds);
                return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
            });
            const values = forecastData.map(d => d.yhat);
            
            window.dashboard.charts.forecast.data.labels = labels;
            window.dashboard.charts.forecast.data.datasets[0].data = values;
            window.dashboard.charts.forecast.update();
        }
    }

    displayForecastDetails(data) {
        const container = document.getElementById('forecastDetails');
        if (!container) return;

        const forecast = data.forecast || [];
        
        // Calculate total forecast
        const totalForecast = forecast.reduce((sum, item) => sum + item.yhat, 0);
        const avgMonthly = totalForecast / (forecast.length || 1);

        let html = `
            <div class="forecast-summary">
                <div class="forecast-stats">
                    <div class="stat-card">
                        <span class="stat-label">Total Predicted Revenue</span>
                        <span class="stat-value">₹${this.formatCurrency(totalForecast)}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Average Monthly Revenue</span>
                        <span class="stat-value">₹${this.formatCurrency(avgMonthly)}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Forecast Period</span>
                        <span class="stat-value">${forecast.length} Months</span>
                    </div>
                </div>
            </div>
            <div class="forecast-table-wrapper">
                <h4>📊 Monthly Forecast Details</h4>
                <div class="table-responsive">
                    <table class="forecast-table">
                        <thead>
                            <tr>
                                <th>Month</th>
                                <th>Predicted Sales (₹)</th>
                                <th>Growth Rate</th>
                                <th>Confidence Level</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        let previousValue = forecast.length > 0 ? forecast[0].yhat : 0;
        
        forecast.forEach((item, index) => {
            const date = new Date(item.ds);
            const month = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
            const value = item.yhat;
            
            // Calculate growth rate
            let growthRate = 0;
            if (index > 0 && previousValue > 0) {
                growthRate = ((value - previousValue) / previousValue) * 100;
            }
            previousValue = value;
            
            // Confidence level based on ensemble variance (simplified)
            const confidence = this.calculateConfidence(index, data);
            
            const growthColor = growthRate > 0 ? '#43e97b' : growthRate < 0 ? '#fa709a' : '#fee140';
            const growthArrow = growthRate > 0 ? '↑' : growthRate < 0 ? '↓' : '→';
            
            html += `
                <tr>
                    <td>${month}</td>
                    <td>₹${value.toFixed(2)}</td>
                    <td style="color: ${growthColor}; font-weight: 600;">
                        ${growthArrow} ${Math.abs(growthRate).toFixed(1)}%
                    </td>
                    <td>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${confidence}%"></div>
                            <span>${confidence.toFixed(0)}%</span>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    displayModelComparison(data) {
        const container = document.getElementById('modelComparison');
        if (!container) return;

        const individualForecasts = data.individual_forecasts || {};
        const modelInfo = data.model_info || [];
        
        if (Object.keys(individualForecasts).length === 0) {
            container.innerHTML = '<p class="no-data">No individual model forecasts available</p>';
            return;
        }

        let html = `
            <h4>🤖 Model Comparison</h4>
            <div class="model-comparison-grid">
        `;

        Object.keys(individualForecasts).forEach(modelName => {
            const modelData = individualForecasts[modelName];
            const info = modelInfo.find(m => m.name === modelName) || {};
            const color = this.modelColors[modelName] || '#999';
            
            // Calculate total for this model
            const total = modelData.reduce((sum, item) => sum + item.yhat, 0);
            const avg = total / (modelData.length || 1);
            
            html += `
                <div class="model-card" style="border-left: 4px solid ${color};">
                    <div class="model-header">
                        <h5>${modelName.charAt(0).toUpperCase() + modelName.slice(1)}</h5>
                        <span class="model-type-badge">${info.type || 'Unknown'}</span>
                    </div>
                    <div class="model-stats">
                        <div class="model-stat">
                            <span class="stat-label">Total Forecast</span>
                            <span class="stat-value">₹${this.formatCurrency(total)}</span>
                        </div>
                        <div class="model-stat">
                            <span class="stat-label">Average Monthly</span>
                            <span class="stat-value">₹${this.formatCurrency(avg)}</span>
                        </div>
                        <div class="model-stat">
                            <span class="stat-label">Status</span>
                            <span class="stat-value ${info.status === 'Active' ? 'status-active' : 'status-inactive'}">${info.status || 'Unknown'}</span>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `
            </div>
            <div class="ensemble-note">
                <p><strong>Ensemble Method:</strong> Weighted average of all models for final prediction</p>
            </div>
        `;

        container.innerHTML = html;
    }

    displayForecastMetrics(data) {
        const container = document.getElementById('forecastMetrics');
        if (!container) return;

        const metrics = data.metrics || {};
        
        if (Object.keys(metrics).length === 0) {
            container.innerHTML = '<p class="no-data">No metrics available</p>';
            return;
        }

        let html = `
            <h4>📈 Forecast Accuracy Metrics</h4>
            <div class="metrics-grid">
        `;

        const metricDescriptions = {
            'mae': 'Mean Absolute Error',
            'rmse': 'Root Mean Square Error',
            'mape': 'Mean Absolute Percentage Error',
            'r2': 'R² Score'
        };

        const metricIcons = {
            'mae': '📊',
            'rmse': '📐',
            'mape': '🎯',
            'r2': '⭐'
        };

        Object.keys(metrics).forEach(key => {
            const value = metrics[key];
            const description = metricDescriptions[key] || key.toUpperCase();
            const icon = metricIcons[key] || '📈';
            
            let displayValue = value;
            let suffix = '';
            
            if (key === 'mape') {
                displayValue = value.toFixed(1);
                suffix = '%';
            } else if (key === 'r2') {
                displayValue = (value * 100).toFixed(1);
                suffix = '%';
            } else if (typeof value === 'number') {
                displayValue = this.formatCurrency(value);
            }
            
            // Determine color based on metric
            let color = '#667eea';
            if (key === 'r2' && value < 0.5) color = '#fa709a';
            if (key === 'mape' && value < 10) color = '#43e97b';
            if (key === 'mape' && value > 20) color = '#fa709a';
            
            html += `
                <div class="metric-card" style="border-bottom: 3px solid ${color};">
                    <div class="metric-icon">${icon}</div>
                    <div class="metric-content">
                        <div class="metric-label">${description}</div>
                        <div class="metric-value">${displayValue}${suffix}</div>
                    </div>
                </div>
            `;
        });

        html += `
            </div>
        `;

        container.innerHTML = html;
    }

    calculateConfidence(index, data) {
        // Simplified confidence calculation based on model agreement
        const individualForecasts = data.individual_forecasts || {};
        const modelCount = Object.keys(individualForecasts).length;
        
        if (modelCount === 0 || !individualForecasts.ensemble) return 85;
        
        // Get predictions from all models for this index
        const predictions = [];
        Object.keys(individualForecasts).forEach(modelName => {
            const forecast = individualForecasts[modelName];
            if (forecast && forecast[index]) {
                predictions.push(forecast[index].yhat);
            }
        });
        
        if (predictions.length === 0) return 85;
        
        // Calculate variance
        const mean = predictions.reduce((a, b) => a + b, 0) / predictions.length;
        const variance = predictions.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / predictions.length;
        const stdDev = Math.sqrt(variance);
        
        // Confidence decreases with higher variance
        const cv = mean > 0 ? stdDev / mean : 0.5;
        let confidence = Math.max(60, Math.min(95, 100 - (cv * 100)));
        
        return confidence;
    }

    formatCurrency(value) {
        if (value >= 10000000) {
            return (value / 10000000).toFixed(2) + ' Cr';
        } else if (value >= 100000) {
            return (value / 100000).toFixed(2) + ' L';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(2) + ' K';
        }
        return value.toFixed(2);
    }

    showError(message) {
        const container = document.getElementById('forecastDetails');
        if (container) {
            container.innerHTML = `
                <div class="error-message">
                    <span class="error-icon">⚠️</span>
                    <p>${message}</p>
                </div>
            `;
        }
    }

    updateForecastDisplay() {
        // Refresh the forecast display with current data
        if (this.forecastData) {
            this.displayForecastDetails(this.forecastData);
        }
    }

    async getForecastHistory() {
        try {
            const response = await axios.get(`${this.baseURL}/forecasting/history`);
            return response.data;
        } catch (error) {
            console.error('Error fetching forecast history:', error);
            return null;
        }
    }

    async exportForecastReport() {
        try {
            const response = await axios.get(`${this.baseURL}/forecasting/export`, {
                responseType: 'blob'
            });
            
            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'forecast_report.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Error exporting forecast:', error);
            this.showError('Failed to export forecast report');
        }
    }
}

// Initialize forecasting manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('forecastDetails')) {
        window.forecastManager = new ForecastingManager();
        
        // Auto-generate forecast if not already loaded
        if (!window.forecastManager.forecastData) {
            window.forecastManager.generateForecast(12);
        }
    }
});

// Export for use in main app
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ForecastingManager;
}