"""
GPT-4 Player

AI player powered by OpenAI's GPT-4.
Requires: pip install openai
"""

from typing import Optional
from ai_player import AIPlayer


class GPT4Player(AIPlayer):
    """
    AI player powered by OpenAI GPT-4.
    
    Uses structured prompts built from Knowledge Graph data.
    Decisions are fully auditable with reasoning logged.
    
    Example usage:
        player = GPT4Player(
            actor_uri="http://beergame.org/retailer#Retailer_Alpha",
            role="Retailer",
            kg_endpoint="BG_Retailer",
            api_key="sk-...",
            model_name="gpt-4-turbo-preview"
        )
        
        decision_log = player.play_turn(week=3)
        print(f"Ordered: {decision_log['decision']} units")
        print(f"Reasoning: {decision_log['reasoning']}")
    """
    
    def __init__(self, 
                 actor_uri: str, 
                 role: str,
                 kg_endpoint: str,
                 api_key: str,
                 model_name: str = "gpt-4-turbo-preview",
                 temperature: float = 0.7,
                 max_tokens: int = 500,
                 base_url: str = "http://localhost:7200"):
        """
        Initialize GPT-4 player.
        
        Args:
            actor_uri: Actor URI
            role: Role name
            kg_endpoint: KG repository ID
            api_key: OpenAI API key
            model_name: GPT-4 model variant (default: "gpt-4-turbo-preview")
            temperature: Sampling temperature 0-1 (default: 0.7)
            max_tokens: Max response tokens (default: 500)
            base_url: GraphDB URL
        """
        super().__init__(actor_uri, role, kg_endpoint, api_key, model_name, base_url)
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai"
            )
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call OpenAI GPT-4 API.
        
        Args:
            prompt: Formatted prompt string
        
        Returns:
            GPT-4 response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert supply chain manager playing the Beer Distribution Game. "
                            "Your goal is to minimize total costs (holding + backlog) while maintaining "
                            "service levels. You make data-driven decisions based on structured information "
                            "from a Knowledge Graph. Always provide clear reasoning for your decisions."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️  GPT-4 API error: {e}")
            # Fallback to conservative order
            return "ORDER: 0\nREASON: API error occurred, defaulting to no order for safety."
    
    def get_player_type(self) -> str:
        """Return player type identifier."""
        return f"gpt4_{self.model_name}"


class GPT4ConservativePlayer(GPT4Player):
    """
    Conservative GPT-4 variant with modified system prompt.
    
    Instructs model to prioritize safety stock over cost minimization.
    """
    
    def _call_llm(self, prompt: str) -> str:
        """Call GPT-4 with conservative system prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a CONSERVATIVE supply chain manager. Your primary goal is to "
                            "AVOID STOCKOUTS at all costs. Maintain higher safety stock (4+ weeks coverage) "
                            "even if holding costs increase. Better to have excess inventory than backlog. "
                            "Make data-driven decisions based on Knowledge Graph information."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️  GPT-4 API error: {e}")
            return "ORDER: 0\nREASON: API error occurred."
    
    def get_player_type(self) -> str:
        return f"gpt4_conservative_{self.model_name}"


class GPT4AggressivePlayer(GPT4Player):
    """
    Aggressive GPT-4 variant with modified system prompt.
    
    Instructs model to minimize inventory and react quickly to demand changes.
    """
    
    def _call_llm(self, prompt: str) -> str:
        """Call GPT-4 with aggressive system prompt."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AGGRESSIVE supply chain manager focused on MINIMIZING INVENTORY. "
                            "Your goal is to reduce holding costs by maintaining lean inventory (2 weeks coverage). "
                            "React quickly to demand changes. Accept some stockout risk to minimize waste. "
                            "Make data-driven decisions based on Knowledge Graph information."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️  GPT-4 API error: {e}")
            return "ORDER: 0\nREASON: API error occurred."
    
    def get_player_type(self) -> str:
        return f"gpt4_aggressive_{self.model_name}"


# Example usage
if __name__ == "__main__":
    import os
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Create GPT-4 player
    player = GPT4Player(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer",
        api_key=api_key
    )
    
    # Mock observation
    mock_observation = {
        'current': {
            'week': 3,
            'inventory': 8,
            'backlog': 0,
            'demand_rate': 6.4,
            'coverage': 1.25,
            'incoming': 4
        },
        'history': [
            {'week': 1, 'inventory': 12, 'backlog': 0, 'demand_rate': 4.0, 'coverage': 3.0},
            {'week': 2, 'inventory': 8, 'backlog': 0, 'demand_rate': 4.0, 'coverage': 2.0}
        ],
        'alerts': ['STOCKOUT_RISK']
    }
    
    # Make decision
    print(f"Player: {player}")
    print(f"\nMaking decision for Week 3...")
    
    decision = player.decide(mock_observation)
    reasoning = player.get_last_reasoning()
    
    print(f"\n✓ Decision: Order {decision} units")
    print(f"✓ Reasoning: {reasoning}")
    
    # Example output:
    # Player: GPT4Player(role='Retailer', type='gpt4_gpt-4-turbo-preview')
    # 
    # Making decision for Week 3...
    # 
    # ✓ Decision: Order 20 units
    # ✓ Reasoning: Demand rate spiked to 6.4 units/week, requiring target inventory 
    #   of 19.2 units. Current inventory (8) plus incoming (4) = 12 units, which is 
    #   significantly below target. Ordering 20 units will restore proper coverage.
