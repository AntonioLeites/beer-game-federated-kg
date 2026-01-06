"""
Beer Game Federated KG - Dynamic Simulation Engine
Simulates the complete beer game dynamics: demand, orders, shipments, inventory updates
UPDATED: SHACL compliant (integer quantities, arrivalWeek as IRI, receivedBy/shippedTo)
"""

import time
import json
import random
import requests
from datetime import datetime

# Import from the correct file - temporal_beer_game_rules.py
try:
    from temporal_beer_game_rules import TemporalBeerGameRuleExecutor
    print("✓ Imported TemporalBeerGameRuleExecutor from temporal_beer_game_rules.py")
except ImportError:
    print("✗ Could not import from temporal_beer_game_rules.py")
    print("  Make sure temporal_beer_game_rules.py is in the same directory")
    raise


class BeerGameDynamicSimulation:
    """
    Complete Beer Game simulation with:
    - Customer demand generation
    - Order processing between actors
    - Shipment creation and arrival
    - Inventory updates
    - Rule execution for metrics and anomaly detection
    """
    
    def __init__(self, graphdb_url="http://localhost:7200"):
        self.graphdb_url = graphdb_url
        self.rule_executor = TemporalBeerGameRuleExecutor(graphdb_url)
        self.session = requests.Session()
        
        # Supply chain configuration (upstream flow)
        self.supply_chain = {
            "Retailer": {
                "repo": "BG_Retailer",
                "uri": "bg_retailer:Retailer_Alpha",
                "namespace": "bg_retailer",
                "upstream_actor": "Wholesaler",
                "upstream_uri": "bg_wholesaler:Wholesaler_Beta"
            },
            "Wholesaler": {
                "repo": "BG_Wholesaler",  # ← Fixed (w/o typo)
                "uri": "bg_wholesaler:Wholesaler_Beta",
                "namespace": "bg_wholesaler",
                "upstream_actor": "Distributor",
                "upstream_uri": "bg_distributor:Distributor_Gamma"
            },
            "Distributor": {
                "repo": "BG_Distributor",
                "uri": "bg_distributor:Distributor_Gamma",
                "namespace": "bg_distributor",
                "upstream_actor": "Factory",
                "upstream_uri": "bg_factory:Factory_Delta"
            },
            "Factory": {
                "repo": "BG_Factory",
                "uri": "bg_factory:Factory_Delta",
                "namespace": "bg_factory",
                "upstream_actor": None,  # No upstream
                "upstream_uri": None
            }
        }
        
        self.results = []
        self.start_time = None
        
    def run_simulation(self, weeks=4, demand_pattern="stable"):
        """
        Run complete simulation
        
        Args:
            weeks (int): Number of weeks
            demand_pattern (str): 'stable', 'spike', 'increasing', 'random'
        """
        self.start_time = datetime.now()
        
        print(f"\n{'='*80}")
        print(f"🎮 BEER GAME DYNAMIC SIMULATION")
        print(f"{'='*80}")
        print(f"   Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Weeks: {weeks}")
        print(f"   Demand pattern: {demand_pattern}")
        print(f"{'='*80}\n")
        
        for week in range(1, weeks + 1):
            print(f"\n{'#'*80}")
            print(f"📅 WEEK {week} - SIMULATION STEP")
            print(f"{'#'*80}")
            
            week_result = self.simulate_week(week, demand_pattern)
            self.results.append(week_result)
            
            time.sleep(1)  # Brief pause
        
        self.generate_report()
    
    def simulate_week(self, week, demand_pattern):
        """Simulate one complete week"""
        result = {
            "week": week,
            "timestamp": datetime.now().isoformat(),
            "phases": {}
        }
        
        # PHASE 1: Generate customer demand
        print(f"\n→ Phase 1: Generating customer demand...")
        demand = self.generate_customer_demand(week, demand_pattern)
        result["phases"]["demand"] = demand
        print(f"   Customer demand: {demand} units")
        
        # PHASE 2: Process shipment arrivals (from previous weeks)
        print(f"\n→ Phase 2: Processing shipment arrivals...")
        arrivals = self.process_shipment_arrivals(week)
        result["phases"]["arrivals"] = arrivals
        
        # PHASE 3: Update inventories (add arrivals, subtract demand/orders)
        print(f"\n→ Phase 3: Updating inventories...")
        inventories = self.update_inventories(week, demand, arrivals)
        result["phases"]["inventories"] = inventories
        
        # PHASE 4: Execute SPARQL rules (calculate metrics, detect risks)
        print(f"\n→ Phase 4: Executing business rules...")
        executed, failed = self.rule_executor.execute_federated_week_simulation(
            week, dry_run=False
        )
        result["phases"]["rules"] = {"executed": executed, "failed": failed}
        
        # PHASE 5: Make ordering decisions (based on suggestedOrderQuantity)
        print(f"\n→ Phase 5: Processing orders...")
        orders = self.process_orders(week)
        result["phases"]["orders"] = orders
        
        # PHASE 6: Create shipments (will arrive in future weeks)
        print(f"\n→ Phase 6: Creating shipments...")
        shipments = self.create_shipments(week, orders)
        result["phases"]["shipments"] = shipments
        
        return result
    
    # def generate_customer_demand(self, week, pattern="stable"):
    #     """Generate customer demand for retailer"""
    #     base_demand = 4
        
    #     if pattern == "stable":
    #         demand = base_demand
    #     elif pattern == "spike":
    #         demand = base_demand * 2 if week == 2 else base_demand
    #     elif pattern == "increasing":
    #         demand = base_demand + (week - 1)
    #     elif pattern == "random":
    #         demand = random.randint(2, 8)
    #     else:
    #         demand = base_demand
        
    #     # Insert CustomerDemand into Retailer repository
    #     query = f"""
    #         PREFIX bg: <http://beergame.org/ontology#>
    #         PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
    #         INSERT DATA {{
    #             bg_retailer:CustomerDemand_Week{week} a bg:CustomerDemand ;
    #                 bg:forWeek bg:Week_{week} ;
    #                 bg:actualDemand "{demand}"^^xsd:integer ;
    #                 bg:demandPattern "{pattern}" .
    #         }}
    #     """
        
    #     self._execute_update(query, "BG_Retailer")
    #     return demand
    
    def generate_customer_demand(self, week, demand_pattern):
        """Generate customer demand for retailer"""
        base_demand = 4
    
        if demand_pattern == "stable":
            demand = base_demand
        elif demand_pattern == "spike":
            demand = base_demand * 2 if week == 2 else base_demand
        elif demand_pattern == "increasing":
            demand = base_demand + (week - 1)
        elif demand_pattern == "random":
            demand = random.randint(2, 8)
        else:
            demand = base_demand
    
        # Insert CustomerDemand into Retailer repository
        # Use PREFIX declarations with INSERT WHERE (not INSERT DATA)
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX bg_retailer: <http://beergame.org/retailer#>
            
            INSERT {{
                bg_retailer:CustomerDemand_Week{week} a bg:CustomerDemand ;
                    bg:forWeek bg:Week_{week} ;
                    bg:actualDemand "{demand}"^^xsd:integer ;
                    bg:demandPattern "{demand_pattern}" .
            }}
            WHERE {{}}
        """
    
        self._execute_update(query, "BG_Retailer")
        return demand
    
    def process_shipment_arrivals(self, week):
        """Process shipments that arrive this week"""
        arrivals = {}
        
        for actor_name, config in self.supply_chain.items():
            # Query shipments arriving this week (arrivalWeek is now an IRI)
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                
                SELECT ?shipment ?qty
                WHERE {{
                    ?shipment a bg:Shipment ;
                              bg:arrivalWeek bg:Week_{week} ;
                              bg:quantity ?qty ;
                              bg:shippedTo {config['uri']} .
                }}
            """
            
            results = self._execute_query(query, config['repo'])
            bindings = results.get("results", {}).get("bindings", [])
            
            total_arriving = sum(int(b["qty"]["value"]) for b in bindings)
            arrivals[actor_name] = total_arriving
            
            if total_arriving > 0:
                print(f"   {actor_name}: {total_arriving} units arriving")
        
        return arrivals
    
    def update_inventories(self, week, customer_demand, arrivals):
        """Update inventory levels for all actors"""
        inventories = {}
        
        for actor_name, config in self.supply_chain.items():
            repo = config['repo']
            
            # Get current inventory from previous week
            prev_week = week - 1
            if prev_week > 0:
                query = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    SELECT ?stock WHERE {{
                        ?inv a bg:Inventory ;
                             bg:forWeek bg:Week_{prev_week} ;
                             bg:belongsTo {config['uri']} ;
                             bg:currentInventory ?stock .
                    }}
                """
                
                result = self._execute_query(query, repo)
                bindings = result.get("results", {}).get("bindings", [])
                
                if bindings:
                    current_stock = int(bindings[0]["stock"]["value"])
                else:
                    current_stock = 12  # Default
            else:
                current_stock = 12  # Initial inventory
            
            # Calculate new stock
            arrivals_qty = arrivals.get(actor_name, 0)
            
            # Retailer loses customer demand, others lose orders to downstream
            if actor_name == "Retailer":
                demand_loss = customer_demand
            else:
                # Simplified: assume 4 units shipped downstream
                demand_loss = 4
            
            new_stock = max(0, current_stock + arrivals_qty - demand_loss)
            
            # Create new Inventory for this week
            inv_uri = f"{config['namespace']}:Inventory_Week{week}"
            
            # Define namespace prefix for this actor
            namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
            
            update = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX {config['namespace']}: <{namespace_uri}>
                
                INSERT {{
                    {inv_uri} a bg:Inventory ;
                        bg:forWeek bg:Week_{week} ;
                        bg:belongsTo {config['uri']} ;
                        bg:currentInventory "{new_stock}"^^xsd:integer ;
                        bg:backlog "0"^^xsd:integer ;
                        bg:holdingCost "0.5"^^xsd:decimal ;
                        bg:backlogCost "1.0"^^xsd:decimal .
                }}
                WHERE {{}}
            """
            
            self._execute_update(update, repo)
            inventories[actor_name] = new_stock
            print(f"   {actor_name}: {current_stock} + {arrivals_qty} - {demand_loss} = {new_stock}")
        
        return inventories
    
    def process_orders(self, week):
        """Process ordering decisions based on suggestedOrderQuantity"""
        orders = {}
        
        for actor_name, config in self.supply_chain.items():
            # Skip Factory (no upstream to order from)
            if not config['upstream_actor']:
                continue
            
            # Get suggested order quantity from ActorMetrics
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                SELECT ?suggested WHERE {{
                    ?metrics a bg:ActorMetrics ;
                             bg:forWeek bg:Week_{week} ;
                             bg:belongsTo {config['uri']} ;
                             bg:suggestedOrderQuantity ?suggested .
                }}
            """
            
            result = self._execute_query(query, config['repo'])
            bindings = result.get("results", {}).get("bindings", [])
            
            if bindings:
                order_qty = int(bindings[0]["suggested"]["value"])
            else:
                order_qty = 4  # Default
            
            # Create Order entity with receivedBy (upstream supplier)
            order_uri = f"{config['namespace']}:Order_Week{week}"
            
            # Define namespace prefixes
            actor_namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
            upstream_actor_name = config['upstream_actor']
            upstream_config = self.supply_chain[upstream_actor_name]
            upstream_namespace = upstream_config['namespace']
            upstream_namespace_uri = f"http://beergame.org/{upstream_namespace.replace('bg_', '')}#"
            
            update = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX {config['namespace']}: <{actor_namespace_uri}>
                PREFIX {upstream_namespace}: <{upstream_namespace_uri}>
                
                INSERT {{
                    {order_uri} a bg:Order ;
                        bg:forWeek bg:Week_{week} ;
                        bg:placedBy {config['uri']} ;
                        bg:receivedBy {config['upstream_uri']} ;
                        bg:orderQuantity "{order_qty}"^^xsd:integer .
                }}
                WHERE {{}}
            """
            self._execute_update(update, config['repo'])
            orders[actor_name] = order_qty
            print(f"   {actor_name} → {config['upstream_actor']}: {order_qty} units")
        
        return orders
    
    def create_shipments(self, week, orders):
        """Create shipments that will arrive in future weeks"""
        shipments = {}
        
        # Reverse order: Factory ships to Distributor, Distributor to Wholesaler, etc.
        chain_order = ["Factory", "Distributor", "Wholesaler", "Retailer"]
        
        for actor_name in chain_order:
            config = self.supply_chain[actor_name]
            
            # Get actor's shipping delay
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                SELECT ?delay WHERE {{
                    {config['uri']} bg:shippingDelay ?delay .
                }}
            """
            
            result = self._execute_query(query, config['repo'])
            bindings = result.get("results", {}).get("bindings", [])
            
            if bindings:
                delay = int(bindings[0]["delay"]["value"])
            else:
                delay = 2
            
            arrival_week_num = week + delay
            
            # Determine quantity to ship and who receives it
            if actor_name == "Factory":
                # Ships to Distributor based on Distributor's order
                qty = orders.get("Distributor", 4)
                receiver_uri = self.supply_chain["Distributor"]["uri"]
            elif actor_name == "Distributor":
                qty = orders.get("Wholesaler", 4)
                receiver_uri = self.supply_chain["Wholesaler"]["uri"]
            elif actor_name == "Wholesaler":
                qty = orders.get("Retailer", 4)
                receiver_uri = self.supply_chain["Retailer"]["uri"]
            else:  # Retailer ships to customer (not modeled)
                continue
            
            shipment_uri = f"{config['namespace']}:Shipment_Week{week}"
            
            # Get receiver config for namespace
            if actor_name == "Factory":
                receiver_config = self.supply_chain["Distributor"]
            elif actor_name == "Distributor":
                receiver_config = self.supply_chain["Wholesaler"]
            elif actor_name == "Wholesaler":
                receiver_config = self.supply_chain["Retailer"]
            else:
                continue
            
            # Define namespace URIs
            actor_namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
            receiver_namespace_uri = f"http://beergame.org/{receiver_config['namespace'].replace('bg_', '')}#"
            
            update = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX {config['namespace']}: <{actor_namespace_uri}>
                PREFIX {receiver_config['namespace']}: <{receiver_namespace_uri}>
                
                INSERT {{
                    {shipment_uri} a bg:Shipment ;
                        bg:forWeek bg:Week_{week} ;
                        bg:shippedFrom {config['uri']} ;
                        bg:shippedTo {receiver_uri} ;
                        bg:quantity "{qty}"^^xsd:integer ;
                        bg:arrivalWeek bg:Week_{arrival_week_num} .
                }}
                WHERE {{}}
            """
            
            self._execute_update(update, config['repo'])
            shipments[actor_name] = {"qty": qty, "arrival": arrival_week_num, "to": receiver_uri}
            print(f"   {actor_name}: ships {qty} units (arrives Week {arrival_week_num})")
        
        return shipments
    
    def _execute_query(self, sparql, repository):
        """Execute SPARQL SELECT query"""
        endpoint = f"{self.graphdb_url}/repositories/{repository}"
        try:
            response = self.session.post(
                endpoint,
                data={"query": sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return {"results": {"bindings": []}}
        except Exception as e:
            print(f"   ⚠️  Query error: {e}")
            return {"results": {"bindings": []}}
    
    def _execute_update(self, sparql, repository):
        """Execute SPARQL UPDATE query"""
        endpoint = f"{self.graphdb_url}/repositories/{repository}/statements"
        
        # DEBUG: Print what we're trying to insert
        print(f"\n   [DEBUG] Executing update on {repository}")
        print(f"   [DEBUG] Query: {sparql}")  # Show the full SPARQL query
        
        try:
            response = self.session.post(
                endpoint,
                data=sparql,
                headers={"Content-Type": "application/sparql-update"},
                timeout=30
            )
            
            print(f"   [DEBUG] Response status: {response.status_code}")
            if response.status_code != 204:
                print(f"   [DEBUG] Error: {response.text}")
                
            return response.status_code == 204
        except Exception as e:
            print(f"   ⚠️  Update error: {e}")
            return False
    
    def generate_report(self):
        """Generate final simulation report"""
        print(f"\n{'='*80}")
        print(f"📊 SIMULATION REPORT")
        print(f"{'='*80}")
        
        # Save to JSON
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"beer_game_dynamic_sim_{timestamp}.json"
        
        report = {
            "simulation": "Beer Game Dynamic Simulation",
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "weeks": len(self.results),
            "results": self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved: {filename}")
        print(f"{'='*80}\n")


def main():
    sim = BeerGameDynamicSimulation()
    
    print("Choose demand pattern:")
    print("1. Stable (constant 4 units)")
    print("2. Spike (doubles at week 2)")
    print("3. Increasing (gradual growth)")
    print("4. Random")
    
    choice = input("\nEnter choice (1-4, default=1): ").strip() or "1"
    
    patterns = {"1": "stable", "2": "spike", "3": "increasing", "4": "random"}
    pattern = patterns.get(choice, "stable")
    
    weeks = int(input("Number of weeks (default=4): ").strip() or "4")
    
    sim.run_simulation(weeks=weeks, demand_pattern=pattern)


if __name__ == "__main__":
    main()