"""
Test Script for Beer Game Rules v2
Execute this on your local machine where GraphDB is running

Steps:
1. Ensure GraphDB is running on http://localhost:7200
2. Ensure initial TTL files are loaded in repositories
3. Run: python test_rules_local.py
"""

import sys
import requests

# Import the rule executor
from temporal_beer_game_rules_v2 import TemporalBeerGameRuleExecutor


def check_graphdb_connection():
    """Test 1: Verify GraphDB is accessible"""
    print("\n1. Testing connection to GraphDB...")
    try:
        response = requests.get("http://localhost:7200/rest/repositories", timeout=5)
        if response.status_code == 200:
            print("   ✓ GraphDB is accessible")
            return True
        else:
            print(f"   ✗ GraphDB returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Cannot connect to GraphDB: {e}")
        print("   → Make sure GraphDB is running on http://localhost:7200")
        return False


def check_repositories(executor):
    """Test 2: Verify repositories exist"""
    print("\n2. Checking repositories...")
    all_exist = True
    for name, repo_id in executor.repositories.items():
        try:
            response = requests.get(
                f"http://localhost:7200/repositories/{repo_id}/size",
                timeout=5
            )
            if response.status_code == 200:
                size = response.text
                print(f"   ✓ {repo_id} exists ({size} statements)")
            else:
                print(f"   ✗ {repo_id} not found")
                all_exist = False
        except Exception as e:
            print(f"   ✗ Error checking {repo_id}: {e}")
            all_exist = False
    return all_exist


