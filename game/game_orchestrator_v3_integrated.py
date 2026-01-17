"""
Game Orchestrator - V3 Integration

Connects the V4 Player System with V3 temporal rules.
This orchestrator:
- Uses V3's temporal_beer_game_rules_v3.py for platform logic
- Allows Players (Algorithmic, AI, Human) to make decisions
- Coordinates the complete weekly cycle
"""

import sys
import os
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Any

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import V3 rule executor
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'SWRL_Rules'))
from temporal_beer_game_rules_v3 import TemporalBeerGameRuleExecutor

# Import players
from players.base_player import Player


class GameOrchestratorV3:
    """
    Game Orchestrator integrated with V3 temporal rules.
    
    Coordinates:
        1. V3 platform rules (SPARQL)
        2. Player decisions (Algorithmic/AI/Human)
        3. Week-by-week simulation cycle
    """
    
    def __init__(self, 
                 players: Dict[str, Player],
                 graphdb_url: str = "http://localhost:7200",
                 demand_pattern: str = "spike"):
        """
        Initialize orchestrator.
        
        Args:
            players: Dict mapping role to Player instance
            graphdb_url: GraphDB base URL
            demand_pattern: Customer demand pattern
        """
        self.players = players
        self.graphdb_url = graphdb_url
        self.demand_pattern = demand_pattern
        self.session = requests.Session()
        
        # Initialize V3 rule executor
        self.rule_executor = TemporalBeerGameRuleExecutor(graphdb_url)
        
        # Supply chain configuration (from V3)
        self.supply_chain = {
            "Retailer": {
                "repo": "BG_Retailer",
                "uri": "http://beergame.org/retailer#Retailer_Alpha",
                "namespace": "bg_retailer",
                "upstream_actor": "Wholesaler",
                "upstream_uri": "http://beergame.org/wholesaler#Wholesaler_Beta"
            },
            "Wholesaler": {
                "repo": "BG_Wholesaler",
                "uri": "http://beergame.org/wholesaler#Wholesaler_Beta",
                "namespace": "bg_wholesaler",
                "upstream_actor": "Distributor",
                "upstream_uri": "http://beergame.org/distributor#Distributor_Gamma"
            },
            "Distributor": {
                "repo": "BG_Distributor",
                "uri": "http://beergame.org/distributor#Distributor_Gamma",
                "namespace": "bg_distributor",
                "upstream_actor": "Factory",
                "upstream_uri": "http://beergame.org/factory#Factory_Delta"
            },
            "Factory": {
                "repo": "BG_Factory",
                "uri": "http://beergame.org/factory#Factory_Delta",
                "namespace": "bg_factory",
                "upstream_actor": None,
                "upstream_uri": None
            }
        }
        
        # Results storage
        self.week_results: List[Dict[str, Any]] = []
        self.player_decisions: Dict[str, List[Dict[str, Any]]] = {
            role: [] for role in players.keys()
        }
    
    def simulate_weeks(self, start_week: int, num_weeks: int) -> Dict[str, Any]:
        """
        Run complete multi-week simulation.
        
        Args:
            start_week: Starting week number
            num_weeks: Number of weeks to simulate
        
        Returns:
            Complete simulation report
        """
        print(f"\n{'='*70}")
        print(f"🎮 BEER GAME SIMULATION (V4 Players + V3 Rules)")
        print(f"{'='*70}")
        print(f"Players:")
        for role, player in self.players.items():
            print(f"  • {role}: {player.get_player_type()}")
        print(f"Weeks: {start_week} → {start_week + num_weeks - 1}")
        print(f"Demand pattern: {self.demand_pattern}")
        print(f"{'='*70}\n")
        
        for week in range(start_week, start_week + num_weeks):
            print(f"\n{'#'*70}")
            print(f"📅 WEEK {week}")
            print(f"{'#'*70}")
            
            week_result = self.simulate_week(week)
            self.week_results.append(week_result)
            
            time.sleep(0.5)  # Brief pause
        
        # Generate report
        report = self._generate_report(start_week, num_weeks)
        self._save_report(report)
        
        return report
    
    def simulate_week(self, week: int) -> Dict[str, Any]:
        """
        Simulate one complete week.
        
        Sequence:
            1. Create week entities
            2. Generate customer demand
            3. Execute V3 pre-decision rules
            4. Players make decisions
            5. Execute V3 post-decision rules
            6. Collect summary
        
        Args:
            week: Week number
        
        Returns:
            Week summary dictionary
        """
        result = {
            "week": week,
            "timestamp": datetime.now().isoformat(),
            "phases": {}
        }
        
        # PHASE 1: Create week entities
        print(f"\n→ Phase 1: Creating week entities...")
        self._create_week_entities(week)
        result["phases"]["week_created"] = True
        
        # PHASE 2: Generate customer demand
        print(f"\n→ Phase 2: Generating customer demand...")
        demand = self._generate_customer_demand(week)
        result["phases"]["demand"] = demand
        print(f"   Customer demand: {demand} units")
        
        # PHASE 3: Execute V3 pre-decision rules
        print(f"\n→ Phase 3: Executing V3 platform rules (pre-decision)...")
        self._execute_v3_rules_pre(week)
        result["phases"]["rules_pre"] = "executed"
        
        # PHASE 4: Players make decisions
        print(f"\n→ Phase 4: Players making decisions...")
        decisions = self._execute_player_turns(week)
        result["phases"]["player_decisions"] = decisions
        
        # PHASE 5: Execute V3 post-decision rules
        print(f"\n→ Phase 5: Executing V3 platform rules (post-decision)...")
        self._execute_v3_rules_post(week)
        result["phases"]["rules_post"] = "executed"
        
        # PHASE 6: Collect summary
        print(f"\n→ Phase 6: Collecting week summary...")
        summary = self._collect_week_summary(week)
        result["summary"] = summary
        
        self._print_week_summary(week, summary)
        
        return result
    
    def _create_week_entities(self, week: int):
        """
        Create Week_N entities in all repositories.
        Uses V3's create_week_entity method.
        """
        self.rule_executor.create_week_entity(week)
        
        # Also create ActorMetrics and Inventory snapshots
        self.rule_executor.create_actor_metrics_snapshot(week)
        self.rule_executor.create_inventory_snapshot(week)
    
    def _generate_customer_demand(self, week: int) -> int:
        """
        Generate customer demand and insert into Retailer repo.
        
        Returns:
            Demand quantity
        """
        # Generate demand based on pattern
        if self.demand_pattern == "spike":
            demand = 12 if week == 3 else 4
        elif self.demand_pattern == "stable":
            demand = 4
        elif self.demand_pattern == "increasing":
            demand = 4 + week
        else:  # random
            import random
            demand = random.randint(2, 8)
        
        # Insert into Retailer repo
        insert_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            INSERT DATA {{
                bg:CustomerDemand_W{week} a bg:CustomerDemand ;
                    bg:forWeek bg:Week_{week} ;
                    bg:belongsTo bg_retailer:Retailer_Alpha ;
                    bg:actualDemand "{demand}"^^xsd:integer .
            }}
        """
        
        endpoint = f"{self.graphdb_url}/repositories/BG_Retailer/statements"
        try:
            self.session.post(
                endpoint,
                data=insert_query,
                headers={"Content-Type": "application/sparql-update"}
            )
        except Exception as e:
            print(f"   ⚠️  Error creating customer demand: {e}")
        
        return demand
    
    def _execute_v3_rules_pre(self, week: int):
        """
        Execute V3 rules BEFORE player decisions.
        
        Rules:
            - DEMAND RATE SMOOTHING (with federation)
            - UPDATE INVENTORY (with federation)
            - INVENTORY COVERAGE
            - STOCKOUT RISK DETECTION
        """
        try:
            # V3 has specialized methods for federated rules
            
            # DEMAND RATE SMOOTHING (with federated demand queries)
            self.rule_executor.execute_demand_rate_smoothing_with_federation(week)
            
            # UPDATE INVENTORY (with federated shipment queries)
            self.rule_executor.execute_inventory_update_with_federation(week)
            
            # Other pre-decision rules
            for rule_name in ["INVENTORY COVERAGE CALCULATION", "STOCKOUT RISK DETECTION"]:
                for repo in self.rule_executor.repositories.values():
                    self.rule_executor.execute_rule(rule_name, repo)
            
            print(f"   ✓ Pre-decision rules executed")
            
        except Exception as e:
            print(f"   ⚠️  Pre-decision rules failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _execute_player_turns(self, week: int) -> Dict[str, int]:
        """
        Execute player turns in supply chain order.
        
        Returns:
            Dictionary of decisions by role
        """
        decisions = {}
        role_order = ['Retailer', 'Wholesaler', 'Distributor', 'Factory']
        
        for role in role_order:
            if role in self.players:
                player = self.players[role]
                
                print(f"\n   🎮 {role}'s turn ({player.get_player_type()})")
                
                try:
                    decision_log = player.play_turn(week)
                    self.player_decisions[role].append(decision_log)
                    decisions[role] = decision_log['decision']
                    
                    print(f"      ✓ Ordered: {decision_log['decision']} units")
                    
                    if decision_log.get('reasoning'):
                        reason = decision_log['reasoning']
                        if len(reason) > 100:
                            reason = reason[:100] + "..."
                        print(f"      💭 {reason}")
                        
                except Exception as e:
                    print(f"      ⚠️  Error: {e}")
                    decisions[role] = 0
        
        return decisions
    
    def _execute_v3_rules_post(self, week: int):
        """
        Execute V3 rules AFTER player decisions.
        
        Rules:
            - ORDER-UP-TO POLICY (for comparison with player decisions)
            - CREATE ORDERS FROM SUGGESTED (creates Order entities)
            - CREATE SHIPMENTS (with federation)
            - BULLWHIP DETECTION
            - TOTAL COST CALCULATION
        """
        try:
            # ORDER-UP-TO POLICY (calculates suggested orders for comparison)
            for repo in self.rule_executor.repositories.values():
                self.rule_executor.execute_rule("ORDER-UP-TO POLICY", repo)
            
            # CREATE ORDERS FROM SUGGESTED
            # Note: This creates orders based on suggestedOrderQuantity
            # Players have already created their orders via play_turn()
            # This rule can be used for comparison or as fallback
            for repo in self.rule_executor.repositories.values():
                self.rule_executor.execute_rule("CREATE ORDERS FROM SUGGESTED", repo)
            
            # CREATE SHIPMENTS (with federated order queries)
            # V3 uses federated queries to find incoming orders
            actor_uris = {
                "BG_Retailer": "http://beergame.org/retailer#Retailer_Alpha",
                "BG_Wholesaler": "http://beergame.org/wholesaler#Wholesaler_Beta",
                "BG_Distributor": "http://beergame.org/distributor#Distributor_Gamma",
                "BG_Factory": "http://beergame.org/factory#Factory_Delta"
            }
            
            for actor_repo, actor_uri in actor_uris.items():
                # Query incoming orders (federated)
                orders = self.rule_executor.query_incoming_orders_federated(week, actor_uri, actor_repo)
                
                # Create shipments based on orders found
                if orders:
                    self.rule_executor.create_shipments_from_federated_orders(week, actor_uri, actor_repo, orders)
            
            # Analysis rules
            for rule_name in ["BULLWHIP DETECTION", "TOTAL COST CALCULATION"]:
                for repo in self.rule_executor.repositories.values():
                    self.rule_executor.execute_rule(rule_name, repo)
            
            print(f"   ✓ Post-decision rules executed")
            
        except Exception as e:
            print(f"   ⚠️  Post-decision rules failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _collect_week_summary(self, week: int) -> Dict[str, Any]:
        """
        Query GraphDB for week summary.
        
        Returns:
            Summary with metrics for all actors
        """
        summary = {"week": week, "actors": {}}
        
        # Namespace mapping for each repository
        namespace_map = {
            "BG_Retailer": "bg_retailer",
            "BG_Wholesaler": "bg_wholesaler",
            "BG_Distributor": "bg_distributor",
            "BG_Factory": "bg_factory"
        }
        
        # Actor name mapping
        actor_names = {
            "Retailer": "Retailer_Alpha",
            "Wholesaler": "Wholesaler_Beta",
            "Distributor": "Distributor_Gamma",
            "Factory": "Factory_Delta"
        }
        
        for role, config in self.supply_chain.items():
            repo = config["repo"]
            ns = namespace_map[repo]
            actor_name = actor_names[role]
            
            # Query with namespace prefix
            # Note: Uses flexible property names (both currentInventory and just inventory work)
            query = f"""
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX {ns}: <http://beergame.org/{ns.replace('bg_', '')}#>
                
                SELECT ?inventory ?backlog ?cost ?demandRate ?coverage
                WHERE {{
                    # Get inventory (flexible - try both property names)
                    ?inv a bg:Inventory ;
                         bg:forWeek bg:Week_{week} ;
                         bg:belongsTo {ns}:{actor_name} .
                    
                    # Try both currentInventory and inventory
                    OPTIONAL {{ ?inv bg:currentInventory ?inventory }}
                    
                    # Try both backlog property names
                    OPTIONAL {{ ?inv bg:backlog ?backlog }}
                    OPTIONAL {{ ?inv bg:currentBacklog ?backlog2 }}
                    BIND(COALESCE(?backlog, ?backlog2, 0) AS ?backlogFinal)
                    
                    # Get metrics
                    OPTIONAL {{
                        {ns}:{actor_name} bg:hasMetrics ?metrics .
                        ?metrics bg:forWeek bg:Week_{week} ;
                                 bg:demandRate ?demandRate ;
                                 bg:inventoryCoverage ?coverage .
                    }}
                    
                    # Get total cost
                    OPTIONAL {{
                        {ns}:{actor_name} bg:totalCost ?cost .
                    }}
                }}
            """
            
            endpoint = f"{self.graphdb_url}/repositories/{repo}"
            try:
                response = self.session.post(
                    endpoint,
                    data={"query": query},
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json().get("results", {}).get("bindings", [])
                    if results:
                        r = results[0]
                        summary["actors"][role] = {
                            "inventory": int(r.get('inventory', {}).get('value', 0)),
                            "backlog": int(r.get('backlogFinal', {}).get('value', 0)),
                            "cost": float(r.get('cost', {}).get('value', 0.0)),
                            "demand_rate": float(r.get('demandRate', {}).get('value', 0.0)),
                            "coverage": float(r.get('coverage', {}).get('value', 0.0))
                        }
                    else:
                        print(f"   ⚠️  No data found for {role} Week {week}")
                else:
                    print(f"   ⚠️  Query failed for {role}: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ⚠️  Error querying {role}: {e}")
        
        return summary
    
    def _print_week_summary(self, week: int, summary: Dict[str, Any]):
        """Print week summary to console."""
        print(f"\n   📊 Week {week} Summary:")
        
        for role, data in summary.get("actors", {}).items():
            print(f"\n      • {role}:")
            print(f"         Inventory: {data.get('inventory', 'N/A')} units")
            print(f"         Backlog: {data.get('backlog', 'N/A')} units")
            print(f"         Coverage: {data.get('coverage', 0.0):.1f} weeks")
            print(f"         Cost: ${data.get('cost', 0.0):.2f}")
    
    def _generate_report(self, start_week: int, num_weeks: int) -> Dict[str, Any]:
        """Generate complete simulation report."""
        total_cost = sum(
            actor_data.get('cost', 0.0)
            for week_result in self.week_results
            for actor_data in week_result.get('summary', {}).get('actors', {}).values()
        )
        
        report = {
            "simulation_info": {
                "start_week": start_week,
                "num_weeks": num_weeks,
                "demand_pattern": self.demand_pattern,
                "timestamp": datetime.now().isoformat()
            },
            "players": {
                role: player.get_player_type()
                for role, player in self.players.items()
            },
            "week_results": self.week_results,
            "player_decisions": self.player_decisions,
            "metrics": {
                "total_cost": total_cost
            }
        }
        
        return report
    
    def _save_report(self, report: Dict[str, Any]):
        """Save report to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"v4_simulation_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved: {filename}")


