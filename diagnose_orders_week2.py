#!/usr/bin/env python3
"""
Diagnose why CREATE ORDERS doesn't create orders in Week 2
"""

import requests

BASE_URL = "http://localhost:7200"

def query_repo(repo, query_name, query):
    """Execute SPARQL SELECT query"""
    print(f"\n{'='*70}")
    print(f"📊 {query_name} - {repo}")
    print(f"{'='*70}")
    
    endpoint = f"{BASE_URL}/repositories/{repo}"
    
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
                for b in bindings:
                    print(f"  {b}")
            else:
                print("  ✗ No results (query matched nothing)")
            
            return bindings
        else:
            print(f"  ✗ Query failed: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []


print("\n" + "="*70)
print("🔍 DIAGNOSIS: Why CREATE ORDERS fails in Week 2")
print("="*70)

# Test 1: Check if Week_2 exists
test1 = """
    PREFIX bg: <http://beergame.org/ontology#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?week ?weekNum
    WHERE {
        ?week a bg:Week ;
              bg:weekNumber ?weekNum .
        
        FILTER(?weekNum = 2)
    }
"""

# Test 2: Check if ActorMetrics exist for Week 2
test2 = """
    PREFIX bg: <http://beergame.org/ontology#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?actor ?actorName ?suggestedQty
    WHERE {
        ?week a bg:Week ;
              bg:weekNumber "2"^^xsd:integer .
        
        ?actor a bg:Actor ;
               bg:hasMetrics ?metrics ;
               rdfs:label ?actorName .
        
        ?metrics bg:forWeek ?week ;
                 bg:suggestedOrderQuantity ?suggestedQty .
    }
"""

# Test 3: Check if previous orders exist (for topology inference)
test3 = """
    PREFIX bg: <http://beergame.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?actor ?actorName ?upstream ?upstreamName
    WHERE {
        ?actor a bg:Actor ;
               rdfs:label ?actorName .
        
        ?prevOrder a bg:Order ;
                   bg:placedBy ?actor ;
                   bg:receivedBy ?upstream .
        
        ?upstream rdfs:label ?upstreamName .
    }
"""

# Test 4: Simulate the BIND operations
test4 = """
    PREFIX bg: <http://beergame.org/ontology#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?actor ?actorName ?upstreamName ?upstreamShort ?orderURI
    WHERE {
        ?week a bg:Week ;
              bg:weekNumber ?weekNum .
        FILTER(?weekNum = 2)
        
        ?actor a bg:Actor ;
               bg:hasMetrics ?metrics ;
               rdfs:label ?actorName .
        
        ?metrics bg:forWeek ?week ;
                 bg:suggestedOrderQuantity ?suggestedQty .
        
        ?prevOrder a bg:Order ;
                   bg:placedBy ?actor ;
                   bg:receivedBy ?upstream .
        
        ?upstream rdfs:label ?upstreamName .
        
        FILTER(?suggestedQty > 0)
        
        # Simulate the BINDs
        BIND(STRBEFORE(?upstreamName, " ") AS ?upstreamShort)
        
        BIND(IRI(CONCAT(
            STRBEFORE(STR(?actor), "#"),
            "#Order_Week",
            STR(?weekNum),
            "_To",
            ?upstreamShort
        )) AS ?orderURI)
    }
"""

# Test 5: Check if orders already exist for Week 2
test5 = """
    PREFIX bg: <http://beergame.org/ontology#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?order ?placedBy ?week
    WHERE {
        ?week a bg:Week ;
              bg:weekNumber "2"^^xsd:integer .
        
        ?order a bg:Order ;
               bg:forWeek ?week ;
               bg:placedBy ?placedBy .
    }
"""

repos = ["BG_Retailer", "BG_Wholesaler", "BG_Distributor", "BG_Factory"]

for repo in repos:
    query_repo(repo, "Test 1: Week_2 exists?", test1)
    query_repo(repo, "Test 2: ActorMetrics with suggestedQty?", test2)
    query_repo(repo, "Test 3: Previous orders for topology?", test3)
    query_repo(repo, "Test 4: Simulate BIND operations", test4)
    query_repo(repo, "Test 5: Orders already exist?", test5)

print("\n" + "="*70)
print("✅ DIAGNOSIS COMPLETE")
print("="*70)
print("\nLook for:")
print("  - Test 4 should show orderURI being generated")
print("  - Test 5 should be empty (no orders yet)")
print("  - If Test 4 is empty, one of the WHERE conditions is failing")
