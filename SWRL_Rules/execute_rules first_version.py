"""
Beer Game Federated KG - Fixed Rule Executor
Corrected version with proper SPARQL prefixes
"""

import requests
import time
import re

class BeerGameRuleExecutor:
    def __init__(self, base_url="http://localhost:7200"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Define all rules with proper prefixes
        self.rules = self._define_rules()
        
        # Repositories to process
        self.repositories = ["BG_Retailer", "BG_Whosaler", "BG_Distributor", "BG_Factory"]
    
    def _define_rules(self):
        """Define all SPARQL rules with proper prefixes"""
        return {
            "BULLWHIP DETECTION": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:hasBullwhipRisk "true"^^xsd:boolean .
                  ?order bg:orderAmplification ?ratio .
                }
                WHERE {
                  ?order a bg:Order ;
                         bg:orderQuantity ?qty ;
                         bg:weekNumber ?week ;
                         bg:placedBy ?actor .
                  
                  ?demand a bg:CustomerDemand ;
                          bg:weekNumber ?week ;
                          bg:actualDemand ?realDemand .
                  
                  FILTER(?realDemand > 0)
                  BIND(?qty / ?realDemand AS ?ratio)
                  FILTER(?ratio > 1.3)
                }
            """,
            
            "ORDER CAPPING (GUARDRAIL)": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:maxOrderQuantity ?maxOrder .
                }
                WHERE {
                  ?actor a bg:Actor ;
                         bg:hasBullwhipRisk "true"^^xsd:boolean .
                  
                  ?demand a bg:CustomerDemand ;
                          bg:actualDemand ?realDemand .
                  
                  BIND(?realDemand * 1.2 AS ?maxOrder)
                }
            """,
            
            "STOCKOUT RISK DETECTION": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:hasStockoutRisk "true"^^xsd:boolean .
                }
                WHERE {
                  ?actor a bg:Actor ;
                         bg:shippingDelay ?leadTime .
                  
                  ?inv a bg:Inventory ;
                       bg:currentInventory ?stock .
                  
                  ?actor bg:demandRate ?rate .
                  
                  FILTER(?rate > 0)
                  BIND(?stock / ?rate AS ?coverage)
                  FILTER(?coverage < ?leadTime)
                }
            """,
            
            "INVENTORY COVERAGE CALCULATION": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:inventoryCoverage ?coverage .
                }
                WHERE {
                  ?actor a bg:Actor .
                  
                  ?inv a bg:Inventory ;
                       bg:currentInventory ?stock .
                  
                  ?actor bg:demandRate ?rate .
                  
                  FILTER(?rate > 0)
                  BIND(?stock / ?rate AS ?coverage)
                }
            """,
            
            "DYNAMIC BUDGET INCREASE (CRITICAL SITUATION)": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:budgetConstraint ?newBudget .
                }
                WHERE {
                  ?actor a bg:Actor ;
                         bg:hasStockoutRisk "true"^^xsd:boolean ;
                         bg:inventoryCoverage ?coverage ;
                         bg:budgetConstraint ?normalBudget .
                  
                  FILTER(?coverage < 2.0)
                  BIND(?normalBudget * 1.5 AS ?newBudget)
                }
            """,
            
            "DYNAMIC BUDGET DECREASE (OVERSTOCK)": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:budgetConstraint ?newBudget .
                }
                WHERE {
                  ?actor a bg:Actor ;
                         bg:demandRate ?rate ;
                         bg:budgetConstraint ?normalBudget .
                  
                  ?inv a bg:Inventory ;
                       bg:currentInventory ?stock .
                  
                  BIND(?rate * 4.0 AS ?optimalStock)
                  BIND(?optimalStock * 1.5 AS ?threshold)
                  
                  FILTER(?stock > ?threshold)
                  BIND(?normalBudget * 0.5 AS ?newBudget)
                }
            """,
            
            "TOTAL COST CALCULATION": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:totalCost ?totalCost .
                }
                WHERE {
                  ?actor a bg:Actor .
                  
                  ?inv a bg:Inventory ;
                       bg:currentInventory ?stock ;
                       bg:backlog ?backlog ;
                       bg:holdingCost ?hCost ;
                       bg:backlogCost ?bCost .
                  
                  BIND((?stock * ?hCost) + (?backlog * ?bCost) AS ?totalCost)
                }
            """,
            
            "SHIPMENT ARRIVAL CALCULATION": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?shipment bg:arrivalWeek ?arrivalWeek .
                }
                WHERE {
                  ?shipment a bg:Shipment ;
                            bg:weekNumber ?currentWeek ;
                            bg:shippedFrom ?actor .
                  
                  ?actor bg:shippingDelay ?delay .
                  
                  BIND(?currentWeek + ?delay AS ?arrivalWeek)
                }
            """,
            
            "ORDER-UP-TO POLICY (SUGGESTED ORDER)": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:suggestedOrderQuantity ?finalOrder .
                }
                WHERE {
                  ?actor a bg:Actor ;
                         bg:demandRate ?rate ;
                         bg:shippingDelay ?leadTime ;
                         bg:orderDelay ?reviewPeriod .
                  
                  ?inv a bg:Inventory ;
                       bg:currentInventory ?currentStock .
                  
                  BIND(?leadTime + ?reviewPeriod AS ?totalDelay)
                  BIND(?rate * ?totalDelay AS ?targetStock)
                  
                  BIND(?targetStock - ?currentStock AS ?orderQty)
                  BIND(IF(?orderQty > 0, ?orderQty, 0) AS ?finalOrder)
                }
            """,
            
            "DEMAND RATE SMOOTHING (EXPONENTIAL SMOOTHING)": """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                INSERT {
                  ?actor bg:demandRate ?smoothedRate .
                }
                WHERE {
                  ?actor a bg:Actor ;
                         bg:demandRate ?oldRate .
                  
                  ?demand a bg:CustomerDemand ;
                          bg:actualDemand ?currentDemand .
                  
                  BIND((?currentDemand * 0.3) + (?oldRate * 0.7) AS ?smoothedRate)
                  
                  BIND(ABS(?smoothedRate - ?oldRate) / ?oldRate AS ?changeRatio)
                  FILTER(?changeRatio > 0.05)
                }
            """
        }
    
    def execute_rule(self, rule_name, repository, dry_run=False):
        """Execute a specific rule on a repository"""
        if rule_name not in self.rules:
            print(f"✗ Rule not found: {rule_name}")
            return False
        
        rule_sparql = self.rules[rule_name]
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        
        if dry_run:
            print(f"   [DRY RUN] Would execute rule '{rule_name}' on {repository}")
            print(f"   SPARQL snippet: {rule_sparql[:200]}...")
            return True
        
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=rule_sparql, headers=headers, timeout=30)
            
            if response.status_code == 204:
                print(f"   ✓ Rule '{rule_name}' executed on {repository}")
                return True
            else:
                print(f"   ✗ Error executing '{rule_name}' on {repository}: {response.status_code} - {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"   ✗ Exception executing '{rule_name}': {e}")
            return False
    
    def execute_all_rules_for_repository(self, repository, week_number, dry_run=False):
        """Execute all rules for a specific repository"""
        print(f"\n{'='*60}")
        print(f"PROCESSING {repository.upper()} - WEEK {week_number}")
        print(f"{'='*60}")
        
        executed = 0
        failed = 0
        
        for rule_name in self.rules.keys():
            print(f"→ Rule: {rule_name}")
            
            if self.execute_rule(rule_name, repository, dry_run):
                executed += 1
            else:
                failed += 1
            
            time.sleep(0.1)  # Small pause
        
        print(f"\n{'='*60}")
        print(f"SUMMARY {repository.upper()}:")
        print(f"  ✓ Rules executed: {executed}")
        print(f"  ✗ Rules failed: {failed}")
        print(f"{'='*60}")
        
        return executed, failed
    
    def execute_federated_week_simulation(self, week_number, dry_run=False):
        """Execute simulation for one week across all repositories"""
        print(f"\n{'#'*70}")
        print(f"WEEK {week_number} SIMULATION - EXECUTING RULES ACROSS SUPPLY CHAIN")
        print(f"{'#'*70}")
        
        total_executed = 0
        total_failed = 0
        
        for repository in self.repositories:
            executed, failed = self.execute_all_rules_for_repository(repository, week_number, dry_run)
            total_executed += executed
            total_failed += failed
        
        # Run federated analysis
        if not dry_run:
            self.run_federated_analysis(week_number)
        
        print(f"\n{'#'*70}")
        print(f"FINAL SUMMARY WEEK {week_number}:")
        print(f"  ✓ Total rules executed: {total_executed}")
        print(f"  ✗ Total rules failed: {total_failed}")
        print(f"  ↻ Actors processed: {len(self.repositories)}")
        print(f"{'#'*70}\n")
        
        return total_executed, total_failed
    
    def run_federated_analysis(self, week_number):
        """Run federated analysis across all repositories"""
        try:
            query = """
                PREFIX bg: <http://beergame.org/ontology#>
                
                SELECT 
                    (COUNT(DISTINCT ?actor) as ?totalActors)
                    (COUNT(?bullwhip) as ?bullwhipRiskCount)
                    (COUNT(?stockout) as ?stockoutRiskCount)
                    (SUM(COALESCE(?totalCost, 0)) as ?chainTotalCost)
                    (AVG(COALESCE(?inventoryCoverage, 0)) as ?avgInventoryCoverage)
                WHERE {
                  SERVICE <http://localhost:7200/repositories/BG_Supply_Chain> {
                    ?actor a bg:Actor .
                    OPTIONAL { ?actor bg:hasBullwhipRisk ?bullwhip }
                    OPTIONAL { ?actor bg:hasStockoutRisk ?stockout }
                    OPTIONAL { ?actor bg:totalCost ?totalCost }
                    OPTIONAL { ?actor bg:inventoryCoverage ?inventoryCoverage }
                  }
                }
            """
            
            endpoint = f"{self.base_url}/repositories/BG_Supply_Chain"
            headers = {"Accept": "application/sparql-results+json"}
            
            response = self.session.post(endpoint, data={"query": query}, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data["results"]["bindings"]:
                    binding = data["results"]["bindings"][0]
                    
                    print(f"\n{'='*60}")
                    print(f"FEDERATED GLOBAL ANALYSIS")
                    print(f"{'='*60}")
                    
                    print(f"\n📊 GLOBAL SUPPLY CHAIN METRICS (Week {week_number}):")
                    print(f"   • Total actors: {binding.get('totalActors', {}).get('value', 'N/A')}")
                    print(f"   • Bullwhip risks: {binding.get('bullwhipRiskCount', {}).get('value', 'N/A')} actors")
                    print(f"   • Stockout risks: {binding.get('stockoutRiskCount', {}).get('value', 'N/A')} actors")
                    print(f"   • Total chain cost: ${float(binding.get('chainTotalCost', {}).get('value', 0)):.2f}")
                    print(f"   • Average inventory coverage: {float(binding.get('avgInventoryCoverage', {}).get('value', 0)):.1f} weeks")
            
        except Exception as e:
            print(f"⚠️  Error in federated analysis: {e}")

def main():
    """Main execution function"""
    print("🎯 BEER GAME FEDERATED KG - FIXED VERSION")
    print("==========================================\n")
    
    executor = FixedBeerGameRuleExecutor()
    
    # Test first with dry run
    print("🔧 TESTING WITH DRY RUN (First week only)")
    print("-" * 50)
    executor.execute_federated_week_simulation(1, dry_run=True)
    
    print("\n" + "="*70)
    print("IF DRY RUN LOOKS GOOD, EXECUTE WITH dry_run=False")
    print("="*70 + "\n")
    
    # Ask user if they want to proceed
    response = input("Proceed with real execution? (y/n): ").lower().strip()
    
    if response == 'y':
        print("\n🚀 STARTING REAL EXECUTION")
        print("-" * 50)
        
        for week in range(1, 5):
            print(f"\n{'#'*70}")
            print(f"📊 WEEK {week} OF 4 - SIMULATING SUPPLY CHAIN")
            print(f"{'#'*70}")
            
            executed, failed = executor.execute_federated_week_simulation(week, dry_run=False)
            
            print(f"\n📈 WEEK {week} SUMMARY:")
            print(f"   • Rules executed: {executed}")
            print(f"   • Rules failed: {failed}")
            
            if executed + failed > 0:
                success_rate = (executed / (executed + failed)) * 100
                print(f"   • Success rate: {success_rate:.1f}%")
            
            if week < 4:
                print(f"\n⏳ Advancing to week {week + 1}...")
                time.sleep(2)
        
        print(f"\n{'='*70}")
        print("✅ SIMULATION COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
    else:
        print("\nExecution cancelled.")

if __name__ == "__main__":
    main()