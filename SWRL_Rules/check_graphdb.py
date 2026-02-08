import requests

base_url = "http://localhost:7200"
repo = "BG_Supply_Chain"

queries = {
    "Contexts": "SELECT (COUNT(?c) as ?count) WHERE { ?c a <http://beergame.org/ontology#DecisionContext> }",
    "Orders": "SELECT (COUNT(?o) as ?count) WHERE { ?o a <http://beergame.org/ontology#Order> }",
    "Weeks": "SELECT (COUNT(?w) as ?count) WHERE { ?w a <http://beergame.org/ontology#Week> }"
}

for name, query in queries.items():
    full_query = f"PREFIX bg: <http://beergame.org/ontology#> {query}"
    response = requests.post(
        f"{base_url}/repositories/{repo}",
        data={'query': full_query},
        headers={'Accept': 'application/sparql-results+json'}
    )
    
    if response.status_code == 200:
        count = response.json()['results']['bindings'][0]['count']['value']
        print(f"{name}: {count}")
    else:
        print(f"{name}: ERROR {response.status_code}")
