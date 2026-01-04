"""
Beer Game Federated KG - Dynamic Simulation Engine
Simulates the beer game operational dynamics:
- Customer demand
- Orders
- Shipments
- Inventory snapshots
- Delegates metrics & risks to temporal rules
"""

import time
import json
import random
import requests
from datetime import datetime

from temporal_beer_game_rules import TemporalBeerGameRuleExecutor


class BeerGameDynamicSimulation:

    def __init__(self, graphdb_url="http://localhost:7200"):
        self.graphdb_url = graphdb_url
        self.session = requests.Session()
        self.rule_executor = TemporalBeerGameRuleExecutor(graphdb_url)

        # Actor chain (downstream → upstream)
        self.actors = {
            "Retailer": {
                "repo": "BG_Retailer",
                "uri": "bg_retailer:Retailer_Alpha",
                "upstream": "Wholesaler"
            },
            "Wholesaler": {
                "repo": "BG_Whosaler",  # typo kept on purpose
                "uri": "bg_wholesaler:Wholesaler_Beta",
                "upstream": "Distributor"
            },
            "Distributor": {
                "repo": "BG_Distributor",
                "uri": "bg_distributor:Distributor_Gamma",
                "upstream": "Factory"
            },
            "Factory": {
                "repo": "BG_Factory",
                "uri": "bg_factory:Factory_Delta",
                "upstream": None
            }
        }

        self.results = []
        self.start_time = None

    # ============================================================
    # MAIN SIMULATION LOOP
    # ============================================================

    def run_simulation(self, weeks=4, demand_pattern="stable"):
        self.start_time = datetime.now()

        print("\n" + "=" * 80)
        print("🎮 BEER GAME DYNAMIC SIMULATION")
        print("=" * 80)
        print(f"   Demand pattern: {demand_pattern}")
        print(f"   Weeks: {weeks}")
        print("=" * 80)

        for week in range(1, weeks + 1):
            print(f"\n{'#' * 80}")
            print(f"📅 WEEK {week}")
            print(f"{'#' * 80}")

            self.simulate_week(week, demand_pattern)
            time.sleep(1)

        self.generate_report()

    def simulate_week(self, week, demand_pattern):
        self.generate_customer_demand(week, demand_pattern)
        self.process_shipment_arrivals(week)
        self.update_inventories(week)
        self.rule_executor.execute_federated_week_simulation(week, dry_run=False)
        self.process_orders(week)
        self.create_shipments(week)

    # ============================================================
    # PHASE 1 – CUSTOMER DEMAND
    # ============================================================

    def generate_customer_demand(self, week, pattern):
        base = 4

        if pattern == "spike" and week == 2:
            demand = base * 2
        elif pattern == "increasing":
            demand = base + week - 1
        elif pattern == "random":
            demand = random.randint(2, 8)
        else:
            demand = base

        print(f"→ Customer demand: {demand} units")

        query = f"""
        PREFIX bg: <http://beergame.org/ontology#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        INSERT DATA {{
            bg_retailer:CustomerDemand_Week{week} a bg:CustomerDemand ;
                bg:forWeek bg:Week_{week} ;
                bg:actualDemand "{demand}"^^xsd:integer .
        }}
        """
        self._execute_update(query, "BG_Retailer")

    # ============================================================
    # PHASE 2 – SHIPMENT ARRIVALS (simplified)
    # ============================================================

    def process_shipment_arrivals(self, week):
        print("→ Processing shipment arrivals (simplified placeholder)")

    # ============================================================
    # PHASE 3 – INVENTORY SNAPSHOTS
    # ============================================================

    def update_inventories(self, week):
        print("→ Updating inventories")

        for actor, cfg in self.actors.items():
            repo = cfg["repo"]
            actor_uri = cfg["uri"]

            prev_week = week - 1
            stock = 12

            if prev_week > 0:
                query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                SELECT ?s WHERE {{
                    ?i a bg:Inventory ;
                       bg:forWeek bg:Week_{prev_week} ;
                       bg:belongsTo {actor_uri} ;
                       bg:currentInventory ?s .
                }}
                """
                res = self._execute_query(query, repo)
                if res["results"]["bindings"]:
                    stock = int(res["results"]["bindings"][0]["s"]["value"])

            if actor == "Retailer":
                stock = max(0, stock - 4)

            inventory_uri = f"{repo.lower()}:Inventory_Week{week}_{actor}"

            update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            INSERT DATA {{
                {inventory_uri} a bg:Inventory ;
                    bg:forWeek bg:Week_{week} ;
                    bg:belongsTo {actor_uri} ;
                    bg:currentInventory "{stock}"^^xsd:decimal ;
                    bg:backlog "0"^^xsd:decimal ;
                    bg:holdingCost "0.5"^^xsd:decimal ;
                    bg:backlogCost "1.0"^^xsd:decimal .
            }}
            """
            self._execute_update(update, repo)

            print(f"   {actor}: inventory = {stock}")

    # ============================================================
    # PHASE 4 – ORDERS
    # ============================================================

    def process_orders(self, week):
        print("→ Processing orders")

        for actor, cfg in self.actors.items():
            if not cfg["upstream"]:
                continue

            upstream = self.actors[cfg["upstream"]]

            query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?q WHERE {{
                ?m a bg:ActorMetrics ;
                   bg:belongsTo {cfg['uri']} ;
                   bg:forWeek bg:Week_{week} ;
                   bg:suggestedOrderQuantity ?q .
            }}
            """
            res = self._execute_query(query, cfg["repo"])
            qty = int(float(res["results"]["bindings"][0]["q"]["value"])) if res["results"]["bindings"] else 4

            order_uri = f"{cfg['repo'].lower()}:Order_Week{week}_{actor}"

            update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            INSERT DATA {{
                {order_uri} a bg:Order ;
                    bg:forWeek bg:Week_{week} ;
                    bg:placedBy {cfg['uri']} ;
                    bg:receivedBy {upstream['uri']} ;
                    bg:orderQuantity "{qty}"^^xsd:decimal .
            }}
            """
            self._execute_update(update, cfg["repo"])

            print(f"   {actor} orders {qty} units")

    # ============================================================
    # PHASE 5 – SHIPMENTS
    # ============================================================

    def create_shipments(self, week):
        print("→ Creating shipments")

        for actor, cfg in self.actors.items():
            if not cfg["upstream"]:
                continue

            upstream = self.actors[cfg["upstream"]]
            arrival_week = week + 2

            shipment_uri = f"{upstream['repo'].lower()}:Shipment_Week{week}_{actor}"

            update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            INSERT DATA {{
                {shipment_uri} a bg:Shipment ;
                    bg:forWeek bg:Week_{week} ;
                    bg:shippedFrom {upstream['uri']} ;
                    bg:shippedTo {cfg['uri']} ;
                    bg:quantity "4"^^xsd:decimal ;
                    bg:arrivalWeek "{arrival_week}"^^xsd:integer .
            }}
            """
            self._execute_update(update, upstream["repo"])

    # ============================================================
    # GRAPHDB HELPERS
    # ============================================================

    def _execute_query(self, sparql, repo):
        url = f"{self.graphdb_url}/repositories/{repo}"
        r = self.session.post(
            url,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"}
        )
        return r.json() if r.status_code == 200 else {"results": {"bindings": []}}

    def _execute_update(self, sparql, repo):
        url = f"{self.graphdb_url}/repositories/{repo}/statements"
        self.session.post(
            url,
            data=sparql,
            headers={"Content-Type": "application/sparql-update"}
        )

    # ============================================================
    # REPORT
    # ============================================================

    def generate_report(self):
        print("\n" + "=" * 80)
        print("✅ SIMULATION COMPLETED SUCCESSFULLY")
        print("=" * 80)


# ============================================================
# MAIN (INTERACTIVE)
# ============================================================

if __name__ == "__main__":
    sim = BeerGameDynamicSimulation()

    print("\nChoose demand pattern:")
    print("1. Stable (constant 4 units)")
    print("2. Spike (doubles at week 2)")
    print("3. Increasing (gradual growth)")
    print("4. Random")

    choice = input("\nEnter choice (1-4, default=1): ").strip() or "1"
    patterns = {
        "1": "stable",
        "2": "spike",
        "3": "increasing",
        "4": "random"
    }
    pattern = patterns.get(choice, "stable")

    weeks = int(input("Number of weeks (default=4): ").strip() or "4")

    sim.run_simulation(weeks=weeks, demand_pattern=pattern)
