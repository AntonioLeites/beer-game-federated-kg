"""
Beer Game Federated KG - Advanced Simulation with Metrics and Reporting
Simulates the beer distribution game across federated knowledge graphs
with detailed logging, performance metrics, and JSON reporting.
"""

import time
import json
import requests
from datetime import datetime
import execute_rules
from execute_rules import BeerGameRuleExecutor

print("Using execute_rules from:", execute_rules.__file__)


class AdvancedBeerGameSimulation:
    def __init__(self, graphdb_url="http://localhost:7200"):
        """
        Initialize the simulation engine.
        
        Args:
            graphdb_url (str): Base URL of the GraphDB instance
        """
        self.executor = BeerGameRuleExecutor()
        self.graphdb_url = graphdb_url
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def run_simulation(self, weeks=4):
        """
        Run the complete simulation.
        
        Args:
            weeks (int): Number of weeks to simulate
        """
        self.start_time = datetime.now()
        
        print(f"\n{'='*80}")
        print(f"🚀 STARTING BEER GAME FEDERATED KG SIMULATION")
        print(f"   Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Weeks: {weeks}")
        print(f"{'='*80}\n")
        
        for week in range(1, weeks + 1):
            week_result = self.simulate_week(week)
            self.results.append(week_result)
            
            # Brief pause between weeks to avoid overloading GraphDB
            if week < weeks:
                time.sleep(2)
        
        self.end_time = datetime.now()
        self.generate_comprehensive_report()
    
    def simulate_week(self, week_number):
        """
        Simulate a single week of the beer game.
        
        Args:
            week_number (int): Week number to simulate
            
        Returns:
            dict: Week simulation results
        """
        print(f"\n📅 {'='*60}")
        print(f"📅 WEEK {week_number} - PROCESSING...")
        print(f"{'='*60}")
        
        start_week = datetime.now()
        
        # Execute all rules for this week
        executed, failed = self.executor.execute_federated_week_simulation(
            week_number, dry_run=False
        )
        
        end_week = datetime.now()
        duration = (end_week - start_week).total_seconds()
        
        # Collect federated metrics from all knowledge graphs
        metrics = self.collect_federated_metrics(week_number)
        
        result = {
            "week": week_number,
            "executed_rules": executed,
            "failed_rules": failed,
            "duration_seconds": duration,
            "timestamp": end_week.isoformat(),
            "metrics": metrics
        }
        
        print(f"\n✅ WEEK {week_number} COMPLETED")
        print(f"   ⏱️  Duration: {duration:.2f} seconds")
        print(f"   📊 Rules: {executed} executed, {failed} failed")
        
        return result
    
    def collect_federated_metrics(self, week):
        """
        Collect metrics from the federated knowledge graph.
        
        Args:
            week (int): Week number
            
        Returns:
            dict: Collected metrics
        """
        try:
            # SPARQL query to get comprehensive metrics
            query = """
                PREFIX bg: <http://beergame.org/ontology#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                
                SELECT 
                    (COUNT(DISTINCT ?actor) as ?totalActors)
                    (COUNT(?bullwhip) as ?bullwhipRiskCount)
                    (COUNT(?stockout) as ?stockoutRiskCount)
                    (SUM(COALESCE(?totalCost, 0)) as ?chainTotalCost)
                    (AVG(COALESCE(?inventoryCoverage, 0)) as ?avgInventoryCoverage)
                WHERE {
                  SERVICE <http://localhost:7200/repositories/BG_Supply_Chain> {
                    ?actor a bg:Actor .
                    OPTIONAL { ?actor bg:hasBullwhipRisk ?bullwhip }
                    OPTIONAL { ?actor bg:hasStockoutRisk ?stockout }
                    OPTIONAL { ?actor bg:totalCost ?totalCost }
                    OPTIONAL { ?actor bg:inventoryCoverage ?inventoryCoverage }
                  }
                }
            """
            
            # Execute the query
            response = requests.post(
                f"{self.graphdb_url}/repositories/BG_Supply_Chain",
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["results"]["bindings"]:
                    binding = data["results"]["bindings"][0]
                    return {
                        "total_actors": int(binding.get("totalActors", {}).get("value", 0)),
                        "bullwhip_risks": int(binding.get("bullwhipRiskCount", {}).get("value", 0)),
                        "stockout_risks": int(binding.get("stockoutRiskCount", {}).get("value", 0)),
                        "total_cost": float(binding.get("chainTotalCost", {}).get("value", 0.0)),
                        "avg_inventory_coverage": float(binding.get("avgInventoryCoverage", {}).get("value", 0.0))
                    }
            
            return {
                "total_actors": 0,
                "bullwhip_risks": 0,
                "stockout_risks": 0,
                "total_cost": 0.0,
                "avg_inventory_coverage": 0.0
            }
            
        except Exception as e:
            print(f"⚠️  Error collecting metrics: {e}")
            return {
                "total_actors": 0,
                "bullwhip_risks": 0,
                "stockout_risks": 0,
                "total_cost": 0.0,
                "avg_inventory_coverage": 0.0,
                "error": str(e)
            }
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive simulation report."""
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"📊 COMPREHENSIVE SIMULATION REPORT")
        print(f"{'='*80}")
        
        # Calculate totals
        total_executed = sum(r["executed_rules"] for r in self.results)
        total_failed = sum(r["failed_rules"] for r in self.results)
        
        print(f"\n📈 EXECUTION STATISTICS:")
        print(f"   • Weeks simulated: {len(self.results)}")
        print(f"   • Total rules executed: {total_executed}")
        print(f"   • Total rules failed: {total_failed}")
        
        if total_executed + total_failed > 0:
            success_rate = (total_executed / (total_executed + total_failed)) * 100
            print(f"   • Overall success rate: {success_rate:.1f}%")
        
        print(f"   • Total simulation time: {total_duration:.2f} seconds")
        print(f"   • Average time per week: {total_duration/len(self.results):.2f} seconds")
        
        # Display weekly metrics
        print(f"\n📅 WEEKLY METRICS:")
        for result in self.results:
            metrics = result["metrics"]
            print(f"   Week {result['week']}:")
            print(f"     • Actors: {metrics.get('total_actors', 0)}")
            print(f"     • Bullwhip risks: {metrics.get('bullwhip_risks', 0)}")
            print(f"     • Stockout risks: {metrics.get('stockout_risks', 0)}")
            print(f"     • Total cost: ${metrics.get('total_cost', 0.0):.2f}")
            print(f"     • Avg inventory coverage: {metrics.get('avg_inventory_coverage', 0.0):.1f} weeks")
        
        # Save detailed report to JSON file
        self.save_report_to_json(total_executed, total_failed, total_duration)
        
        print(f"\n💾 Detailed report saved to JSON file")
        print(f"{'='*80}\n")
    
    def save_report_to_json(self, total_executed, total_failed, total_duration):
        """Save the complete simulation report to a JSON file."""
        report = {
            "simulation": {
                "name": "Beer Game Federated KG Simulation",
                "description": "Supply chain simulation using federated knowledge graphs and SPARQL rules",
                "version": "1.0.0"
            },
            "execution": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_duration_seconds": total_duration,
                "total_weeks": len(self.results),
                "total_rules_executed": total_executed,
                "total_rules_failed": total_failed,
                "success_rate": (total_executed/(total_executed+total_failed))*100 if total_executed+total_failed > 0 else 100
            },
            "configuration": {
                "graphdb_url": self.graphdb_url,
                "repositories": ["BG_Retailer", "BG_Wholesaler", "BG_Distributor", "BG_Factory", "BG_Supply_Chain"]
            },
            "weekly_results": self.results,
            "summary_metrics": {
                "peak_bullwhip_risks": max(r["metrics"].get("bullwhip_risks", 0) for r in self.results),
                "peak_stockout_risks": max(r["metrics"].get("stockout_risks", 0) for r in self.results),
                "total_supply_chain_cost": sum(r["metrics"].get("total_cost", 0) for r in self.results),
                "avg_inventory_coverage": sum(r["metrics"].get("avg_inventory_coverage", 0) for r in self.results) / len(self.results) if self.results else 0
            }
        }
        
        # Generate filename with timestamp
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"beer_game_simulation_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"   Report saved as: {filename}")

def main():
    """Main execution function."""
    print("🎯 ADVANCED BEER GAME FEDERATED KG SIMULATION")
    print("=============================================\n")
    
    # Configuration
    simulation = AdvancedBeerGameSimulation()
    
    try:
        # Run simulation for 4 weeks
        simulation.run_simulation(weeks=4)
        
        # Additional analysis
        print("\n📊 ADDITIONAL ANALYSIS")
        print("-" * 40)
        
        # You can add more analysis here
        # Example: Compare with HBR study results
        print("Comparison with HBR Study (2025):")
        print("• HBR reported: 67% cost reduction with GenAI agents")
        print("• Your federated KG approach eliminates central orchestrator bottleneck")
        print("• SWRL rules provide explicit, auditable causal reasoning")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Simulation failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()