"""
Beer Game Federated KG - Dynamic Simulation Engine (FINAL FIX)
Simulates the complete beer game dynamics: demand, orders, shipments, inventory updates

CRITICAL FIXES:
1. Outbound shipments based on RECEIVED orders (not current week orders)
2. Proper Week entity creation before use
3. No deletion of existing metrics
4. Correct temporal sequencing
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
    Complete Beer Game simulation with proper temporal semantics
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
                "repo": "BG_Wholesaler",
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
                "upstream_actor": None,
                "upstream_uri": None
            }
        }
        
        self.results = []
        self.start_time = None
        
    def run_simulation(self, weeks=4, demand_pattern="stable"):
        """Run complete simulation"""
        self.start_time = datetime.now()
        
        print(f"\n{'='*80}")
        print(f"🎮 BEER GAME DYNAMIC SIMULATION (FINAL)")
        print(f"{'='*80}")
        print(f"   Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Weeks: {weeks}")
        print(f"   Demand pattern: {demand_pattern}")
        print(f"{'='*80}\n")
        
        for week in range(1, weeks + 1):
            print(f"\n{'#'*80}")
            print(f"📅 WEEK {week} - SIMULATION STEP")
            print(f"{'#'*80}")
            
            # CRITICAL: Create Week entity first
            self.create_week_entity(week)
            
            week_result = self.simulate_week(week, demand_pattern)
            self.results.append(week_result)
            
            time.sleep(1)
        
        self.generate_report()
    
    def create_week_entity(self, week):
        """Create bg:Week entity if it doesn't exist"""
        for actor_name, config in self.supply_chain.items():
            # Check if week exists
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                ASK WHERE {{ bg:Week_{week} a bg:Week }}
            """
            
            result = self._execute_query(query, config['repo'])
            exists = result.get("boolean", False)
            
            if not exists:
                # Create week entity
                update = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    
                    INSERT {{
                        bg:Week_{week} a bg:Week ;
                            bg:weekNumber "{week}"^^xsd:integer ;
                            rdfs:label "Week {week}" .
                    }}
                    WHERE {{}}
                """
                self._execute_update(update, config['repo'])
                print(f"   ✓ Created Week_{week} entity in {actor_name}")
                break  # Only need to create once
    
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
        
        # PHASE 2: Process shipment arrivals
        print(f"\n→ Phase 2: Processing shipment arrivals...")
        arrivals = self.process_shipment_arrivals(week)
        result["phases"]["arrivals"] = arrivals
        
        # PHASE 3: Update inventories
        print(f"\n→ Phase 3: Updating inventories...")
        inventories = self.update_inventories(week, demand, arrivals)
        result["phases"]["inventories"] = inventories
        
        # PHASE 4: Execute rules (WITHOUT dry_run to actually create metrics)
        print(f"\n→ Phase 4: Executing business rules...")
        executed, failed = self.rule_executor.execute_federated_week_simulation(
            week, dry_run=False
        )
        result["phases"]["rules"] = {"executed": executed, "failed": failed}
        
        # PHASE 5: Make ordering decisions
        print(f"\n→ Phase 5: Processing orders...")
        orders = self.process_orders(week)
        result["phases"]["orders"] = orders
        
        # PHASE 6: Create shipments
        print(f"\n→ Phase 6: Creating shipments...")
        shipments = self.create_shipments_fixed(week)
        result["phases"]["shipments"] = shipments
        
        return result
    
    def generate_customer_demand(self, week, pattern="stable"):
        """Generate customer demand for retailer"""
        base_demand = 4
        
        if pattern == "stable":
            demand = base_demand
        elif pattern == "spike":
            demand = base_demand if week != 3 else 12
        elif pattern == "increasing":
            demand = base_demand + (week - 1)
        elif pattern == "random":
            demand = random.randint(2, 8)
        else:
            demand = base_demand
        
        config = self.supply_chain["Retailer"]
        actor_namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
        
        update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX {config['namespace']}: <{actor_namespace_uri}>
            
            INSERT {{
                {config['namespace']}:CustomerDemand_Week{week} a bg:CustomerDemand ;
                    bg:forWeek bg:Week_{week} ;
                    bg:actualDemand "{demand}"^^xsd:integer ;
                    bg:demandPattern "{pattern}"^^xsd:string .
            }}
            WHERE {{}}
        """
        self._execute_update(update, config['repo'])
        return demand
    
    def process_shipment_arrivals(self, week):
        """Check for inbound shipments arriving this week"""
        arrivals = {}
        
        for actor_name, config in self.supply_chain.items():
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                SELECT ?shipment ?qty WHERE {{
                    ?shipment a bg:Shipment ;
                        bg:shippedTo {config['uri']} ;
                        bg:arrivalWeek bg:Week_{week} ;
                        bg:quantity ?qty .
                }}
            """
            
            result = self._execute_query(query, config['repo'])
            bindings = result.get("results", {}).get("bindings", [])
            
            total_arriving = sum(int(b["qty"]["value"]) for b in bindings)
            arrivals[actor_name] = total_arriving
            
            if total_arriving > 0:
                print(f"   {actor_name}: receiving {total_arriving} units")
        
        return arrivals
    
    def update_inventories(self, week, customer_demand, arrivals):
        """Update inventory levels for all actors"""
        inventories = {}
        
        for actor_name, config in self.supply_chain.items():
            # Get previous inventory
            if week == 1:
                prev_inv = 12
                prev_backlog = 0
            else:
                query = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    SELECT ?inv ?backlog WHERE {{
                        ?inventory a bg:Inventory ;
                            bg:forWeek bg:Week_{week - 1} ;
                            bg:belongsTo {config['uri']} ;
                            bg:currentInventory ?inv ;
                            bg:backlog ?backlog .
                    }}
                """
                
                result = self._execute_query(query, config['repo'])
                bindings = result.get("results", {}).get("bindings", [])
                
                if bindings:
                    prev_inv = int(bindings[0]["inv"]["value"])
                    prev_backlog = int(bindings[0]["backlog"]["value"])
                else:
                    prev_inv = 12
                    prev_backlog = 0
            
            # Calculate demand
            if actor_name == "Retailer":
                demand_this_week = customer_demand
            else:
                # Query orders received from downstream
                demand_query = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    SELECT (SUM(?qty) as ?total) WHERE {{
                        ?order a bg:Order ;
                            bg:forWeek bg:Week_{week} ;
                            bg:receivedBy {config['uri']} ;
                            bg:orderQuantity ?qty .
                    }}
                """
                order_result = self._execute_query(demand_query, config['repo'])
                order_bindings = order_result.get("results", {}).get("bindings", [])
                
                if order_bindings and order_bindings[0].get("total"):
                    demand_this_week = int(order_bindings[0]["total"]["value"])
                else:
                    demand_this_week = 0
            
            # Update inventory
            incoming = arrivals.get(actor_name, 0)
            new_inv = prev_inv + incoming
            
            # Fulfill demand
            total_demand = demand_this_week + prev_backlog
            if new_inv >= total_demand:
                outgoing = total_demand
                new_inv -= total_demand
                new_backlog = 0
            else:
                outgoing = new_inv
                new_backlog = total_demand - outgoing
                new_inv = 0
            
            inventories[actor_name] = {
                "current": new_inv,
                "backlog": new_backlog,
                "incoming": incoming,
                "outgoing": outgoing
            }
            
            # Create Inventory entity
            actor_namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
            
            update = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX {config['namespace']}: <{actor_namespace_uri}>
                
                INSERT {{
                    {config['namespace']}:Inventory_Week{week} a bg:Inventory ;
                        bg:forWeek bg:Week_{week} ;
                        bg:belongsTo {config['uri']} ;
                        bg:currentInventory "{new_inv}"^^xsd:integer ;
                        bg:backlog "{new_backlog}"^^xsd:integer ;
                        bg:incomingShipment "{incoming}"^^xsd:integer ;
                        bg:outgoingShipment "{outgoing}"^^xsd:integer ;
                        bg:holdingCost "0.50"^^xsd:decimal ;
                        bg:backlogCost "1.00"^^xsd:decimal .
                }}
                WHERE {{}}
            """
            self._execute_update(update, config['repo'])
            
            print(f"   {actor_name}: inv={new_inv}, backlog={new_backlog}, in={incoming}, out={outgoing}")
        
        return inventories
    
    def process_orders(self, week):
        """Process ordering decisions"""
        orders = {}
        chain_order = ["Retailer", "Wholesaler", "Distributor"]
        
        for actor_name in chain_order:
            config = self.supply_chain[actor_name]
            
            # Get suggested order quantity
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
            
            # Create Order
            upstream_config = self.supply_chain[config['upstream_actor']]
            order_uri = f"{config['namespace']}:Order_Week{week}"
            
            actor_namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
            upstream_namespace_uri = f"http://beergame.org/{upstream_config['namespace'].replace('bg_', '')}#"
            
            update = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX {config['namespace']}: <{actor_namespace_uri}>
                PREFIX {upstream_config['namespace']}: <{upstream_namespace_uri}>
                
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
    
    def create_shipments_fixed(self, week):
        """
        FIXED: Create shipments based on ACTUAL orders received, not current orders
        """
        shipments = {"outbound": {}, "inbound": {}}
        
        # Process each actor
        for actor_name, config in self.supply_chain.items():
            actor_namespace_uri = f"http://beergame.org/{config['namespace'].replace('bg_', '')}#"
            
            # ===== OUTBOUND: Based on orders RECEIVED from downstream =====
            if actor_name != "Retailer":
                # Determine downstream
                if actor_name == "Factory":
                    downstream_name = "Distributor"
                elif actor_name == "Distributor":
                    downstream_name = "Wholesaler"
                elif actor_name == "Wholesaler":
                    downstream_name = "Retailer"
                
                downstream_config = self.supply_chain[downstream_name]
                downstream_namespace_uri = f"http://beergame.org/{downstream_config['namespace'].replace('bg_', '')}#"
                
                # Query for orders received FROM downstream this week
                order_query = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    SELECT (SUM(?qty) as ?total) WHERE {{
                        ?order a bg:Order ;
                            bg:forWeek bg:Week_{week} ;
                            bg:receivedBy {config['uri']} ;
                            bg:placedBy {downstream_config['uri']} ;
                            bg:orderQuantity ?qty .
                    }}
                """
                
                order_result = self._execute_query(order_query, config['repo'])
                order_bindings = order_result.get("results", {}).get("bindings", [])
                
                if order_bindings and order_bindings[0].get("total"):
                    qty = int(order_bindings[0]["total"]["value"])
                else:
                    qty = 4  # Default if no orders found
                
                # Get shipping delay
                shipping_delay = self._get_actor_delay(config, 'shippingDelay')
                arrival_week_num = week + shipping_delay
                
                outbound_uri = f"{config['namespace']}:Shipment_Week{week}_To{downstream_name}"
                
                update = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    PREFIX {config['namespace']}: <{actor_namespace_uri}>
                    PREFIX {downstream_config['namespace']}: <{downstream_namespace_uri}>
                    
                    INSERT {{
                        {outbound_uri} a bg:Shipment ;
                            bg:forWeek bg:Week_{week} ;
                            bg:belongsTo {config['uri']} ;
                            bg:shippedFrom {config['uri']} ;
                            bg:shippedTo {downstream_config['uri']} ;
                            bg:shippedQuantity "{qty}"^^xsd:integer ;
                            bg:quantity "{qty}"^^xsd:integer ;
                            bg:arrivalWeek bg:Week_{arrival_week_num} .
                    }}
                    WHERE {{}}
                """
                
                self._execute_update(update, config['repo'])
                shipments["outbound"][actor_name] = {
                    "to": downstream_name,
                    "qty": qty,
                    "arrival": arrival_week_num
                }
                print(f"   {actor_name} → {downstream_name}: {qty} units (arrives Week {arrival_week_num})")
            
            # ===== INBOUND: Based on orders PLACED to upstream =====
            if actor_name != "Factory":
                upstream_name = config['upstream_actor']
                upstream_config = self.supply_chain[upstream_name]
                upstream_namespace_uri = f"http://beergame.org/{upstream_config['namespace'].replace('bg_', '')}#"
                
                # Query for MY order to upstream this week
                my_order_query = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    SELECT ?qty WHERE {{
                        ?order a bg:Order ;
                            bg:forWeek bg:Week_{week} ;
                            bg:placedBy {config['uri']} ;
                            bg:receivedBy {upstream_config['uri']} ;
                            bg:orderQuantity ?qty .
                    }}
                """
                
                my_order_result = self._execute_query(my_order_query, config['repo'])
                my_order_bindings = my_order_result.get("results", {}).get("bindings", [])
                
                if my_order_bindings:
                    qty = int(my_order_bindings[0]["qty"]["value"])
                else:
                    qty = 4  # Default
                
                # Get shipping delay from UPSTREAM (sender)
                shipping_delay = self._get_actor_delay(upstream_config, 'shippingDelay')
                arrival_week_num = week + shipping_delay
                
                inbound_uri = f"{config['namespace']}:Shipment_Week{week}_From{upstream_name}"
                
                update = f"""
                    PREFIX bg: <http://beergame.org/ontology#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    PREFIX {config['namespace']}: <{actor_namespace_uri}>
                    PREFIX {upstream_config['namespace']}: <{upstream_namespace_uri}>
                    
                    INSERT {{
                        {inbound_uri} a bg:Shipment ;
                            bg:forWeek bg:Week_{week} ;
                            bg:belongsTo {config['uri']} ;
                            bg:shippedFrom {upstream_config['uri']} ;
                            bg:shippedTo {config['uri']} ;
                            bg:shippedQuantity "{qty}"^^xsd:integer ;
                            bg:quantity "{qty}"^^xsd:integer ;
                            bg:arrivalWeek bg:Week_{arrival_week_num} .
                    }}
                    WHERE {{}}
                """
                
                self._execute_update(update, config['repo'])
                shipments["inbound"][actor_name] = {
                    "from": upstream_name,
                    "qty": qty,
                    "arrival": arrival_week_num
                }
                print(f"   {actor_name} ← {upstream_name}: expecting {qty} units (arrives Week {arrival_week_num})")
        
        return shipments
    
    def _get_actor_delay(self, config, delay_type):
        """Get delay from actor configuration"""
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?delay WHERE {{
                {config['uri']} bg:{delay_type} ?delay .
            }}
        """
        
        result = self._execute_query(query, config['repo'])
        bindings = result.get("results", {}).get("bindings", [])
        
        if bindings:
            return int(bindings[0]["delay"]["value"])
        return 2 if delay_type == 'shippingDelay' else 1
    
    def _execute_query(self, sparql, repository):
        """Execute SPARQL SELECT or ASK query"""
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
        try:
            response = self.session.post(
                endpoint,
                data={"update": sparql},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            return response.status_code == 204
        except Exception as e:
            print(f"   ⚠️  Update error: {e}")
            return False
    
    def generate_report(self):
        """Generate final report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"📊 SIMULATION REPORT")
        print(f"{'='*80}")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Weeks simulated: {len(self.results)}")
        print(f"\n{'='*80}\n")
        
        report_file = f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "simulation_info": {
                    "start": self.start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"📁 Full report saved to: {report_file}")


def main():
    """Interactive menu for running simulation"""
    sim = BeerGameDynamicSimulation()
    
    print("\n" + "="*80)
    print("🍺 BEER GAME FEDERATED SIMULATION")
    print("="*80)
    print("\nChoose demand pattern:")
    print("1. Stable (constant 4 units)")
    print("2. Spike (12 units at week 3)")
    print("3. Increasing (gradual growth)")
    print("4. Random (2-8 units)")
    
    choice = input("\nEnter choice (1-4, default=1): ").strip() or "1"
    
    patterns = {
        "1": "stable",
        "2": "spike",
        "3": "increasing",
        "4": "random"
    }
    pattern = patterns.get(choice, "stable")
    
    weeks_input = input("Number of weeks (default=4): ").strip() or "4"
    try:
        weeks = int(weeks_input)
    except ValueError:
        weeks = 4
    
    print(f"\n🎯 Running simulation:")
    print(f"   Pattern: {pattern}")
    print(f"   Weeks: {weeks}")
    print("\nPress Ctrl+C to cancel...\n")
    
    try:
        sim.run_simulation(weeks=weeks, demand_pattern=pattern)
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error during simulation: {e}")
        raise


if __name__ == "__main__":
    main()