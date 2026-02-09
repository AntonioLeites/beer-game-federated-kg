// Decision Timeline Visualization with D3.js - V3.3 Complete Timeline
// Supports ActionDecision and NoActionDecision for complete decision tracking

class DecisionTimeline {
    constructor(containerId) {
        this.container = d3.select(`#${containerId}`);
        this.svg = null;
        this.data = null;
        this.connectionsData = null;
        this.hierarchyData = null;
        this.selectedContext = null;
        this.tooltip = null;
        this.showArrows = true;
        this.links = [];

        // Animation properties
        this.isPlaying = false;
        this.currentWeek = 0;
        this.animationSpeed = 1000; // ms per week
        this.animationTimer = null;
        
        // Supply chain actor order (top to bottom in visualization)
        this.actorOrder = {
            'Factory': 1,
            'Distributor': 2,
            'Wholesaler': 3,
            'Retailer': 4
        };
    }
    
    async init() {
        try {
            // Show loading
            this.showLoading();
            
            // Fetch all data using V3.3 queries
            const allData = await fetchAllData();
            
            if (allData.contexts.length === 0) {
                this.showError('No decision contexts found. Run a simulation first.');
                return;
            }
            
            // Store data
            this.data = allData.contexts;
            this.connectionsData = allData.connections;
            this.hierarchyData = allData.hierarchy;
            
            // Create tooltip
            this.createTooltip();
            
            // Render visualization
            this.render();
            
            // Update statistics
            this.updateStats(allData.stats);
            
            // Setup UI controls
            this.setupExport();
            this.setupArrowsToggle();
            this.setupAnimationControls();
            
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
    
    getActorType(actorName) {
        // Extract actor type from actor name (e.g., "Retailer_Alpha" -> "Retailer")
        if (actorName.includes('Retailer')) return 'Retailer';
        if (actorName.includes('Wholesaler')) return 'Wholesaler';
        if (actorName.includes('Distributor')) return 'Distributor';
        if (actorName.includes('Factory')) return 'Factory';
        return 'Unknown';
    }
    
    sortActorsBySupplyChain(actors) {
        // Sort actors in supply chain order: Retailer (bottom) to Factory (top)
        // But we want Factory at top, then Distributor, then Wholesaler, then Retailer at bottom
        return actors.sort((a, b) => {
            const typeA = this.getActorType(a);
            const typeB = this.getActorType(b);
            
            // Use the actorOrder mapping for sorting
            const orderA = this.actorOrder[typeA] || 99;
            const orderB = this.actorOrder[typeB] || 99;
            
            return orderA - orderB; // Ascending order
        });
    }
    
    showTooltip(event, d) {
        const actorType = this.getActorType(d.actorName);
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
        
        let decisionInfo = '';
        if (d.decisionType === 'ActionDecision') {
            const amplification = d.orderQty && d.demandRate 
                ? (d.orderQty / d.demandRate).toFixed(2)
                : 'N/A';
            
            decisionInfo = `
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Order:</span> 
                    <strong>${d.orderQty} units</strong>
                </div>
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Amplification:</span> 
                    <strong>${amplification}x</strong>
                </div>
            `;
        } else {
            decisionInfo = `
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Decision:</span> 
                    <strong>No Action (No order placed)</strong>
                </div>
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Rationale:</span> 
                    <em style="font-size: 12px;">Sufficient inventory or low demand</em>
                </div>
            `;
        }
        
        // Find connected links for this decision
        const outgoingLink = this.links.find(link => link.source === d);
        const incomingLink = this.links.find(link => link.target === d);
        
        let connectionInfo = '';
        if (outgoingLink) {
            const targetType = this.getActorType(outgoingLink.target.actorName);
            connectionInfo += `
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px;">
                    <div style="opacity: 0.8;">⬆️ Order flows upstream to:</div>
                    <strong>${targetType}: ${outgoingLink.target.actorName} (Week ${outgoingLink.target.week})</strong>
                </div>
            `;
        }
        if (incomingLink) {
            const sourceType = this.getActorType(incomingLink.source.actorName);
            connectionInfo += `
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px;">
                    <div style="opacity: 0.8;">⬇️ Incoming order from:</div>
                    <strong>${sourceType}: ${incomingLink.source.actorName} (Week ${incomingLink.source.week})</strong>
                    <div style="opacity: 0.8; font-size: 11px;">${incomingLink.quantity} units</div>
                </div>
            `;
        }
        
        const html = `
            <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">
                Week ${d.week} - ${actorType}: ${d.actorName}
                <span style="font-size: 11px; opacity: 0.7; margin-left: 8px;">
                    (${d.decisionType})
                </span>
            </div>
            <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 8px;">
                ${decisionInfo}
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Risk:</span> 
                    <strong>${riskEmoji} ${d.risk.toUpperCase()}</strong>
                </div>
                ${d.quality ? `
                <div style="margin-bottom: 4px;">
                    <span style="opacity: 0.8;">Outcome:</span> 
                    <strong>${qualityEmoji} ${d.quality}</strong>
                </div>
                ` : ''}
            </div>
            ${connectionInfo}
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
    
    highlightConnections(d) {
        // Find connected links
        const connectedLinks = this.links.filter(link => 
            link.source === d || link.target === d
        );
        
        // Fade out all arrows
        this.svg.selectAll('.propagation-arrow')
            .transition()
            .duration(200)
            .attr('stroke-opacity', 0.1);
        
        // Highlight connected arrows
        this.svg.selectAll('.propagation-arrow')
            .filter(link => connectedLinks.includes(link))
            .transition()
            .duration(200)
            .attr('stroke-opacity', 0.9)
            .attr('stroke-width', link => {
                const strokeScale = d3.scaleLinear()
                    .domain([0, d3.max(this.data, d => d.orderQty || 0)])
                    .range([2, 10]);
                return strokeScale(link.quantity);
            });
        
        // Fade out other decision points
        this.svg.selectAll('.decision-point')
            .filter(point => point !== d && 
                   !connectedLinks.some(link => link.source === point || link.target === point))
            .transition()
            .duration(200)
            .attr('opacity', 0.2);
        
        // Highlight connected decision points
        this.svg.selectAll('.decision-point')
            .filter(point => point === d || 
                   connectedLinks.some(link => link.source === point || link.target === point))
            .transition()
            .duration(200)
            .attr('opacity', 1);
    }
    
    resetHighlight() {
        // Restore all arrows
        this.svg.selectAll('.propagation-arrow')
            .transition()
            .duration(200)
            .attr('stroke-opacity', 0.4)
            .attr('stroke-width', link => {
                const strokeScale = d3.scaleLinear()
                    .domain([0, d3.max(this.data, d => d.orderQty || 0)])
                    .range([1, 8]);
                return strokeScale(link.quantity);
            });
        
        // Restore all decision points
        this.svg.selectAll('.decision-point')
            .transition()
            .duration(200)
            .attr('opacity', 0.8);
    }
    
    setupExport() {
        const exportBtn = document.getElementById('export-btn');
        if (!exportBtn) return;
        
        exportBtn.addEventListener('click', () => this.exportToPNG());
    }
    
    setupArrowsToggle() {
        const toggleBtn = document.getElementById('arrows-toggle');
        if (!toggleBtn) return;
        
        toggleBtn.addEventListener('click', () => {
            this.showArrows = !this.showArrows;
            toggleBtn.textContent = this.showArrows ? '🔗 Hide Arrows' : '🔗 Show Arrows';
            this.toggleArrows();
        });
    }
    
    toggleArrows() {
        const arrows = this.svg.selectAll('.propagation-arrow');
        arrows.style('display', this.showArrows ? 'block' : 'none');
    }
    
    setupAnimationControls() {
        const playBtn = document.getElementById('play-btn');
        const resetBtn = document.getElementById('reset-btn');
        const speedSelect = document.getElementById('speed-select');
        
        if (!playBtn || !resetBtn || !speedSelect) return;
        
        playBtn.addEventListener('click', () => this.togglePlayPause());
        resetBtn.addEventListener('click', () => this.resetAnimation());
        speedSelect.addEventListener('change', (e) => {
            this.animationSpeed = 1000 / parseFloat(e.target.value);
            if (this.isPlaying) {
                this.stopAnimation();
                this.startAnimation();
            }
        });
    }
    
    togglePlayPause() {
        if (this.isPlaying) {
            this.pauseAnimation();
        } else {
            this.playAnimation();
        }
    }
    
    playAnimation() {
        const playBtn = document.getElementById('play-btn');
        playBtn.textContent = '⏸️ Pause';
        playBtn.classList.add('playing');
        
        this.isPlaying = true;
        this.startAnimation();
    }
    
    pauseAnimation() {
        const playBtn = document.getElementById('play-btn');
        playBtn.textContent = '▶️ Play';
        playBtn.classList.remove('playing');
        
        this.isPlaying = false;
        this.stopAnimation();
    }
    
    resetAnimation() {
        this.stopAnimation();
        this.currentWeek = 0;
        this.isPlaying = false;
        
        const playBtn = document.getElementById('play-btn');
        playBtn.textContent = '▶️ Play';
        playBtn.classList.remove('playing');
        
        // Hide all elements
        this.svg.selectAll('.decision-point').style('display', 'none');
        this.svg.selectAll('.propagation-arrow').style('display', 'none');
        this.svg.selectAll('.quality-indicator').style('display', 'none');
        
        document.getElementById('current-week').textContent = 'Week -';
    }
    
    startAnimation() {
        const weeks = [...new Set(this.data.map(d => d.week))].sort((a, b) => a - b);
        
        if (this.currentWeek === 0) {
            // Start from the beginning
            this.resetAnimation();
            this.currentWeek = weeks[0];
        }
        
        this.animationTimer = setInterval(() => {
            this.showWeek(this.currentWeek);
            
            const currentIndex = weeks.indexOf(this.currentWeek);
            if (currentIndex < weeks.length - 1) {
                this.currentWeek = weeks[currentIndex + 1];
            } else {
                // End of animation
                this.pauseAnimation();
                this.currentWeek = 0; // Reset for next play
            }
        }, this.animationSpeed);
    }
    
    stopAnimation() {
        if (this.animationTimer) {
            clearInterval(this.animationTimer);
            this.animationTimer = null;
        }
    }
    
    showWeek(week) {
        document.getElementById('current-week').textContent = `Week ${week}`;
        
        // Show this week's decisions with animation
        const decisionsThisWeek = this.data.filter(d => d.week === week);
        
        decisionsThisWeek.forEach(decision => {
            // Show decision circle
            this.svg.selectAll('.decision-point')
                .filter(d => d === decision)
                .style('display', 'block')
                .classed('animated-enter', true)
                .each(function() {
                    // Remove class after animation
                    setTimeout(() => {
                        d3.select(this).classed('animated-enter', false);
                    }, 400);
                });
            
            // Show quality indicator if exists
            if (decision.quality) {
                this.svg.selectAll('.quality-indicator')
                    .filter(d => d === decision)
                    .style('display', 'block');
            }
            
            // Show outgoing arrows
            const outgoingLinks = this.links.filter(link => link.source === decision);
            outgoingLinks.forEach(link => {
                this.svg.selectAll('.propagation-arrow')
                    .filter(l => l === link)
                    .style('display', this.showArrows ? 'block' : 'none')
                    .attr('stroke-dasharray', '100')
                    .attr('stroke-dashoffset', '100')
                    .classed('animated-enter', true)
                    .transition()
                    .duration(600)
                    .attr('stroke-dashoffset', '0')
                    .on('end', function() {
                        d3.select(this)
                            .attr('stroke-dasharray', 'none')
                            .classed('animated-enter', false);
                    });
            });
        });
    }
    
    computePropagationLinks() {
        // Use connection data fetched from SPARQL
        if (!this.connectionsData || this.connectionsData.length === 0) {
            return [];
        }
        
        const links = [];
        
        this.connectionsData.forEach(conn => {
            const sourceDecision = this.data.find(d => 
                d.actor === conn.sourceActor && d.week === conn.sourceWeek
            );
            
            const targetDecision = this.data.find(d => 
                d.actor === conn.targetActor && d.week === conn.targetWeek
            );
            
            if (sourceDecision && targetDecision) {
                const amplification = conn.orderQty / (conn.demandRate || 1);
                
                links.push({
                    source: sourceDecision,
                    target: targetDecision,
                    quantity: conn.orderQty,
                    demandRate: conn.demandRate,
                    amplification: amplification
                });
            }
        });
        
        return links;
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
        
        // Get unique weeks
        const weeks = [...new Set(this.data.map(d => d.week))].sort((a, b) => a - b);
        
        // Get actors and sort by supply chain position
        let actors = [...new Set(this.data.map(d => d.actorName))];
        actors = this.sortActorsBySupplyChain(actors);
        
        // Scales
        const xScale = d3.scaleLinear()
            .domain([d3.min(weeks), d3.max(weeks)])
            .range([0, innerWidth]);
        
        const yScale = d3.scaleBand()
            .domain(actors)
            .range([0, innerHeight])
            .padding(0.3);
        
        const radiusScale = d3.scaleSqrt()
            .domain([0, d3.max(this.data, d => {
                if (d.decisionType === 'ActionDecision' && d.orderQty && d.demandRate) {
                    return d.orderQty / d.demandRate;
                }
                return 1;
            })])
            .range([CONFIG.visualization.pointRadius.min, CONFIG.visualization.pointRadius.max]);
        
        const strokeScale = d3.scaleLinear()
            .domain([0, d3.max(this.data, d => d.orderQty || 0)])
            .range([1, 8]);
        
        // Add supply chain flow indicator on Y-axis
        g.append('text')
            .attr('x', -10)
            .attr('y', innerHeight / 2)
            .attr('text-anchor', 'end')
            .attr('transform', 'rotate(-90)')
            .style('font-size', '12px')
            .style('fill', '#666')
            .text('Supply Chain Flow: Factory → Distributor → Wholesaler → Retailer');
        
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
        
        const yAxis = d3.axisLeft(yScale)
            .tickFormat(d => {
                // Display actor type and name for clarity
                const actorType = this.getActorType(d);
                return `${actorType}: ${d}`;
            });
        
        g.append('g')
            .attr('class', 'axis y-axis')
            .call(yAxis);
        
        // Add supply chain flow arrows on Y-axis
        actors.forEach((actor, index) => {
            if (index < actors.length - 1) {
                const currentActorType = this.getActorType(actor);
                const nextActorType = this.getActorType(actors[index + 1]);
                
                // Add flow arrow between actors
                g.append('line')
                    .attr('class', 'supply-chain-flow')
                    .attr('x1', -30)
                    .attr('x2', -30)
                    .attr('y1', yScale(actor) + yScale.bandwidth())
                    .attr('y2', yScale(actors[index + 1]))
                    .attr('stroke', '#999')
                    .attr('stroke-width', 1)
                    .attr('stroke-dasharray', '5,5')
                    .attr('marker-end', 'url(#flowArrow)');
                    
                g.append('text')
                    .attr('x', -35)
                    .attr('y', (yScale(actor) + yScale(actors[index + 1]) + yScale.bandwidth()) / 2)
                    .attr('text-anchor', 'end')
                    .style('font-size', '10px')
                    .style('fill', '#666')
                    .style('font-style', 'italic')
                    .text('supplies to');
            }
        });
        
        // Define flow arrow marker
        const defs = this.svg.append('defs');
        
        defs.append('marker')
            .attr('id', 'flowArrow')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('refX', 0)
            .attr('refY', 3)
            .attr('orient', 'auto')
            .append('polygon')
            .attr('points', '0 0, 6 3, 0 6')
            .attr('fill', '#666');
        
        defs.append('marker')
            .attr('id', 'arrowhead')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('refX', 5)
            .attr('refY', 2)
            .attr('orient', 'auto')
            .append('polygon')
            .attr('points', '0 0, 6 2, 0 4')
            .attr('fill', '#666');
        
        // Compute propagation links
        this.links = this.computePropagationLinks();
        
        // Draw arrows
        const arrowsGroup = g.append('g').attr('class', 'arrows-layer');
        
        const arrows = arrowsGroup.selectAll('.propagation-arrow')
            .data(this.links)
            .enter()
            .append('line')
            .attr('class', 'propagation-arrow')
            .attr('x1', d => xScale(d.source.week))
            .attr('y1', d => yScale(d.source.actorName) + yScale.bandwidth() / 2)
            .attr('x2', d => xScale(d.target.week))
            .attr('y2', d => yScale(d.target.actorName) + yScale.bandwidth() / 2)
            .attr('stroke', d => {
                if (d.amplification > 2.0) return '#F44336';
                if (d.amplification > 1.5) return '#FF9800';
                return '#9E9E9E';
            })
            .attr('stroke-width', d => strokeScale(d.quantity))
            .attr('stroke-opacity', 0.4)
            .attr('marker-end', 'url(#arrowhead)')
            .style('pointer-events', 'none');
        
        // Decision points
        const self = this;
        const points = g.selectAll('.decision-point')
            .data(this.data)
            .enter()
            .append('circle')
            .attr('class', d => `decision-point ${d.decisionType}`)
            .attr('cx', d => xScale(d.week))
            .attr('cy', d => yScale(d.actorName) + yScale.bandwidth() / 2)
            .attr('r', d => {
                // For NoActionDecision, smaller radius
                if (d.decisionType === 'NoActionDecision') {
                    return CONFIG.visualization.pointRadius.min * 0.7;
                }
                // For ActionDecision, radius based on amplification
                const amplification = d.orderQty / (d.demandRate || 1);
                return radiusScale(amplification);
            })
            .attr('fill', d => {
                // Different color for NoActionDecision
                if (d.decisionType === 'NoActionDecision') {
                    return '#AAAAAA'; // Gray for NoAction
                }
                return CONFIG.colors.risk[d.risk] || '#999';
            })
            .attr('stroke', d => {
                // Different border for NoActionDecision
                if (d.decisionType === 'NoActionDecision') {
                    return '#888888';
                }
                return 'none';
            })
            .attr('stroke-width', 1)
            .attr('opacity', 0.8)
            .on('click', (event, d) => this.showContextDetail(d))
            .on('mouseenter', function(event, d) {
                d3.select(this)
                    .attr('stroke', '#333')
                    .attr('stroke-width', 2);
                self.showTooltip(event, d);
                self.highlightConnections(d);
            })
            .on('mousemove', (event) => {
                self.updateTooltipPosition(event);
            })
            .on('mouseleave', function() {
                d3.select(this)
                    .attr('stroke', d => d.decisionType === 'NoActionDecision' ? '#888888' : 'none')
                    .attr('stroke-width', 1);
                self.hideTooltip();
                self.resetHighlight();
            });
        
        // Quality indicators (only for decisions with quality assessment)
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
        
        // Decision types
        legend.append('div').style('font-weight', 'bold').text('Decision Types:');
        
        const actionLegend = legend.append('div').attr('class', 'legend-item');
        actionLegend.append('div')
            .attr('class', 'legend-color')
            .style('background-color', '#2196F3')
            .style('border', 'none');
        actionLegend.append('span').text('Action Decision (order placed)');
        
        const noActionLegend = legend.append('div').attr('class', 'legend-item');
        noActionLegend.append('div')
            .attr('class', 'legend-color')
            .style('background-color', '#AAAAAA')
            .style('border', '1px solid #888');
        noActionLegend.append('span').text('No-Action Decision (sufficient inventory)');
        
        legend.append('div').style('width', '100%');
        
        // Risk levels
        legend.append('div').style('font-weight', 'bold').text('Risk Levels:');
        Object.entries(CONFIG.colors.risk).forEach(([risk, color]) => {
            const item = legend.append('div').attr('class', 'legend-item');
            item.append('div')
                .attr('class', 'legend-color')
                .style('background-color', color);
            item.append('span').text(risk);
        });
        
        legend.append('div').style('width', '100%');
        
        // Quality outcomes
        legend.append('div').style('font-weight', 'bold').text('Outcome Quality:');
        Object.entries(CONFIG.colors.quality).forEach(([quality, color]) => {
            const item = legend.append('div').attr('class', 'legend-item');
            item.append('div')
                .attr('class', 'legend-color')
                .style('background-color', color);
            item.append('span').text(quality);
        });
        
        legend.append('div').style('width', '100%');
        
        // Arrows legend
        legend.append('div').style('font-weight', 'bold').text('Order Propagation:');
        
        const arrowNormal = legend.append('div').attr('class', 'legend-item');
        arrowNormal.append('div')
            .style('width', '20px')
            .style('height', '3px')
            .style('background-color', '#9E9E9E');
        arrowNormal.append('span').text('normal flow');
        
        const arrowBullwhip = legend.append('div').attr('class', 'legend-item');
        arrowBullwhip.append('div')
            .style('width', '20px')
            .style('height', '4px')
            .style('background-color', '#FF9800');
        arrowBullwhip.append('span').text('bullwhip (1.5-2x)');
        
        const arrowHigh = legend.append('div').attr('class', 'legend-item');
        arrowHigh.append('div')
            .style('width', '20px')
            .style('height', '5px')
            .style('background-color', '#F44336');
        arrowHigh.append('span').text('high amplification (>2x)');
    }
    
    showContextDetail(context) {
        this.selectedContext = context;
        
        const panel = d3.select('#detail-panel');
        panel.classed('hidden', false);
        
        const actorType = this.getActorType(context.actorName);
        const amplification = context.orderQty && context.demandRate 
            ? (context.orderQty / context.demandRate).toFixed(2)
            : 'N/A';
        
        let decisionSection = '';
        if (context.decisionType === 'ActionDecision') {
            decisionSection = `
                <div class="context-section">
                    <h3>Action Decision</h3>
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
            `;
        } else {
            decisionSection = `
                <div class="context-section">
                    <h3>No-Action Decision</h3>
                    <div class="context-row">
                        <span class="label">No order placed</span>
                        <span class="value">Sufficient inventory or low demand</span>
                    </div>
                    <div class="context-row">
                        <span class="label">Policy:</span>
                        <span class="value">Passive / Conservative</span>
                    </div>
                    <div class="context-row">
                        <span class="label">Amplification:</span>
                        <span class="value">N/A (no order)</span>
                    </div>
                </div>
            `;
        }
        
        panel.html(`
            <div class="context-card">
                <h2>Week ${context.week} - ${actorType}: ${context.actorName}</h2>
                
                <div class="context-grid">
                    ${decisionSection}
                    
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
    
    async updateStats(statsData) {
        const stats = statsData || await fetchActorStats();
        
        const totalDecisions = stats.reduce((sum, s) => sum + s.totalDecisions, 0);
        const totalActionDecisions = stats.reduce((sum, s) => sum + s.actionDecisions, 0);
        const totalNoActionDecisions = stats.reduce((sum, s) => sum + s.noActionDecisions, 0);
        const totalBullwhip = stats.reduce((sum, s) => sum + s.bullwhipCount, 0);
        
        const avgAmplification = stats.reduce((sum, s) => {
            const actorWeight = s.actionDecisions;
            return sum + (s.avgAmplification || 0) * actorWeight;
        }, 0) / totalActionDecisions || 0;
        
        const statsHtml = `
            <div class="stat-card">
                <h3>Total Decisions</h3>
                <div class="value">${totalDecisions}</div>
                <div class="label">
                    Action: ${totalActionDecisions} | 
                    No Action: ${totalNoActionDecisions}
                </div>
            </div>
            <div class="stat-card">
                <h3>Avg Amplification</h3>
                <div class="value">${avgAmplification.toFixed(2)}x</div>
                <div class="label">Only Action decisions</div>
            </div>
            <div class="stat-card">
                <h3>Bullwhip Events</h3>
                <div class="value">${totalBullwhip}</div>
                <div class="label">Amplification > 1.5x</div>
            </div>
            <div class="stat-card">
                <h3>Weeks Simulated</h3>
                <div class="value">${[...new Set(this.data.map(d => d.week))].length}</div>
                <div class="label">With complete timeline</div>
            </div>
        `;
        
        d3.select('.stats-grid').html(statsHtml);
    }
    
    async exportToPNG() {
        const exportBtn = document.getElementById('export-btn');
        exportBtn.disabled = true;
        exportBtn.textContent = '⏳ Exporting...';
        
        try {
            const svgElement = this.svg.node();
            const bbox = svgElement.getBBox();
            
            const canvas = document.createElement('canvas');
            const scale = 2;
            canvas.width = (bbox.width + CONFIG.visualization.margin.left + CONFIG.visualization.margin.right) * scale;
            canvas.height = (bbox.height + CONFIG.visualization.margin.top + CONFIG.visualization.margin.bottom) * scale;
            
            const ctx = canvas.getContext('2d');
            ctx.scale(scale, scale);
            
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            const svgData = new XMLSerializer().serializeToString(svgElement);
            const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
            const svgUrl = URL.createObjectURL(svgBlob);
            
            const img = new Image();
            img.onload = () => {
                ctx.drawImage(img, 0, 0);
                URL.revokeObjectURL(svgUrl);
                
                canvas.toBlob((blob) => {
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
                    link.download = `beer-game-timeline-${timestamp}.png`;
                    link.href = url;
                    link.click();
                    URL.revokeObjectURL(url);
                    
                    this.showNotification('✓ Timeline exported successfully!');
                    
                    exportBtn.disabled = false;
                    exportBtn.textContent = '📥 Export PNG';
                });
            };
            
            img.onerror = () => {
                throw new Error('Failed to load SVG image');
            };
            
            img.src = svgUrl;
            
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('✗ Export failed: ' + error.message, true);
            exportBtn.disabled = false;
            exportBtn.textContent = '📥 Export PNG';
    }
    }
    
    showNotification(message, isError = false) {
        const notification = document.createElement('div');
        notification.className = 'export-notification';
        notification.textContent = message;
        if (isError) {
            notification.style.background = '#F44336';
        }
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 2500);
    }
    
    showLoading() {
        this.container.html('<div class="loading">Loading decision contexts...</div>');
    }
    
    showError(message) {
        this.container.html(`<div class="error">${message}</div>`);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const timeline = new DecisionTimeline('timeline-container');
    timeline.init();
});