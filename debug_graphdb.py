"""
Debug Script: Inspect GraphDB data after Week 2

This script queries the actual data in GraphDB to understand
why the summary query isn't returning results.
"""

import requests
import json

def query_graphdb(repo, query):
    """Execute SPARQL query on repository."""
    endpoint = f"http://localhost:7200/repositories/{repo}"
    response = requests.post(
        endpoint,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

def inspect_retailer_week2():
    """Inspect what's in BG_Retailer for Week 2."""
    print("\n" + "="*70)
    print("🔍 INSPECTING BG_Retailer - Week 2")
    print("="*70)
    
    # Query 1: Check if Week_2 entity exists
    query1 = """
        PREFIX bg: <http://beergame.org/ontology#>
        SELECT * WHERE {
            bg:Week_2 ?p ?o .
        }
    """
    print("\n1. Week_2 entity:")
    result = query_graphdb("BG_Retailer", query1)
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        for b in bindings[:5]:
            print(f"   {b['p']['value']}: {b['o']['value']}")
    
    # Query 2: Check Inventory entities
    query2 = """
        PREFIX bg: <http://beergame.org/ontology#>
        SELECT ?inv ?week ?actor ?stock ?backlog WHERE {
            ?inv a bg:Inventory ;
                 bg:forWeek ?week ;
                 bg:belongsTo ?actor ;
                 bg:currentInventory ?stock ;
                 bg:currentBacklog ?backlog .
        }
        ORDER BY ?week
    """
    print("\n2. Inventory entities:")
    result = query_graphdb("BG_Retailer", query2)
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        for b in bindings:
            print(f"   Week: {b.get('week', {}).get('value', 'N/A')}")
            print(f"   Actor: {b.get('actor', {}).get('value', 'N/A')}")
            print(f"   Stock: {b.get('stock', {}).get('value', 'N/A')}")
            print(f"   Backlog: {b.get('backlog', {}).get('value', 'N/A')}")
            print()
    
    # Query 3: Check ActorMetrics
    query3 = """
        PREFIX bg: <http://beergame.org/ontology#>
        SELECT ?metrics ?week ?actor ?rate ?coverage WHERE {
            ?metrics a bg:ActorMetrics ;
                     bg:forWeek ?week ;
                     bg:belongsTo ?actor ;
                     bg:demandRate ?rate ;
                     bg:inventoryCoverage ?coverage .
        }
        ORDER BY ?week
    """
    print("\n3. ActorMetrics:")
    result = query_graphdb("BG_Retailer", query3)
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        for b in bindings:
            print(f"   Week: {b.get('week', {}).get('value', 'N/A')}")
            print(f"   Actor: {b.get('actor', {}).get('value', 'N/A')}")
            print(f"   Rate: {b.get('rate', {}).get('value', 'N/A')}")
            print(f"   Coverage: {b.get('coverage', {}).get('value', 'N/A')}")
            print()
    
    # Query 4: Test the actual summary query
    query4 = """
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX bg_retailer: <http://beergame.org/retailer#>
        
        SELECT ?inventory ?backlog ?cost ?demandRate ?coverage
        WHERE {
            # Get inventory
            ?inv a bg:Inventory ;
                 bg:forWeek bg:Week_2 ;
                 bg:belongsTo bg_retailer:Retailer_Alpha ;
                 bg:currentInventory ?inventory ;
                 bg:currentBacklog ?backlog .
            
            # Get metrics
            OPTIONAL {
                bg_retailer:Retailer_Alpha bg:hasMetrics ?metrics .
                ?metrics bg:forWeek bg:Week_2 ;
                         bg:demandRate ?demandRate ;
                         bg:inventoryCoverage ?coverage .
            }
            
            # Get total cost
            OPTIONAL {
                bg_retailer:Retailer_Alpha bg:totalCost ?cost .
            }
        }
    """
    print("\n4. Testing summary query (the one that fails):")
    result = query_graphdb("BG_Retailer", query4)
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            print(f"   ✓ Found {len(bindings)} results!")
            for b in bindings:
                print(f"   Inventory: {b.get('inventory', {}).get('value', 'N/A')}")
                print(f"   Backlog: {b.get('backlog', {}).get('value', 'N/A')}")
                print(f"   Coverage: {b.get('coverage', {}).get('value', 'N/A')}")
        else:
            print(f"   ⚠️  No results (this is the problem)")
    
    # Query 5: Let's try WITHOUT specifying Week_2 explicitly
    query5 = """
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX bg_retailer: <http://beergame.org/retailer#>
        
        SELECT ?inv ?week ?inventory ?backlog
        WHERE {
            ?inv a bg:Inventory ;
                 bg:forWeek ?week ;
                 bg:belongsTo bg_retailer:Retailer_Alpha .
            
            OPTIONAL { ?inv bg:currentInventory ?inventory }
            OPTIONAL { ?inv bg:currentBacklog ?backlog }
        }
    """
    print("\n5. Inventory without specifying week:")
    result = query_graphdb("BG_Retailer", query5)
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        print(f"   Found {len(bindings)} inventory entities")
        for b in bindings[:3]:
            print(f"   {b.get('inv', {}).get('value', 'N/A')}")
            print(f"   Week: {b.get('week', {}).get('value', 'N/A')}")
            print(f"   Inventory: {b.get('inventory', {}).get('value', 'N/A')}")
            print()


if __name__ == "__main__":
    inspect_retailer_week2()
    
    print("\n" + "="*70)
    print("💡 DIAGNOSIS:")
    print("="*70)
    print("Compare the actual URIs in the data with what the query expects.")
    print("The issue is likely a mismatch in how Week_2 or the actor is referenced.")
