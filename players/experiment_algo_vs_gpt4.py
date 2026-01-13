"""
Experiment: Algorithmic vs GPT-4 Player

Compare performance and variance between:
    - Baseline: All algorithmic players (V3)
    - AI Test: Retailer = GPT-4, others = Algorithmic
    
Metrics:
    - Total cost
    - Variance across runs
    - Decision reasoning quality
    - Bullwhip amplitude
"""

import os
import sys
from algorithmic_player import AlgorithmicPlayer
from gpt4_player import GPT4Player
from game_orchestrator import GameOrchestrator


def run_baseline_experiment():
    """
    Run V3 baseline: All algorithmic players.
    
    Expected results (from V3 validation):
        - Retailer: 100% accuracy
        - Wholesaler: 95% accuracy
        - Low variance (<5%)
    """
    print("\n" + "="*70)
    print("EXPERIMENT 1: ALGORITHMIC BASELINE (V3 Replication)")
    print("="*70)
    
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
    
    orchestrator = GameOrchestrator(players, demand_pattern="spike")
    report = orchestrator.simulate_weeks(start_week=2, num_weeks=5)
    
    print(f"\n📊 BASELINE RESULTS:")
    print(f"   Total Cost: ${report['metrics']['total_cost']:.2f}")
    print(f"   Bullwhip Events: {report['metrics']['bullwhip_events']}")
    print(f"   Stockout Events: {report['metrics']['stockout_events']}")
    
    return report


