"""
Beer Game Federated KG - TEMPORAL VERSION (UPDATED)
Updated for SHACL compliance:
- Integer quantities (orderQuantity, shipment quantity)
- arrivalWeek as bg:Week IRI (not xsd:integer)
"""

import requests
import time

def get_temporal_rules():
    """
    Define all SPARQL rules for TEMPORAL ontology
    Key changes:
    - bg:weekNumber → bg:forWeek (pointing to bg:Week instance)
    - Metrics attached to bg:ActorMetrics, not bg:Actor directly
    - All entities have bg:forWeek and bg:belongsTo
    - Integer quantities for discrete units
    - arrivalWeek as IRI to bg:Week
    """
    return {
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
                # Find order for current week
                ?order a bg:Order ;
                       bg:orderQuantity ?qty ;
                       bg:forWeek ?week ;
                       bg:placedBy ?actor .
                
                # Find customer demand for same week
                ?demand a bg:CustomerDemand ;
                        bg:forWeek ?week ;
                        bg:actualDemand ?realDemand .
                
                # Calculate amplification ratio (quantities are integers)
                FILTER(?realDemand > 0)
                BIND(xsd:decimal(?qty) / xsd:decimal(?realDemand) AS ?ratio)
                FILTER(?ratio > 1.3)
                
                # Find ActorMetrics for this actor and week
                ?actor bg:hasMetrics ?metrics .
                ?metrics bg:forWeek ?week .
                
                # Delete old values if exist
                OPTIONAL { ?metrics bg:hasBullwhipRisk ?oldRisk }
                OPTIONAL { ?order bg:orderAmplification ?oldAmp }
            }
        """,
        
        "ORDER CAPPING (GUARDRAIL)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?metrics bg:maxOrderQuantity ?oldMax .
            }
            INSERT {
                ?metrics bg:maxOrderQuantity ?maxOrder .
            }
            WHERE {
                # Find actors with bullwhip risk
                ?actor a bg:Actor ;
                       bg:hasMetrics ?metrics .
                
                ?metrics bg:forWeek ?week ;
                         bg:hasBullwhipRisk "true"^^xsd:boolean .
                
                # Get actual demand for that week
                ?demand a bg:CustomerDemand ;
                        bg:forWeek ?week ;
                        bg:actualDemand ?realDemand .
                
                # Calculate max allowed order (120% of real demand, rounded to integer)
                BIND(CEIL(xsd:decimal(?realDemand) * 1.2) AS ?maxOrder)
                
                OPTIONAL { ?metrics bg:maxOrderQuantity ?oldMax }
            }
        """,
        
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
                # Get actor's lead time
                ?actor a bg:Actor ;
                       bg:shippingDelay ?leadTime ;
                       bg:hasMetrics ?metrics .
                
                # Get metrics for specific week
                ?metrics bg:forWeek ?week ;
                         bg:demandRate ?rate .
                
                # Get inventory for same week
                ?inv a bg:Inventory ;
                     bg:forWeek ?week ;
                     bg:belongsTo ?actor ;
                     bg:currentInventory ?stock .
                
                # Check if coverage < lead time
                FILTER(?rate > 0)
                BIND(xsd:decimal(?stock) / ?rate AS ?coverage)
                FILTER(?coverage < ?leadTime)
                
                OPTIONAL { ?metrics bg:hasStockoutRisk ?oldRisk }
            }
        """,
        
        "INVENTORY COVERAGE CALCULATION (Fixed)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            DELETE {
                ?metrics bg:inventoryCoverage ?any .
            }
            INSERT {
                ?metrics bg:inventoryCoverage ?coverage .
            }
            WHERE {
                # Get metrics for any week
                ?metrics a bg:ActorMetrics ;
                        bg:forWeek ?week ;
                        bg:belongsTo ?actor ;
                        bg:demandRate ?rate .
                
                # Get inventory for the SAME week
                ?inv a bg:Inventory ;
                    bg:forWeek ?week ;
                    bg:belongsTo ?actor ;
                    bg:currentInventory ?stock .

                FILTER(?rate > 0)
                BIND(xsd:decimal(?stock) / ?rate AS ?coverage)
                
                OPTIONAL { ?metrics bg:inventoryCoverage ?any }
            }
        """,
        
        "DYNAMIC BUDGET INCREASE (CRITICAL SITUATION)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:budgetConstraint ?oldBudget .
            }
            INSERT {
                ?actor bg:budgetConstraint ?newBudget .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:budgetConstraint ?normalBudget ;
                       bg:hasMetrics ?metrics .
                
                ?metrics bg:hasStockoutRisk "true"^^xsd:boolean ;
                         bg:inventoryCoverage ?coverage .
                
                # Only increase if coverage < 2 weeks
                FILTER(?coverage < 2.0)
                BIND(?normalBudget * 1.5 AS ?newBudget)
                
                OPTIONAL { ?actor bg:budgetConstraint ?oldBudget }
            }
        """,
        
        "DYNAMIC BUDGET DECREASE (OVERSTOCK)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:budgetConstraint ?oldBudget .
            }
            INSERT {
                ?actor bg:budgetConstraint ?newBudget .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:budgetConstraint ?normalBudget ;
                       bg:hasMetrics ?metrics .
                
                ?metrics bg:forWeek ?week ;
                         bg:demandRate ?rate .
                
                ?inv a bg:Inventory ;
                     bg:forWeek ?week ;
                     bg:belongsTo ?actor ;
                     bg:currentInventory ?stock .
                
                # Optimal stock = 4 weeks of demand
                BIND(?rate * 4.0 AS ?optimalStock)
                BIND(?optimalStock * 1.5 AS ?threshold)
                
                # Reduce budget if overstocked
                FILTER(xsd:decimal(?stock) > ?threshold)
                BIND(?normalBudget * 0.5 AS ?newBudget)
                
                OPTIONAL { ?actor bg:budgetConstraint ?oldBudget }
            }
        """,
        
        "TOTAL COST CALCULATION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:totalCost ?oldCost .
            }
            INSERT {
                ?actor bg:totalCost ?totalCost .
            }
            WHERE {
                ?actor a bg:Actor .
                
                ?inv a bg:Inventory ;
                     bg:belongsTo ?actor ;
                     bg:forWeek ?week ;
                     bg:currentInventory ?stock ;
                     bg:backlog ?backlog ;
                     bg:holdingCost ?hCost ;
                     bg:backlogCost ?bCost .
                
                BIND((xsd:decimal(?stock) * ?hCost) + (xsd:decimal(?backlog) * ?bCost) AS ?totalCost)
                
                OPTIONAL { ?actor bg:totalCost ?oldCost }
            }
        """,
        
        "SHIPMENT ARRIVAL CALCULATION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?shipment bg:arrivalWeek ?oldArrival .
            }
            INSERT {
                ?shipment bg:arrivalWeek ?arrivalWeekIRI .
            }
            WHERE {
                ?shipment a bg:Shipment ;
                          bg:forWeek ?week ;
                          bg:shippedFrom ?actor .
                
                ?week bg:weekNumber ?currentWeekNum .
                ?actor bg:shippingDelay ?delay .
                
                # Calculate arrival week number
                BIND(?currentWeekNum + ?delay AS ?arrivalWeekNum)
                
                # Convert to IRI (bg:Week_N)
                BIND(IRI(CONCAT("http://beergame.org/ontology#Week_", STR(?arrivalWeekNum))) AS ?arrivalWeekIRI)
                
                OPTIONAL { ?shipment bg:arrivalWeek ?oldArrival }
            }
        """,
        
        "ORDER-UP-TO POLICY (SUGGESTED ORDER - Fixed)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?metrics bg:suggestedOrderQuantity ?oldOrder .
            }
            INSERT {
                ?metrics bg:suggestedOrderQuantity ?finalOrder .
            }
            WHERE {
                # Get metrics for any week
                ?metrics a bg:ActorMetrics ;
                        bg:forWeek ?week ;
                        bg:belongsTo ?actor ;
                        bg:demandRate ?rate .
                
                # Get actor properties (lead times are static on Actor)
                ?actor a bg:Actor ;
                       bg:shippingDelay ?leadTime ;
                       bg:orderDelay ?reviewPeriod .

                # Get inventory for the SAME week
                ?inv a bg:Inventory ;
                    bg:forWeek ?week ;
                    bg:belongsTo ?actor ;
                    bg:currentInventory ?currentStock .                         

                BIND(xsd:decimal(?leadTime + ?reviewPeriod) AS ?totalDelay)
                BIND(?rate * ?totalDelay AS ?targetStock)
                BIND(?targetStock - xsd:decimal(?currentStock) AS ?orderQty)
                
                # Round up to nearest integer for discrete units
                BIND(xsd:integer(CEIL(IF(?orderQty > 0, ?orderQty, 0))) AS ?finalOrder)

                OPTIONAL { ?metrics bg:suggestedOrderQuantity ?oldOrder }
            }
        """,
        
        "DEMAND RATE SMOOTHING (EXPONENTIAL SMOOTHING)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?currentMetrics bg:demandRate ?oldRate .
            }
            INSERT {
                ?currentMetrics bg:demandRate ?smoothedRate .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:hasMetrics ?currentMetrics .
                
                ?currentMetrics bg:forWeek ?week ;
                                bg:demandRate ?oldRate .
                
                # Get actual demand for this week
                ?demand a bg:CustomerDemand ;
                        bg:forWeek ?week ;
                        bg:actualDemand ?currentDemand .
                
                # Exponential smoothing: 30% new, 70% old
                BIND((xsd:decimal(?currentDemand) * 0.3) + (?oldRate * 0.7) AS ?smoothedRate)
                
                # Only update if change > 5%
                BIND(ABS(?smoothedRate - ?oldRate) / ?oldRate AS ?changeRatio)
                FILTER(?changeRatio > 0.05)
            }
        """,
        
        "CLEAR RISK FLAGS": """
            PREFIX bg: <http://beergame.org/ontology#>
            
            DELETE {
                ?metrics bg:hasBullwhipRisk ?risk .
                ?metrics bg:hasStockoutRisk ?stockout .
            }
            WHERE {
                ?metrics a bg:ActorMetrics .
                OPTIONAL { ?metrics bg:hasBullwhipRisk ?risk }
                OPTIONAL { ?metrics bg:hasStockoutRisk ?stockout }
            }
        """
    }


