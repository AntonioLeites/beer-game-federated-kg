"""
Experiment: V3 Integration Test

Test that V4 Player System integrates correctly with V3 temporal rules.

Goals:
1. Verify GameOrchestratorV3 connects to GraphDB
2. Confirm AlgorithmicPlayer decisions are created in KG
3. Validate V3 rules execute correctly
4. Compare results with pure V3 baseline

Requirements:
- GraphDB running on localhost:7200
- All 4 repositories created (BG_Retailer, BG_Wholesaler, BG_Distributor, BG_Factory)
- temporal_beer_game_rules_v3.py in SWRL_Rules/
"""

import sys
import os

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.game_orchestrator_v3_integrated import GameOrchestratorV3
from players.algorithmic_player import AlgorithmicPlayer


def test_orchestrator_initialization():
    """
    Test 1: Verify orchestrator can be initialized.
    """
    print("\n" + "="*70)
    print("TEST 1: ORCHESTRATOR INITIALIZATION")
    print("="*70)
    
    try:
        # Create players
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
        
        print(f"\n✓ Orchestrator created successfully")
        print(f"✓ Players registered: {list(orchestrator.players.keys())}")
        print(f"✓ GraphDB URL: {orchestrator.graphdb_url}")
        print(f"✓ Demand pattern: {orchestrator.demand_pattern}")
        print(f"✓ V3 Rule Executor initialized: {orchestrator.rule_executor is not None}")
        
        print(f"\n✅ PASS: Orchestrator initialization successful")
        return True, orchestrator
        
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_single_week_simulation(orchestrator):
    """
    Test 2: Run a single week simulation.
    
    This tests:
    - Week entity creation
    - Customer demand generation
    - V3 rule execution
    - Player decision making
    - Summary collection
    """
    print("\n" + "="*70)
    print("TEST 2: SINGLE WEEK SIMULATION")
    print("="*70)
    
    try:
        week = 2  # Start at week 2 (week 1 is initial state)
        
        print(f"\nRunning simulation for Week {week}...")
        
        week_result = orchestrator.simulate_week(week)
        
        # Validate result structure
        assert "week" in week_result, "Missing 'week' in result"
        assert "phases" in week_result, "Missing 'phases' in result"
        assert "summary" in week_result, "Missing 'summary' in result"
        
        print(f"\n✓ Week {week} completed")
        print(f"✓ Phases executed: {list(week_result['phases'].keys())}")
        
        # Check player decisions
        decisions = week_result['phases'].get('player_decisions', {})
        print(f"\n✓ Player decisions:")
        for role, qty in decisions.items():
            print(f"   • {role}: {qty} units")
        
        # Check summary
        summary = week_result.get('summary', {})
        actors = summary.get('actors', {})
        print(f"\n✓ Actors with data: {list(actors.keys())}")
        
        print(f"\n✅ PASS: Single week simulation successful")
        return True
        
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_week_simulation(orchestrator):
    """
    Test 3: Run multiple weeks (mini simulation).
    
    This tests:
    - Week-to-week continuity
    - Accumulated metrics
    - Report generation
    """
    print("\n" + "="*70)
    print("TEST 3: MULTI-WEEK SIMULATION (3 weeks)")
    print("="*70)
    
    try:
        start_week = 2
        num_weeks = 3
        
        print(f"\nRunning simulation: Weeks {start_week} → {start_week + num_weeks - 1}")
        
        report = orchestrator.simulate_weeks(start_week, num_weeks)
        
        # Validate report structure
        assert "simulation_info" in report, "Missing simulation_info"
        assert "players" in report, "Missing players"
        assert "week_results" in report, "Missing week_results"
        assert "metrics" in report, "Missing metrics"
        
        print(f"\n✓ Simulation completed")
        print(f"✓ Weeks simulated: {len(report['week_results'])}")
        print(f"✓ Total cost: ${report['metrics']['total_cost']:.2f}")
        
        # Show player decision counts
        player_decisions = report.get('player_decisions', {})
        print(f"\n✓ Player decision history:")
        for role, decisions in player_decisions.items():
            print(f"   • {role}: {len(decisions)} decisions logged")
        
        print(f"\n✅ PASS: Multi-week simulation successful")
        return True, report
        
    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def run_full_integration_test():
    """
    Run complete integration test suite.
    """
    print("\n" + "="*70)
    print("🧪 V3 INTEGRATION TEST SUITE")
    print("="*70)
    print("\nThis test validates that V4 Player System integrates with V3:")
    print("  • GraphDB connection")
    print("  • V3 temporal rules execution")
    print("  • Player decision persistence")
    print("  • Week-to-week simulation")
    
    results = []
    
    # Test 1: Initialization
    success, orchestrator = test_orchestrator_initialization()
    results.append(("Orchestrator Initialization", success))
    
    if not success:
        print("\n⚠️  Cannot proceed without successful initialization")
        return False
    
    # Test 2: Single week
    success = test_single_week_simulation(orchestrator)
    results.append(("Single Week Simulation", success))
    
    if not success:
        print("\n⚠️  Single week test failed, skipping multi-week")
        return False
    
    # Test 3: Multi-week
    success, report = test_multi_week_simulation(orchestrator)
    results.append(("Multi-Week Simulation", success))
    
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
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n💡 V4 Player System successfully integrated with V3!")
        print("\nYou can now:")
        print("  1. ✅ Run full simulations with AlgorithmicPlayer")
        print("  2. 🤖 Add AI players (GPT-4, Claude)")
        print("  3. 📊 Compare with V3 baseline results")
        return True
    else:
        print("\n⚠️  Some tests failed.")
        print("\nCommon issues:")
        print("  • GraphDB not running (start with: graphdb-desktop)")
        print("  • Repositories not created (check GraphDB UI)")
        print("  • temporal_beer_game_rules_v3.py not found")
        return False


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("⚙️  PRE-FLIGHT CHECKS")
    print("="*70)
    
    # Check GraphDB
    import requests
    try:
        response = requests.get("http://localhost:7200/rest/repositories")
        if response.status_code == 200:
            repos = response.json()
            repo_ids = [r['id'] for r in repos]
            print(f"✓ GraphDB running")
            print(f"✓ Repositories found: {repo_ids}")
            
            required = ['BG_Retailer', 'BG_Wholesaler', 'BG_Distributor', 'BG_Factory']
            missing = [r for r in required if r not in repo_ids]
            
            if missing:
                print(f"\n⚠️  WARNING: Missing repositories: {missing}")
                print(f"   Create them in GraphDB before running tests")
        else:
            print(f"⚠️  GraphDB responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ GraphDB not accessible: {e}")
        print(f"   Start GraphDB and try again")
        sys.exit(1)
    
    # Check V3 rules file
    import os
    rules_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'SWRL_Rules',
        'temporal_beer_game_rules_v3.py'
    )
    
    if os.path.exists(rules_path):
        print(f"✓ temporal_beer_game_rules_v3.py found")
    else:
        print(f"⚠️  temporal_beer_game_rules_v3.py not found at: {rules_path}")
        print(f"   Make sure it exists in SWRL_Rules/")
    
    print(f"\n{'='*70}")
    
    # Run tests
    success = run_full_integration_test()
    
    sys.exit(0 if success else 1)