def check_initial_data():
    """Test 3: Verify initial TTL data is loaded"""
    print("\n3. Checking initial data (Week_1, Inventory, ActorMetrics)...")
    
    query = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        SELECT ?type (COUNT(?entity) as ?count)
        WHERE {
            {
                ?entity a bg:Week .
                BIND("Week" as ?type)
            } UNION {
                ?entity a bg:Inventory ;
                        bg:forWeek bg:Week_1 .
                BIND("Inventory_Week1" as ?type)
            } UNION {
                ?entity a bg:ActorMetrics ;
                        bg:forWeek bg:Week_1 .
                BIND("ActorMetrics_Week1" as ?type)
            } UNION {
                ?entity a bg:Actor .
                BIND("Actor" as ?type)
            }
        }
        GROUP BY ?type
        ORDER BY ?type
    """
    
    endpoint = "http://localhost:7200/repositories/BG_Retailer"
    
    try:
        response = requests.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            bindings = result.get("results", {}).get("bindings", [])
            
            has_data = False
            for b in bindings:
                entity_type = b["type"]["value"]
                count = int(b["count"]["value"])
                print(f"   ✓ {entity_type}: {count}")
                if count > 0:
                    has_data = True
            
            if not has_data:
                print("   ✗ No initial data found!")
                print("   → Load the TTL files: beer_game_retailer_kg.ttl, etc.")
                return False
            
            return True
        else:
            print(f"   ✗ Query failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_rule_execution(executor, rule_name, repository="BG_Retailer"):
    """Test executing a single rule"""
    print(f"\n📝 Testing rule: {rule_name}")
    print("-" * 70)
    
    success = executor.execute_rule(rule_name, repository, dry_run=False)
    
    if success:
        print(f"   ✓ Rule executed successfully")
        return True
    else:
        print(f"   ✗ Rule execution failed")
        return False


def verify_rule_effects(rule_name):
    """Verify that a rule had the expected effect"""
    print(f"\n🔍 Verifying effects of: {rule_name}")
    
    # Define verification queries for each rule
    verification_queries = {
        "INVENTORY COVERAGE CALCULATION": """
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?metrics ?coverage
            WHERE {
                ?metrics a bg:ActorMetrics ;
                         bg:forWeek bg:Week_1 ;
                         bg:inventoryCoverage ?coverage .
            }
        """,
        
        "DEMAND RATE SMOOTHING": """
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?metrics ?demandRate
            WHERE {
                ?metrics a bg:ActorMetrics ;
                         bg:forWeek bg:Week_1 ;
                         bg:demandRate ?demandRate .
            }
        """,
        
        "ORDER-UP-TO POLICY": """
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?metrics ?suggested
            WHERE {
                ?metrics a bg:ActorMetrics ;
                         bg:forWeek bg:Week_1 ;
                         bg:suggestedOrderQuantity ?suggested .
            }
        """
    }
    
    if rule_name not in verification_queries:
        print(f"   ⚠️  No verification query defined for this rule")
        return True
    
    query = verification_queries[rule_name]
    endpoint = "http://localhost:7200/repositories/BG_Retailer"
    
    try:
        response = requests.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            bindings = result.get("results", {}).get("bindings", [])
            
            if bindings:
                print(f"   ✓ Rule produced results:")
                for b in bindings:
                    for key, value in b.items():
                        print(f"      {key} = {value['value']}")
                return True
            else:
                print(f"   ✗ Rule did not produce expected results")
                return False
        else:
            print(f"   ✗ Verification query failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error verifying: {e}")
        return False


def main():
    """Main test suite"""
    print("="*70)
    print("🧪 BEER GAME RULES V2 - TEST SUITE")
    print("="*70)
    
    # Create executor
    executor = TemporalBeerGameRuleExecutor()
    
    # Pre-flight checks
    if not check_graphdb_connection():
        print("\n❌ Cannot proceed without GraphDB")
        return
    
    if not check_repositories(executor):
        print("\n❌ Not all repositories are available")
        return
    
    if not check_initial_data():
        print("\n❌ Initial data not loaded")
        return
    
    print("\n" + "="*70)
    print("✅ PRE-FLIGHT CHECKS PASSED")
    print("="*70)
    
    # Offer testing mode options
    print("\n" + "="*70)
    print("📋 SELECT TEST MODE")
    print("="*70)
    print("1. Individual rule testing (safe - read only)")
    print("2. Week simulation with DRY RUN first")
    print("3. Full week simulation (modifies data)")
    print("="*70)
    
    mode = input("\nSelect mode (1-3, default=1): ").strip() or "1"
    
    if mode == "1":
        # MODO 1: Test individual rules
        test_individual_rules(executor)
        
    elif mode == "2" or mode == "3":
        # MODO 2 o 3: Week simulation
        test_week_simulation(executor, dry_run=(mode == "2"))
    
    else:
        print("\nInvalid option")
        return
    
    print("\n" + "="*70)
    print("✅ TEST SUITE COMPLETE")
    print("="*70)


def test_individual_rules(executor):
    """Test individual rules one by one"""
    print("\n" + "="*70)
    print("📋 TESTING INDIVIDUAL RULES")
    print("="*70)
    
    # Category 2: Metrics (safe, no side effects on documents)
    safe_rules = [
        "INVENTORY COVERAGE CALCULATION",
        "DEMAND RATE SMOOTHING",
        "ORDER-UP-TO POLICY"
    ]
    
    for rule_name in safe_rules:
        if test_rule_execution(executor, rule_name):
            verify_rule_effects(rule_name)
        
        print()  # Blank line between tests
    
    # Ask before testing rules that create/modify documents
    print("\n" + "="*70)
    print("⚠️  WARNING: Next tests will modify graph data")
    print("Rules that CREATE or UPDATE entities:")
    print("  - UPDATE INVENTORY")
    print("  - CREATE ORDERS FROM SUGGESTED")
    print("  - CREATE SHIPMENTS FROM ORDERS")
    print("="*70)
    
    response = input("\nProceed with data-modifying tests? (y/n): ").lower().strip()
    
    if response == 'y':
        modifying_rules = [
            "UPDATE INVENTORY",
            "STOCKOUT RISK DETECTION",
            "BULLWHIP DETECTION",
            "TOTAL COST CALCULATION"
        ]
        
        for rule_name in modifying_rules:
            test_rule_execution(executor, rule_name)
            print()
    else:
        print("\nSkipping data-modifying tests")


def test_week_simulation(executor, dry_run=True):
    """Test full week simulation with all rules in order"""
    print("\n" + "="*70)
    print("📅 WEEK SIMULATION TEST")
    print("="*70)
    
    if dry_run:
        print("\n🔧 TESTING WITH DRY RUN (Week 1)")
        print("-" * 70)
        executor.execute_week_rules(1, dry_run=True)
        
        print("\n" + "="*70)
        print("IF DRY RUN LOOKS GOOD, EXECUTE WITH REAL DATA")
        print("="*70)
        
        response = input("\nProceed with real execution? (y/n): ").lower().strip()
        
        if response != 'y':
            print("\nExecution cancelled")
            return
    
    # Real execution
    print("\n🚀 STARTING REAL EXECUTION")
    print("-" * 70)
    
    num_weeks = int(input("How many weeks to simulate? (1-10, default=1): ").strip() or "1")
    
    repos = list(executor.repositories.values())
    
    for week in range(1, num_weeks + 1):
        print(f"\n{'#'*70}")
        print(f"📅 WEEK {week} OF {num_weeks}")
        print(f"{'#'*70}")
        
        executed, failed = executor.execute_week_rules(week, repos, dry_run=False)
        
        # Show summary
        query_week_summary(week)
        
        if week < num_weeks:
            print(f"\n⏳ Advancing to week {week + 1}...")
            import time
            time.sleep(1)
    
    print(f"\n{'='*70}")
    print("✅ SIMULATION COMPLETED SUCCESSFULLY")
    print(f"{'='*70}")


def query_week_summary(week):
    """Query and display week summary"""
    print(f"\n📊 WEEK {week} SUMMARY:")
    print("="*60)
    
    query = f"""
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?actorName ?inv ?backlog ?coverage ?suggested ?cost
        WHERE {{
            ?actor a bg:Actor ;
                   rdfs:label ?actorName .
            
            # Get inventory
            OPTIONAL {{
                ?invEntity a bg:Inventory ;
                           bg:forWeek bg:Week_{week} ;
                           bg:belongsTo ?actor ;
                           bg:currentInventory ?inv ;
                           bg:backlog ?backlog .
            }}
            
            # Get metrics
            OPTIONAL {{
                ?actor bg:hasMetrics ?metrics .
                ?metrics bg:forWeek bg:Week_{week} ;
                         bg:inventoryCoverage ?coverage ;
                         bg:suggestedOrderQuantity ?suggested .
            }}
            
            # Get total cost
            OPTIONAL {{
                ?actor bg:totalCost ?cost .
            }}
        }}
        ORDER BY ?actorName
    """
    
    endpoint = "http://localhost:7200/repositories/BG_Retailer"
    
    try:
        response = requests.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            bindings = result.get("results", {}).get("bindings", [])
            
            for b in bindings:
                actor = b.get("actorName", {}).get("value", "Unknown")
                inv = b.get("inv", {}).get("value", "N/A")
                backlog = b.get("backlog", {}).get("value", "N/A")
                coverage = b.get("coverage", {}).get("value", "N/A")
                suggested = b.get("suggested", {}).get("value", "N/A")
                cost = b.get("cost", {}).get("value", "N/A")
                
                print(f"  {actor}:")
                print(f"    Inventory: {inv}")
                print(f"    Backlog: {backlog}")
                print(f"    Coverage: {coverage} weeks")
                print(f"    Suggested order: {suggested}")
                print(f"    Total cost: ${cost}")
        else:
            print(f"   ✗ Query failed: {response.status_code}")
    
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("="*60)


if __name__ == "__main__":
    main()
