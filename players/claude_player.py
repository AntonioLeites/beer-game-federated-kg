"""
Claude Player

AI player powered by Anthropic's Claude.
Requires: pip install anthropic
"""

from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from players.ai_player import AIPlayer


class ClaudePlayer(AIPlayer):
    """
    AI player powered by Anthropic Claude.
    
    Uses structured prompts built from Knowledge Graph data.
    Decisions are fully auditable with reasoning logged.
    
    Example usage:
        player = ClaudePlayer(
            actor_uri="http://beergame.org/retailer#Retailer_Alpha",
            role="Retailer",
            kg_endpoint="BG_Retailer",
            api_key="sk-ant-...",
            model_name="claude-sonnet-4-20250514"
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
                 model_name: str = "claude-sonnet-4-20250514",
                 temperature: float = 1.0,
                 max_tokens: int = 500,
                 base_url: str = "http://localhost:7200"):
        """
        Initialize Claude player.
        
        Args:
            actor_uri: Actor URI
            role: Role name
            kg_endpoint: KG repository ID
            api_key: Anthropic API key (starts with "sk-ant-")
            model_name: Claude model (default: "claude-sonnet-4-20250514")
            temperature: Sampling temperature 0-1 (default: 1.0)
            max_tokens: Max response tokens (default: 500)
            base_url: GraphDB URL
        """
        super().__init__(actor_uri, role, kg_endpoint, api_key, model_name, base_url)
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Anthropic client
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "Anthropic library not installed. Install with: pip install anthropic"
            )
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call Anthropic Claude API.
        
        Args:
            prompt: Formatted prompt string
        
        Returns:
            Claude response text
        """
        try:
            # Claude uses system message separately
            system_message = (
                "You are an expert supply chain manager playing the Beer Distribution Game. "
                "Your goal is to minimize total costs (holding + backlog) while maintaining "
                "service levels. You make data-driven decisions based on structured information "
                "from a Knowledge Graph. Always provide clear reasoning for your decisions."
            )
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract text from response
            return response.content[0].text
            
        except Exception as e:
            print(f"⚠️  Claude API error: {e}")
            # Fallback to conservative order
            return "ORDER: 0\nREASON: API error occurred, defaulting to no order for safety."
    
    def get_player_type(self) -> str:
        """Return player type identifier."""
        return f"claude_{self.model_name}"


class ClaudeConservativePlayer(ClaudePlayer):
    """
    Conservative Claude variant with modified system prompt.
    
    Instructs model to prioritize safety stock over cost minimization.
    """
    
    def _call_llm(self, prompt: str) -> str:
        """Call Claude with conservative system prompt."""
        try:
            system_message = (
                "You are a CONSERVATIVE supply chain manager. Your primary goal is to "
                "AVOID STOCKOUTS at all costs. Maintain higher safety stock (4+ weeks coverage) "
                "even if holding costs increase. Better to have excess inventory than backlog. "
                "Make data-driven decisions based on Knowledge Graph information."
            )
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"⚠️  Claude API error: {e}")
            return "ORDER: 0\nREASON: API error occurred."
    
    def get_player_type(self) -> str:
        return f"claude_conservative_{self.model_name}"


class ClaudeAggressivePlayer(ClaudePlayer):
    """
    Aggressive Claude variant with modified system prompt.
    
    Instructs model to minimize inventory and react quickly to demand changes.
    """
    
    def _call_llm(self, prompt: str) -> str:
        """Call Claude with aggressive system prompt."""
        try:
            system_message = (
                "You are an AGGRESSIVE supply chain manager focused on MINIMIZING INVENTORY. "
                "Your goal is to reduce holding costs by maintaining lean inventory (2 weeks coverage). "
                "React quickly to demand changes. Accept some stockout risk to minimize waste. "
                "Make data-driven decisions based on Knowledge Graph information."
            )
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"⚠️  Claude API error: {e}")
            return "ORDER: 0\nREASON: API error occurred."
    
    def get_player_type(self) -> str:
        return f"claude_aggressive_{self.model_name}"


# Example usage
if __name__ == "__main__":
    import os
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  Set ANTHROPIC_API_KEY environment variable")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
        exit(1)
    
    # Create Claude player
    player = ClaudePlayer(
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
    # Player: ClaudePlayer(role='Retailer', type='claude_claude-sonnet-4-20250514')
    # 
    # Making decision for Week 3...
    # 
    # ✓ Decision: Order 20 units
    # ✓ Reasoning: The demand rate has spiked to 6.4 units/week, indicating target 
    #   inventory should be around 19.2 units. Current inventory of 8 plus incoming 
    #   4 equals 12, which is well below target. Ordering 20 units will help restore 
    #   proper coverage and address the stockout risk alert.
