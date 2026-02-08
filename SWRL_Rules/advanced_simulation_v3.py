"""
Beer Game Simulation Orchestrator V3 (Federated Queries Architecture)

Design Philosophy:
- Orchestrator ONLY generates external events (customer demand)
- Orchestrator creates temporal anchors (Week entities)
- ALL business logic is delegated to SPARQL rules
- Orchestrator reads results computed by rules

V3 KEY CHANGES:
- ❌ REMOVED: propagate_orders_to_receivers() - No longer needed
- ❌ REMOVED: propagate_shipments_to_receivers() - No longer needed
- ✅ NEW: Uses BG_Supply_Chain federation for cross-repo visibility
- ✅ NEW: Queries are federated, writes are local (clean separation)

Separation of Concerns:
- This file: Events, Time, Orchestration
- temporal_beer_game_rules_v3.py: Logic, Decisions, Metrics (with federation)
"""

import requests
import random
import time
from temporal_beer_game_rules_v3 import TemporalBeerGameRuleExecutor


class BeerGameOrchestrator:
    """
    Orchestrates Beer Game simulation by:
    1. Creating temporal structure (Week entities)
    2. Generating exogenous events (customer demand)
    3. Executing business rules (V3: with federated queries)
    4. Reporting results
    
    Does NOT:
    - Calculate inventory
    - Make ordering decisions
    - Compute metrics
    - Create shipments/orders (rules do this)
    - Propagate data manually (federation handles it)
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
            if response.status_code == 204:
                return True
            else:
                print(f"      ✗ Update failed: HTTP {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"      ✗ Update exception: {e}")
            import traceback
            traceback.print_exc()
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
        elif demand_pattern == "oscillating":
            demand = 8 if week % 2 == 0 else 4
        elif demand_pattern == "increasing":
            demand = 4 + (week - 1)
        elif demand_pattern == "random":
            demand = random.randint(2, 8)
        else:
            demand = 4
        
        # Create CustomerDemand entity (only for Retailer)
        config = self.supply_chain["Retailer"]
        
        # Use DELETE+INSERT to ensure correct demand value (idempotent)
        update = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX {config['namespace']}: <http://beergame.org/{config['namespace'].replace('bg_', '')}#>
            
            DELETE {{
                {config['namespace']}:CustomerDemand_Week{week} bg:actualDemand ?oldDemand ;
                                                                   rdfs:comment ?oldComment .
            }}
            INSERT {{
                {config['namespace']}:CustomerDemand_Week{week} a bg:CustomerDemand ;
                    bg:forWeek bg:Week_{week} ;
                    bg:belongsTo <{config['uri']}> ;
                    bg:actualDemand "{demand}"^^xsd:integer ;
                    rdfs:comment "Customer demand for Week {week}" .
            }}
            WHERE {{
                OPTIONAL {{
                    {config['namespace']}:CustomerDemand_Week{week} bg:actualDemand ?oldDemand .
                }}
                OPTIONAL {{
                    {config['namespace']}:CustomerDemand_Week{week} rdfs:comment ?oldComment .
                }}
            }}
        """
        
        self._execute_update(update, config['repo'])
        print(f"      Customer demand: {demand} units")
        
        # Verify it was created
        verify_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            SELECT ?demand
            WHERE {{
                ?entity a bg:CustomerDemand ;
                        bg:forWeek bg:Week_{week} ;
                        bg:actualDemand ?demand .
            }}
        """
        result = self._execute_query(verify_query, config['repo'])
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            actual = bindings[0]['demand']['value']
            print(f"      ✓ Verified in GraphDB: {actual} units")
        else:
            print(f"      ⚠️  WARNING: CustomerDemand not found in GraphDB!")
        
        return demand
    
    def get_week_summary(self, week):
        """Read results computed by rules - comprehensive metrics"""
        print(f"\n📊 WEEK {week} SUMMARY:")
        print("="*60)
        
        summary = {}
        
        for actor_name, config in self.supply_chain.items():
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?inv ?backlog ?coverage ?suggested ?cost 
                       ?demandRate ?bullwhip ?stockout
                       (COUNT(DISTINCT ?orderPlaced) as ?ordersPlaced)
                       (COUNT(DISTINCT ?orderReceived) as ?ordersReceived)
                       (COUNT(DISTINCT ?shipment) as ?shipmentsCreated)
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
                                 bg:suggestedOrderQuantity ?suggested ;
                                 bg:demandRate ?demandRate ;
                                 bg:hasBullwhipRisk ?bullwhip ;
                                 bg:hasStockoutRisk ?stockout .
                    }}
                    
                    # Get total cost
                    OPTIONAL {{
                        <{config['uri']}> bg:totalCost ?cost .
                    }}
                    
                    # Count orders PLACED by this actor (outgoing)
                    OPTIONAL {{
                        ?orderPlaced a bg:Order ;
                               bg:forWeek bg:Week_{week} ;
                               bg:placedBy <{config['uri']}> .
                    }}
                    
                    # Count orders RECEIVED by this actor (incoming/propagated)
                    OPTIONAL {{
                        ?orderReceived a bg:Order ;
                                       bg:forWeek bg:Week_{week} ;
                                       bg:receivedBy <{config['uri']}> .
                    }}
                    
                    # Count shipments sent this week
                    OPTIONAL {{
                        ?shipment a bg:Shipment ;
                                  bg:forWeek bg:Week_{week} ;
                                  bg:shippedFrom <{config['uri']}> .
                    }}
                }}
                GROUP BY ?inv ?backlog ?coverage ?suggested ?cost ?demandRate ?bullwhip ?stockout
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
                    "total_cost": float(b.get("cost", {}).get("value", 0.0)),
                    "demand_rate": float(b.get("demandRate", {}).get("value", 0.0)),
                    "bullwhip_risk": b.get("bullwhip", {}).get("value", "false").lower() == "true",
                    "stockout_risk": b.get("stockout", {}).get("value", "false").lower() == "true",
                    "orders_placed": int(b.get("ordersPlaced", {}).get("value", 0)),
                    "orders_received": int(b.get("ordersReceived", {}).get("value", 0)),
                    "shipments_created": int(b.get("shipmentsCreated", {}).get("value", 0))
                }
                summary[actor_name] = actor_data
                
                print(f"  {actor_name}:")
                print(f"    Inventory: {actor_data['inventory']}")
                print(f"    Backlog: {actor_data['backlog']}")
                print(f"    Coverage: {actor_data['coverage']:.1f} weeks")
                print(f"    Demand rate: {actor_data['demand_rate']:.1f}")
                print(f"    Suggested order: {actor_data['suggested_order']}")
                print(f"    Orders placed: {actor_data['orders_placed']} | received: {actor_data['orders_received']}")
                print(f"    Shipments created: {actor_data['shipments_created']}")
                
                # Show warnings
                if actor_data['bullwhip_risk']:
                    print(f"    ⚠️  BULLWHIP RISK DETECTED")
                if actor_data['stockout_risk']:
                    print(f"    ⚠️  STOCKOUT RISK DETECTED")
                    
                print(f"    Total cost: ${actor_data['total_cost']:.2f}")
        
        print("="*60)
        return summary
    
    # =========================================================================
    # V3: PROPAGATION METHODS REMOVED
    # =========================================================================
    # In V2, we manually propagated orders and shipments between repositories.
    # In V3, we use BG_Supply_Chain federation - queries automatically see
    # data across all repos without manual copying.
    #
    # REMOVED METHODS:
    # - propagate_orders_to_receivers() → Replaced by federated CREATE SHIPMENTS query
    # - propagate_shipments_to_receivers() → Replaced by federated UPDATE INVENTORY query
    #
    # This simplifies the codebase and improves performance (no data duplication).
    # =========================================================================
    
    def simulate_week(self, week, demand_pattern="stable"):
        """
        Orchestrate one week of simulation
        
        V3 CHANGES:
        - No manual propagation (federation handles cross-repo visibility)
        - Simpler flow: Create → Generate → Execute → Report
        
        Steps:
        1. Create temporal structure (Week entities, Metrics, Inventory)
        2. Generate exogenous event (customer demand)
        3. Execute business rules (V3: with federated queries)
        4. Read and report results
        """
        print(f"\n{'#'*80}")
        print(f"📅 WEEK {week} - SIMULATION (V3 - Federated)")
        print(f"{'#'*80}")
        
        # Step 1: Create temporal structure
        print(f"\n🏗️  Creating temporal structure...")
        self.rule_executor.create_week_entity(week)
        
        # Only create ActorMetrics for Week > 1 (Week 1 is in initial TTL)
        if week > 1:
            self.rule_executor.create_actor_metrics_snapshot(week)
            self.rule_executor.create_inventory_snapshot(week)
        
        # Step 2: Generate external event
        demand = self.generate_customer_demand(week, demand_pattern)
        
        # Step 3: Execute business rules (V3: includes federated queries)
        print(f"\n   Executing business rules (V3 - with federation)...")
        repos = [config['repo'] for config in self.supply_chain.values()]
        self.rule_executor.execute_week_rules(week, repos)
        
        # V3: No manual propagation needed!
        # - UPDATE INVENTORY queries BG_Supply_Chain for arriving shipments
        # - CREATE SHIPMENTS queries BG_Supply_Chain for incoming orders
        # - Federation handles visibility automatically
        
        # Step 4: Read results
        summary = self.get_week_summary(week)
        
        return {
            "week": week,
            "demand": demand,
            "summary": summary
        }
    
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
        # V3.1 NEW: Post-mortem analysis
        analyze_decision_outcomes(
            self.session, 
            weeks, 
            self.supply_chain,
            self.base_url
        )
        
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
                    "demand_rate": actor_summary['demand_rate'],
                    "suggested_order": actor_summary['suggested_order'],
                    "orders_placed": actor_summary['orders_placed'],
                    "orders_received": actor_summary['orders_received'],
                    "shipments_created": actor_summary['shipments_created'],
                    "bullwhip_risk": actor_summary['bullwhip_risk'],
                    "stockout_risk": actor_summary['stockout_risk'],
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
    print("  3. Oscillating (4 units, 8 units alternating)")
    print("  4. Increasing (gradual growth)")
    print("  5. Random (2-8 units)")

    
    choice = input("\nEnter choice (1-4, default=1): ").strip() or "1"
    
    patterns = {
        "1": "stable",
        "2": "spike",
        "3": "oscillating",
        "4": "increasing",
        "5": "random"
    }
    pattern = patterns.get(choice, "stable")
    
    weeks = int(input("Number of weeks (default=4): ").strip() or "4")
    
    # Run simulation
    orchestrator.run_simulation(weeks=weeks, demand_pattern=pattern)
    
    print("\n✅ Simulation complete!")


def analyze_decision_outcomes(session, total_weeks, supply_chain, base_url):
    """
    V3.1: Post-mortem analysis - Update DecisionContext with actual outcomes
    """
    print(f"\n{'='*70}")
    print(f"📊 POST-MORTEM ANALYSIS: Decision Outcomes")
    print(f"{'='*70}\n")
    
    contexts_analyzed = 0
    contexts_updated = 0
    
    for actor_name, config in supply_chain.items():
        repo = config['repo']
        actor_uri = config['uri']
        actor_ns = config['namespace']
        
        print(f"→ Analyzing {actor_name} decisions...")
        
        # Query all contexts for this actor
        list_contexts_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT ?context ?week
            WHERE {{
                ?context a bg:DecisionContext ;
                         bg:belongsTo <{actor_uri}> ;
                         bg:forWeek ?weekIRI .
                
                ?weekIRI bg:weekNumber ?week .
            }}
            ORDER BY ?week
        """
        
        try:
            response = session.post(
                f"{base_url}/repositories/{repo}",
                data={'query': list_contexts_query},
                headers={'Accept': 'application/sparql-results+json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                bindings = data.get('results', {}).get('bindings', [])
                
                if not bindings:
                    print(f"      (No contexts found)")
                    continue
                
                for binding in bindings:
                    week = int(binding['week']['value'])
                    context_uri = binding['context']['value']
                    contexts_analyzed += 1
                    
                    # Query outcome data
                    outcome_query = f"""
                        PREFIX bg: <http://beergame.org/ontology#>
                        
                        SELECT ?orderQty ?demandRate ?nextBacklog
                        WHERE {{
                            <{context_uri}> bg:capturesMetrics ?metrics .
                            ?metrics bg:demandRate ?demandRate .
                            
                            ?order bg:basedOnContext <{context_uri}> ;
                                   bg:orderQuantity ?orderQty .
                            
                            OPTIONAL {{
                                ?nextInv a bg:Inventory ;
                                         bg:belongsTo <{actor_uri}> ;
                                         bg:forWeek ?nextWeekIRI ;
                                         bg:backlog ?nextBacklog .
                                
                                ?nextWeekIRI bg:weekNumber ?nextWeekNum .
                                FILTER(?nextWeekNum = {week + 2})
                            }}
                        }}
                    """
                    
                    outcome_response = session.post(
                        f"{base_url}/repositories/{repo}",
                        data={'query': outcome_query},
                        headers={'Accept': 'application/sparql-results+json'},
                        timeout=10
                    )
                    
                    if outcome_response.status_code == 200:
                        outcome_data = outcome_response.json()
                        outcome_bindings = outcome_data.get('results', {}).get('bindings', [])
                        
                        if outcome_bindings:
                            outcome_binding = outcome_bindings[0]
                            order_qty = float(outcome_binding['orderQty']['value'])
                            demand_rate = float(outcome_binding['demandRate']['value'])
                            
                            # Determine if caused bullwhip
                            amplification = order_qty / max(demand_rate, 0.1)
                            caused_bullwhip = amplification > 1.5
                            
                            # Determine if caused stockout
                            caused_stockout = False
                            actual_outcome = "Insufficient data (no Week+2 inventory)"
                            quality = "unknown"
                            
                            if 'nextBacklog' in outcome_binding:
                                next_backlog = float(outcome_binding['nextBacklog']['value'])
                                caused_stockout = next_backlog > 0
                                
                                if next_backlog > 0:
                                    actual_outcome = f"Led to stockout of {next_backlog:.0f} units"
                                    quality = "poor"
                                elif amplification > 2.0:
                                    actual_outcome = f"Caused {amplification:.1f}x amplification"
                                    quality = "suboptimal"
                                elif amplification < 0.8:
                                    actual_outcome = "Conservative order, stable inventory"
                                    quality = "good"
                                else:
                                    actual_outcome = "Balanced order, maintained stability"
                                    quality = "optimal"
                            
                            # Update context with outcome
                            update_query = f"""
                                PREFIX bg: <http://beergame.org/ontology#>
                                
                                DELETE {{
                                    <{context_uri}> bg:actualOutcome ?oldOutcome ;
                                                    bg:outcomeQuality ?oldQuality ;
                                                    bg:causedBullwhip ?oldBullwhip ;
                                                    bg:causedStockout ?oldStockout .
                                }}
                                INSERT {{
                                    <{context_uri}> bg:actualOutcome "{actual_outcome.replace('"', '\\"')}" ;
                                                    bg:outcomeQuality "{quality}" ;
                                                    bg:causedBullwhip {str(caused_bullwhip).lower()} ;
                                                    bg:causedStockout {str(caused_stockout).lower()} .
                                }}
                                WHERE {{
                                    OPTIONAL {{ <{context_uri}> bg:actualOutcome ?oldOutcome }}
                                    OPTIONAL {{ <{context_uri}> bg:outcomeQuality ?oldQuality }}
                                    OPTIONAL {{ <{context_uri}> bg:causedBullwhip ?oldBullwhip }}
                                    OPTIONAL {{ <{context_uri}> bg:causedStockout ?oldStockout }}
                                }}
                            """
                            
                            update_response = session.post(
                                f"{base_url}/repositories/{repo}/statements",
                                data={'update': update_query},
                                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                timeout=10
                            )
                            
                            if update_response.status_code == 204:
                                print(f"      Week {week}: {quality} - {actual_outcome[:50]}...")
                                contexts_updated += 1
                            else:
                                print(f"      Week {week}: ✗ Update failed (HTTP {update_response.status_code})")
                        else:
                            print(f"      Week {week}: No outcome data found")
                    else:
                        print(f"      Week {week}: ✗ Query failed (HTTP {outcome_response.status_code})")
        
        except Exception as e:
            print(f"      ✗ Exception: {e}")
    
    print(f"\n✓ Post-mortem complete: {contexts_updated}/{contexts_analyzed} contexts updated\n")

if __name__ == "__main__":
    main()
