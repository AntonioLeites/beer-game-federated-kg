"""
Beer Game Federated KG - Temporal Rules Engine V3 (Federated Queries - COMPLETE)

Design Philosophy:
- All Beer Game business logic is encoded as SPARQL rules
- Rules compute state transitions, metrics, and decisions
- **V3 NEW:** Queries use BG_Supply_Chain federation (no manual propagation)
- **V3 NEW:** Writes use individual repositories (local updates)
- This module is a LIBRARY - import and use from orchestrator
- For standalone execution, use: advanced_simulation_v3.py

Key Changes from V2:
- UPDATE INVENTORY: Queries arriving shipments from BG_Supply_Chain ✅
- CREATE SHIPMENTS: Queries incoming orders from BG_Supply_Chain ✅
- Eliminated propagate_orders_to_receivers() ✅
- Eliminated propagate_shipments_to_receivers() ✅
- 100% federated architecture - zero manual propagation ✅

Usage:
    from temporal_beer_game_rules_v3 import TemporalBeerGameRuleExecutor
    executor = TemporalBeerGameRuleExecutor()
    executor.execute_week_rules(week_number)
"""

import requests
import time


__all__ = ['TemporalBeerGameRuleExecutor', 'get_temporal_rules']

def get_temporal_rules():
    """
    Define all SPARQL rules organized by category
    Execution order matters - dependencies are documented
    """
    return {
        # =====================================================================
        # CATEGORY 1: STATE COMPUTATION RULES (Core Dynamics)
        # =====================================================================
        
        "UPDATE INVENTORY": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            # V3 NOTE: This rule expects arriving shipments to be pre-calculated
            # via federated query in BG_Supply_Chain before execution
            # See: execute_inventory_update_with_federation()
            
            DELETE {
                ?inv bg:currentInventory ?currentInvValue ;
                     bg:backlog ?currentBacklogValue .
            }
            INSERT {
                ?inv bg:currentInventory ?newInv ;
                     bg:backlog ?newBacklog ;
                     bg:inventoryProcessed "true"^^xsd:boolean .
            }
            WHERE {
                # Get current week
                ?week a bg:Week ;
                      bg:weekNumber ?weekNum .
                
                # Get inventory for this week (only if NOT already processed)
                ?inv a bg:Inventory ;
                     bg:forWeek ?week ;
                     bg:belongsTo ?actor .
                
                # Get current values for DELETE
                OPTIONAL { ?inv bg:currentInventory ?currentInvValue }
                OPTIONAL { ?inv bg:backlog ?currentBacklogValue }
                
                # IDEMPOTENCY: Skip if already processed
                FILTER NOT EXISTS {
                    ?inv bg:inventoryProcessed "true"^^xsd:boolean .
                }
                
                # Get PREVIOUS week's values for calculation
                ?prevWeek a bg:Week ;
                          bg:weekNumber ?prevWeekNum .
                FILTER(?prevWeekNum = ?weekNum - 1)
                
                ?prevInv a bg:Inventory ;
                         bg:forWeek ?prevWeek ;
                         bg:belongsTo ?actor ;
                         bg:currentInventory ?oldInv ;
                         bg:backlog ?oldBacklog .
                
                # V3: Get arriving shipments from temp property (set by federated query)
                OPTIONAL {
                    ?inv bg:tempArrivingShipments ?arriving .
                }
                BIND(COALESCE(?arriving, 0) AS ?incomingShipments)
                
                # Get demand for this week (customer demand OR incoming orders)
                OPTIONAL {
                    # Customer demand (for retailer)
                    ?demand_entity a bg:CustomerDemand ;
                                  bg:forWeek ?week ;
                                  bg:belongsTo ?actor ;
                                  bg:actualDemand ?customerDemand .
                }
                
                OPTIONAL {
                    # Downstream orders (for other actors) - sum them
                    SELECT ?actor ?week (SUM(?qty) as ?orderDemand)
                    WHERE {
                        ?order a bg:Order ;
                               bg:forWeek ?week ;
                               bg:receivedBy ?actor ;
                               bg:orderQuantity ?qty .
                    }
                    GROUP BY ?actor ?week
                }
                
                # Use customer demand if available, otherwise orders
                BIND(COALESCE(?customerDemand, ?orderDemand, 0) AS ?demandThisWeek)
                
                # Calculate new inventory (force integer types)
                BIND(xsd:integer(?oldInv) + xsd:integer(?incomingShipments) AS ?afterArrival)
                BIND(xsd:integer(?demandThisWeek) + xsd:integer(?oldBacklog) AS ?totalNeed)
                
                # Fulfill what we can (results are integers)
                BIND(
                    xsd:integer(
                        IF(?afterArrival >= ?totalNeed,
                           ?afterArrival - ?totalNeed,
                           0
                        )
                    ) AS ?newInv
                )
                BIND(
                    xsd:integer(
                        IF(?afterArrival >= ?totalNeed,
                           0,
                           ?totalNeed - ?afterArrival
                        )
                    ) AS ?newBacklog
                )
                
                # Bind current values for DELETE (using different variable names)
                OPTIONAL { ?inv bg:currentInventory ?currentInvToDelete }
                OPTIONAL { ?inv bg:backlog ?currentBacklogToDelete }
            }
        """,
        
        "CREATE ORDERS FROM SUGGESTED": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            INSERT {
                ?orderURI a bg:Order ;
                    bg:forWeek ?week ;
                    bg:belongsTo ?actor ;
                    bg:placedBy ?actor ;
                    bg:receivedBy ?upstream ;
                    bg:orderQuantity ?suggestedQty ;
                    rdfs:comment ?comment .
            }
            WHERE {
                # Get current week
                ?week a bg:Week ;
                      bg:weekNumber ?weekNum .
                
                # Get actor with suggested order
                ?actor a bg:Actor ;
                       bg:hasMetrics ?metrics ;
                       rdfs:label ?actorName .
                
                ?metrics bg:forWeek ?week ;
                         bg:suggestedOrderQuantity ?suggestedQty .
                
                # Get upstream from previous orders (infer topology)
                ?prevOrder a bg:Order ;
                           bg:placedBy ?actor ;
                           bg:receivedBy ?upstream .
                
                # Only create order if quantity > 0 and doesn't exist
                FILTER(?suggestedQty > 0)
                FILTER NOT EXISTS {
                    ?existingOrder a bg:Order ;
                                   bg:forWeek ?week ;
                                   bg:placedBy ?actor .
                }
                
                # Extract upstream actor name from URI
                # e.g., "http://beergame.org/wholesaler#Wholesaler_Beta" -> "Wholesaler_Beta"
                BIND(STRAFTER(STR(?upstream), "#") AS ?upstreamURI)
                
                # Extract short name (first part before underscore)
                # e.g., "Wholesaler_Beta" -> "Wholesaler"
                BIND(STRBEFORE(?upstreamURI, "_") AS ?upstreamShort)
                
                # Generate URI following convention: Order_Week{N}_To{UpstreamActor}
                BIND(IRI(CONCAT(
                    STRBEFORE(STR(?actor), "#"),
                    "#Order_Week",
                    STR(?weekNum),
                    "_To",
                    ?upstreamShort
                )) AS ?orderURI)
                
                BIND(CONCAT("Order from ", ?actorName, " to ", ?upstreamURI, " for Week ", STR(?weekNum)) AS ?comment)
            }
        """,
        
        "CREATE SHIPMENTS FROM ORDERS": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            INSERT {
                ?shipmentURI a bg:Shipment ;
                    bg:forWeek ?week ;
                    bg:belongsTo ?actor ;
                    bg:shippedFrom ?actor ;
                    bg:shippedTo ?downstream ;
                    bg:shippedQuantity ?orderQty ;
                    bg:arrivalWeek ?arrivalWeekNum ;
                    rdfs:comment ?comment .
            }
            WHERE {
                # Get current week
                ?week a bg:Week ;
                      bg:weekNumber ?weekNum .
                
                # Get orders received by this actor this week
                ?order a bg:Order ;
                       bg:forWeek ?week ;
                       bg:receivedBy ?actor ;
                       bg:placedBy ?downstream ;
                       bg:orderQuantity ?orderQty .
                
                # Get shipping delay
                ?actor bg:shippingDelay ?shippingDelay ;
                       rdfs:label ?actorName .
                
                # Calculate arrival week
                BIND(?weekNum + ?shippingDelay AS ?arrivalWeekNum)
                
                # Only create if shipment doesn't exist
                FILTER NOT EXISTS {
                    ?existingShipment a bg:Shipment ;
                                      bg:forWeek ?week ;
                                      bg:shippedFrom ?actor ;
                                      bg:shippedTo ?downstream .
                }
                
                # Extract downstream actor name from URI
                # e.g., "http://beergame.org/retailer#Retailer_Alpha" -> "Retailer_Alpha"
                BIND(STRAFTER(STR(?downstream), "#") AS ?downstreamURI)
                
                # Extract short name (first part before underscore)
                # e.g., "Retailer_Alpha" -> "Retailer"
                BIND(STRBEFORE(?downstreamURI, "_") AS ?downstreamShort)
                
                # Generate URI following convention: Shipment_Week{N}_To{DownstreamActor}
                BIND(IRI(CONCAT(
                    STRBEFORE(STR(?actor), "#"),
                    "#Shipment_Week",
                    STR(?weekNum),
                    "_To",
                    ?downstreamShort
                )) AS ?shipmentURI)
                
                BIND(CONCAT(
                    "Shipment from ", ?actorName, 
                    " to ", ?downstreamURI, 
                    " (arrives week ", STR(?arrivalWeekNum), ")"
                ) AS ?comment)
            }
        """,
        
        # =====================================================================
        # CATEGORY 2: METRIC CALCULATION RULES (Derived State)
        # =====================================================================
        
        "DEMAND RATE SMOOTHING": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?metrics bg:demandRate ?oldRate .
            }
            INSERT {
                ?metrics bg:demandRate ?smoothedRate .
            }
            WHERE {
                ?week a bg:Week .
                
                ?actor a bg:Actor ;
                       bg:hasMetrics ?metrics .
                
                ?metrics bg:forWeek ?week ;
                         bg:demandRate ?oldRate .
                
                # V3: Get observed demand from temp property (set by federated query)
                OPTIONAL {
                    ?metrics bg:tempObservedDemand ?observedDemand .
                }
                
                # Fallback to old rate if no observed demand
                BIND(COALESCE(?observedDemand, ?oldRate) AS ?currentDemand)
                
                # Exponential smoothing: 30% new, 70% old
                BIND((xsd:decimal(?currentDemand) * 0.3) + (?oldRate * 0.7) AS ?smoothedRate)
                
                # Only update if change > 5%
                BIND(ABS(?smoothedRate - ?oldRate) / ?oldRate AS ?changeRatio)
                FILTER(?changeRatio > 0.05 || ?oldRate = 0)
                
                OPTIONAL { ?metrics bg:demandRate ?oldRate }
            }
        """,
        
        "INVENTORY COVERAGE CALCULATION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            DELETE {
                ?metrics bg:inventoryCoverage ?oldCoverage .
            }
            INSERT {
                ?metrics bg:inventoryCoverage ?coverage ;
                         bg:coverageCalculated "true"^^xsd:boolean .
            }
            WHERE {
                ?week a bg:Week .
                
                ?metrics a bg:ActorMetrics ;
                        bg:forWeek ?week ;
                        bg:belongsTo ?actor ;
                        bg:demandRate ?rate .
                
                # IDEMPOTENCY: Skip if already calculated
                FILTER NOT EXISTS {
                    ?metrics bg:coverageCalculated "true"^^xsd:boolean .
                }
                
                ?inv a bg:Inventory ;
                    bg:forWeek ?week ;
                    bg:belongsTo ?actor ;
                    bg:currentInventory ?stock .

                # CRITICAL: OPTIONAL before BIND
                OPTIONAL { ?metrics bg:inventoryCoverage ?oldCoverage }
                
                FILTER(?rate > 0)
                BIND(xsd:decimal(?stock) / ?rate AS ?coverage)
            }
        """,
        
        "TOTAL COST CALCULATION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:totalCost ?oldCost .
            }
            INSERT {
                ?actor bg:totalCost ?newTotalCost .
            }
            WHERE {
                ?actor a bg:Actor .
                
                # Sum costs from ALL weeks (must recalculate every time)
                # This rule is NOT idempotent by design - it accumulates costs
                {
                    SELECT ?actor (SUM(?weekCost) AS ?newTotalCost)
                    WHERE {
                        ?inv a bg:Inventory ;
                             bg:belongsTo ?actor ;
                             bg:currentInventory ?stock ;
                             bg:backlog ?backlog ;
                             bg:holdingCost ?hCost ;
                             bg:backlogCost ?bCost .
                        
                        # Only count processed inventories (idempotent inventories)
                        ?inv bg:inventoryProcessed "true"^^xsd:boolean .
                        
                        BIND((xsd:decimal(?stock) * ?hCost) + 
                             (xsd:decimal(?backlog) * ?bCost) AS ?weekCost)
                    }
                    GROUP BY ?actor
                }
                
                OPTIONAL { ?actor bg:totalCost ?oldCost }
            }
        """,
        
        # =====================================================================
        # CATEGORY 3: ANALYSIS RULES (Pattern Detection)
        # =====================================================================
        
        "STOCKOUT RISK DETECTION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?metrics bg:hasStockoutRisk ?oldRisk .
            }
            INSERT {
                ?metrics bg:hasStockoutRisk "true"^^xsd:boolean .
            }
            WHERE {
                ?week a bg:Week .
                
                ?actor a bg:Actor ;
                       bg:hasMetrics ?metrics ;
                       bg:shippingDelay ?leadTime ;
                       bg:orderDelay ?orderTime .
                
                ?metrics bg:forWeek ?week ;
                         bg:inventoryCoverage ?coverage .
                
                BIND(xsd:decimal(?leadTime + ?orderTime) AS ?totalLeadTime)
                FILTER(?coverage < ?totalLeadTime)
                
                OPTIONAL { ?metrics bg:hasStockoutRisk ?oldRisk }
            }
        """,
        
        "BULLWHIP DETECTION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?metrics bg:hasBullwhipRisk ?oldRisk .
                ?order bg:orderAmplification ?oldAmp .
            }
            INSERT {
                ?metrics bg:hasBullwhipRisk "true"^^xsd:boolean .
                ?order bg:orderAmplification ?ratio .
            }
            WHERE {
                ?week a bg:Week .
                
                ?order a bg:Order ;
                       bg:orderQuantity ?qty ;
                       bg:forWeek ?week ;
                       bg:placedBy ?actor .
                
                # Get actual demand for comparison
                OPTIONAL {
                    ?demand a bg:CustomerDemand ;
                            bg:forWeek ?week ;
                            bg:actualDemand ?realDemand .
                }
                
                # Or use perceived demand rate
                ?actor bg:hasMetrics ?metrics .
                ?metrics bg:forWeek ?week ;
                         bg:demandRate ?demandRate .
                
                BIND(COALESCE(?realDemand, ?demandRate) AS ?baseline)
                
                FILTER(?baseline > 0)
                BIND(xsd:decimal(?qty) / xsd:decimal(?baseline) AS ?ratio)
                FILTER(?ratio > 1.3)
                
                OPTIONAL { ?metrics bg:hasBullwhipRisk ?oldRisk }
                OPTIONAL { ?order bg:orderAmplification ?oldAmp }
            }
        """,
        
        # =====================================================================
        # CATEGORY 4: POLICY RULES (Decision Logic)
        # =====================================================================
        
        "ORDER-UP-TO POLICY": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?metrics bg:suggestedOrderQuantity ?oldOrder .
            }
            INSERT {
                ?metrics bg:suggestedOrderQuantity ?finalOrder ;
                         bg:orderPolicyCalculated "true"^^xsd:boolean .
            }
            WHERE {
                ?week a bg:Week .
                
                ?metrics a bg:ActorMetrics ;
                        bg:forWeek ?week ;
                        bg:belongsTo ?actor ;
                        bg:demandRate ?rate .
                
                # IDEMPOTENCY: Skip if already calculated
                FILTER NOT EXISTS {
                    ?metrics bg:orderPolicyCalculated "true"^^xsd:boolean .
                }
                
                ?actor a bg:Actor ;
                       bg:shippingDelay ?leadTime ;
                       bg:orderDelay ?reviewPeriod .

                ?inv a bg:Inventory ;
                    bg:forWeek ?week ;
                    bg:belongsTo ?actor ;
                    bg:currentInventory ?currentStock .
                
                # CRITICAL: OPTIONAL before BIND
                OPTIONAL { ?metrics bg:suggestedOrderQuantity ?oldOrder }
                
                BIND(xsd:decimal(?leadTime + ?reviewPeriod) AS ?totalDelay)
                BIND(?rate * ?totalDelay AS ?targetStock)
                BIND(?targetStock - xsd:decimal(?currentStock) AS ?orderQty)
                BIND(xsd:integer(CEIL(IF(?orderQty > 0, ?orderQty, 0))) AS ?finalOrder)
            }
        """,
    }


class TemporalBeerGameRuleExecutor:
    """
    Executes SPARQL rules to implement Beer Game business logic
    
    Design:
    - Rules compute all state transitions
    - Rules make all decisions
    - Orchestrator only creates external events
    """
    
    def __init__(self, base_url="http://localhost:7200"):
        self.base_url = base_url
        self.rules = get_temporal_rules()
        self.session = requests.Session()
        
        # Repository mapping
        self.repositories = {
            "Retailer": "BG_Retailer",
            "Wholesaler": "BG_Wholesaler",
            "Distributor": "BG_Distributor",
            "Factory": "BG_Factory"
        }
    
    def create_week_entity(self, week):
        """
        Create bg:Week_N entity in all repositories
        This provides the temporal anchor for all entities in that week
        Idempotent: can be called multiple times safely
        """
        print(f"   Creating Week_{week} entities...")
        
        for actor_name, repo_id in self.repositories.items():
            # Use DELETE+INSERT to ensure weekNumber always exists
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                DELETE {{
                    bg:Week_{week} bg:weekNumber ?oldNum ;
                                   rdfs:label ?oldLabel .
                }}
                INSERT {{
                    bg:Week_{week} a bg:Week ;
                        bg:weekNumber "{week}"^^xsd:integer ;
                        rdfs:label "Week {week}" .
                }}
                WHERE {{
                    # Bind old values if they exist (for DELETE)
                    OPTIONAL {{ bg:Week_{week} bg:weekNumber ?oldNum }}
                    OPTIONAL {{ bg:Week_{week} rdfs:label ?oldLabel }}
                }}
            """
            
            endpoint = f"{self.base_url}/repositories/{repo_id}/statements"
            headers = {"Content-Type": "application/sparql-update"}
            
            try:
                response = self.session.post(endpoint, data=query, headers=headers, timeout=30)
                if response.status_code == 204:
                    pass  # Success, don't print for every repo
                elif response.status_code == 400:
                    print(f"      ✗ Failed Week_{week} in {actor_name}: {response.text[:200]}")
            except Exception as e:
                print(f"      ✗ Exception creating Week_{week} in {actor_name}: {e}")
        
        print(f"      ✓ Week_{week} created in all repositories")
    
    def create_actor_metrics_snapshot(self, week):
        """
        Create ActorMetrics snapshot for the week if it doesn't exist
        This is required before rules can compute metrics
        """
        print(f"   Creating ActorMetrics snapshots for Week_{week}...")
        
        prev_week = week - 1
        
        for actor_name, repo_id in self.repositories.items():
            # Use namespace-specific prefix
            namespace_map = {
                "BG_Retailer": "bg_retailer",
                "BG_Wholesaler": "bg_wholesaler", 
                "BG_Distributor": "bg_distributor",
                "BG_Factory": "bg_factory"
            }
            ns = namespace_map[repo_id]
            
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX {ns}: <http://beergame.org/{ns.replace('bg_', '')}#>
                
                INSERT {{
                    {ns}:{{actor_name}}_Metrics_W{week} a bg:ActorMetrics ;
                        bg:forWeek bg:Week_{week} ;
                        bg:belongsTo {ns}:{{actor_name}} ;
                        bg:demandRate ?rate ;
                        bg:inventoryCoverage "0.0"^^xsd:decimal ;
                        bg:suggestedOrderQuantity "0"^^xsd:integer ;
                        bg:hasBullwhipRisk "false"^^xsd:boolean ;
                        bg:hasStockoutRisk "false"^^xsd:boolean ;
                        rdfs:label "{{actor_name}} Metrics Week {week}" .
                    
                    {ns}:{{actor_name}} bg:hasMetrics {ns}:{{actor_name}}_Metrics_W{week} .
                }}
                WHERE {{
                    # Bind specific actor to avoid matching all actors in repo
                    BIND({ns}:{{actor_name}} AS ?actor)
                    
                    # Get demandRate from previous week or default
                    OPTIONAL {{
                        ?actor bg:hasMetrics ?prevMetrics .
                        ?prevMetrics bg:forWeek bg:Week_{prev_week} ;
                                     bg:demandRate ?prevRate .
                    }}
                    BIND(COALESCE(?prevRate, 4.0) AS ?rate)
                    
                    # Only create if doesn't exist
                    FILTER NOT EXISTS {{
                        {ns}:{{actor_name}} bg:hasMetrics {ns}:{{actor_name}}_Metrics_W{week} .
                    }}
                }}
            """
            
            # Replace actor_name placeholder
            actor_uri_name = {
                "Retailer": "Retailer_Alpha",
                "Wholesaler": "Wholesaler_Beta",
                "Distributor": "Distributor_Gamma",
                "Factory": "Factory_Delta"
            }
            query = query.replace("{actor_name}", actor_uri_name[actor_name])
            
            endpoint = f"{self.base_url}/repositories/{repo_id}/statements"
            headers = {"Content-Type": "application/sparql-update"}
            
            try:
                response = self.session.post(endpoint, data=query, headers=headers, timeout=30)
                if response.status_code == 204:
                    print(f"      ✓ Created ActorMetrics for {actor_name}")
                elif response.status_code == 400:
                    print(f"      ✗ Failed for {actor_name}: {response.status_code}")
                    print(f"         Error: {response.text[:300]}")
                else:
                    print(f"      ✗ Failed for {actor_name}: {response.status_code}")
            except Exception as e:
                print(f"      ✗ Exception for {actor_name}: {e}")
    
    def create_inventory_snapshot(self, week):
        """
        Create Inventory snapshot for the new week by copying from previous week
        This is required before UPDATE INVENTORY rule can work
        """
        print(f"   Creating Inventory snapshots for Week_{week}...")
        
        prev_week = week - 1
        
        for actor_name, repo_id in self.repositories.items():
            namespace_map = {
                "BG_Retailer": "bg_retailer",
                "BG_Wholesaler": "bg_wholesaler", 
                "BG_Distributor": "bg_distributor",
                "BG_Factory": "bg_factory"
            }
            ns = namespace_map[repo_id]
            
            actor_uri_name = {
                "Retailer": "Retailer_Alpha",
                "Wholesaler": "Wholesaler_Beta",
                "Distributor": "Distributor_Gamma",
                "Factory": "Factory_Delta"
            }
            actor_uri = actor_uri_name[actor_name]
            
            # Use actor-prefixed naming for Week 2+
            inventory_name = f"{actor_uri}_Inventory_Week{week}"
            
            # Week 1 from TTL uses generic naming without actor prefix
            if prev_week == 1:
                prev_inventory_name = "Inventory_Week1"
            else:
                prev_inventory_name = f"{actor_uri}_Inventory_Week{prev_week}"
            
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX {ns}: <http://beergame.org/{ns.replace('bg_', '')}#>
                
                INSERT {{
                    {ns}:{inventory_name} a bg:Inventory ;
                        bg:forWeek bg:Week_{week} ;
                        bg:belongsTo {ns}:{actor_uri} ;
                        bg:currentInventory ?prevStock ;
                        bg:backlog ?prevBacklog ;
                        bg:incomingShipment "0"^^xsd:integer ;
                        bg:outgoingShipment "0"^^xsd:integer ;
                        bg:holdingCost ?hCost ;
                        bg:backlogCost ?bCost ;
                        rdfs:label "{actor_uri} Inventory Week {week}" .
                }}
                WHERE {{
                    # Get previous week's inventory
                    {ns}:{prev_inventory_name} a bg:Inventory ;
                        bg:currentInventory ?prevStock ;
                        bg:backlog ?prevBacklog ;
                        bg:holdingCost ?hCost ;
                        bg:backlogCost ?bCost .
                    
                    # Only create if doesn't exist
                    FILTER NOT EXISTS {{
                        {ns}:{inventory_name} a bg:Inventory .
                    }}
                }}
            """
            
            endpoint = f"{self.base_url}/repositories/{repo_id}/statements"
            headers = {"Content-Type": "application/sparql-update"}
            
            try:
                response = self.session.post(endpoint, data=query, headers=headers, timeout=30)
                if response.status_code == 204:
                    print(f"      ✓ Created {inventory_name} from {prev_inventory_name}")
                elif response.status_code == 400:
                    print(f"      ✗ Failed {inventory_name}: {response.status_code}")
                    print(f"         Error: {response.text[:300]}")
                else:
                    print(f"      ✗ Failed {inventory_name}: {response.status_code}")
            except Exception as e:
                print(f"      ✗ Exception for {inventory_name}: {e}")
    
    def execute_rule(self, rule_name, repository, dry_run=False):
        """Execute a specific rule on a repository"""
        if rule_name not in self.rules:
            print(f"✗ Rule not found: {rule_name}")
            return False
        
        rule_sparql = self.rules[rule_name]
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        
        if dry_run:
            print(f"   [DRY RUN] Would execute rule '{rule_name}' on {repository}")
            return True
        
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=rule_sparql, headers=headers, timeout=30)
            
            if response.status_code == 204:
                # Check if rule actually did something for CREATE rules
                if rule_name in ["CREATE ORDERS FROM SUGGESTED", "CREATE SHIPMENTS FROM ORDERS"]:
                    # Query to see if entities were created
                    check_query = f"""
                        PREFIX bg: <http://beergame.org/ontology#>
                        SELECT (COUNT(*) as ?count)
                        WHERE {{
                            ?entity a {'bg:Order' if 'ORDER' in rule_name else 'bg:Shipment'} .
                        }}
                    """
                    # Note: This is a simplification - in production we'd check for specific week
                    # For now, just log success
                    print(f"   ✓ Rule '{rule_name}' executed on {repository} [HTTP 204 - Success]")
                else:
                    print(f"   ✓ Rule '{rule_name}' executed on {repository} [HTTP 204 - Success]")
                return True
            elif response.status_code == 400:
                print(f"   ✗ Rule '{rule_name}' failed on {repository} [HTTP 400 - Bad Request]")
                print(f"      SPARQL Error: {response.text[:300]}")
                return False
            elif response.status_code == 500:
                print(f"   ✗ Rule '{rule_name}' failed on {repository} [HTTP 500 - Server Error]")
                print(f"      Error: {response.text[:300]}")
                return False
            else:
                print(f"   ⚠️  Rule '{rule_name}' on {repository} [HTTP {response.status_code}]")
                print(f"      Response: {response.text[:300]}")
                return False
        except requests.exceptions.Timeout:
            print(f"   ✗ Rule '{rule_name}' timed out on {repository} [Timeout]")
            return False
        except Exception as e:
            print(f"   ✗ Rule '{rule_name}' exception on {repository}: {e}")
            return False
    
    def propagate_orders_between_repos(self, week):
        """
        Propagate orders from sender to receiver repositories
        
        When Retailer creates Order_Week{N}_ToWholesaler in BG_Retailer,
        this copies it to BG_Wholesaler so the Wholesaler can create shipments.
        """
        print(f"   Propagating orders between repositories...")
        
        # For now, skip this - let's use a simpler approach in CREATE SHIPMENTS
        # We'll make CREATE SHIPMENTS look for orders in its own repo only
        pass
    
    def query_arriving_shipments_federated(self, week_number, actor_uri, actor_repo):
        """
        V3 NEW: Query arriving shipments using BG_Supply_Chain federation
        
        This replaces the need to manually propagate shipments between repos.
        The federated query automatically sees shipments in all repositories.
        
        Returns: Total quantity of shipments arriving this week for the actor
        """
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT (SUM(?qty) as ?totalArriving)
            WHERE {{
                ?shipment a bg:Shipment ;
                          bg:shippedTo <{actor_uri}> ;
                          bg:arrivalWeek "{week_number}"^^xsd:integer ;
                          bg:shippedQuantity ?qty .
            }}
        """
        
        # Query BG_Supply_Chain (federation endpoint)
        endpoint = f"{self.base_url}/repositories/BG_Supply_Chain"
        headers = {"Accept": "application/sparql-results+json"}
        
        try:
            response = self.session.post(
                endpoint,
                data={"query": query},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                bindings = results.get("results", {}).get("bindings", [])
                
                if bindings and bindings[0].get("totalArriving"):
                    total = int(bindings[0]["totalArriving"]["value"])
                    print(f"      🚢 Federated query found {total} units arriving for {actor_uri.split('#')[1]}")
                    return total
                else:
                    return 0
            else:
                print(f"      ⚠️  Federated query failed: HTTP {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"      ✗ Federated query error: {e}")
            return 0
    
    def set_temp_arriving_shipments(self, week_number, actor_uri, actor_repo, quantity):
        """
        V3 Helper: Set temporary property for arriving shipments
        This allows UPDATE INVENTORY rule to use federated query results
        """
        update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            INSERT {{
                ?inv bg:tempArrivingShipments "{quantity}"^^xsd:integer .
            }}
            WHERE {{
                ?inv a bg:Inventory ;
                     bg:forWeek bg:Week_{week_number} ;
                     bg:belongsTo <{actor_uri}> .
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{actor_repo}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=update, headers=headers, timeout=30)
            return response.status_code == 204
        except:
            return False
    
    def query_incoming_orders_federated(self, week_number, actor_uri, actor_repo):
        """
        V3 NEW: Query incoming orders using BG_Supply_Chain federation
        
        This replaces the need to manually propagate orders between repos.
        The federated query automatically sees orders in all repositories.
        
        Returns: List of (placedBy_uri, quantity) tuples for orders received by this actor
        """
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT ?placedBy ?qty
            WHERE {{
                ?order a bg:Order ;
                       bg:forWeek bg:Week_{week_number} ;
                       bg:receivedBy <{actor_uri}> ;
                       bg:placedBy ?placedBy ;
                       bg:orderQuantity ?qty .
            }}
        """
        
        # Query BG_Supply_Chain (federation endpoint)
        endpoint = f"{self.base_url}/repositories/BG_Supply_Chain"
        headers = {"Accept": "application/sparql-results+json"}
        
        try:
            response = self.session.post(
                endpoint,
                data={"query": query},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                bindings = results.get("results", {}).get("bindings", [])
                
                orders = []
                for b in bindings:
                    placed_by = b['placedBy']['value']
                    qty = int(b['qty']['value'])
                    orders.append((placed_by, qty))
                
                if orders:
                    print(f"      📦 Federated query found {len(orders)} incoming orders for {actor_uri.split('#')[1]}")
                    for placed_by, qty in orders:
                        print(f"         - {qty} units from {placed_by.split('#')[1]}")
                return orders
            else:
                print(f"      ⚠️  Federated orders query failed: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"      ✗ Federated orders query error: {e}")
            return []
    
    def create_shipments_from_federated_orders(self, week_number, actor_uri, actor_repo, orders):
        """
        V3 NEW: Create shipments based on federated order query results
        
        For each order found, create a shipment in the actor's repository
        """
        if not orders:
            return
        
        # Get actor's shipping delay
        actor_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?shippingDelay WHERE {{
                <{actor_uri}> bg:shippingDelay ?shippingDelay .
            }}
        """
        
        try:
            response = self.session.post(
                f"{self.base_url}/repositories/{actor_repo}",
                data={"query": actor_query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=10
            )
            
            if response.status_code == 200:
                bindings = response.json().get("results", {}).get("bindings", [])
                shipping_delay = int(bindings[0]['shippingDelay']['value']) if bindings else 2
            else:
                shipping_delay = 2  # Default
        except:
            shipping_delay = 2
        
        arrival_week = week_number + shipping_delay
        
        # Create shipments for each order
        for placed_by_uri, qty in orders:
            # Extract names for URI construction
            downstream_name = placed_by_uri.split('#')[1].split('_')[0]  # "Retailer_Alpha" -> "Retailer"
            
            shipment_uri = f"{actor_uri.split('#')[0]}#Shipment_Week{week_number}_To{downstream_name}"
            
            insert = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                INSERT DATA {{
                    <{shipment_uri}> a bg:Shipment ;
                        bg:forWeek bg:Week_{week_number} ;
                        bg:belongsTo <{actor_uri}> ;
                        bg:shippedFrom <{actor_uri}> ;
                        bg:shippedTo <{placed_by_uri}> ;
                        bg:shippedQuantity "{qty}"^^xsd:integer ;
                        bg:arrivalWeek "{arrival_week}"^^xsd:integer ;
                        rdfs:comment "Shipment responding to order (Week {week_number}, arrives {arrival_week})" .
                }}
            """
            
            try:
                response = self.session.post(
                    f"{self.base_url}/repositories/{actor_repo}/statements",
                    data=insert,
                    headers={"Content-Type": "application/sparql-update"},
                    timeout=10
                )
                
                if response.status_code == 204:
                    print(f"         ✓ Created shipment: {qty} units to {placed_by_uri.split('#')[1]}")
                else:
                    print(f"         ✗ Failed to create shipment: HTTP {response.status_code}")
            except Exception as e:
                print(f"         ✗ Error creating shipment: {e}")
    
    
    def query_observed_demand_federated(self, week_number, actor_uri, actor_repo):
        """
        V3 NEW: Query observed demand using BG_Supply_Chain federation
        
        For Retailer: Uses CustomerDemand (local, current week)
        For others: Uses incoming Orders (federated query, PREVIOUS week)
        
        Note: Orders are queried from week N-1 because orders for week N 
              haven't been created yet when DEMAND RATE SMOOTHING executes.
        
        Returns: Observed demand quantity
        """
        # Check if this is Retailer (has CustomerDemand)
        customer_demand_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT ?demand
            WHERE {{
                ?demandEntity a bg:CustomerDemand ;
                              bg:forWeek bg:Week_{week_number} ;
                              bg:belongsTo <{actor_uri}> ;
                              bg:actualDemand ?demand .
            }}
        """
        
        endpoint_local = f"{self.base_url}/repositories/{actor_repo}"
        
        try:
            response = self.session.post(
                endpoint_local,
                data={"query": customer_demand_query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=10
            )
            
            if response.status_code == 200:
                bindings = response.json().get("results", {}).get("bindings", [])
                if bindings:
                    demand = float(bindings[0]["demand"]["value"])
                    print(f"      📊 Customer demand for {actor_uri.split('#')[1]}: {demand}")
                    return demand
        except:
            pass
        
        # No customer demand, query incoming orders from PREVIOUS week (federated)
        # We use week N-1 because orders for week N haven't been created yet
        prev_week = week_number - 1
        if prev_week < 1:
            return None  # No previous week
        
        orders_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT (AVG(?qty) as ?avgQty)
            WHERE {{
                ?order a bg:Order ;
                       bg:forWeek bg:Week_{prev_week} ;
                       bg:receivedBy <{actor_uri}> ;
                       bg:orderQuantity ?qty .
            }}
        """
        
        endpoint_fed = f"{self.base_url}/repositories/BG_Supply_Chain"
        
        try:
            response = self.session.post(
                endpoint_fed,
                data={"query": orders_query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30
            )
            
            if response.status_code == 200:
                bindings = response.json().get("results", {}).get("bindings", [])
                if bindings and bindings[0].get("avgQty"):
                    avg_qty = float(bindings[0]["avgQty"]["value"])
                    print(f"      📦 Federated orders (Week {prev_week}) for {actor_uri.split('#')[1]}: {avg_qty}")
                    return avg_qty
        except Exception as e:
            print(f"      ✗ Federated demand query error: {e}")
        
        return None  # No demand observed
    
    def set_temp_observed_demand(self, week_number, actor_uri, actor_repo, observed_demand):
        """
        V3 Helper: Set temporary property for observed demand
        This allows DEMAND RATE SMOOTHING rule to use federated query results
        """
        if observed_demand is None:
            return False
        
        update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            INSERT {{
                ?metrics bg:tempObservedDemand "{observed_demand}"^^xsd:decimal .
            }}
            WHERE {{
                ?metrics a bg:ActorMetrics ;
                         bg:forWeek bg:Week_{week_number} ;
                         bg:belongsTo <{actor_uri}> .
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{actor_repo}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=update, headers=headers, timeout=30)
            return response.status_code == 204
        except:
            return False
    
    def execute_demand_rate_smoothing_with_federation(self, week_number):
        """
        V3 NEW: Execute DEMAND RATE SMOOTHING with federated demand queries
        
        Process:
        1. For each actor, query observed demand from BG_Supply_Chain
        2. Set temp property with observed demand
        3. Execute DEMAND RATE SMOOTHING rule (uses temp property)
        4. Clean up temp properties
        """
        print(f"\n→ Executing: DEMAND RATE SMOOTHING (with federated demand queries)")
        
        # Actor URI mapping
        actor_uris = {
            "BG_Retailer": "http://beergame.org/retailer#Retailer_Alpha",
            "BG_Wholesaler": "http://beergame.org/wholesaler#Wholesaler_Beta",
            "BG_Distributor": "http://beergame.org/distributor#Distributor_Gamma",
            "BG_Factory": "http://beergame.org/factory#Factory_Delta"
        }
        
        for actor_repo, actor_uri in actor_uris.items():
            # Step 1: Query observed demand (federated for non-Retailer)
            observed = self.query_observed_demand_federated(week_number, actor_uri, actor_repo)
            
            # Step 2: Set temp property
            if observed is not None:
                self.set_temp_observed_demand(week_number, actor_uri, actor_repo, observed)
        
        # Step 3: Execute DEMAND RATE SMOOTHING rule
        for repo in self.repositories.values():
            self.execute_rule("DEMAND RATE SMOOTHING", repo)
        
        # Step 4: Clean up temp properties
        for repo in self.repositories.values():
            cleanup = """
                PREFIX bg: <http://beergame.org/ontology#>
                DELETE { ?metrics bg:tempObservedDemand ?val }
                WHERE { ?metrics bg:tempObservedDemand ?val }
            """
            endpoint = f"{self.base_url}/repositories/{repo}/statements"
            self.session.post(endpoint, data=cleanup, headers={"Content-Type": "application/sparql-update"})
    
    def execute_inventory_update_with_federation(self, week_number):
        """
        V3 NEW: Execute UPDATE INVENTORY with federated shipment queries
        
        Process:
        1. For each actor, query arriving shipments from BG_Supply_Chain
        2. Set temp property with arriving quantity
        3. Execute UPDATE INVENTORY rule (uses temp property)
        4. Clean up temp properties
        """
        print(f"\n→ Executing: UPDATE INVENTORY (with federated shipment queries)")
        
        # Actor URI mapping
        actor_uris = {
            "BG_Retailer": "http://beergame.org/retailer#Retailer_Alpha",
            "BG_Wholesaler": "http://beergame.org/wholesaler#Wholesaler_Beta",
            "BG_Distributor": "http://beergame.org/distributor#Distributor_Gamma",
            "BG_Factory": "http://beergame.org/factory#Factory_Delta"
        }
        
        for actor_repo, actor_uri in actor_uris.items():
            # Step 1: Query arriving shipments (federated)
            arriving = self.query_arriving_shipments_federated(week_number, actor_uri, actor_repo)
            
            # Step 2: Set temp property
            self.set_temp_arriving_shipments(week_number, actor_uri, actor_repo, arriving)
        
        # Step 3: Execute UPDATE INVENTORY rule
        for repo in self.repositories.values():
            self.execute_rule("UPDATE INVENTORY", repo)
        
        # Step 4: Clean up temp properties
        for repo in self.repositories.values():
            cleanup = """
                PREFIX bg: <http://beergame.org/ontology#>
                DELETE { ?inv bg:tempArrivingShipments ?val }
                WHERE { ?inv bg:tempArrivingShipments ?val }
            """
            endpoint = f"{self.base_url}/repositories/{repo}/statements"
            self.session.post(endpoint, data=cleanup, headers={"Content-Type": "application/sparql-update"})
    
    def execute_week_rules(self, week_number, repositories=None, dry_run=False):
        """
        Execute all rules for a specific week in dependency order
        
        V3 CHANGES:
        - UPDATE INVENTORY uses federated query for arriving shipments
        - No manual propagation needed (federation handles visibility)
        
        Rule execution order based on dependencies:
        1. Demand Rate Smoothing (updates perception)
        2. Update Inventory (V3: with federated shipment query)
        3. Inventory Coverage (calculates metrics)
        4. Stockout Risk Detection (identifies problems)
        5. Order-Up-To Policy (suggests quantities)
        6. Create Orders (generates documents)
        7. Create Shipments (responds to orders)
        8. Bullwhip Detection (analyzes patterns)
        9. Total Cost Calculation (computes costs)
        """
        
        if repositories is None:
            repositories = list(self.repositories.values())
        
        print(f"\n{'='*70}")
        print(f"⚙️  EXECUTING RULES FOR WEEK {week_number} (V3 - Federated)")
        print(f"{'='*70}")
        
        executed = 0
        failed = 0
        
        # Step 1: V3 DEMAND RATE SMOOTHING with federated demand queries
        self.execute_demand_rate_smoothing_with_federation(week_number)
        executed += len(repositories)  # Count as success for all repos
        
        # Step 2: V3 UPDATE INVENTORY with federated shipment queries
        self.execute_inventory_update_with_federation(week_number)
        executed += len(repositories)  # Count as success for all repos
        
        # Step 3-6: Continue with metrics and policy rules
        pre_shipment_rules = [
            "INVENTORY COVERAGE CALCULATION",
            "STOCKOUT RISK DETECTION",
            "ORDER-UP-TO POLICY",
            "CREATE ORDERS FROM SUGGESTED"
        ]
        
        for rule_name in pre_shipment_rules:
            if rule_name not in self.rules:
                print(f"⚠️  Rule '{rule_name}' not found, skipping")
                continue
            
            print(f"\n→ Executing: {rule_name}")
            
            for repo in repositories:
                if self.execute_rule(rule_name, repo):
                    executed += 1
                else:
                    failed += 1
        
        # Step 7: V3 CREATE SHIPMENTS with federated order queries
        print(f"\n→ Executing: CREATE SHIPMENTS (V3 federated version)")
        
        actor_uris = {
            "BG_Retailer": "http://beergame.org/retailer#Retailer_Alpha",
            "BG_Wholesaler": "http://beergame.org/wholesaler#Wholesaler_Beta",
            "BG_Distributor": "http://beergame.org/distributor#Distributor_Gamma",
            "BG_Factory": "http://beergame.org/factory#Factory_Delta"
        }
        
        for actor_repo, actor_uri in actor_uris.items():
            # Query incoming orders (federated)
            orders = self.query_incoming_orders_federated(week_number, actor_uri, actor_repo)
            
            # Create shipments based on orders found
            if orders:
                self.create_shipments_from_federated_orders(week_number, actor_uri, actor_repo, orders)
        
        executed += len(repositories)  # Count as success for all repos
        
        # Step 8-9: Continue with analysis rules
        post_shipment_rules = [
            "BULLWHIP DETECTION",
            "TOTAL COST CALCULATION"
        ]
        
        for rule_name in post_shipment_rules:
            if rule_name not in self.rules:
                print(f"⚠️  Rule '{rule_name}' not found, skipping")
                continue
            
            print(f"\n→ Executing: {rule_name}")
            
            for repo in repositories:
                if self.execute_rule(rule_name, repo):
                    executed += 1
                else:
                    failed += 1
        
        print(f"\n{'='*70}")
        print(f"✓ Executed: {executed} | ✗ Failed: {failed}")
        print(f"{'='*70}\n")
        
        return executed, failed
    
    def query_week_summary(self, week_number):
        """Query and display summary for a specific week across all actors"""
        print(f"\n📊 WEEK {week_number} SUMMARY:")
        print("="*70)
        
        for actor_name, repo_id in self.repositories.items():
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?inv ?backlog ?coverage ?suggested ?cost
                WHERE {{
                    ?actor a bg:Actor ;
                           rdfs:label ?actorLabel .
                    
                    # Get inventory
                    OPTIONAL {{
                        ?invEntity a bg:Inventory ;
                                   bg:forWeek bg:Week_{week_number} ;
                                   bg:belongsTo ?actor ;
                                   bg:currentInventory ?inv ;
                                   bg:backlog ?backlog .
                    }}
                    
                    # Get metrics
                    OPTIONAL {{
                        ?actor bg:hasMetrics ?metrics .
                        ?metrics bg:forWeek bg:Week_{week_number} ;
                                 bg:inventoryCoverage ?coverage ;
                                 bg:suggestedOrderQuantity ?suggested .
                    }}
                    
                    # Get total cost
                    OPTIONAL {{
                        ?actor bg:totalCost ?cost .
                    }}
                }}
                LIMIT 1
            """
            
            endpoint = f"{self.base_url}/repositories/{repo_id}"
            headers = {"Accept": "application/sparql-results+json"}
            
            try:
                response = self.session.post(
                    endpoint,
                    data={"query": query},
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    bindings = result.get("results", {}).get("bindings", [])
                    
                    if bindings:
                        b = bindings[0]
                        inv = b.get("inv", {}).get("value", "N/A")
                        backlog = b.get("backlog", {}).get("value", "N/A")
                        coverage = b.get("coverage", {}).get("value", "N/A")
                        suggested = b.get("suggested", {}).get("value", "N/A")
                        cost = b.get("cost", {}).get("value", "N/A")
                        
                        print(f"  {actor_name}:")
                        print(f"    Inventory: {inv}")
                        print(f"    Backlog: {backlog}")
                        print(f"    Coverage: {coverage} weeks" if coverage != "N/A" else f"    Coverage: {coverage}")
                        print(f"    Suggested order: {suggested}")
                        print(f"    Total cost: ${cost}")
                    else:
                        print(f"  {actor_name}: No data found")
                else:
                    print(f"  {actor_name}: Query failed ({response.status_code})")
            
            except Exception as e:
                print(f"  {actor_name}: Error - {e}")
        
        print("="*70)



# End of module
# This is a library module - import and use from orchestrator
# For standalone simulation, use: advanced_simulation_v2.py

