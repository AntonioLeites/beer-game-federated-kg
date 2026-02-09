// Dashboard V3.3 Configuration
const CONFIG = {
    graphdb: {
        url: 'http://localhost:8001',
        repository: 'BG_Supply_Chain'  
    },
    visualization: {
        width: 1200,
        height: 600,
        margin: {
            top: 40,
            right: 30,
            bottom: 50,
            left: 150
        },
        pointRadius: {
            min: 6,
            max: 25
        }
    },
    colors: {
        risk: {
            low: '#4CAF50',      // Green
            medium: '#FFC107',   // Yellow
            high: '#FF9800',     // Orange
            critical: '#F44336'  // Red
        },
        quality: {
            optimal: '#2196F3',  // Blue
            good: '#4CAF50',     // Green
            suboptimal: '#FF9800', // Orange
            poor: '#F44336',     // Red
            unknown: '#9E9E9E'   // Gray
        },
        decisionType: {
            ActionDecision: '#2196F3',  // Blue
            NoActionDecision: '#9E9E9E' // Gray
        }
    },
    animation: {
        defaultSpeed: 1.0,  // 1x by default
        speeds: [0.5, 1.0, 2.0, 4.0]
    }
};

// Export for use in other files (e.g., queries.js)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
