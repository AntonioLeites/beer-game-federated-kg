// SPARQL Query Functions para V3.3

async function fetchContexts() {
    const query = `
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?actor ?actorName ?week ?decisionType ?decisionUri ?contextUri
               ?orderQty ?demandRate ?risk ?trend ?policy ?quality ?outcome 
               ?inventory ?backlog ?coverage ?bullwhip ?stockout
        WHERE {
            # Obtain ALL Decisions (ActionDecision or NoActionDecision)
            {
                ?decisionUri a bg:ActionDecision ;
                           bg:madeBy ?actor ;
                           bg:forWeek ?weekIRI ;
                           bg:hasDecisionContext ?contextUri .
                BIND("ActionDecision" AS ?decisionType)
                
                # Obtain related order (if any)
                OPTIONAL {
                    ?order bg:basedOnContext ?contextUri ;
                           bg:orderQuantity ?orderQty .
                }
            } UNION {
                ?decisionUri a bg:NoActionDecision ;
                           bg:madeBy ?actor ;
                           bg:forWeek ?weekIRI ;
                           bg:hasDecisionContext ?contextUri .
                BIND("NoActionDecision" AS ?decisionType)
                BIND(0 AS ?orderQty)  # NoActionDecision tiene orderQty = 0
            }
            
            ?weekIRI bg:weekNumber ?week .
            
            # Obtain the DecisionContext and its data
            ?contextUri a bg:DecisionContext ;
                       bg:belongsTo ?actor ;
                       bg:riskAssessment ?risk ;
                       bg:perceivedTrend ?trend ;
                       bg:activePolicy ?policy ;
                       bg:capturesInventoryState ?invState ;
                       bg:capturesMetrics ?metrics .
            
            # Obtain inventory data
            ?invState bg:currentInventory ?inventory ;
                      bg:backlog ?backlog .
            
            # Obtain metrics
            ?metrics bg:demandRate ?demandRate ;
                     bg:inventoryCoverage ?coverage .
            
            # Obtain actor name
            ?actor rdfs:label ?actorName .
            
            # Obtain outcome information (optional - post-mortem)
            OPTIONAL { ?contextUri bg:outcomeQuality ?quality }
            OPTIONAL { ?contextUri bg:actualOutcome ?outcome }
            OPTIONAL { ?contextUri bg:causedBullwhip ?bullwhip }
            OPTIONAL { ?contextUri bg:causedStockout ?stockout }
        }
        ORDER BY ?week ?actor
    `;
    
    return executeSparqlQuery(query);
}

async function fetchActorStats() {
    const query = `
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?actor ?actorName 
               (COUNT(DISTINCT ?decision) as ?totalDecisions)
               (COUNT(DISTINCT ?actionDecision) as ?actionDecisions)
               (COUNT(DISTINCT ?noActionDecision) as ?noActionDecisions)
               (AVG(?amplification) as ?avgAmplification)
               (SUM(IF(?bullwhip="true"^^xsd:boolean, 1, 0)) as ?bullwhipCount)
        WHERE {
            # Count all decisions
            ?decision a bg:Decision ;
                     bg:madeBy ?actor .
            
            # Count ActionDecisions
            OPTIONAL {
                ?actionDecision a bg:ActionDecision ;
                               bg:madeBy ?actor ;
                               bg:hasDecisionContext ?context .
                
                # Obtain Order to calculate amplification
                OPTIONAL {
                    ?order bg:basedOnContext ?context ;
                           bg:orderQuantity ?orderQty .
                    
                    ?context bg:capturesMetrics ?metrics .
                    ?metrics bg:demandRate ?demandRate .
                    
                    BIND(?orderQty / ?demandRate AS ?amplification)
                }
                
                # Obtain bullwhip information
                OPTIONAL {
                    ?context bg:causedBullwhip ?bullwhip .
                }
            }
            
            # Count NoActionDecisions
            OPTIONAL {
                ?noActionDecision a bg:NoActionDecision ;
                                 bg:madeBy ?actor .
            }
            
            ?actor rdfs:label ?actorName .
        }
        GROUP BY ?actor ?actorName
    `;
    
    return executeSparqlQuery(query);
}

