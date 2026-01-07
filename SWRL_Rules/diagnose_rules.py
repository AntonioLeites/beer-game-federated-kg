"""
Diagnostic script to understand why rules are not producing results
Run this to see what data exists and what's missing
"""

import requests

BASE_URL = "http://localhost:7200"
REPO = "BG_Retailer"

def run_query(query, title):
    """Execute a query and print results"""
    print(f"\n{'='*70}")
    print(f"🔍 {title}")
    print(f"{'='*70}")
    
    endpoint = f"{BASE_URL}/repositories/{REPO}"
    
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
                print(f"✓ Found {len(bindings)} results:")
                for i, b in enumerate(bindings, 1):
                    print(f"  {i}. ", end="")
                    for key, value in b.items():
                        print(f"{key}={value['value']} ", end="")
                    print()
            else:
                print("✗ No results found")
        else:
            print(f"✗ Query failed: {response.status_code}")
            print(f"   {response.text[:200]}")
    
    except Exception as e:
        print(f"✗ Error: {e}")


# Test 1: Check Week entities
run_query("""
PREFIX bg: <http://beergame.org/ontology#>
SELECT ?week ?num WHERE {
    ?week a bg:Week ;
          bg:weekNumber ?num .
}
ORDER BY ?num
""", "TEST 1: Week entities")


# Test 2: Check ActorMetrics
run_query("""
PREFIX bg: <http://beergame.org/ontology#>
SELECT ?metrics ?week ?actor ?demandRate WHERE {
    ?metrics a bg:ActorMetrics ;
             bg:forWeek ?week ;
             bg:belongsTo ?actor ;
             bg:demandRate ?demandRate .
}
""", "TEST 2: ActorMetrics existence")


# Test 3: Check Inventory
run_query("""
PREFIX bg: <http://beergame.org/ontology#>
SELECT ?inv ?week ?actor ?stock WHERE {
    ?inv a bg:Inventory ;
         bg:forWeek ?week ;
         bg:belongsTo ?actor ;
         bg:currentInventory ?stock .
}
""", "TEST 3: Inventory existence")


# Test 4: Check if INVENTORY COVERAGE rule can match
run_query("""
PREFIX bg: <http://beergame.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?metrics ?inv ?rate ?stock WHERE {
    ?week a bg:Week .
    
    ?metrics a bg:ActorMetrics ;
            bg:forWeek ?week ;
            bg:belongsTo ?actor ;
            bg:demandRate ?rate .
    
    ?inv a bg:Inventory ;
        bg:forWeek ?week ;
        bg:belongsTo ?actor ;
        bg:currentInventory ?stock .
    
    FILTER(?rate > 0)
}
""", "TEST 4: Data needed for INVENTORY COVERAGE rule")


# Test 5: Check if ORDER-UP-TO rule can match
run_query("""
PREFIX bg: <http://beergame.org/ontology#>

SELECT ?metrics ?actor ?rate ?leadTime ?reviewPeriod ?stock WHERE {
    ?week a bg:Week .
    
    ?metrics a bg:ActorMetrics ;
            bg:forWeek ?week ;
            bg:belongsTo ?actor ;
            bg:demandRate ?rate .
    
    ?actor a bg:Actor ;
           bg:shippingDelay ?leadTime ;
           bg:orderDelay ?reviewPeriod .

    ?inv a bg:Inventory ;
        bg:forWeek ?week ;
        bg:belongsTo ?actor ;
        bg:currentInventory ?stock .
}
""", "TEST 5: Data needed for ORDER-UP-TO POLICY rule")


# Test 6: Check inventoryCoverage property
run_query("""
PREFIX bg: <http://beergame.org/ontology#>
SELECT ?metrics ?coverage WHERE {
    ?metrics a bg:ActorMetrics ;
             bg:inventoryCoverage ?coverage .
}
""", "TEST 6: Check if inventoryCoverage exists anywhere")


# Test 7: Check suggestedOrderQuantity property
run_query("""
PREFIX bg: <http://beergame.org/ontology#>
SELECT ?metrics ?suggested WHERE {
    ?metrics a bg:ActorMetrics ;
             bg:suggestedOrderQuantity ?suggested .
}
""", "TEST 7: Check if suggestedOrderQuantity exists anywhere")


print("\n" + "="*70)
print("🎯 DIAGNOSTIC COMPLETE")
print("="*70)
print("\nInterpretation:")
print("  - If TEST 4 returns 0 results → Rule cannot match (missing data)")
print("  - If TEST 4 returns results but TEST 6 is empty → Rule executed but didn't insert")
print("  - If TEST 6 has results → Rule worked!")
print("="*70)
