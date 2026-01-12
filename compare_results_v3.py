"""
Compare theoretical vs actual Beer Game simulation results - V3
THEORETICAL VALUES: Calculated manually applying rules step-by-step
"""

import json
import sys

# Theoretical results - SPIKE PATTERN (Demand = 12 at Week 3)
# Calculated manually following the rules:
# 1. DEMAND RATE SMOOTHING: α=0.3 (70% old, 30% new)
# 2. ORDER-UP-TO POLICY: Target = demandRate × (shippingDelay + orderDelay) = rate × 3
# 3. UPDATE INVENTORY: Considers arriving shipments (2-week delay)

theoretical = {
    "Retailer": {
        2: {"inventory": 8, "backlog": 0, "demand_rate": 4.0, "suggested_order": 4, "orders_placed": 1},
        3: {"inventory": 0, "backlog": 0, "demand_rate": 6.4, "suggested_order": 20, "orders_placed": 1},
        4: {"inventory": 0, "backlog": 0, "demand_rate": 5.68, "suggested_order": 18, "orders_placed": 1},
        5: {"inventory": 16, "backlog": 0, "demand_rate": 5.18, "suggested_order": 0, "orders_placed": 0},
        6: {"inventory": 30, "backlog": 0, "demand_rate": 4.82, "suggested_order": 0, "orders_placed": 0},
    },
    "Wholesaler": {
        # Note: Wholesaler sees Retailer orders with 1-week lag in DEMAND RATE
        # (queries orders from previous week)
        2: {"inventory": 12, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1},
        3: {"inventory": 16, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1},  # Sees order Week 2 = 4
        4: {"inventory": 16, "backlog": 0, "demand_rate": 8.8, "shipments_created": 1},  # Sees order Week 3 = 20
        5: {"inventory": 16, "backlog": 0, "demand_rate": 11.56, "shipments_created": 1}, # Sees order Week 4 = 18
        6: {"inventory": 27, "backlog": 0, "demand_rate": 8.09, "shipments_created": 0},  # Sees order Week 5 = 0
    },
    "Distributor": {
        2: {"inventory": 12, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1},
        3: {"inventory": 16, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1},
        4: {"inventory": 16, "backlog": 0, "demand_rate": 7.3, "shipments_created": 1},
        5: {"inventory": 16, "backlog": 0, "demand_rate": 8.51, "shipments_created": 1},
        6: {"inventory": 23, "backlog": 0, "demand_rate": 9.16, "shipments_created": 0},
    },
    "Factory": {
        2: {"inventory": 12, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1},
        3: {"inventory": 16, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1},
        4: {"inventory": 16, "backlog": 0, "demand_rate": 6.1, "shipments_created": 1},
        5: {"inventory": 16, "backlog": 0, "demand_rate": 6.07, "shipments_created": 1},
        6: {"inventory": 20, "backlog": 0, "demand_rate": 7.15, "shipments_created": 1},
    }
}

def compare_results(json_file):
    """Compare actual results with theoretical predictions"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract weekly results from structure
    weekly_results = {}
    for week_data in data.get("simulation", {}).get("weekly_results", []):
        week = week_data["week"]
        weekly_results[str(week)] = week_data
    
    print("="*110)
    print("📊 THEORETICAL vs ACTUAL - V3 FEDERATED ARCHITECTURE")
    print("="*110)
    print(f"\nSimulation: {data['metadata']['simulation_date']}")
    print(f"Weeks found: {sorted([int(k) for k in weekly_results.keys()])}")
    print(f"Demand pattern: {data['metadata']['demand_pattern']}")
    print(f"\nNOTE: Theoretical values calculated manually applying rules step-by-step")
    
    for actor in ["Retailer", "Wholesaler", "Distributor", "Factory"]:
        print(f"\n{'='*110}")
        print(f"🎯 {actor.upper()}")
        print(f"{'='*110}")
        
        print(f"\n{'Week':<6} {'Metric':<20} {'Theoretical':<15} {'Actual':<15} {'Diff':<15} {'Status':<10}")
        print("-"*110)
        
        if actor not in theoretical:
            continue
            
        for week in sorted(theoretical[actor].keys()):
            week_key = str(week)
            
            if week_key not in weekly_results:
                print(f"{week:<6} {'ALL':<20} {'N/A':<15} {'NOT SIMULATED':<15} {'N/A':<15} {'⚠️ MISSING':<10}")
                continue
            
            if actor not in weekly_results[week_key]["actors"]:
                print(f"{week:<6} {'ALL':<20} {'N/A':<15} {'ACTOR MISSING':<15} {'N/A':<15} {'❌ ERROR':<10}")
                continue
            
            actual_data = weekly_results[week_key]["actors"][actor]
            theo_data = theoretical[actor][week]
            
            if actor == "Retailer":
                metrics = [
                    ("inventory", "Inventory"),
                    ("backlog", "Backlog"),
                    ("demand_rate", "Demand Rate"),
                    ("suggested_order", "Suggested Order"),
                    ("orders_placed", "Orders Placed"),
                ]
            else:
                metrics = [
                    ("inventory", "Inventory"),
                    ("backlog", "Backlog"),
                    ("demand_rate", "Demand Rate"),
                    ("shipments_created", "Shipments Created"),
                ]
            
            for metric_key, metric_name in metrics:
                theo_val = theo_data.get(metric_key, 0)
                actual_val = actual_data.get(metric_key, 0)
                
                if actual_val is None:
                    actual_val = 0
                if theo_val is None:
                    theo_val = 0
                
                diff = actual_val - theo_val
                
                if abs(diff) < 0.1:
                    status = "✅ MATCH"
                elif abs(diff) < 2:
                    status = "⚠️ CLOSE"
                else:
                    status = "❌ DIFF"
                
                print(f"{week:<6} {metric_name:<20} {theo_val:<15.2f} {actual_val:<15.2f} {diff:<15.2f} {status:<10}")
    
    print("\n" + "="*110)
    print("Legend:")
    print("  ✅ MATCH (diff < 0.1) - Perfect match with manual calculation")
    print("  ⚠️ CLOSE (diff < 2.0) - Minor rounding/timing difference")
    print("  ❌ DIFF (diff >= 2.0) - Significant difference, investigate")
    print("\nNOTE: Wholesaler/Distributor/Factory demand rates have 1-week lag by design")
    print("      (they see orders from previous week via federated query)")
    print("="*110)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        compare_results(sys.argv[1])
    else:
        print("Usage: python compare_results_v3.py <json_report_file>")
        print("Example: python compare_results_v3.py beer_game_report_20260110_190738.json")
