// GraphDB Configuration
const CONFIG = {
    graphdb: {
        url: 'http://localhost:8001',
        repository: 'BG_Supply_Chain'
    },
    
    // Color schemes
    colors: {
        risk: {
            low: '#4CAF50',      // Green
            medium: '#FFC107',   // Amber
            high: '#FF9800',     // Orange
            critical: '#F44336'  // Red
        },
        quality: {
            optimal: '#4CAF50',
            good: '#8BC34A',
            suboptimal: '#FF9800',
            poor: '#F44336',
            unknown: '#9E9E9E'
        },
        actors: {
            'Retailer_Alpha': '#2196F3',
            'Wholesaler_Beta': '#9C27B0',
            'Distributor_Gamma': '#FF5722',
            'Factory_Delta': '#795548'
        }
    },
    
    // Visual settings
    visualization: {
        width: 1200,
        height: 500,
        margin: { top: 40, right: 40, bottom: 60, left: 150 },
        pointRadius: {
            min: 5,
            max: 20
        }
    }
};
