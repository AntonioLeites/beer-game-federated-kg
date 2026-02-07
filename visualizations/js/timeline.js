// Timeline Visualization with D3.js

class DecisionTimeline {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.svg = null;
        this.data = null;
        this.selectedContext = null;
        this.tooltip = null;
    }
    
    async init() {
        try {
            // Show loading
            this.showLoading();
            
            // Fetch data
            this.data = await fetchContexts();
            
            if (this.data.length === 0) {
                this.showError('No decision contexts found. Run a simulation first.');
                return;
            }
            
            // Create tooltip
            this.createTooltip();
            
            // Render
            this.render();
            this.updateStats();
            
        } catch (error) {
            console.error('Initialization failed:', error);
            this.showError(`Failed to load data: ${error.message}`);
        }
    }
    
    createTooltip() {
        // Remove existing tooltip if any
        d3.select('#tooltip').remove();
        
        // Create tooltip div
        this.tooltip = d3.select('body')
            .append('div')
            .attr('id', 'tooltip')
            .style('position', 'absolute')
            .style('visibility', 'hidden')
            .style('background', 'rgba(0, 0, 0, 0.9)')
            .style('color', 'white')
            .style('padding', '12px 16px')
            .style('border-radius', '6px')
            .style('font-size', '13px')
            .style('line-height', '1.6')
            .style('box-shadow', '0 4px 12px rgba(0,0,0,0.3)')
            .style('pointer-events', 'none')
            .style('z-index', '1000')
            .style('max-width', '300px');
    }
    
    showTooltip(event, d) {
        const amplification = (d.orderQty / d.demandRate).toFixed(2);
        const riskEmoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }[d.risk] || '⚪';
        
        const qualityEmoji = {
            'optimal': '✓',
            'good': '~',
            'suboptimal': '⚠',
            'poor': '✗',
            'unknown': '?'
        }[d.quality] || '';
        
        const html = `
            <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">
                Week ${d.week} - ${d.actorName}
            </div>
            <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 8px;">
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Order:</span> 
                    <strong>${d.orderQty} units</strong>
                </div>
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Risk:</span> 
                    <strong>${riskEmoji} ${d.risk.toUpperCase()}</strong>
                </div>
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Amplification:</span> 
                    <strong>${amplification}x</strong>
                </div>
                ${d.quality ? `
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Outcome:</span> 
                    <strong>${qualityEmoji} ${d.quality}</strong>
                </div>
                ` : ''}
            </div>
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 11px; opacity: 0.7;">
                Click for full details
            </div>
        `;
        
        this.tooltip
            .html(html)
            .style('visibility', 'visible');
        
        this.updateTooltipPosition(event);
    }
    
    updateTooltipPosition(event) {
        const tooltipNode = this.tooltip.node();
        const tooltipWidth = tooltipNode.offsetWidth;
        const tooltipHeight = tooltipNode.offsetHeight;
        
        let left = event.pageX + 15;
        let top = event.pageY - tooltipHeight / 2;
        
        // Keep tooltip within viewport
        if (left + tooltipWidth > window.innerWidth) {
            left = event.pageX - tooltipWidth - 15;
        }
        
        if (top < 10) {
            top = 10;
        } else if (top + tooltipHeight > window.innerHeight) {
            top = window.innerHeight - tooltipHeight - 10;
        }
        
        this.tooltip
            .style('left', `${left}px`)
            .style('top', `${top}px`);
    }
    
    hideTooltip() {
        this.tooltip.style('visibility', 'hidden');
    }
    
    showLoading() {
        this.container.html('<div class="loading">Loading decision contexts</div>');
    }
    
    showError(message) {
        this.container.html(`<div class="error">${message}</div>`);
    }
    
    render() {
        // Clear container
        this.container.html('');
        
        // Setup dimensions
        const { width, height, margin } = CONFIG.visualization;
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;
        
        // Create SVG
        this.svg = this.container
            .append('svg')
            .attr('width', width)
            .attr('height', height);
        
        const g = this.svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Get unique weeks and actors
        const weeks = [...new Set(this.data.map(d => d.week))].sort((a, b) => a - b);
        const actors = [...new Set(this.data.map(d => d.actorName))];
        
        // Scales
        const xScale = d3.scaleLinear()
            .domain([d3.min(weeks), d3.max(weeks)])
            .range([0, innerWidth]);
        
        const yScale = d3.scaleBand()
            .domain(actors)
            .range([0, innerHeight])
            .padding(0.3);
        
        const radiusScale = d3.scaleSqrt()
            .domain([0, d3.max(this.data, d => d.orderQty / d.demandRate)])
            .range([CONFIG.visualization.pointRadius.min, CONFIG.visualization.pointRadius.max]);
        
        // Grid
        g.append('g')
            .attr('class', 'grid')
            .selectAll('line')
            .data(weeks)
            .enter()
            .append('line')
            .attr('x1', d => xScale(d))
            .attr('x2', d => xScale(d))
            .attr('y1', 0)
            .attr('y2', innerHeight)
            .attr('stroke', '#eee');
        
        // Axes
        const xAxis = d3.axisBottom(xScale)
            .tickValues(weeks)
            .tickFormat(d => `Week ${d}`);
        
        g.append('g')
            .attr('class', 'axis x-axis')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis);
        
        const yAxis = d3.axisLeft(yScale);
        
        g.append('g')
            .attr('class', 'axis y-axis')
            .call(yAxis);
        
        // Decision points
        const self = this;
        const points = g.selectAll('.decision-point')
            .data(this.data)
            .enter()
            .append('circle')
            .attr('class', 'decision-point')
            .attr('cx', d => xScale(d.week))
            .attr('cy', d => yScale(d.actorName) + yScale.bandwidth() / 2)
            .attr('r', d => radiusScale(d.orderQty / d.demandRate))
            .attr('fill', d => CONFIG.colors.risk[d.risk] || '#999')
            .attr('opacity', 0.8)
            .on('click', (event, d) => this.showContextDetail(d))
            .on('mouseenter', function(event, d) {
                d3.select(this)
                    .attr('opacity', 1)
                    .attr('stroke', '#333')
                    .attr('stroke-width', 2);
                self.showTooltip(event, d);
            })
            .on('mousemove', (event) => {
                self.updateTooltipPosition(event);
            })
            .on('mouseleave', function() {
                d3.select(this)
                    .attr('opacity', 0.8)
                    .attr('stroke', 'none');
                self.hideTooltip();
            });
        
        // Quality indicators (small dots)
        g.selectAll('.quality-indicator')
            .data(this.data.filter(d => d.quality))
            .enter()
            .append('circle')
            .attr('class', 'quality-indicator')
            .attr('cx', d => xScale(d.week))
            .attr('cy', d => yScale(d.actorName) + yScale.bandwidth() / 2)
            .attr('r', 3)
            .attr('fill', d => CONFIG.colors.quality[d.quality] || '#999')
            .attr('stroke', 'white')
            .attr('stroke-width', 1)
            .style('pointer-events', 'none');
        
        // Legend
        this.renderLegend();
    }
    
    renderLegend() {
        const legend = d3.select('.legend');
        legend.html('');
        
        // Risk levels
        legend.append('div').style('font-weight', 'bold').text('Risk:');
        Object.entries(CONFIG.colors.risk).forEach(([risk, color]) => {
            const item = legend.append('div').attr('class', 'legend-item');
            item.append('div')
                .attr('class', 'legend-color')
                .style('background-color', color);
            item.append('span').text(risk);
        });
        
        legend.append('div').style('width', '100%');
        
        // Quality
        legend.append('div').style('font-weight', 'bold').text('Outcome:');
        Object.entries(CONFIG.colors.quality).forEach(([quality, color]) => {
            const item = legend.append('div').attr('class', 'legend-item');
            item.append('div')
                .attr('class', 'legend-color')
                .style('background-color', color);
            item.append('span').text(quality);
        });
    }
    
    showContextDetail(context) {
        this.selectedContext = context;
        
        const panel = d3.select('#detail-panel');
        panel.classed('hidden', false);
        
        const amplification = (context.orderQty / context.demandRate).toFixed(2);
        
        panel.html(`
            <div class="context-card">
                <h2>Week ${context.week} - ${context.actorName} Decision</h2>
                
                <div class="context-grid">
                    <div class="context-section">
                        <h3>Decision</h3>
                        <div class="context-row">
                            <span class="label">Order Quantity:</span>
                            <span class="value">${context.orderQty} units</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Policy:</span>
                            <span class="value">${context.policy}</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Amplification:</span>
                            <span class="value">${amplification}x</span>
                        </div>
                    </div>
                    
                    <div class="context-section">
                        <h3>State</h3>
                        <div class="context-row">
                            <span class="label">Inventory:</span>
                            <span class="value">${context.inventory} units</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Backlog:</span>
                            <span class="value">${context.backlog} units</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Coverage:</span>
                            <span class="value">${context.coverage.toFixed(1)} weeks</span>
                        </div>
                    </div>
                    
                    <div class="context-section">
                        <h3>Assessment</h3>
                        <div class="context-row">
                            <span class="label">Risk:</span>
                            <span class="badge risk-${context.risk}">${context.risk}</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Trend:</span>
                            <span class="value">${context.trend}</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Demand Rate:</span>
                            <span class="value">${context.demandRate.toFixed(1)} units/wk</span>
                        </div>
                    </div>
                    
                    ${context.quality ? `
                    <div class="context-section">
                        <h3>Outcome</h3>
                        <div class="context-row">
                            <span class="label">Quality:</span>
                            <span class="badge quality-${context.quality}">${context.quality}</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Bullwhip:</span>
                            <span class="value">${context.bullwhip ? 'Yes ⚠️' : 'No ✓'}</span>
                        </div>
                        <div class="context-row">
                            <span class="label">Stockout:</span>
                            <span class="value">${context.stockout ? 'Yes ⚠️' : 'No ✓'}</span>
                        </div>
                    </div>
                    ` : ''}
                </div>
                
                ${context.outcome ? `
                <div style="margin-top: 20px;">
                    <h3 style="font-size: 13px; text-transform: uppercase; color: #666; margin-bottom: 10px;">Result</h3>
                    <div class="rationale">${context.outcome}</div>
                </div>
                ` : ''}
            </div>
        `);
    }
    
    async updateStats() {
        const stats = await fetchActorStats();
        
        const totalDecisions = stats.reduce((sum, s) => sum + s.decisions, 0);
        const totalBullwhip = stats.reduce((sum, s) => sum + s.bullwhipCount, 0);
        const avgAmplification = (stats.reduce((sum, s) => sum + s.avgAmplification * s.decisions, 0) / totalDecisions).toFixed(2);
        
        const statsHtml = `
            <div class="stat-card">
                <h3>Total Decisions</h3>
                <div class="value">${totalDecisions}</div>
                <div class="label">Across all actors</div>
            </div>
            <div class="stat-card">
                <h3>Avg Amplification</h3>
                <div class="value">${avgAmplification}x</div>
                <div class="label">Order / Demand ratio</div>
            </div>
            <div class="stat-card">
                <h3>Bullwhip Events</h3>
                <div class="value">${totalBullwhip}</div>
                <div class="label">Amplification > 1.5x</div>
            </div>
            <div class="stat-card">
                <h3>Weeks Simulated</h3>
                <div class="value">${[...new Set(this.data.map(d => d.week))].length}</div>
                <div class="label">With decisions</div>
            </div>
        `;
        
        d3.select('.stats-grid').html(statsHtml);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const timeline = new DecisionTimeline('timeline-container');
    timeline.init();
});
