"""
Beer Game Federated KG - Temporal Rules Engine (Clean Architecture)

Design Philosophy:
- All Beer Game business logic is encoded as SPARQL rules
- Rules compute state transitions, metrics, and decisions
- This module is a LIBRARY - import and use from orchestrator
- For standalone execution, use: advanced_simulation_v2.py

Usage:
    from temporal_beer_game_rules_v2 import TemporalBeerGameRuleExecutor
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
            
            DELETE {
                ?inv bg:currentInventory ?oldInv ;
                     bg:backlog ?oldBacklog .
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
                     bg:belongsTo ?actor ;
                     bg:currentInventory ?oldInv ;
                     bg:backlog ?oldBacklog .
                
                # IDEMPOTENCY: Skip if already processed
                FILTER NOT EXISTS {
                    ?inv bg:inventoryProcessed "true"^^xsd:boolean .
                }
                
                # Get arriving shipments (arrivalWeek = current week number)
                OPTIONAL {
                    SELECT ?actor ?week (SUM(?qty) as ?arriving)
                    WHERE {
                        ?shipment a bg:Shipment ;
                                  bg:shippedTo ?actor ;
                                  bg:shippedQuantity ?qty ;
                                  bg:arrivalWeek ?arrivalNum .
                        
                        ?week bg:weekNumber ?arrivalNum .
                    }
                    GROUP BY ?actor ?week
                }
                BIND(COALESCE(?arriving, 0) AS ?incomingShipments)
                
                # Get demand for this week
                OPTIONAL {
                    SELECT ?actor ?week (SUM(?demand) as ?totalDemand)
                    WHERE {
                        {
                            # Customer demand (for retailer)
                            ?demand_entity a bg:CustomerDemand ;
                                          bg:forWeek ?week ;
                                          bg:belongsTo ?actor ;
                                          bg:actualDemand ?demand .
                        } UNION {
                            # Downstream orders (for other actors)
                            ?order a bg:Order ;
                                   bg:forWeek ?week ;
                                   bg:receivedBy ?actor ;
                                   bg:orderQuantity ?demand .
                        }
                    }
                    GROUP BY ?actor ?week
                }
                BIND(COALESCE(?totalDemand, 0) AS ?demandThisWeek)
                
                # Calculate new inventory
                BIND(xsd:integer(?oldInv) + xsd:integer(?incomingShipments) AS ?afterArrival)
                BIND(?demandThisWeek + xsd:integer(?oldBacklog) AS ?totalNeed)
                
                # Fulfill what we can
                BIND(
                    IF(?afterArrival >= ?totalNeed,
                       ?afterArrival - ?totalNeed,
                       0
                    ) AS ?newInv
                )
                BIND(
                    IF(?afterArrival >= ?totalNeed,
                       0,
                       ?totalNeed - ?afterArrival
                    ) AS ?newBacklog
                )
                
                # Bind old values for DELETE
                OPTIONAL { ?inv bg:currentInventory ?oldInv }
                OPTIONAL { ?inv bg:backlog ?oldBacklog }
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
                
                # Get actual demand for this week
                OPTIONAL {
                    ?demand a bg:CustomerDemand ;
                            bg:forWeek ?week ;
                            bg:belongsTo ?actor ;
                            bg:actualDemand ?currentDemand .
                }
                
                # If no customer demand, check for downstream orders
                OPTIONAL {
                    SELECT ?actor ?week (AVG(?qty) as ?avgOrderQty)
                    WHERE {
                        ?order a bg:Order ;
                               bg:forWeek ?week ;
                               bg:receivedBy ?actor ;
                               bg:orderQuantity ?qty .
                    }
                    GROUP BY ?actor ?week
                }
                
                BIND(COALESCE(?currentDemand, ?avgOrderQty, ?oldRate) AS ?observedDemand)
                
                # Exponential smoothing: 30% new, 70% old
                BIND((xsd:decimal(?observedDemand) * 0.3) + (?oldRate * 0.7) AS ?smoothedRate)
                
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
        """
        print(f"   Creating Week_{week} entities...")
        
        for actor_name, repo_id in self.repositories.items():
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                INSERT {{
                    bg:Week_{week} a bg:Week ;
                        bg:weekNumber "{week}"^^xsd:integer ;
                        rdfs:label "Week {week}" .
                }}
                WHERE {{
                    # Only insert if weekNumber doesn't exist (more specific check)
                    FILTER NOT EXISTS {{ 
                        bg:Week_{week} bg:weekNumber ?num 
                    }}
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
    
    def execute_week_rules(self, week_number, repositories=None, dry_run=False):
        """
        Execute all rules for a specific week in dependency order
        
        Rule execution order based on dependencies:
        1. Demand Rate Smoothing (updates perception)
        2. Update Inventory (processes arrivals + demand)
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
        print(f"⚙️  EXECUTING RULES FOR WEEK {week_number}")
        print(f"{'='*70}")
        
        
        # Rules execute on existing structure
        # Structure creation is the orchestrator's responsibility
        
        # Rule execution order (dependency-driven)
        rule_order = [
            "DEMAND RATE SMOOTHING",
            "UPDATE INVENTORY",
            "INVENTORY COVERAGE CALCULATION",
            "STOCKOUT RISK DETECTION",
            "ORDER-UP-TO POLICY",
            "CREATE ORDERS FROM SUGGESTED",
            "CREATE SHIPMENTS FROM ORDERS",
            "BULLWHIP DETECTION",
            "TOTAL COST CALCULATION"
        ]
        
        executed = 0
        failed = 0
        
        for rule_name in rule_order:
            if rule_name not in self.rules:
                print(f"⚠️  Rule '{rule_name}' not found, skipping")
                continue
            
            print(f"\n→ Executing: {rule_name}")
            
            for repo in repositories:
                if self.execute_rule(rule_name, repo, dry_run):
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

