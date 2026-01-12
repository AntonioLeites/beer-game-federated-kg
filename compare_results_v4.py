"""
Compare theoretical vs actual Beer Game simulation results - V4 (Clásico sin lag)
THEORETICAL VALUES: Recalculados manualmente sin lag artificial en perceived demand
- Observed demand = misma semana para todos los actores
- Backlog se suma correctamente al cálculo de suggested order
- CEIL en suggested order
"""

import json
import sys

# Theoretical results - SPIKE PATTERN (Demand = 12 at Week 3)
# Recalculados siguiendo Beer Game clásico: perceived demand de la misma semana
theoretical = {
    "Retailer": {
        2: {"inventory": 4.0,   "backlog": 0.0, "demand_rate": 4.00, "suggested_order": 8,  "orders_placed": 1},
        3: {"inventory": 0.0,   "backlog": 4.0, "demand_rate": 6.40, "suggested_order": 24, "orders_placed": 1},
        4: {"inventory": 4.0,   "backlog": 0.0, "demand_rate": 5.68, "suggested_order": 14, "orders_placed": 1},
        5: {"inventory": 24.0,  "backlog": 0.0, "demand_rate": 5.18, "suggested_order": 0,  "orders_placed": 0},
        6: {"inventory": 34.0,  "backlog": 0.0, "demand_rate": 4.82, "suggested_order": 0,  "orders_placed": 0},
    },
    "Wholesaler": {
        2: {"inventory": 8.0,   "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
        3: {"inventory": 0.0,   "backlog": 4.0, "demand_rate": 6.40, "shipments_created": 1},
        4: {"inventory": 0.0,   "backlog": 10.0,"demand_rate": 5.68, "shipments_created": 1},
        5: {"inventory": 24.0,  "backlog": 0.0, "demand_rate": 4.82, "shipments_created": 1},
        6: {"inventory": 45.0,  "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 0},
    },
    "Distributor": {
        2: {"inventory": 4.0,   "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
        3: {"inventory": 4.0,   "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
        4: {"inventory": 0.0,   "backlog": 4.0, "demand_rate": 6.40, "shipments_created": 1},
        5: {"inventory": 0.0,   "backlog": 13.0,"demand_rate": 5.68, "shipments_created": 1},
        6: {"inventory": 24.0,  "backlog": 0.0, "demand_rate": 4.82, "shipments_created": 0},
    },
    "Factory": {
        2: {"inventory": 4.0,   "backlog": 0.0, "demand_rate": 4.00, "shipments_created": 1},
        3: {"inventory": 0.0,   "backlog": 4.0, "demand_rate": 4.00, "shipments_created": 1},
        4: {"inventory": 0.0,   "backlog": 4.0, "demand_rate": 6.40, "shipments_created": 1},
        5: {"inventory": 0.0,   "backlog": 17.0,"demand_rate": 5.68, "shipments_created": 1},
        6: {"inventory": 8.0,   "backlog": 0.0, "demand_rate": 4.82, "shipments_created": 1},
    }
}

def compare_results(json_file):
    """Compare actual results with theoretical predictions (versión clásica sin lag)"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract weekly results from structure
    weekly_results = {}
    for week_data in data.get("simulation", {}).get("weekly_results", []):
        week = week_data["week"]
        weekly_results[str(week)] = week_data
    
    print("="*110)
    print("📊 THEORETICAL vs ACTUAL - V4 (Beer Game CLÁSICO - sin lag en perceived demand)")
    print("="*110)
    print(f"\nSimulation: {data['metadata']['simulation_date']}")
    print(f"Weeks found: {sorted([int(k) for k in weekly_results.keys()])}")
    print(f"Demand pattern: {data['metadata']['demand_pattern']}")
    print(f"\nTHEORETICAL: Recalculado manualmente siguiendo Beer Game clásico")
    print("   - Perceived demand = misma semana para todos los actores")
    print("   - Backlog se suma al cálculo de suggested order")
    print("   - CEIL en suggested order")
    
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
    print("  ✅ MATCH (diff < 0.1) - Perfect match")
    print("  ⚠️ CLOSE (diff < 2.0) - Minor difference (timing, rounding, etc.)")
    print("  ❌ DIFF (diff >= 2.0) - Significant difference → revisar timing o federación")
    print("\nNOTA: Esta versión teórica NO incluye lag artificial en perceived demand")
    print("      (todos los actores ven incoming orders de la misma semana)")
    print("="*110)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        compare_results(sys.argv[1])
    else:
        print("Usage: python compare_results_v4.py <json_report_file>")
        print("Example: python compare_results_v4.py beer_game_report_20260110_190738.json")