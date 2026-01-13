"""
Base Player Interface for Beer Distribution Game

This module defines the abstract interface that all player types must implement.
Players can be algorithmic policies, AI agents, or human interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import requests


class Player(ABC):
    """
    Abstract base class for all Beer Game players.
    
    Each player represents one actor in the supply chain:
    - Retailer
    - Wholesaler
    - Distributor
    - Factory
    
    Players observe structured state from the Knowledge Graph,
    make ordering decisions, and log their reasoning.
    """
    
    def __init__(self, 
                 actor_uri: str, 
                 role: str,
                 kg_endpoint: str,
                 base_url: str = "http://localhost:7200"):
        """
        Initialize player.
        
        Args:
            actor_uri: Full URI of this actor (e.g., "http://beergame.org/retailer#Retailer_Alpha")
            role: Human-readable role ("Retailer", "Wholesaler", "Distributor", "Factory")
            kg_endpoint: Repository ID for this actor's KG (e.g., "BG_Retailer")
            base_url: GraphDB base URL
        """
        self.actor_uri = actor_uri
        self.role = role
        self.kg_endpoint = kg_endpoint
        self.base_url = base_url
        self.session = requests.Session()
        
        # Decision history (for analysis)
        self.decision_history: List[Dict[str, Any]] = []
    
    # ==================== ABSTRACT METHODS ====================
    
    @abstractmethod
    def decide(self, observation: Dict[str, Any]) -> int:
        """
        Make ordering decision based on observed state.
        
        Args:
            observation: Dictionary containing:
                - current: Current week state (inventory, backlog, demand_rate, etc)
                - history: Historical data (last N weeks)
                - alerts: Risk alerts from platform rules
        
        Returns:
            Order quantity (non-negative integer)
        """
        pass
    
    @abstractmethod
    def get_player_type(self) -> str:
        """
        Return player type identifier.
        
        Returns:
            String like "algorithmic", "gpt4", "claude", "human"
        """
        pass
    
    # ==================== CONCRETE METHODS ====================
    
    def play_turn(self, week: int) -> Dict[str, Any]:
        """
        Execute one turn: observe, decide, act, log.
        
        Args:
            week: Current week number
        
        Returns:
            Dictionary with decision details:
                - week: Week number
                - decision: Order quantity
                - observation: What player observed
                - reasoning: Why player decided (if available)
                - timestamp: When decision was made
        """
        # 1. Observe current state
        observation = self.observe(week)
        
        # 2. Make decision
        decision = self.decide(observation)
        
        # 3. Validate decision
        decision = max(0, int(decision))  # Non-negative integer
        
        # 4. Create order in KG
        self.create_order(week, decision)
        
        # 5. Log decision
        log_entry = {
            'week': week,
            'decision': decision,
            'observation': observation,
            'reasoning': self.get_last_reasoning(),  # Subclass may override
            'player_type': self.get_player_type()
        }
        self.decision_history.append(log_entry)
        
        return log_entry
    
    def observe(self, week: int) -> Dict[str, Any]:
        """
        Query Knowledge Graph for current state.
        
        Returns:
            Dictionary with structured observation:
                - current: Current week state
                - history: Last 5 weeks
                - alerts: Risk alerts
        """
        current_state = self._query_current_state(week)
        history = self._query_history(week, lookback=5)
        alerts = self._query_alerts(week)
        
        return {
            'current': current_state,
            'history': history,
            'alerts': alerts
        }
    
    def _query_current_state(self, week: int) -> Dict[str, Any]:
        """Query current week state from local KG."""
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT ?inventory ?backlog ?demandRate ?coverage ?incoming
            WHERE {{
                # Current inventory and backlog
                ?inv a bg:Inventory ;
                     bg:forWeek bg:Week_{week} ;
                     bg:belongsTo <{self.actor_uri}> ;
                     bg:currentInventory ?inventory ;
                     bg:currentBacklog ?backlog .
                
                # Metrics (demand rate, coverage)
                ?metrics a bg:ActorMetrics ;
                         bg:forWeek bg:Week_{week} ;
                         bg:belongsTo <{self.actor_uri}> ;
                         bg:demandRate ?demandRate ;
                         bg:inventoryCoverage ?coverage .
                
                # Incoming shipments (arriving in 2 weeks)
                OPTIONAL {{
                    SELECT (SUM(?qty) as ?incoming)
                    WHERE {{
                        ?shipment a bg:Shipment ;
                                  bg:shippedTo <{self.actor_uri}> ;
                                  bg:arrivalWeek bg:Week_{week + 2} ;
                                  bg:shippedQuantity ?qty .
                    }}
                }}
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{self.kg_endpoint}"
        response = self.session.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"}
        )
        
        if response.status_code == 200:
            results = response.json().get("results", {}).get("bindings", [])
            if results:
                r = results[0]
                return {
                    'week': week,
                    'inventory': int(r['inventory']['value']),
                    'backlog': int(r['backlog']['value']),
                    'demand_rate': float(r['demandRate']['value']),
                    'coverage': float(r['coverage']['value']),
                    'incoming': int(r.get('incoming', {}).get('value', 0))
                }
        
        # Fallback
        return {
            'week': week,
            'inventory': 0,
            'backlog': 0,
            'demand_rate': 4.0,
            'coverage': 0.0,
            'incoming': 0
        }
    
    def _query_history(self, current_week: int, lookback: int = 5) -> List[Dict[str, Any]]:
        """Query historical data (last N weeks)."""
        history = []
        for week in range(max(1, current_week - lookback), current_week):
            state = self._query_current_state(week)
            history.append(state)
        return history
    
    def _query_alerts(self, week: int) -> List[str]:
        """Query risk alerts from platform rules."""
        query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT ?alert
            WHERE {{
                ?metrics a bg:ActorMetrics ;
                         bg:forWeek bg:Week_{week} ;
                         bg:belongsTo <{self.actor_uri}> .
                
                {{
                    ?metrics bg:hasBullwhipRisk true .
                    BIND("BULLWHIP_RISK" AS ?alert)
                }}
                UNION
                {{
                    ?metrics bg:hasStockoutRisk true .
                    BIND("STOCKOUT_RISK" AS ?alert)
                }}
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{self.kg_endpoint}"
        response = self.session.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"}
        )
        
        alerts = []
        if response.status_code == 200:
            results = response.json().get("results", {}).get("bindings", [])
            alerts = [r['alert']['value'] for r in results]
        
        return alerts
    
    def create_order(self, week: int, quantity: int):
        """
        Create order entity in Knowledge Graph.
        
        Args:
            week: Week number
            quantity: Order quantity (non-negative integer)
        """
        # Determine receiver based on role
        receiver_map = {
            'Retailer': 'http://beergame.org/wholesaler#Wholesaler_Beta',
            'Wholesaler': 'http://beergame.org/distributor#Distributor_Gamma',
            'Distributor': 'http://beergame.org/factory#Factory_Delta',
            'Factory': None  # Factory doesn't order from anyone
        }
        
        receiver = receiver_map.get(self.role)
        if not receiver or quantity == 0:
            return  # No order needed
        
        order_uri = f"{self.actor_uri}_Order_W{week}"
        
        insert_query = f"""
            PREFIX bg: <http://beergame.org/ontology#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            INSERT DATA {{
                <{order_uri}> a bg:Order ;
                    bg:forWeek bg:Week_{week} ;
                    bg:placedBy <{self.actor_uri}> ;
                    bg:receivedBy <{receiver}> ;
                    bg:orderQuantity "{quantity}"^^xsd:integer ;
                    bg:playerType "{self.get_player_type()}" .
            }}
        """
        
        endpoint = f"{self.base_url}/repositories/{self.kg_endpoint}/statements"
        self.session.post(
            endpoint,
            data=insert_query,
            headers={"Content-Type": "application/sparql-update"}
        )
    
    def get_last_reasoning(self) -> Optional[str]:
        """
        Get reasoning for last decision (if available).
        
        Subclasses that support reasoning should override this.
        
        Returns:
            Reasoning string or None
        """
        return None
    
    def get_decision_history(self) -> List[Dict[str, Any]]:
        """
        Get full decision history for this player.
        
        Returns:
            List of decision log entries
        """
        return self.decision_history
    
    def __repr__(self):
        return f"{self.__class__.__name__}(role='{self.role}', type='{self.get_player_type()}')"
