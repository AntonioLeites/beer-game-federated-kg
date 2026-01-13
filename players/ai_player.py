"""
AI Player Base Class

Abstract base for players powered by Large Language Models.
Provides common infrastructure for prompt generation, response parsing,
and decision logging with full audit trail.
"""

from abc import abstractmethod
from typing import Dict, Any, Tuple, Optional
from base_player import Player


class AIPlayer(Player):
    """
    Abstract base class for AI-powered players.
    
    Subclasses must implement:
        - _call_llm(): Interface to specific LLM (GPT, Claude, etc)
        - get_player_type(): Return model identifier
    
    Provides common functionality:
        - Prompt generation from structured KG data
        - Response parsing (ORDER: X | REASON: ...)
        - Decision audit trail with full reasoning
    """
    
    def __init__(self, 
                 actor_uri: str, 
                 role: str,
                 kg_endpoint: str,
                 api_key: Optional[str] = None,
                 model_name: Optional[str] = None,
                 base_url: str = "http://localhost:7200"):
        """
        Initialize AI player.
        
        Args:
            actor_uri: Actor URI
            role: Role name
            kg_endpoint: KG repository ID
            api_key: LLM API key (if required)
            model_name: Specific model version (e.g., "gpt-4", "claude-3-opus")
            base_url: GraphDB URL
        """
        super().__init__(actor_uri, role, kg_endpoint, base_url)
        self.api_key = api_key
        self.model_name = model_name
        self.last_reasoning = None  # Store latest reasoning for audit
    
    def decide(self, observation: Dict[str, Any]) -> int:
        """
        Make ordering decision using LLM reasoning.
        
        Args:
            observation: State observation from KG
        
        Returns:
            Order quantity (non-negative integer)
        """
        # 1. Build prompt from structured observation
        prompt = self._build_prompt(observation)
        
        # 2. Call LLM
        response = self._call_llm(prompt)
        
        # 3. Parse response
        order, reasoning = self._parse_response(response)
        
        # 4. Store reasoning for audit trail
        self.last_reasoning = reasoning
        
        # 5. Validate and return
        return max(0, int(order))
    
    def _build_prompt(self, observation: Dict[str, Any]) -> str:
        """
        Build LLM prompt from structured observation.
        
        The prompt provides:
            - Current state (inventory, backlog, demand_rate, incoming)
            - Historical context (last 5 weeks)
            - Risk alerts from platform rules
            - Decision constraints (costs, delays)
        
        Args:
            observation: Structured observation from KG
        
        Returns:
            Formatted prompt string
        """
        current = observation['current']
        history = observation['history']
        alerts = observation['alerts']
        
        # Build prompt
        prompt = f"""You are the {self.role} in a supply chain (Beer Distribution Game).

## CURRENT STATE (Week {current['week']}):
- Your inventory: {current['inventory']} units
- Your backlog: {current['backlog']} units
- Demand rate (exponentially smoothed): {current['demand_rate']:.1f} units/week
- Inventory coverage: {current['coverage']:.1f} weeks (Target: 3.0 weeks)
- Incoming shipments (arriving Week {current['week'] + 2}): {current['incoming']} units

## HISTORICAL CONTEXT (Last {len(history)} weeks):
"""
        
        # Add history table
        if history:
            prompt += "Week | Inventory | Backlog | Demand Rate | Coverage\n"
            prompt += "---- | --------- | ------- | ----------- | --------\n"
            for h in history:
                prompt += f"{h['week']:4d} | {h['inventory']:9d} | {h['backlog']:7d} | {h['demand_rate']:11.1f} | {h['coverage']:8.1f}\n"
        else:
            prompt += "(No historical data available)\n"
        
        # Add alerts
        if alerts:
            prompt += f"\n## RISK ALERTS:\n"
            for alert in alerts:
                if alert == "BULLWHIP_RISK":
                    prompt += "⚠️  BULLWHIP RISK: Demand variability detected (ratio > 1.3×)\n"
                elif alert == "STOCKOUT_RISK":
                    prompt += "⚠️  STOCKOUT RISK: Low inventory coverage (< 2 weeks)\n"
        
        # Add decision constraints
        prompt += f"""
## SUPPLY CHAIN CONTEXT:
- Your role: {self.role}
- Target inventory coverage: 3 weeks of demand
- Shipping delay: 2 weeks (orders arrive 2 weeks after placement)
- Holding cost: $0.50 per unit per week
- Backlog cost: $1.00 per unit per week (2× holding cost)

## YOUR TASK:
Decide how many units to order this week to minimize total costs while maintaining service.

Consider:
1. Current inventory vs target (3 weeks coverage)
2. Backlog that needs to be cleared
3. Incoming shipments arriving soon
4. Recent demand trends (increasing/decreasing?)
5. Risk alerts (if any)

## RESPONSE FORMAT:
Provide your decision in this exact format:

ORDER: <quantity>
REASON: <brief explanation in 2-3 sentences>

Example:
ORDER: 18
REASON: Demand rate increased to 8.8 units/week, requiring target inventory of 26.4 units. Current inventory (16) plus incoming shipments (4) falls short. Ordering 18 units will restore adequate coverage and clear any backlog.

Your response:
"""
        
        return prompt
    
    @abstractmethod
    def _call_llm(self, prompt: str) -> str:
        """
        Call specific LLM API.
        
        Subclasses must implement this to interface with:
            - OpenAI (GPT-4, GPT-5)
            - Anthropic (Claude)
            - Google (Gemini)
            - Meta (Llama)
            - etc.
        
        Args:
            prompt: Formatted prompt string
        
        Returns:
            LLM response text
        """
        pass
    
    def _parse_response(self, response: str) -> Tuple[int, str]:
        """
        Parse LLM response to extract order quantity and reasoning.
        
        Expected format:
            ORDER: 18
            REASON: Brief explanation...
        
        Args:
            response: Raw LLM response
        
        Returns:
            Tuple of (order_quantity, reasoning)
        """
        try:
            # Split by lines
            lines = response.strip().split('\n')
            
            order = None
            reason_lines = []
            
            for line in lines:
                line = line.strip()
                
                # Extract ORDER
                if line.upper().startswith('ORDER:'):
                    order_str = line.split(':', 1)[1].strip()
                    # Extract number (handle cases like "ORDER: 18 units")
                    import re
                    match = re.search(r'\d+', order_str)
                    if match:
                        order = int(match.group())
                
                # Extract REASON
                elif line.upper().startswith('REASON:'):
                    reason_text = line.split(':', 1)[1].strip()
                    reason_lines.append(reason_text)
                elif reason_lines:  # Continuation of reason
                    reason_lines.append(line)
            
            # Validate
            if order is None:
                print(f"⚠️  Failed to parse ORDER from response, defaulting to 0")
                order = 0
            
            reasoning = ' '.join(reason_lines) if reason_lines else "No reasoning provided"
            
            return order, reasoning
            
        except Exception as e:
            print(f"⚠️  Error parsing response: {e}")
            print(f"    Raw response: {response[:200]}...")
            return 0, f"Parse error: {str(e)}"
    
    def get_last_reasoning(self) -> Optional[str]:
        """
        Get reasoning for last decision.
        
        Returns:
            Reasoning string from LLM or None
        """
        return self.last_reasoning
    
    def get_prompt_for_last_decision(self) -> Optional[str]:
        """
        Get the full prompt used for last decision (for debugging/audit).
        
        Returns:
            Prompt string or None
        """
        if not self.decision_history:
            return None
        
        last = self.decision_history[-1]
        observation = last['observation']
        return self._build_prompt(observation)
