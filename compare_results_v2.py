"""
Compare theoretical vs actual Beer Game simulation results
UPDATED: Reads from simulation.weekly_results[] structure
"""

import json
import sys

# Theoretical results - SPIKE PATTERN (Demand = 12 at Week 3)
theoretical = {
    "Retailer": {
        1: {"inventory": 12, "backlog": 0, "demand_rate": 4.0, "suggested_order": 4, "orders_placed": 1, "total_cost": 12.0},
        2: {"inventory": 8, "backlog": 0, "demand_rate": 4.0, "suggested_order": 8, "orders_placed": 1, "total_cost": 8.0},
        3: {"inventory": 0, "backlog": 4, "demand_rate": 6.4, "suggested_order": 20, "orders_placed": 1, "total_cost": 10.0},
        4: {"inventory": 0, "backlog": 8, "demand_rate": 5.68, "suggested_order": 18, "orders_placed": 1, "total_cost": 18.0},
        5: {"inventory": 4, "backlog": 8, "demand_rate": 5.18, "suggested_order": 16, "orders_placed": 1, "total_cost": 22.0},
        6: {"inventory": 12, "backlog": 0, "demand_rate": 4.82, "suggested_order": 6, "orders_placed": 1, "total_cost": 12.0},
    },
    "Wholesaler": {
        1: {"inventory": 12, "backlog": 0, "demand_rate": 4.0, "shipments_created": 1, "total_cost": 12.0},
        2: {"inventory": 8, "backlog": 0, "demand_rate": 5.2, "shipments_created": 1, "total_cost": 8.0},
        3: {"inventory": 4, "backlog": 16, "demand_rate": 9.64, "shipments_created": 1, "total_cost": 36.0},
        4: {"inventory": 0, "backlog": 24, "demand_rate": 12.15, "shipments_created": 1, "total_cost": 50.0},
        5: {"inventory": 10, "backlog": 30, "demand_rate": 13.31, "shipments_created": 1, "total_cost": 70.0},
        6: {"inventory": 20, "backlog": 0, "demand_rate": 10.32, "shipments_created": 1, "total_cost": 20.0},
    }
}

def compare_results(json_file):
    """Compare actual results with theoretical predictions"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract weekly results from new structure
    weekly_results = {}
    for week_data in data.get("simulation", {}).get("weekly_results", []):
        week = week_data["week"]
        weekly_results[str(week)] = week_data
    
    print("="*110)
    print("📊 THEORETICAL vs ACTUAL - SPIKE PATTERN (Demand=12 at Week 3)")
    print("="*110)
    print(f"\nSimulation: {data['metadata']['simulation_date']}")
    print(f"Weeks found: {sorted([int(k) for k in weekly_results.keys()])}")
    print(f"Demand pattern: {data['metadata']['demand_pattern']}")
    
    for actor in ["Retailer", "Wholesaler"]:
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
                    ("total_cost", "Total Cost")
                ]
            else:
                metrics = [
                    ("inventory", "Inventory"),
                    ("backlog", "Backlog"),
                    ("demand_rate", "Demand Rate"),
                    ("shipments_created", "Shipments Created"),
                    ("total_cost", "Total Cost")
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
    print("  ✅ MATCH (diff < 0.1) - Perfect match")
    print("  ⚠️ CLOSE (diff < 2.0) - Minor difference, acceptable")
    print("  ❌ DIFF (diff >= 2.0) - Significant difference, investigate")
    print("="*110)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        compare_results(sys.argv[1])
    else:
        print("Usage: python compare_results.py <json_report_file>")
        print("Example: python compare_results.py beer_game_report_20260109_191122.json")
