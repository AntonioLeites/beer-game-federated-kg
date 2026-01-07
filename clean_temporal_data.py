"""
Clean temporal data from all repositories without recreating them
This preserves the initial TTL data (Actor, Inventory_Week1, etc.)
and only removes data created by simulation runs
"""

import requests

BASE_URL = "http://localhost:7200"

REPOSITORIES = {
    "Retailer": "BG_Retailer",
    "Wholesaler": "BG_Wholesaler",
    "Distributor": "BG_Distributor",
    "Factory": "BG_Factory"
}

def execute_update(repo, query, description):
    """Execute SPARQL UPDATE query"""
    endpoint = f"{BASE_URL}/repositories/{repo}/statements"
    headers = {"Content-Type": "application/sparql-update"}
    
    try:
        response = requests.post(endpoint, data=query, headers=headers, timeout=30)
        if response.status_code == 204:
            print(f"   ✓ {description}")
            return True
        else:
            print(f"   ✗ {description} - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ {description} - Error: {e}")
        return False


def clean_repository(repo_name, repo_id):
    """Clean temporal data from a repository"""
    print(f"\n{'='*70}")
    print(f"Cleaning {repo_name} ({repo_id})")
    print(f"{'='*70}")
    
    # 1. Delete ALL ActorMetrics (will be recreated by script with correct naming)
    query1 = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        DELETE {
            ?metrics ?p ?o .
            ?actor bg:hasMetrics ?metrics .
        }
        WHERE {
            ?metrics a bg:ActorMetrics .
            ?metrics ?p ?o .
            OPTIONAL { ?actor bg:hasMetrics ?metrics }
        }
    """
    execute_update(repo_id, query1, "Delete ALL ActorMetrics (will be recreated)")
    
    # 2. Delete ALL Shipments except Week_1
    query2 = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        DELETE {
            ?shipment ?p ?o .
        }
        WHERE {
            ?shipment a bg:Shipment .
            FILTER(!CONTAINS(STR(?shipment), "Week1") && !CONTAINS(STR(?shipment), "Week_1"))
            
            ?shipment ?p ?o .
        }
    """
    execute_update(repo_id, query2, "Delete Shipments (not Week 1)")
    
    # 3. Delete ALL Orders except Week_1
    query3 = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        DELETE {
            ?order ?p ?o .
        }
        WHERE {
            ?order a bg:Order .
            FILTER(!CONTAINS(STR(?order), "Week1") && !CONTAINS(STR(?order), "Week_1"))
            
            ?order ?p ?o .
        }
    """
    execute_update(repo_id, query3, "Delete Orders (not Week 1)")
    
    # 4. Delete Week entities except Week_1
    query4 = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        DELETE {
            ?week ?p ?o .
        }
        WHERE {
            ?week a bg:Week .
            FILTER(!CONTAINS(STR(?week), "Week_1"))
            
            ?week ?p ?o .
        }
    """
    execute_update(repo_id, query4, "Delete Week entities (not Week_1)")
    
    # 5. Delete CustomerDemand except Week 1
    query5 = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        DELETE {
            ?demand ?p ?o .
        }
        WHERE {
            ?demand a bg:CustomerDemand .
            FILTER(!CONTAINS(STR(?demand), "Week1") && !CONTAINS(STR(?demand), "Week_1"))
            
            ?demand ?p ?o .
        }
    """
    execute_update(repo_id, query5, "Delete CustomerDemand (not Week 1)")
    
    # 6. Clean duplicate Inventory values
    query6 = """
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        DELETE {
            ?inv bg:currentInventory ?stock ;
                 bg:backlog ?backlog .
        }
        INSERT {
            ?inv bg:currentInventory ?maxStock ;
                 bg:backlog "0"^^xsd:integer .
        }
        WHERE {
            ?inv a bg:Inventory ;
                 bg:forWeek bg:Week_1 .
            
            # Get all stock values
            {
                SELECT ?inv (MAX(?s) as ?maxStock) WHERE {
                    ?inv a bg:Inventory ;
                         bg:forWeek bg:Week_1 ;
                         bg:currentInventory ?s .
                }
                GROUP BY ?inv
            }
            
            ?inv bg:currentInventory ?stock .
            OPTIONAL { ?inv bg:backlog ?backlog }
        }
    """
    execute_update(repo_id, query6, "Reset Inventory_Week1 to initial state")
    
    # 7. Delete ALL Inventory except Week_1
    query7 = """
        PREFIX bg: <http://beergame.org/ontology#>
        
        DELETE {
            ?inv ?p ?o .
        }
        WHERE {
            ?inv a bg:Inventory .
            FILTER(!CONTAINS(STR(?inv), "Week1") && !CONTAINS(STR(?inv), "Week_1"))
            
            ?inv ?p ?o .
        }
    """
    execute_update(repo_id, query7, "Delete Inventory (not Week 1)")
    
    print(f"✅ {repo_name} cleaned successfully")


def main():
    """Clean all repositories"""
    print("="*70)
    print("🧹 CLEANING TEMPORAL DATA FROM ALL REPOSITORIES")
    print("="*70)
    print("\nThis will:")
    print("  • Keep Week_1 and all initial TTL data")
    print("  • Remove all data from Week > 1")
    print("  • Clean duplicate values in Week_1")
    print("  • Reset to initial state")
    print("="*70)
    
    response = input("\nProceed? (y/n): ").lower().strip()
    
    if response != 'y':
        print("\nCancelled.")
        return
    
    for repo_name, repo_id in REPOSITORIES.items():
        clean_repository(repo_name, repo_id)
    
    print("\n" + "="*70)
    print("✅ ALL REPOSITORIES CLEANED")
    print("="*70)
    print("\nNext steps:")
    print("  1. Run: python temporal_beer_game_rules_v2.py")
    print("  2. Simulate weeks without duplicates")
    print("="*70)


if __name__ == "__main__":
    main()