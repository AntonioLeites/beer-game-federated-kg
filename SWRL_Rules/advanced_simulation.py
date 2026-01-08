"""
Beer Game Simulation Orchestrator (Clean Architecture)

Design Philosophy:
- Orchestrator ONLY generates external events (customer demand)
- Orchestrator creates temporal anchors (Week entities)
- ALL business logic is delegated to SPARQL rules
- Orchestrator reads results computed by rules

Separation of Concerns:
- This file: Events, Time, Orchestration
- temporal_beer_game_rules.py: Logic, Decisions, Metrics
"""

import requests
import random
import time
from temporal_beer_game_rules_v2 import TemporalBeerGameRuleExecutor


class BeerGameOrchestrator:
    """
    Orchestrates Beer Game simulation by:
    1. Creating temporal structure (Week entities)
    2. Generating exogenous events (customer demand)
    3. Executing business rules
    4. Reporting results
    
    Does NOT:
    - Calculate inventory
    - Make ordering decisions
    - Compute metrics
    - Create shipments/orders (rules do this)
    """
    
    def __init__(self, base_url="http://localhost:7200"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Supply chain configuration
        self.supply_chain = {
            "Retailer": {
                "uri": "http://beergame.org/retailer#Retailer_Alpha",
                "namespace": "bg_retailer",
                "repo": "BG_Retailer"
            },
            "Wholesaler": {
                "uri": "http://beergame.org/wholesaler#Wholesaler_Beta",
                "namespace": "bg_wholesaler",
                "repo": "BG_Wholesaler"
            },
            "Distributor": {
                "uri": "http://beergame.org/distributor#Distributor_Gamma",
                "namespace": "bg_distributor",
                "repo": "BG_Distributor"
            },
            "Factory": {
                "uri": "http://beergame.org/factory#Factory_Delta",
                "namespace": "bg_factory",
                "repo": "BG_Factory"
            }
        }
        
        # Rule executor
        self.rule_executor = TemporalBeerGameRuleExecutor(base_url)
        
        # Results tracking
        self.results = []
    
    def _execute_query(self, query, repository):
        """Execute SPARQL SELECT query"""
        endpoint = f"{self.base_url}/repositories/{repository}"
        headers = {"Accept": "application/sparql-results+json"}
        
        try:
            response = self.session.post(
                endpoint,
                data={"query": query},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Query error: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Query exception: {e}")
            return {}
    
    def _execute_update(self, update, repository):
        """Execute SPARQL UPDATE query"""
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(
                endpoint,
                data=update,
                headers=headers,
                timeout=30
            )
            return response.status_code == 204
        except Exception as e:
            print(f"Update exception: {e}")
            return False
    
    # NOTE: create_week_entity, create_actor_metrics_snapshot, and
    # create_inventory_snapshot are now called from rule_executor
    # This maintains separation: orchestrator delegates structure creation
    # to the executor's utility methods
    
    def generate_customer_demand(self, week, demand_pattern="stable"):
        """
        Generate customer demand (exogenous event)
        
        This is the ONLY thing the orchestrator generates
        Everything else is computed by rules
        """
        print(f"   Generating customer demand for Week_{week}...")
        
        # Demand patterns
        if demand_pattern == "stable":
            demand = 4
        elif demand_pattern == "spike":
            demand = 12 if week == 3 else 4
        elif demand_pattern == "increasing":
            demand = 4 + (week - 1)
        elif demand_pattern == "random":
            demand = random.randint(2, 8)
        else:
            demand = 4
        
        # Create CustomerDemand entity (only for Retailer)
        config = self.supply_chain["Retailer"]
        
        update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX {config['namespace']}: <http://beergame.org/{config['namespace'].replace('bg_', '')}#>
            
            INSERT {{
                {config['namespace']}:CustomerDemand_Week{week} a bg:CustomerDemand ;
                    bg:forWeek bg:Week_{week} ;
                    bg:belongsTo {config['uri']} ;
                    bg:actualDemand "{demand}"^^xsd:integer ;
                    rdfs:comment "Customer demand for Week {week}" .
            }}
            WHERE {{
                FILTER NOT EXISTS {{
                    {config['namespace']}:CustomerDemand_Week{week} a bg:CustomerDemand .
                }}
            }}
        """
        
        self._execute_update(update, config['repo'])
        print(f"      Customer demand: {demand} units")
        
        return demand
    
    def get_week_summary(self, week):
        """Read results computed by rules"""
        print(f"\n📊 WEEK {week} SUMMARY:")
        print("="*60)
        
        summary = {}
        
        for actor_name, config in self.supply_chain.items():
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?inv ?backlog ?coverage ?suggested ?cost
                WHERE {{
                    # Get inventory
                    OPTIONAL {{
                        ?invEntity a bg:Inventory ;
                                   bg:forWeek bg:Week_{week} ;
                                   bg:belongsTo <{config['uri']}> ;
                                   bg:currentInventory ?inv ;
                                   bg:backlog ?backlog .
                    }}
                    
                    # Get metrics
                    OPTIONAL {{
                        <{config['uri']}> bg:hasMetrics ?metrics .
                        ?metrics bg:forWeek bg:Week_{week} ;
                                 bg:inventoryCoverage ?coverage ;
                                 bg:suggestedOrderQuantity ?suggested .
                    }}
                    
                    # Get total cost
                    OPTIONAL {{
                        <{config['uri']}> bg:totalCost ?cost .
                    }}
                }}
            """
            
            result = self._execute_query(query, config['repo'])
            bindings = result.get("results", {}).get("bindings", [])
            
            if bindings:
                b = bindings[0]
                actor_data = {
                    "inventory": int(b.get("inv", {}).get("value", 0)),
                    "backlog": int(b.get("backlog", {}).get("value", 0)),
                    "coverage": float(b.get("coverage", {}).get("value", 0.0)),
                    "suggested_order": int(b.get("suggested", {}).get("value", 0)),
                    "total_cost": float(b.get("cost", {}).get("value", 0.0))
                }
                summary[actor_name] = actor_data
                
                print(f"  {actor_name}:")
                print(f"    Inventory: {actor_data['inventory']}")
                print(f"    Backlog: {actor_data['backlog']}")
                print(f"    Coverage: {actor_data['coverage']:.1f} weeks")
                print(f"    Suggested order: {actor_data['suggested_order']}")
                print(f"    Total cost: ${actor_data['total_cost']:.2f}")
        
        print("="*60)
        return summary
    
    def propagate_orders_to_receivers(self, week):
        """
        Copy orders to receiver repositories so they can create shipments
        
        Example: When Retailer creates Order_Week2_ToWholesaler in BG_Retailer,
        this copies it as Order_Week2_FromRetailer to BG_Wholesaler.
        """
        print(f"\n🔄 Propagating orders to receiver repositories...")
        
        # Order flow: sender -> receiver
        flows = [
            ("BG_Retailer", "BG_Wholesaler", "Retailer", "Wholesaler"),
            ("BG_Wholesaler", "BG_Distributor", "Wholesaler", "Distributor"),
            ("BG_Distributor", "BG_Factory", "Distributor", "Factory"),
        ]
        
        total_propagated = 0
        
        for sender_repo, receiver_repo, sender_name, receiver_name in flows:
            print(f"   Checking {sender_name} → {receiver_name}...")
            
            # Query orders in sender repo
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                SELECT ?placedBy ?receivedBy ?qty
                WHERE {{
                    ?order a bg:Order ;
                           bg:forWeek bg:Week_{week} ;
                           bg:placedBy ?placedBy ;
                           bg:receivedBy ?receivedBy ;
                           bg:orderQuantity ?qty .
                }}
            """
            
            try:
                response = requests.post(
                    f"{self.base_url}/repositories/{sender_repo}",
                    data={"query": query},
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    bindings = response.json().get("results", {}).get("bindings", [])
                    print(f"      Found {len(bindings)} orders to propagate")
                    
                    if not bindings:
                        print(f"      ⚠️  No orders found in {sender_repo} for Week {week}")
                        continue
                    
                    for b in bindings:
                        placed_by = b['placedBy']['value']
                        received_by = b['receivedBy']['value']
                        qty = b['qty']['value']
                        
                        print(f"      Processing order: {qty} units, {placed_by} → {received_by}")
                        
                        # Extract short names from URIs
                        sender_short = placed_by.split('#')[1].split('_')[0]
                        receiver_ns = received_by.split('#')[0]
                        
                        # Create order in receiver's repo
                        insert = f"""
                            PREFIX bg: <http://beergame.org/ontology#>
                            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                            PREFIX ns: <{receiver_ns}#>
                            
                            INSERT DATA {{
                                ns:Order_Week{week}_From{sender_short} a bg:Order ;
                                    bg:forWeek bg:Week_{week} ;
                                    bg:placedBy <{placed_by}> ;
                                    bg:receivedBy <{received_by}> ;
                                    bg:orderQuantity "{qty}"^^xsd:integer .
                            }}
                        """
                        
                        print(f"      Inserting to {receiver_repo}...")
                        
                        resp = requests.post(
                            f"{self.base_url}/repositories/{receiver_repo}/statements",
                            data=insert,
                            headers={"Content-Type": "application/sparql-update"},
                            timeout=10
                        )
                        
                        if resp.status_code == 204:
                            print(f"      ✓ Propagated order {sender_name}→{receiver_name}")
                            total_propagated += 1
                        else:
                            print(f"      ✗ Failed to propagate {sender_name}→{receiver_name}: {resp.status_code}")
                            print(f"         Response: {resp.text[:200]}")
                else:
                    print(f"      ✗ Query failed: {response.status_code}")
                            
            except Exception as e:
                print(f"      ✗ Error propagating {sender_name}→{receiver_name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n   Total orders propagated: {total_propagated}")
    
    def simulate_week(self, week, demand_pattern="stable"):
        """
        Orchestrate one week of simulation
        
        Steps:
        1. Create temporal structure (Week entities, Metrics, Inventory)
        2. Generate exogenous event (customer demand)
        3. Execute business rules (all logic delegated)
        4. Read and report results
        """
        print(f"\n{'#'*80}")
        print(f"📅 WEEK {week} - SIMULATION")
        print(f"{'#'*80}")
        try
        
            # Step 1: Create temporal structure
            print(f"\n🏗️  Creating temporal structure...")
            self.rule_executor.create_week_entity(week)
            
            # Only create ActorMetrics for Week > 1 (Week 1 is in initial TTL)
            if week > 1:
                print("\n   [DEBUG] CHECKPOINT 1: After execute_week_rules")
                self.rule_executor.create_actor_metrics_snapshot(week)
                self.rule_executor.create_inventory_snapshot(week)
            
            # Step 2: Generate external event
            demand = self.generate_customer_demand(week, demand_pattern)
            
            # Step 3: Execute business rules (ALL LOGIC HERE)
            print(f"\n   Executing business rules...")
            repos = [config['repo'] for config in self.supply_chain.values()]
            self.rule_executor.execute_week_rules(week, repos)
            print("\n   [DEBUG] CHECKPOINT 1: After execute_week_rules")
            
            # Step 3.5: Propagate orders to receiver repositories
            # (so receivers can create shipments in response)
            print(f"\n   [DEBUG] Week={week}, checking if should propagate (week > 1)...")
            if week > 1:  # Week 1 orders already in TTL
                print(f"   [DEBUG] Calling propagate_orders_to_receivers({week})...")
                self.propagate_orders_to_receivers(week)
            else:
                print(f"   [DEBUG] Skipping propagation for Week 1 (orders in TTL)")
            
            # Step 4: Read results
            summary = self.get_week_summary(week)
            
            return {
                "week": week,
                "demand": demand,
                "summary": summary
            }
            
        except Exception as e:
        print(f"\n❌ EXCEPTION in simulate_week: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    def get_existing_weeks(self):
        """Query GraphDB to find which weeks already exist"""
        print("\n🔍 Checking for existing weeks...")
        
        # Query any repository (they all have the same weeks)
        repo = list(self.supply_chain.values())[0]['repo']
        
        query = """
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT DISTINCT ?weekNum
            WHERE {
                ?week a bg:Week ;
                      bg:weekNumber ?weekNum .
            }
            ORDER BY ?weekNum
        """
        
        endpoint = f"{self.base_url}/repositories/{repo}"
        
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
                weeks = [int(b['weekNum']['value']) for b in bindings]
                
                if weeks:
                    print(f"   Found existing weeks: {weeks}")
                else:
                    print(f"   No existing weeks found (clean start)")
                
                return weeks
            else:
                print(f"   ⚠️  Could not query existing weeks: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"   ⚠️  Error checking existing weeks: {e}")
            return []
    
    def run_simulation(self, weeks=4, demand_pattern="stable"):
        """Run multi-week simulation (incremental - only simulates new weeks)"""
        
        # Check which weeks already exist
        existing_weeks = self.get_existing_weeks()
        max_existing = max(existing_weeks) if existing_weeks else 0
        
        if max_existing >= weeks:
            print(f"\n⚠️  Weeks 1-{weeks} already simulated (max existing: {max_existing})")
            print(f"   To re-simulate, run clean_temporal_data.py first")
            print(f"   Or specify more weeks (e.g., {max_existing + 1}+)")
            return
        
        start_week = max_existing + 1
        
        print(f"\n{'='*80}")
        print(f"🎮 BEER GAME SIMULATION - WEEKS {start_week} TO {weeks}")
        if start_week > 1:
            print(f"   Resuming from Week {start_week} (Weeks 1-{max_existing} already exist)")
        print(f"   Demand Pattern: {demand_pattern}")
        print(f"{'='*80}")
        
        for week in range(start_week, weeks + 1):
            result = self.simulate_week(week, demand_pattern)
            result['demand_pattern'] = demand_pattern  # Add pattern to result
            self.results.append(result)
            
            if week < weeks:
                time.sleep(1)
        
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final simulation report with rich data"""
        print(f"\n{'='*80}")
        print("📈 FINAL SIMULATION REPORT")
        print(f"{'='*80}")
        
        if not self.results:
            print("No results to report")
            return
        
        print(f"\nTotal weeks simulated: {len(self.results)}")
        
        # Calculate total costs
        print("\n💰 TOTAL COSTS:")
        final_costs = {}
        for actor_name in self.supply_chain.keys():
            final_week = self.results[-1]
            if actor_name in final_week['summary']:
                cost = final_week['summary'][actor_name]['total_cost']
                final_costs[actor_name] = cost
                print(f"   {actor_name}: ${cost:.2f}")
        
        print(f"\n{'='*80}")
        
        # Save JSON report with rich structure
        import json
        from datetime import datetime
        
        # Build detailed weekly data
        weekly_details = []
        for result in self.results:
            week_data = {
                "week": result['week'],
                "demand": result['demand'],
                "actors": {}
            }
            
            for actor_name, actor_summary in result['summary'].items():
                week_data["actors"][actor_name] = {
                    "inventory": actor_summary['inventory'],
                    "backlog": actor_summary['backlog'],
                    "coverage": actor_summary['coverage'],
                    "suggested_order": actor_summary['suggested_order'],
                    "total_cost": actor_summary['total_cost']
                }
            
            weekly_details.append(week_data)
        
        report = {
            "metadata": {
                "simulation_date": datetime.now().isoformat(),
                "weeks_simulated": len(self.results),
                "demand_pattern": self.results[0].get('demand_pattern', 'unknown') if self.results else None,
                "supply_chain": {
                    actor: {
                        "uri": config['uri'],
                        "repository": config['repo']
                    }
                    for actor, config in self.supply_chain.items()
                }
            },
            "simulation": {
                "weekly_results": weekly_details,
                "final_costs": final_costs,
                "total_cost": sum(final_costs.values())
            },
            "performance": {
                "retailer_service_level": self._calculate_service_level("Retailer"),
                "average_inventory": self._calculate_avg_inventory(),
                "total_backlog": self._calculate_total_backlog()
            }
        }
        
        report_file = f"beer_game_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Could not save report: {e}")
    
    def _calculate_service_level(self, actor_name):
        """Calculate service level (weeks without backlog / total weeks)"""
        if not self.results:
            return 0.0
        
        weeks_without_backlog = sum(
            1 for r in self.results 
            if actor_name in r['summary'] and r['summary'][actor_name]['backlog'] == 0
        )
        return weeks_without_backlog / len(self.results)
    
    def _calculate_avg_inventory(self):
        """Calculate average inventory across all actors and weeks"""
        if not self.results:
            return 0.0
        
        total_inv = 0
        count = 0
        for result in self.results:
            for actor_summary in result['summary'].values():
                total_inv += actor_summary['inventory']
                count += 1
        
        return total_inv / count if count > 0 else 0.0
    
    def _calculate_total_backlog(self):
        """Calculate total backlog across all actors in final week"""
        if not self.results:
            return 0
        
        final_week = self.results[-1]
        return sum(
            actor_summary['backlog'] 
            for actor_summary in final_week['summary'].values()
        )


def main():
    """Interactive simulation"""
    print("🎯 BEER GAME ORCHESTRATOR (Clean Architecture)")
    print("=" * 80)
    print("Architecture:")
    print("  • Orchestrator: Events + Time (this file)")
    print("  • Rules Engine: Logic + Decisions (SPARQL)")
    print("=" * 80 + "\n")
    
    orchestrator = BeerGameOrchestrator()
    
    # Interactive menu
    print("Choose demand pattern:")
    print("  1. Stable (constant 4 units)")
    print("  2. Spike (12 units at week 3)")
    print("  3. Increasing (gradual growth)")
    print("  4. Random (2-8 units)")
    
    choice = input("\nEnter choice (1-4, default=1): ").strip() or "1"
    
    patterns = {
        "1": "stable",
        "2": "spike",
        "3": "increasing",
        "4": "random"
    }
    pattern = patterns.get(choice, "stable")
    
    weeks = int(input("Number of weeks (default=4): ").strip() or "4")
    
    # Run simulation
    orchestrator.run_simulation(weeks=weeks, demand_pattern=pattern)
    
    print("\n✅ Simulation complete!")


if __name__ == "__main__":
    main()