async function fetchDecisionConnections() {
    /**
    * V3.3: Obtain connections between decisions to display propagation arrows
    * Based on the supply chain structure: Retailer → Wholesaler → Distributor → Factory
     */
    const query = `
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?sourceActor ?sourceWeek ?targetActor ?targetWeek ?orderQty
        WHERE {
            ?sourceDecision a bg:Decision ;
                           bg:madeBy ?sourceActor ;
                           bg:forWeek ?sourceWeekIRI .
            
            ?sourceWeekIRI bg:weekNumber ?sourceWeek .
            
            ?sourceDecision bg:hasDecisionContext ?context .
            ?order bg:basedOnContext ?context ;
                   bg:placedBy ?sourceActor ;
                   bg:receivedBy ?targetActor ;
                   bg:orderQuantity ?orderQty .
            
            ?targetActor bg:shippingDelay ?shippingDelay .
            BIND(?sourceWeek + ?shippingDelay AS ?targetWeek)
            
            FILTER EXISTS {
                ?targetDecision a bg:Decision ;
                               bg:madeBy ?targetActor ;
                               bg:forWeek ?targetWeekIRI .
                
                ?targetWeekIRI bg:weekNumber ?targetWeek .
            }
            
            FILTER(?sourceWeek >= 2)
        }
        ORDER BY ?sourceWeek ?sourceActor
    `;
    
    // return executeSparqlQuery(query);
    const result = await executeSparqlQuery(query);

    // Filter out connections where sourceWeek < 2 (no decisions exist)
    const filtered = result.filter(conn => conn.sourceWeek >= 2);

    // Deduplicar 
    const seen = new Set();
    const deduplicated = result.filter(conn => {
        const key = `${conn.sourceActor}-${conn.sourceWeek}-${conn.targetActor}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });

    console.log('fetchDecisionConnections result:', deduplicated);
    return deduplicated;
}

async function fetchActorHierarchy() {
    /**
     * Infer supply chain hierarchy from actual orders
     * (bg:suppliesTo property doesn't exist in data)
     */
    const query = `
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?actor ?actorName ?upstreamActor ?upstreamName
        WHERE {
            # Find orders to infer hierarchy
            ?order a bg:Order ;
                   bg:placedBy ?actor ;
                   bg:receivedBy ?upstreamActor .
            
            # Get actor names
            ?actor rdfs:label ?actorName .
            ?upstreamActor rdfs:label ?upstreamName .
        }
    `;
    
    return executeSparqlQuery(query);
}

async function fetchAllData() {
    /**
     * Function to obtain all the data needed for the dashboard in a single call (using Promise.all to parallelize)
     */
    try {
        const [contexts, stats, connections, hierarchy] = await Promise.all([
            fetchContexts(),
            fetchActorStats(),
            fetchDecisionConnections(),
            fetchActorHierarchy()
        ]);

        console.log('All data loaded:', { // ← AÑADIR
            contexts: contexts.length,
            connections: connections.length,
            hierarchy: hierarchy.length
        });
        
        return {
            contexts,
            stats,
            connections,
            hierarchy
        };
    } catch (error) {
        console.error('Error fetching all data:', error);
        throw error;
    }
}

async function executeSparqlQuery(query) {
    const url = `${CONFIG.graphdb.url}/repositories/${CONFIG.graphdb.repository}`;
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/sparql-results+json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `query=${encodeURIComponent(query)}`
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return parseBindings(data.results.bindings);
        
    } catch (error) {
        console.error('SPARQL query failed:', error);
        throw error;
    }
}

function parseBindings(bindings) {
    return bindings.map(binding => {
        const parsed = {};
        for (const [key, value] of Object.entries(binding)) {
            // Extract value based on type
            if (value.type === 'uri') {
                parsed[key] = value.value;
            } else if (value.datatype === 'http://www.w3.org/2001/XMLSchema#integer' ||
                       value.datatype === 'http://www.w3.org/2001/XMLSchema#decimal' ||
                       value.datatype === 'http://www.w3.org/2001/XMLSchema#float') {
                parsed[key] = parseFloat(value.value);
            } else if (value.datatype === 'http://www.w3.org/2001/XMLSchema#boolean') {
                parsed[key] = value.value === 'true';
            } else {
                parsed[key] = value.value;
            }
        }
        return parsed;
    });
}

// Extract short name of actor from URI
function getActorShortName(uri) {
    const match = uri.match(/(Retailer|Wholesaler|Distributor|Factory)_[A-Za-z]+$/);
    return match ? match[0] : uri;
}

// Get actor type from URI
function getActorType(uri) {
    if (uri.includes('Retailer')) return 'Retailer';
    if (uri.includes('Wholesaler')) return 'Wholesaler';
    if (uri.includes('Distributor')) return 'Distributor';
    if (uri.includes('Factory')) return 'Factory';
    return 'Unknown';
}