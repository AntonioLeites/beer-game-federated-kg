"""
Experiment: Algorithmic Baseline

Validate the Player System using only AlgorithmicPlayer (no AI needed).
This should replicate V3 results to prove the new architecture works.

Goals:
1. Verify AlgorithmicPlayer works correctly
2. Validate decision logic and variants
3. Establish baseline for future AI comparisons
4. No API costs (100% free)
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from players.algorithmic_player import (
    AlgorithmicPlayer,
    ConservativeAlgorithmicPlayer,
    AggressiveAlgorithmicPlayer
)


def test_player_standalone():
    """
    Test a single player in isolation (no KG needed).
    
    Validates:
    - Player instantiation
    - decide() logic
    - Reasoning generation
    """
    print("\n" + "="*70)
    print("TEST 1: STANDALONE PLAYER (No GraphDB)")
    print("="*70)
    
    player = AlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer",
        target_coverage=3.0
    )
    
    # Create mock observation (simulates KG data)
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
    
    # Display observation
    print(f"\n📊 Mock Observation (Week 3):")
    print(f"   Inventory: {mock_observation['current']['inventory']} units")
    print(f"   Backlog: {mock_observation['current']['backlog']} units")
    print(f"   Demand Rate: {mock_observation['current']['demand_rate']} units/week")
    print(f"   Coverage: {mock_observation['current']['coverage']:.1f} weeks")
    print(f"   Alerts: {mock_observation['alerts']}")
    
    # Make decision
    decision = player.decide(mock_observation)
    
    # Store for reasoning
    player.decision_history.append({
        'week': 3,
        'decision': decision,
        'observation': mock_observation,
        'reasoning': None
    })
    
    reasoning = player.get_last_reasoning()
    
    print(f"\n✓ Player Type: {player.get_player_type()}")
    print(f"✓ Decision: Order {decision} units")
    print(f"✓ Reasoning: {reasoning}")
    
    # Validate decision logic
    # target = demand_rate × coverage = 6.4 × 3 = 19.2
    # order = target - inventory + backlog = 19.2 - 8 + 0 = 11.2 → 11
    expected_target = mock_observation['current']['demand_rate'] * 3.0
    expected_order = expected_target - mock_observation['current']['inventory'] + mock_observation['current']['backlog']
    expected_order = max(0, int(expected_order))
    
    if decision == expected_order:
        print(f"\n✅ PASS: Decision matches expected ({expected_order} units)")
        return True
    else:
        print(f"\n⚠️  FAIL: Decision {decision} doesn't match expected {expected_order}")
        return False


def test_multiple_variants():
    """
    Test different player strategies produce different decisions.
    """
    print("\n" + "="*70)
    print("TEST 2: PLAYER VARIANTS (No GraphDB)")
    print("="*70)
    
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
        'alerts': []
    }
    
    # Create variants
    standard = AlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer"
    )
    
    conservative = ConservativeAlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer"
    )
    
    aggressive = AggressiveAlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer"
    )
    
    # Get decisions
    decision_standard = standard.decide(mock_observation)
    decision_conservative = conservative.decide(mock_observation)
    decision_aggressive = aggressive.decide(mock_observation)
    
    print(f"\n📊 Same observation, different strategies:")
    print(f"   Aggressive (2 weeks):    Order {decision_aggressive} units")
    print(f"   Standard (3 weeks):      Order {decision_standard} units")
    print(f"   Conservative (4 weeks):  Order {decision_conservative} units")
    
    # Expected: Aggressive < Standard < Conservative
    # Aggressive: 6.4 * 2 - 8 = 4.8 → 4
    # Standard: 6.4 * 3 - 8 = 11.2 → 11
    # Conservative: 6.4 * 4 - 8 = 17.6 → 17
    
    if decision_aggressive < decision_standard < decision_conservative:
        print(f"\n✅ PASS: Ordering correct (Aggressive < Standard < Conservative)")
        return True
    else:
        print(f"\n⚠️  FAIL: Expected {decision_aggressive} < {decision_standard} < {decision_conservative}")
        return False


def test_decision_logging():
    """
    Test decision history logging.
    """
    print("\n" + "="*70)
    print("TEST 3: DECISION LOGGING")
    print("="*70)
    
    player = AlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer"
    )
    
    # Make 3 decisions
    for week in [2, 3, 4]:
        mock_obs = {
            'current': {
                'week': week,
                'inventory': 8 + week,
                'backlog': 0,
                'demand_rate': 4.0 + week * 0.5,
                'coverage': 2.0,
                'incoming': 4
            },
            'history': [],
            'alerts': []
        }
        
        decision = player.decide(mock_obs)
        
        # Manually log (normally play_turn() does this)
        player.decision_history.append({
            'week': week,
            'decision': decision,
            'observation': mock_obs,
            'reasoning': player.get_last_reasoning()
        })
    
    # Check history
    history = player.get_decision_history()
    
    print(f"\n✓ Made {len(history)} decisions")
    
    for entry in history:
        print(f"\n   Week {entry['week']}:")
        print(f"      Decision: {entry['decision']} units")
        print(f"      Demand Rate: {entry['observation']['current']['demand_rate']}")
    
    if len(history) == 3:
        print(f"\n✅ PASS: All decisions logged correctly")
        return True
    else:
        print(f"\n⚠️  FAIL: Expected 3 decisions, got {len(history)}")
        return False


def run_all_tests():
    """Run all standalone tests."""
    print("\n" + "="*70)
    print("🧪 ALGORITHMIC PLAYER TESTS")
    print("="*70)
    print("\nThese tests validate the Player System without requiring:")
    print("  ✅ GraphDB (uses mock data)")
    print("  ✅ API keys (algorithmic only)")
    print("  ✅ Network (all local)")
    print("\nIf these pass, the foundation is solid for AI experiments.")
    
    results = []
    
    # Run tests
    results.append(("Standalone Player Logic", test_player_standalone()))
    results.append(("Multiple Strategy Variants", test_multiple_variants()))
    results.append(("Decision History Logging", test_decision_logging()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    
    passed = sum(r[1] for r in results)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\n{'='*70}")
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n💡 Next steps:")
        print("   1. ✅ Player System validated")
        print("   2. 🔄 Integrate with GraphDB (connect to V3 rules)")
        print("   3. 🤖 Add AI players (requires API keys)")
        return True
    else:
        print("\n⚠️  Some tests failed. Fix issues before proceeding.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n" + "="*70)
        print("✅ ALGORITHMIC BASELINE VALIDATED")
        print("="*70)
        print("\nThe Player System is ready for:")
        print("  • Integration with V3 orchestrator")
        print("  • AI player experiments")
        print("  • Multi-player comparisons")
        sys.exit(0)
    else:
        sys.exit(1)
