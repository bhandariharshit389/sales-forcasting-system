// Dashboard helper functions and utilities

class DashboardUtils {
    static formatCurrency(value) {
        if (value >= 10000000) {
            return (value / 10000000).toFixed(2) + ' Cr';
        } else if (value >= 100000) {
            return (value / 100000).toFixed(2) + ' L';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(2) + ' K';
        }
        return value.toFixed(2);
    }

    static formatDate(date) {
        return new Date(date).toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }

    static getColorPalette(length) {
        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c', 
            '#4facfe', '#43e97b', '#fa709a', '#fee140',
            '#a8edea', '#fed6e3', '#d299c2', '#fecfef'
        ];
        return colors.slice(0, length);
    }

    static getRandomColor() {
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#43e97b', '#fa709a', '#fee140'];
        return colors[Math.floor(Math.random() * colors.length)];
    }
}

// Export utilities
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardUtils;
}