class TemporalBeerGameRuleExecutor:
    """
    Executor for temporal beer game rules
    Handles week progression and ActorMetrics snapshots
    """
    
    def __init__(self, base_url="http://localhost:7200"):
        self.base_url = base_url
        self.session = requests.Session()
        self.rules = get_temporal_rules()
        
        # Fix typo in repository name
        self.repositories = [
            "BG_Retailer", 
            "BG_Wholesaler",     # Keep typo as-is since that's how it's named in GraphDB - Fixed 
            "BG_Distributor", 
            "BG_Factory"
        ]
    
    def create_week_instance(self, week_number, repository):
        """
        Ensure Week instance exists before running rules
        """
        week_uri = f"bg:Week_{week_number}"
        
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            INSERT {{
                {week_uri} a bg:Week ;
                    bg:weekNumber "{week_number}"^^xsd:integer ;
                    rdfs:label "Week {week_number}" .
            }}
            WHERE {{
                FILTER NOT EXISTS {{
                    {week_uri} a bg:Week .
                }}
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=query, headers=headers, timeout=30)
            if response.status_code == 204:
                return True
            else:
                print(f"   ⚠️  Warning: Could not create Week_{week_number}: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ⚠️  Exception creating week: {e}")
            return False
    
    def create_actor_metrics_snapshot(self, week_number, repository):
        """
        Create ActorMetrics snapshot for the week if it doesn't exist
        FIXED: Simplified URI construction to avoid IRI validation errors
        """
        prev_week = week_number - 1
        
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            INSERT {{
                ?newMetrics a bg:ActorMetrics ;
                    bg:forWeek bg:Week_{week_number} ;
                    bg:belongsTo ?actor ;
                    bg:demandRate ?rate ;
                    bg:inventoryCoverage "0.0"^^xsd:decimal ;
                    bg:hasBullwhipRisk "false"^^xsd:boolean ;
                    bg:hasStockoutRisk "false"^^xsd:boolean ;
                    rdfs:label ?metricsLabel .
                
                ?actor bg:hasMetrics ?newMetrics .
            }}
            WHERE {{
                ?actor a bg:Actor ;
                       rdfs:label ?actorName .
                
                # Get demandRate from previous week or default to 4.0
                OPTIONAL {{
                    ?actor bg:hasMetrics ?prevMetrics .
                    ?prevMetrics bg:forWeek bg:Week_{prev_week} ;
                                 bg:demandRate ?prevRate .
                    FILTER({week_number} > 1)
                }}
                BIND(COALESCE(?prevRate, 4.0) AS ?rate)
                
                # Only create if doesn't exist
                FILTER NOT EXISTS {{
                    ?actor bg:hasMetrics ?existingMetrics .
                    ?existingMetrics bg:forWeek bg:Week_{week_number} .
                }}
                
                # Generate unique URI - construct the full URI string then convert to IRI
                BIND(CONCAT(
                    "http://beergame.org/ontology#",
                    STRAFTER(STR(?actor), "#"),
                    "_Metrics_W{week_number}"
                ) AS ?metricsURI)
                BIND(IRI(?metricsURI) AS ?newMetrics)
                
                # Create readable label
                BIND(CONCAT(?actorName, " Metrics Week {week_number}") AS ?metricsLabel)
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=query, headers=headers, timeout=30)
            if response.status_code == 204:
                return True
            else:
                print(f"   ⚠️  Warning: Could not create ActorMetrics for Week {week_number}")
                print(f"      Status: {response.status_code}")
                if response.status_code in [400, 500]:
                    print(f"      Error: {response.text[:500]}")
                    print(f"      Query preview (first 300 chars):")
                    print(f"      {query[:300]}")
                return False
        except Exception as e:
            print(f"   ⚠️  Exception creating metrics: {e}")
            return False
    
    def cleanup_duplicate_metrics(self, repository):
        """
        CRITICAL FIX: Remove ALL metrics and recreate clean structure
        This is a nuclear option but necessary to fix recursive URIs
        """
        query = """
            PREFIX bg: <http://beergame.org/ontology#>
            
            DELETE {
                ?actor bg:hasMetrics ?metrics .
                ?metrics ?p ?o .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:hasMetrics ?metrics .
                ?metrics ?p ?o .
                
                # Delete ANY metrics (we'll recreate clean ones)
                FILTER(CONTAINS(STR(?metrics), "Metrics"))
            }
        """
        
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=query, headers=headers, timeout=30)
            if response.status_code == 204:
                print(f"   ✓ Cleaned ALL metrics in {repository} - will recreate")
                return True
            else:
                print(f"   ⚠️  Could not clean metrics: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ⚠️  Exception cleaning metrics: {e}")
            return False
    
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
                print(f"   ✓ Rule '{rule_name}' executed on {repository}")
                return True
            else:
                print(f"   ✗ Error executing '{rule_name}' on {repository}: {response.status_code}")
                if response.status_code == 400:
                    error_text = response.text[:500]
                    print(f"      Error: {error_text}")
                return False
                
        except Exception as e:
            print(f"   ✗ Exception executing '{rule_name}': {e}")
            return False
    
    def execute_all_rules_for_repository(self, repository, week_number, dry_run=False):
        """Execute all rules for a specific repository and week"""
        print(f"\n{'='*60}")
        print(f"PROCESSING {repository.upper()} - WEEK {week_number}")
        print(f"{'='*60}")
        
        # Step 0: Clean ALL metrics for EVERY week (nuclear option)
        if not dry_run:
            print(f"→ Cleaning ALL metrics (will recreate)...")
            self.cleanup_duplicate_metrics(repository)
        
        # Step 1: Ensure Week instance exists
        if not dry_run:
            print(f"→ Ensuring Week_{week_number} instance exists...")
            self.create_week_instance(week_number, repository)
            
            print(f"→ Creating ActorMetrics snapshot for Week {week_number}...")
            self.create_actor_metrics_snapshot(week_number, repository)
        
        executed = 0
        failed = 0
        
        # Step 2: Clear risk flags FIRST
        if "CLEAR RISK FLAGS" in self.rules:
            print(f"→ Rule: CLEAR RISK FLAGS")
            if self.execute_rule("CLEAR RISK FLAGS", repository, dry_run):
                executed += 1
            else:
                failed += 1
        
        # Step 3: Apply all other rules
        for rule_name in self.rules.keys():
            if rule_name == "CLEAR RISK FLAGS":
                continue
            
            print(f"→ Rule: {rule_name}")
            
            if self.execute_rule(rule_name, repository, dry_run):
                executed += 1
            else:
                failed += 1
            
            time.sleep(0.1)
        
        print(f"\n{'='*60}")
        print(f"SUMMARY {repository.upper()}:")
        print(f"  ✓ Rules executed: {executed}")
        print(f"  ✗ Rules failed: {failed}")
        print(f"{'='*60}")
        
        return executed, failed
    
    def execute_federated_week_simulation(self, week_number, dry_run=False):
        """Execute simulation for one week across all repositories"""
        print(f"\n{'#'*70}")
        print(f"📅 WEEK {week_number} SIMULATION - TEMPORAL MODEL")
        print(f"{'#'*70}")
        
        total_executed = 0
        total_failed = 0
        
        for repository in self.repositories:
            executed, failed = self.execute_all_rules_for_repository(
                repository, week_number, dry_run
            )
            total_executed += executed
            total_failed += failed
        
        print(f"\n{'#'*70}")
        print(f"FINAL SUMMARY WEEK {week_number}:")
        print(f"  ✓ Total rules executed: {total_executed}")
        print(f"  ✗ Total rules failed: {total_failed}")
        print(f"  ↻ Actors processed: {len(self.repositories)}")
        print(f"{'#'*70}\n")
        
        return total_executed, total_failed
    
    def query_week_summary(self, week_number):
        """Query summary metrics for a specific week across all actors"""
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?actorName 
                   (SUM(?totalCost) as ?chainCost)
                   (COUNT(?bullwhip) as ?bullwhipCount)
                   (COUNT(?stockout) as ?stockoutCount)
                   (AVG(?coverage) as ?avgCoverage)
            WHERE {{
                ?actor a bg:Actor ;
                       rdfs:label ?actorName ;
                       bg:hasMetrics ?metrics .
                
                ?metrics bg:forWeek bg:Week_{week_number} .
                
                OPTIONAL {{ ?actor bg:totalCost ?totalCost }}
                OPTIONAL {{ ?metrics bg:hasBullwhipRisk ?bullwhip }}
                OPTIONAL {{ ?metrics bg:hasStockoutRisk ?stockout }}
                OPTIONAL {{ ?metrics bg:inventoryCoverage ?coverage }}
            }}
            GROUP BY ?actorName
        """
        
        endpoint = f"{self.base_url}/repositories/{self.repositories[0]}"
        headers = {"Accept": "application/sparql-results+json"}
        
        try:
            response = self.session.post(
                endpoint, 
                data={"query": query}, 
                headers=headers, 
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n📊 WEEK {week_number} SUMMARY:")
                print("="*60)
                for binding in data["results"]["bindings"]:
                    actor = binding.get('actorName', {}).get('value', 'Unknown')
                    cost = float(binding.get('chainCost', {}).get('value', 0))
                    bullwhip = int(binding.get('bullwhipCount', {}).get('value', 0))
                    stockout = int(binding.get('stockoutCount', {}).get('value', 0))
                    coverage = float(binding.get('avgCoverage', {}).get('value', 0))
                    
                    print(f"  {actor}:")
                    print(f"    Cost: ${cost:.2f}")
                    print(f"    Bullwhip risks: {bullwhip}")
                    print(f"    Stockout risks: {stockout}")
                    print(f"    Avg coverage: {coverage:.1f} weeks")
                print("="*60)
        except Exception as e:
            print(f"⚠️  Could not query summary: {e}")


def main():
    """Main execution function"""
    print("🎯 BEER GAME FEDERATED KG - TEMPORAL VERSION (UPDATED)")
    print("=" * 70)
    print("Features:")
    print("  • ActorMetrics snapshots per week")
    print("  • bg:forWeek linking to bg:Week instances")
    print("  • bg:belongsTo for entity ownership")
    print("  • Integer quantities for discrete units")
    print("  • arrivalWeek as bg:Week IRI")
    print("  • SHACL compliant data types")
    print("=" * 70 + "\n")
    
    executor = TemporalBeerGameRuleExecutor()
    
    # Test with dry run first
    print("🔧 TESTING WITH DRY RUN (Week 1)")
    print("-" * 70)
    executor.execute_federated_week_simulation(1, dry_run=True)
    
    print("\n" + "="*70)
    print("IF DRY RUN LOOKS GOOD, EXECUTE WITH dry_run=False")
    print("="*70 + "\n")
    
    response = input("Proceed with real execution? (y/n): ").lower().strip()
    
    if response == 'y':
        print("\n🚀 STARTING REAL EXECUTION")
        print("-" * 70)
        
        num_weeks = int(input("How many weeks to simulate? (1-100): ") or "4")
        
        for week in range(1, num_weeks + 1):
            print(f"\n{'#'*70}")
            print(f"📅 WEEK {week} OF {num_weeks}")
            print(f"{'#'*70}")
            
            executed, failed = executor.execute_federated_week_simulation(
                week, dry_run=False
            )
            
            executor.query_week_summary(week)
            
            if week < num_weeks:
                print(f"\n⏳ Advancing to week {week + 1}...")
                time.sleep(1)
        
        print(f"\n{'='*70}")
        print("✅ SIMULATION COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
    else:
        print("\nExecution cancelled.")


if __name__ == "__main__":
    main()