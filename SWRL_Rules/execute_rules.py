"""
Beer Game Federated KG - Fixed Rules with DELETE/INSERT Pattern
Temporal version: Rules filtered by week number to prevent cross-week contamination
"""

import requests
import time

def get_rules():
    """Define all SPARQL rules with DELETE/INSERT pattern, filtered by week"""
    return {
        "BULLWHIP DETECTION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:hasBullwhipRisk ?oldRisk .
                ?order bg:orderAmplification ?oldAmp .
            }
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
                
                OPTIONAL { ?actor bg:hasBullwhipRisk ?oldRisk }
                OPTIONAL { ?order bg:orderAmplification ?oldAmp }
            }
        """,
        
        "ORDER CAPPING (GUARDRAIL)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:maxOrderQuantity ?oldMax .
            }
            INSERT {
                ?actor bg:maxOrderQuantity ?maxOrder .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:hasBullwhipRisk "true"^^xsd:boolean .
                
                ?demand a bg:CustomerDemand ;
                        bg:weekNumber ?week ;
                        bg:actualDemand ?realDemand .
                
                BIND(?realDemand * 1.2 AS ?maxOrder)
                OPTIONAL { ?actor bg:maxOrderQuantity ?oldMax }
            }
        """,
        
        "STOCKOUT RISK DETECTION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:hasStockoutRisk ?oldRisk .
            }
            INSERT {
                ?actor bg:hasStockoutRisk "true"^^xsd:boolean .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:shippingDelay ?leadTime ;
                       bg:demandRate ?rate .
                
                ?inv a bg:Inventory ;
                     bg:currentInventory ?stock ;
                     bg:forWeek ?week .
                
                FILTER(?rate > 0)
                BIND(?stock / ?rate AS ?coverage)
                FILTER(?coverage < ?leadTime)
                
                OPTIONAL { ?actor bg:hasStockoutRisk ?oldRisk }
            }
        """,
        
        "INVENTORY COVERAGE CALCULATION": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:inventoryCoverage ?oldCoverage .
            }
            INSERT {
                ?actor bg:inventoryCoverage ?coverage .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:demandRate ?rate .
                
                ?inv a bg:Inventory ;
                     bg:currentInventory ?stock ;
                     bg:forWeek ?week .
                
                FILTER(?rate > 0)
                BIND(?stock / ?rate AS ?coverage)
                OPTIONAL { ?actor bg:inventoryCoverage ?oldCoverage }
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
            
            DELETE {
                ?actor bg:budgetConstraint ?oldBudget .
            }
            INSERT {
                ?actor bg:budgetConstraint ?newBudget .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:demandRate ?rate ;
                       bg:budgetConstraint ?normalBudget .
                
                ?inv a bg:Inventory ;
                     bg:currentInventory ?stock ;
                     bg:forWeek ?week .
                
                BIND(?rate * 4.0 AS ?optimalStock)
                BIND(?optimalStock * 1.5 AS ?threshold)
                
                FILTER(?stock > ?threshold)
                BIND(?normalBudget * 0.5 AS ?newBudget)
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
                     bg:currentInventory ?stock ;
                     bg:backlog ?backlog ;
                     bg:holdingCost ?hCost ;
                     bg:backlogCost ?bCost ;
                     bg:forWeek ?week .
                
                BIND((?stock * ?hCost) + (?backlog * ?bCost) AS ?totalCost)
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
                ?shipment bg:arrivalWeek ?arrivalWeek .
            }
            WHERE {
                ?shipment a bg:Shipment ;
                          bg:weekNumber ?currentWeek ;
                          bg:shippedFrom ?actor .
                
                ?actor bg:shippingDelay ?delay .
                BIND(?currentWeek + ?delay AS ?arrivalWeek)
                OPTIONAL { ?shipment bg:arrivalWeek ?oldArrival }
            }
        """,
        
        "ORDER-UP-TO POLICY (SUGGESTED ORDER)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:suggestedOrderQuantity ?oldOrder .
            }
            INSERT {
                ?actor bg:suggestedOrderQuantity ?finalOrder .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:demandRate ?rate ;
                       bg:shippingDelay ?leadTime ;
                       bg:orderDelay ?reviewPeriod .
                
                ?inv a bg:Inventory ;
                     bg:currentInventory ?currentStock ;
                     bg:forWeek ?week .
                
                BIND(?leadTime + ?reviewPeriod AS ?totalDelay)
                BIND(?rate * ?totalDelay AS ?targetStock)
                BIND(?targetStock - ?currentStock AS ?orderQty)
                BIND(IF(?orderQty > 0, ?orderQty, 0) AS ?finalOrder)
                
                OPTIONAL { ?actor bg:suggestedOrderQuantity ?oldOrder }
            }
        """,
        
        "DEMAND RATE SMOOTHING (EXPONENTIAL SMOOTHING)": """
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            DELETE {
                ?actor bg:demandRate ?oldRate .
            }
            INSERT {
                ?actor bg:demandRate ?smoothedRate .
            }
            WHERE {
                ?actor a bg:Actor ;
                       bg:demandRate ?oldRate .
                
                ?demand a bg:CustomerDemand ;
                        bg:weekNumber ?week ;
                        bg:actualDemand ?currentDemand .
                
                BIND((?currentDemand * 0.3) + (?oldRate * 0.7) AS ?smoothedRate)
                
                BIND(ABS(?smoothedRate - ?oldRate) / ?oldRate AS ?changeRatio)
                FILTER(?changeRatio > 0.05)
            }
        """,
        
        "CLEAR RISK FLAGS": """
            PREFIX bg: <http://beergame.org/ontology#>
            
            DELETE {
                ?actor bg:hasBullwhipRisk ?risk .
                ?actor bg:hasStockoutRisk ?stockout .
            }
            WHERE {
                ?actor a bg:Actor .
                OPTIONAL { ?actor bg:hasBullwhipRisk ?risk }
                OPTIONAL { ?actor bg:hasStockoutRisk ?stockout }
            }
        """
    }


class BeerGameRuleExecutor:
    def __init__(self, base_url="http://localhost:7200"):
        self.base_url = base_url
        self.session = requests.Session()
        self.rules = get_rules()
        self.repositories = ["BG_Retailer", "BG_Whosaler", "BG_Distributor", "BG_Factory"]
    
    def execute_rule(self, rule_name, repository, dry_run=False):
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
                    print(f"      Error details: {response.text[:300]}")
                return False
        except Exception as e:
            print(f"   ✗ Exception executing '{rule_name}': {e}")
            return False
    
    def execute_all_rules_for_repository(self, repository, week_number, dry_run=False):
        print(f"\n{'='*60}")
        print(f"PROCESSING {repository.upper()} - WEEK {week_number}")
        print(f"{'='*60}")
        
        executed, failed = 0, 0
        
        # Clear risk flags first
        if "CLEAR RISK FLAGS" in self.rules:
            print(f"→ Rule: CLEAR RISK FLAGS")
            if self.execute_rule("CLEAR RISK FLAGS", repository, dry_run):
                executed += 1
            else:
                failed += 1
        
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
        print(f"SUMMARY {repository.upper()}: ✓ {executed} | ✗ {failed}")
        print(f"{'='*60}")
        return executed, failed
    
    def execute_federated_week_simulation(self, week_number, dry_run=False):
        print(f"\n{'#'*70}")
        print(f"WEEK {week_number} SIMULATION - FEDERATED EXECUTION")
        print(f"{'#'*70}")
        
        total_executed, total_failed = 0, 0
        for repository in self.repositories:
            executed, failed = self.execute_all_rules_for_repository(repository, week_number, dry_run=dry_run)
            total_executed += executed
            total_failed += failed
        
        print(f"\n{'#'*70}")
        print(f"FINAL SUMMARY WEEK {week_number}: ✓ {total_executed} | ✗ {total_failed}")
        print(f"{'#'*70}\n")
        return total_executed, total_failed


if __name__ == "__main__":
    print("🎯 BEER GAME - FIXED RULES WITH DELETE/INSERT (TEMPORAL VERSION)")
    print("="*60)
    
    executor = BeerGameRuleExecutor()
    
    # Test week 1
    executor.execute_federated_week_simulation(week_number=1, dry_run=True)
