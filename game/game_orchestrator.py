"""
Game Orchestrator

Coordinates multi-player Beer Game simulations.
Handles turn-taking, rule execution, and result collection.
"""

from typing import Dict, List, Any
from base_player import Player
import requests
import json
from datetime import datetime


class GameOrchestrator:
    """
    Orchestrates Beer Game with mixed player types.
    
    Responsibilities:
        - Initialize week entities
        - Execute platform rules (SPARQL)
        - Coordinate player turns
        - Collect and analyze results
    """
    
    def __init__(self, 
                 players: Dict[str, Player],
                 base_url: str = "http://localhost:7200",
                 demand_pattern: str = "spike"):
        """
        Initialize game orchestrator.
        
        Args:
            players: Dictionary mapping role → Player instance
                     e.g., {'Retailer': GPT4Player(...), 'Wholesaler': AlgorithmicPlayer(...)}
            base_url: GraphDB base URL
            demand_pattern: Customer demand pattern ('stable', 'spike', 'increasing', 'random')
        """
        self.players = players
        self.base_url = base_url
        self.demand_pattern = demand_pattern
        self.session = requests.Session()
        
        # Results storage
        self.week_summaries: List[Dict[str, Any]] = []
        self.player_decisions: Dict[str, List[Dict[str, Any]]] = {
            role: [] for role in players.keys()
        }
    
    def simulate_weeks(self, start_week: int, num_weeks: int) -> Dict[str, Any]:
        """
        Simulate multiple weeks of the Beer Game.
        
        Args:
            start_week: Starting week number
            num_weeks: Number of weeks to simulate
        
        Returns:
            Dictionary with simulation results:
                - week_summaries: List of per-week summaries
                - player_decisions: All decisions by role
                - metrics: Aggregate performance metrics
        """
        print(f"\n{'='*70}")
        print(f"🎮 STARTING MULTI-PLAYER SIMULATION")
        print(f"{'='*70}")
        print(f"Players:")
        for role, player in self.players.items():
            print(f"  • {role}: {player.get_player_type()}")
        print(f"Weeks: {start_week} → {start_week + num_weeks - 1}")
        print(f"Demand pattern: {self.demand_pattern}")
        print(f"{'='*70}\n")
        
        for week in range(start_week, start_week + num_weeks):
            print(f"\n📅 WEEK {week}")
            print(f"{'-'*70}")
            
            summary = self.simulate_week(week)
            self.week_summaries.append(summary)
        
        # Calculate aggregate metrics
        metrics = self._calculate_metrics()
        
        # Generate report
        report = {
            'simulation_start': datetime.now().isoformat(),
            'demand_pattern': self.demand_pattern,
            'weeks': list(range(start_week, start_week + num_weeks)),
            'players': {role: player.get_player_type() for role, player in self.players.items()},
            'week_summaries': self.week_summaries,
            'player_decisions': self.player_decisions,
            'metrics': metrics
        }
        
        # Save report
        self._save_report(report)
        
        return report
    
    def simulate_week(self, week: int) -> Dict[str, Any]:
        """
        Simulate one week.
        
        Sequence:
            1. Create week entities
            2. Generate customer demand
            3. Execute platform rules (pre-decision)
            4. Players make decisions
            5. Execute platform rules (post-decision)
            6. Collect summary
        
        Args:
            week: Week number
        
        Returns:
            Week summary dictionary
        """
        # 1. Create week entity
        self._create_week_entity(week)
        
        # 2. Generate customer demand
        demand = self._generate_customer_demand(week)
        print(f"   📊 Customer demand: {demand} units")
        
        # 3. Execute pre-decision platform rules
        self._execute_platform_rules_pre(week)
        
        # 4. Players make decisions (in supply chain order)
        role_order = ['Retailer', 'Wholesaler', 'Distributor', 'Factory']
        
        for role in role_order:
            if role in self.players:
                player = self.players[role]
                print(f"\n   🎮 {role}'s turn ({player.get_player_type()})")
                
                decision_log = player.play_turn(week)
                self.player_decisions[role].append(decision_log)
                
                print(f"      ✓ Ordered: {decision_log['decision']} units")
                if decision_log.get('reasoning'):
                    # Truncate reasoning for display
                    reason = decision_log['reasoning']
                    if len(reason) > 100:
                        reason = reason[:100] + "..."
                    print(f"      💭 Reasoning: {reason}")
        
        # 5. Execute post-decision platform rules
        self._execute_platform_rules_post(week)
        
        # 6. Collect summary
        summary = self._collect_week_summary(week)
        
        print(f"\n   📊 Week {week} Complete:")
        for role in role_order:
            if role in summary['actors']:
                actor_data = summary['actors'][role]
                print(f"      • {role}: Inv={actor_data.get('inventory', 'N/A')}, "
                      f"Backlog={actor_data.get('backlog', 'N/A')}, "
                      f"Cost=${actor_data.get('cost', 'N/A'):.2f}")
        
        return summary
    
    def _create_week_entity(self, week: int):
        """Create Week_N entity in all repositories."""
        # Implementation would call temporal_beer_game_rules_v3.py methods
        # For now, placeholder
        pass
    
    def _generate_customer_demand(self, week: int) -> int:
        """Generate customer demand for this week."""
        # Implement demand patterns
        if self.demand_pattern == "spike":
            return 12 if week == 3 else 4
        elif self.demand_pattern == "stable":
            return 4
        elif self.demand_pattern == "increasing":
            return 4 + week
        else:  # random
            import random
            return random.randint(2, 8)
    
    def _execute_platform_rules_pre(self, week: int):
        """Execute platform rules before player decisions."""
        # DEMAND RATE SMOOTHING
        # UPDATE INVENTORY
        # INVENTORY COVERAGE
        # STOCKOUT RISK DETECTION
        pass
    
    def _execute_platform_rules_post(self, week: int):
        """Execute platform rules after player decisions."""
        # CREATE SHIPMENTS
        # BULLWHIP DETECTION
        # TOTAL COST CALCULATION
        pass
    
    def _collect_week_summary(self, week: int) -> Dict[str, Any]:
        """Collect week summary from all actors."""
        # Query KG for week summary
        # Return structured data
        return {
            'week': week,
            'actors': {
                role: {'inventory': 0, 'backlog': 0, 'cost': 0.0}
                for role in self.players.keys()
            }
        }
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate performance metrics."""
        metrics = {
            'total_cost': 0.0,
            'total_backlog': 0,
            'bullwhip_events': 0,
            'stockout_events': 0
        }
        
        # Aggregate from week summaries
        for summary in self.week_summaries:
            for role, actor_data in summary['actors'].items():
                metrics['total_cost'] += actor_data.get('cost', 0.0)
                metrics['total_backlog'] += actor_data.get('backlog', 0)
        
        return metrics
    
    def _save_report(self, report: Dict[str, Any]):
        """Save simulation report to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"multi_player_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved: {filename}")


# Example usage
if __name__ == "__main__":
    from algorithmic_player import AlgorithmicPlayer
    from gpt4_player import GPT4Player
    import os
    
    # Setup players
    players = {
        'Retailer': AlgorithmicPlayer(
            actor_uri="http://beergame.org/retailer#Retailer_Alpha",
            role="Retailer",
            kg_endpoint="BG_Retailer"
        ),
        'Wholesaler': GPT4Player(
            actor_uri="http://beergame.org/wholesaler#Wholesaler_Beta",
            role="Wholesaler",
            kg_endpoint="BG_Wholesaler",
            api_key=os.getenv("OPENAI_API_KEY")
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
    orchestrator = GameOrchestrator(players, demand_pattern="spike")
    
    # Run simulation
    report = orchestrator.simulate_weeks(start_week=2, num_weeks=5)
    
    print(f"\n✅ Simulation complete!")
    print(f"Total cost: ${report['metrics']['total_cost']:.2f}")