def run_gpt4_retailer_experiment(api_key: str):
    """
    Run AI test: Retailer = GPT-4, others = Algorithmic.
    
    Research questions:
        - Does AI player perform better/worse than algorithm?
        - What is variance across multiple runs?
        - Are AI decisions explainable/reasonable?
    """
    print("\n" + "="*70)
    print("EXPERIMENT 2: GPT-4 RETAILER vs ALGORITHMIC UPSTREAM")
    print("="*70)
    
    players = {
        'Retailer': GPT4Player(
            actor_uri="http://beergame.org/retailer#Retailer_Alpha",
            role="Retailer",
            kg_endpoint="BG_Retailer",
            api_key=api_key,
            model_name="gpt-4-turbo-preview",
            temperature=0.7  # Some variance for multiple runs
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
    
    orchestrator = GameOrchestrator(players, demand_pattern="spike")
    report = orchestrator.simulate_weeks(start_week=2, num_weeks=5)
    
    print(f"\n📊 GPT-4 RESULTS:")
    print(f"   Total Cost: ${report['metrics']['total_cost']:.2f}")
    print(f"   Bullwhip Events: {report['metrics']['bullwhip_events']}")
    print(f"   Stockout Events: {report['metrics']['stockout_events']}")
    
    # Print GPT-4's reasoning for analysis
    print(f"\n💭 GPT-4 DECISION REASONING:")
    retailer_decisions = report['player_decisions']['Retailer']
    for decision in retailer_decisions:
        print(f"\n   Week {decision['week']}:")
        print(f"   Decision: {decision['decision']} units")
        print(f"   Reasoning: {decision.get('reasoning', 'N/A')[:200]}...")
    
    return report


def run_variance_test(api_key: str, num_runs: int = 5):
    """
    Run multiple iterations to measure variance.
    
    Compare:
        - Algorithmic variance (should be 0% - deterministic)
        - GPT-4 variance (measure across runs)
    
    This replicates the HBR study's variance measurement (46%).
    """
    print("\n" + "="*70)
    print(f"EXPERIMENT 3: VARIANCE TEST ({num_runs} runs)")
    print("="*70)
    
    algo_costs = []
    gpt4_costs = []
    
    for run in range(num_runs):
        print(f"\n--- Run {run + 1}/{num_runs} ---")
        
        # Run with algorithmic
        players_algo = {
            'Retailer': AlgorithmicPlayer(
                actor_uri="http://beergame.org/retailer#Retailer_Alpha",
                role="Retailer",
                kg_endpoint="BG_Retailer"
            ),
            # ... other players
        }
        orch_algo = GameOrchestrator(players_algo, demand_pattern="spike")
        report_algo = orch_algo.simulate_weeks(start_week=2, num_weeks=5)
        algo_costs.append(report_algo['metrics']['total_cost'])
        
        # Clean KG between runs (implementation needed)
        # clean_temporal_data()
        
        # Run with GPT-4
        players_gpt4 = {
            'Retailer': GPT4Player(
                actor_uri="http://beergame.org/retailer#Retailer_Alpha",
                role="Retailer",
                kg_endpoint="BG_Retailer",
                api_key=api_key,
                temperature=0.7
            ),
            # ... other players
        }
        orch_gpt4 = GameOrchestrator(players_gpt4, demand_pattern="spike")
        report_gpt4 = orch_gpt4.simulate_weeks(start_week=2, num_weeks=5)
        gpt4_costs.append(report_gpt4['metrics']['total_cost'])
    
    # Calculate variance
    import statistics
    
    algo_mean = statistics.mean(algo_costs)
    algo_stdev = statistics.stdev(algo_costs) if len(algo_costs) > 1 else 0
    algo_variance_pct = (algo_stdev / algo_mean * 100) if algo_mean > 0 else 0
    
    gpt4_mean = statistics.mean(gpt4_costs)
    gpt4_stdev = statistics.stdev(gpt4_costs) if len(gpt4_costs) > 1 else 0
    gpt4_variance_pct = (gpt4_stdev / gpt4_mean * 100) if gpt4_mean > 0 else 0
    
    print(f"\n📊 VARIANCE ANALYSIS:")
    print(f"\nAlgorithmic (Baseline):")
    print(f"   Mean Cost: ${algo_mean:.2f}")
    print(f"   Std Dev: ${algo_stdev:.2f}")
    print(f"   Variance: {algo_variance_pct:.1f}%")
    
    print(f"\nGPT-4 (AI):")
    print(f"   Mean Cost: ${gpt4_mean:.2f}")
    print(f"   Std Dev: ${gpt4_stdev:.2f}")
    print(f"   Variance: {gpt4_variance_pct:.1f}%")
    
    print(f"\n🎯 COMPARISON:")
    print(f"   HBR AI Variance: 46%")
    print(f"   Our Algo Variance: {algo_variance_pct:.1f}% (expected ~0%)")
    print(f"   Our GPT-4 Variance: {gpt4_variance_pct:.1f}% (goal: <30%)")
    
    if gpt4_variance_pct < 30:
        print(f"   ✅ SUCCESS: GPT-4 variance below 30% threshold!")
    else:
        print(f"   ⚠️  GPT-4 variance exceeds 30% threshold")
    
    return {
        'algorithmic': {'mean': algo_mean, 'stdev': algo_stdev, 'variance_pct': algo_variance_pct},
        'gpt4': {'mean': gpt4_mean, 'stdev': gpt4_stdev, 'variance_pct': gpt4_variance_pct}
    }


def main():
    """Run all experiments."""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='sk-...'")
        sys.exit(1)
    
    # Run experiments
    baseline_report = run_baseline_experiment()
    
    gpt4_report = run_gpt4_retailer_experiment(api_key)
    
    # Optional: Run variance test (takes longer)
    # variance_results = run_variance_test(api_key, num_runs=5)
    
    print("\n" + "="*70)
    print("✅ ALL EXPERIMENTS COMPLETE")
    print("="*70)
    
    # Compare results
    baseline_cost = baseline_report['metrics']['total_cost']
    gpt4_cost = gpt4_report['metrics']['total_cost']
    
    print(f"\n📊 SUMMARY:")
    print(f"   Baseline (All Algo): ${baseline_cost:.2f}")
    print(f"   GPT-4 Retailer: ${gpt4_cost:.2f}")
    
    if gpt4_cost < baseline_cost:
        improvement = (baseline_cost - gpt4_cost) / baseline_cost * 100
        print(f"   🎉 GPT-4 improved by {improvement:.1f}%!")
    elif gpt4_cost > baseline_cost:
        degradation = (gpt4_cost - baseline_cost) / baseline_cost * 100
        print(f"   ⚠️  GPT-4 increased cost by {degradation:.1f}%")
    else:
        print(f"   Equal performance")


if __name__ == "__main__":
    main()
