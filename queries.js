// SPARQL Query Functions

async function fetchContexts() {
    const query = `
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT DISTINCT ?actor ?actorName ?week ?orderQty ?demandRate 
               ?risk ?trend ?policy ?quality ?outcome 
               ?inventory ?backlog ?coverage ?bullwhip ?stockout
        WHERE {
            ?context a bg:DecisionContext ;
                     bg:belongsTo ?actor ;
                     bg:forWeek ?weekIRI ;
                     bg:riskAssessment ?risk ;
                     bg:perceivedTrend ?trend ;
                     bg:activePolicy ?policy ;
                     bg:capturesInventoryState ?invState ;
                     bg:capturesMetrics ?metrics .
            
            ?weekIRI bg:weekNumber ?week .
            
            ?invState bg:currentInventory ?inventory ;
                      bg:backlog ?backlog .
            
            ?metrics bg:demandRate ?demandRate ;
                     bg:inventoryCoverage ?coverage .
            
            ?actor rdfs:label ?actorName .
            
            # Order is OPTIONAL - contexts can exist without orders (when suggestedQty=0)
            OPTIONAL {
                ?order bg:basedOnContext ?context ;
                       bg:orderQuantity ?orderQtyRaw .
            }
            
            # Default to 0 if no order exists
            BIND(COALESCE(?orderQtyRaw, 0) AS ?orderQty)
            
            OPTIONAL { ?context bg:outcomeQuality ?quality }
            OPTIONAL { ?context bg:actualOutcome ?outcome }
            OPTIONAL { ?context bg:causedBullwhip ?bullwhip }
            OPTIONAL { ?context bg:causedStockout ?stockout }
        }
        ORDER BY ?week ?actor
    `;
    
    return executeSparqlQuery(query);
}

async function fetchActorStats() {
    const query = `
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?actor ?actorName 
               (COUNT(DISTINCT ?context) as ?decisions)
               (AVG(?amplification) as ?avgAmplification)
               (SUM(IF(?bullwhip="true"^^xsd:boolean, 1, 0)) as ?bullwhipCount)
        WHERE {
            ?context a bg:DecisionContext ;
                     bg:belongsTo ?actor ;
                     bg:capturesMetrics ?metrics .
            
            ?actor rdfs:label ?actorName .
            
            ?metrics bg:demandRate ?demandRate .
            
            # Order is OPTIONAL
            OPTIONAL {
                ?order bg:basedOnContext ?context ;
                       bg:orderQuantity ?orderQtyRaw .
            }
            
            OPTIONAL { ?context bg:causedBullwhip ?bullwhip }
            
            # Calculate amplification (use 0 if no order)
            BIND(COALESCE(?orderQtyRaw, 0) / ?demandRate AS ?amplification)
        }
        GROUP BY ?actor ?actorName
    `;
    
    return executeSparqlQuery(query);
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
                       value.datatype === 'http://www.w3.org/2001/XMLSchema#decimal') {
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

// Extract actor short name from URI
function getActorShortName(uri) {
    const match = uri.match(/(Retailer|Wholesaler|Distributor|Factory)_[A-Za-z]+$/);
    return match ? match[0] : uri;
}