# Example usage
if __name__ == "__main__":
    from players.algorithmic_player import AlgorithmicPlayer
    
    # Create all algorithmic players (V3 baseline)
    players = {
        'Retailer': AlgorithmicPlayer(
            actor_uri="http://beergame.org/retailer#Retailer_Alpha",
            role="Retailer",
            kg_endpoint="BG_Retailer"
        ),
        'Wholesaler': AlgorithmicPlayer(
            actor_uri="http://beergame.org/wholesaler#Wholesaler_Beta",
            role="Wholesaler",
            kg_endpoint="BG_Wholesaler"
        ),
        'Distributor': AlgorithmicPlayer(
            actor_uri="http://beergame.org/distributor#Distributor_Gamma",
            role="Distributor",
            kg_endpoint="BG_Distributor"
        ),
        'Factory': AlgorithmicPlayer(
            actor_uri="http://beergame.org/factory#Factory_Delta",
            role="Factory",
            kg_endpoint="BG_Factory"
        )
    }
    
    # Create orchestrator
    orchestrator = GameOrchestratorV3(players, demand_pattern="spike")
    
    # Run simulation
    report = orchestrator.simulate_weeks(start_week=2, num_weeks=5)
    
    print(f"\n✅ Simulation complete!")
    print(f"Total cost: ${report['metrics']['total_cost']:.2f}")
