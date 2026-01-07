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
        
        # Step 1: Create temporal structure
        print(f"\n🏗️  Creating temporal structure...")
        self.rule_executor.create_week_entity(week)
        self.rule_executor.create_actor_metrics_snapshot(week)
        if week > 1:
            self.rule_executor.create_inventory_snapshot(week)
        
        # Step 2: Generate external event
        demand = self.generate_customer_demand(week, demand_pattern)
        
        # Step 3: Execute business rules (ALL LOGIC HERE)
        print(f"\n   Executing business rules...")
        repos = [config['repo'] for config in self.supply_chain.values()]
        self.rule_executor.execute_week_rules(week, repos)
        
        # Step 4: Read results
        summary = self.get_week_summary(week)
        
        return {
            "week": week,
            "demand": demand,
            "summary": summary
        }
    
    def run_simulation(self, weeks=4, demand_pattern="stable"):
        """Run multi-week simulation"""
        print(f"\n{'='*80}")
        print(f"🎮 BEER GAME SIMULATION - {weeks} WEEKS")
        print(f"   Demand Pattern: {demand_pattern}")
        print(f"{'='*80}")
        
        for week in range(1, weeks + 1):
            result = self.simulate_week(week, demand_pattern)
            result['demand_pattern'] = demand_pattern  # Add pattern to result
            self.results.append(result)
            
            if week < weeks:
                time.sleep(1)
        
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final simulation report"""
        print(f"\n{'='*80}")
        print("📈 FINAL SIMULATION REPORT")
        print(f"{'='*80}")
        
        if not self.results:
            print("No results to report")
            return
        
        print(f"\nTotal weeks simulated: {len(self.results)}")
        
        # Calculate total costs
        print("\n💰 TOTAL COSTS:")
        for actor_name in self.supply_chain.keys():
            final_week = self.results[-1]
            if actor_name in final_week['summary']:
                cost = final_week['summary'][actor_name]['total_cost']
                print(f"   {actor_name}: ${cost:.2f}")
        
        print(f"\n{'='*80}")
        
        # Save JSON report
        import json
        from datetime import datetime
        
        report = {
            "simulation_date": datetime.now().isoformat(),
            "weeks_simulated": len(self.results),
            "demand_pattern": self.results[0].get('demand_pattern', 'unknown') if self.results else None,
            "weeks": self.results,
            "final_costs": {
                actor_name: self.results[-1]['summary'][actor_name]['total_cost']
                for actor_name in self.supply_chain.keys()
                if actor_name in self.results[-1]['summary']
            } if self.results else {}
        }
        
        report_file = f"beer_game_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Could not save report: {e}")


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
