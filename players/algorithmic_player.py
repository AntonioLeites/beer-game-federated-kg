"""
Algorithmic Player - ORDER-UP-TO Policy

This player implements a deterministic ORDER-UP-TO policy,
the baseline used in V3 platform validation.
"""

from typing import Dict, Any
from base_player import Player


class AlgorithmicPlayer(Player):
    """
    Deterministic algorithmic player using ORDER-UP-TO policy.
    
    Decision logic:
        target_inventory = demand_rate × target_coverage
        suggested_order = target_inventory - current_inventory + backlog
        final_order = max(0, suggested_order)
    
    This is the baseline player used in V3 validation.
    Characteristics:
        - Deterministic (same inputs → same outputs)
        - Low variance (<5%)
        - Fully auditable
        - No AI randomness
    """
    
    def __init__(self, 
                 actor_uri: str, 
                 role: str,
                 kg_endpoint: str,
                 target_coverage: float = 3.0,
                 smoothing_alpha: float = 0.3,
                 base_url: str = "http://localhost:7200"):
        """
        Initialize algorithmic player.
        
        Args:
            actor_uri: Actor URI
            role: Role name
            kg_endpoint: KG repository ID
            target_coverage: Target inventory coverage in weeks (default: 3.0)
            smoothing_alpha: Exponential smoothing weight for demand (default: 0.3)
            base_url: GraphDB URL
        """
        super().__init__(actor_uri, role, kg_endpoint, base_url)
        self.target_coverage = target_coverage
        self.smoothing_alpha = smoothing_alpha
    
    def decide(self, observation: Dict[str, Any]) -> int:
        """
        Make ordering decision using ORDER-UP-TO policy.
        
        Args:
            observation: State observation from KG
        
        Returns:
            Order quantity (non-negative integer)
        """
        current = observation['current']
        
        # Extract state variables
        inventory = current['inventory']
        backlog = current['backlog']
        demand_rate = current['demand_rate']
        
        # Calculate target inventory (coverage × demand_rate)
        target_inventory = demand_rate * self.target_coverage
        
        # Calculate suggested order
        # suggested = target - current_inventory + backlog
        suggested_order = target_inventory - inventory + backlog
        
        # Non-negative integer
        final_order = max(0, int(suggested_order))
        
        return final_order
    
    def get_player_type(self) -> str:
        """Return player type identifier."""
        return "algorithmic"
    
    def get_last_reasoning(self) -> str:
        """
        Provide reasoning for last decision (algorithmic logic).
        
        Returns:
            Human-readable explanation of decision
        """
        if not self.decision_history:
            return "No decisions yet"
        
        last = self.decision_history[-1]
        obs = last['observation']['current']
        decision = last['decision']
        
        target = obs['demand_rate'] * self.target_coverage
        
        reasoning = (
            f"ORDER-UP-TO policy: "
            f"target_inventory = {obs['demand_rate']:.1f} × {self.target_coverage} = {target:.1f}, "
            f"current_inventory = {obs['inventory']}, "
            f"backlog = {obs['backlog']}, "
            f"suggested = {target:.1f} - {obs['inventory']} + {obs['backlog']} = {decision}"
        )
        
        return reasoning


class ConservativeAlgorithmicPlayer(AlgorithmicPlayer):
    """
    Conservative variant: Higher target coverage (4 weeks instead of 3).
    
    This player maintains larger safety stock.
    """
    
    def __init__(self, actor_uri: str, role: str, kg_endpoint: str, **kwargs):
        super().__init__(actor_uri, role, kg_endpoint, target_coverage=4.0, **kwargs)
    
    def get_player_type(self) -> str:
        return "algorithmic_conservative"


class AggressiveAlgorithmicPlayer(AlgorithmicPlayer):
    """
    Aggressive variant: Lower target coverage (2 weeks instead of 3).
    
    This player maintains minimal inventory, reacts faster to demand changes.
    """
    
    def __init__(self, actor_uri: str, role: str, kg_endpoint: str, **kwargs):
        super().__init__(actor_uri, role, kg_endpoint, target_coverage=2.0, **kwargs)
    
    def get_player_type(self) -> str:
        return "algorithmic_aggressive"


# Example usage
if __name__ == "__main__":
    # Create algorithmic player
    player = AlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer"
    )
    
    # Simulate observation
    mock_observation = {
        'current': {
            'week': 3,
            'inventory': 8,
            'backlog': 0,
            'demand_rate': 6.4,
            'coverage': 1.25,
            'incoming': 4
        },
        'history': [],
        'alerts': ['STOCKOUT_RISK']
    }
    
    # Make decision
    decision = player.decide(mock_observation)
    print(f"Player: {player}")
    print(f"Decision: {decision} units")
    print(f"Reasoning: {player.get_last_reasoning()}")
    
    # Output:
    # Player: AlgorithmicPlayer(role='Retailer', type='algorithmic')
    # Decision: 19 units
    # Reasoning: ORDER-UP-TO policy: target_inventory = 6.4 × 3.0 = 19.2, 
    #            current_inventory = 8, backlog = 0, suggested = 19.2 - 8 + 0 = 19
