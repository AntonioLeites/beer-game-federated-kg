"""
Beer Game Federated KG - Real Execution Script
Executes SPARQL CONSTRUCT rules across federated knowledge graphs
for supply chain simulation.
"""

import time
from execute_rules import BeerGameRuleExecutor  # Import from your existing module

def main():
    print("🎯 BEER GAME FEDERATED KG - REAL EXECUTION")
    print("==========================================\n")
    
    # Initialize rule executor
    executor = BeerGameRuleExecutor()
    
    # Number of weeks to simulate
    total_weeks = 4
    
    for week in range(1, total_weeks + 1):
        print(f"\n{'#'*70}")
        print(f"📊 WEEK {week} OF {total_weeks} - SIMULATING SUPPLY CHAIN")
        print(f"{'#'*70}")
        
        # Execute all rules in real mode (dry_run=False)
        executed, failed = executor.execute_federated_week_simulation(week, dry_run=False)
        
        # Display immediate summary
        print(f"\n📈 WEEK {week} SUMMARY:")
        print(f"   • Rules executed: {executed}")
        print(f"   • Rules failed: {failed}")
        
        # Calculate success rate
        if executed + failed > 0:
            success_rate = (executed / (executed + failed)) * 100
            print(f"   • Success rate: {success_rate:.1f}%")
        else:
            print(f"   • Success rate: 100%")
        
        # Pause between weeks (except the last one)
        if week < total_weeks:
            print(f"\n⏳ Advancing to week {week + 1}...")
            time.sleep(3)  # 3-second pause between weeks
    
    print(f"\n{'='*70}")
    print("✅ SIMULATION COMPLETED SUCCESSFULLY")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()