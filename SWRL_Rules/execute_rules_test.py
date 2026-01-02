# execute_rules.py
import requests
import time
from pathlib import Path

class BeerGameRuleExecutor:
    def __init__(self, base_url="http://localhost:7200"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Setup individual rules
        self.rules = self._load_rules_from_file()
    
    def _load_rules_from_file(self):
        """Load rules from file or setup inline """
        rules_file = Path("beer-game-rules.sparql")
        
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                content = f.read()
            
            # Extract rules from file
            rules = {}
            current_rule = []
            rule_name = None
            
            for line in content.split('\n'):
                if line.startswith('#### RULE'):
                    if rule_name and current_rule:
                        rules[rule_name] = '\n'.join(current_rule)
                    rule_name = line.strip('# ').split(':')[1].strip()
                    current_rule = [line]
                elif current_rule is not None:
                    current_rule.append(line)
            
            if rule_name and current_rule:
                rules[rule_name] = '\n'.join(current_rule)
            
            return rules
        else:
            # Setup rules inline if no file exists
            return self._get_default_rules()
    
    def _get_default_rules(self):
        """Define rules as  dict"""
        return {
            "bullwhip_detection": """...""",  # Rule 1 complete
            "order_capping": """...""",       # Rule 2 complete
            # ... etc para todas las reglas
        }
    
    def execute_rule(self, rule_name, repository, dry_run=False):
        """Ejecuta una regla específica en un repositorio"""
        if rule_name not in self.rules:
            print(f"✗ Regla no encontrada: {rule_name}")
            return False
        
        rule_sparql = self.rules[rule_name]
        endpoint = f"{self.base_url}/repositories/{repository}/statements"
        
        if dry_run:
            print(f"[DRY RUN] Ejecutaría regla '{rule_name}' en {repository}")
            print(f"SPARQL:\n{rule_sparql[:200]}...")
            return True
        
        headers = {"Content-Type": "application/sparql-update"}
        
        try:
            response = self.session.post(endpoint, data=rule_sparql, headers=headers)
            
            if response.status_code == 204:
                print(f"✓ Regla '{rule_name}' ejecutada en {repository}")
                return True
            else:
                print(f"✗ Error ejecutando '{rule_name}' en {repository}: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Excepción ejecutando '{rule_name}': {e}")
            return False
    
    def execute_all_rules_for_actor(self, actor_repo, week_number, dry_run=False):
        """Ejecuta todas las reglas para un actor específico"""
        print(f"\n{'='*60}")
        print(f"EJECUTANDO REGLAS PARA {actor_repo.upper()} - SEMANA {week_number}")
        print(f"{'='*60}")
        
        rules_executed = 0
        rules_failed = 0
        
        for rule_name in self.rules.keys():
            print(f"\n→ Regla: {rule_name}")
            
            if self.execute_rule(rule_name, actor_repo, dry_run):
                rules_executed += 1
            else:
                rules_failed += 1
            
            time.sleep(0.2)  # Pequeña pausa para no sobrecargar
        
        print(f"\n{'='*60}")
        print(f"RESUMEN {actor_repo.upper()}:")
        print(f"  ✓ Reglas ejecutadas: {rules_executed}")
        print(f"  ✗ Reglas falladas: {rules_failed}")
        print(f"{'='*60}")
        
        return rules_executed, rules_failed
    
    def execute_federated_week_simulation(self, week_number, dry_run=False):
        """Ejecuta todas las reglas en todos los actores (simulación semanal)"""
        print(f"\n{'#'*70}")
        print(f"SIMULACIÓN SEMANA {week_number} - EJECUTANDO REGLAS EN TODA LA CADENA")
        print(f"{'#'*70}")
        
        actors = ["BG_Retailer", "BG_Whosaler", "BG_Distributor", "BG_Factory"]
        
        total_executed = 0
        total_failed = 0
        
        for actor in actors:
            executed, failed = self.execute_all_rules_for_actor(actor, week_number, dry_run)
            total_executed += executed
            total_failed += failed
        
        # Ejecutar reglas en el repositorio federado para análisis global
        print(f"\n{'='*60}")
        print("ANÁLISIS FEDERADO GLOBAL")
        print(f"{'='*60}")
        
        # Consulta federada para métricas globales
        federated_query = """
            PREFIX bg: <http://beergame.org/ontology#>
            
            SELECT 
                (COUNT(?actor) as ?totalActors)
                (COUNT(?bullwhip) as ?bullwhipRiskCount)
                (COUNT(?stockout) as ?stockoutRiskCount)
                (SUM(?totalCost) as ?chainTotalCost)
                (AVG(?inventoryCoverage) as ?avgCoverage)
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
        
        if not dry_run:
            self.execute_federated_query(federated_query, week_number)
        
        print(f"\n{'#'*70}")
        print(f"RESUMEN FINAL SEMANA {week_number}:")
        print(f"  ✓ Total reglas ejecutadas: {total_executed}")
        print(f"  ✗ Total reglas falladas: {total_failed}")
        print(f"  ↻ Actores procesados: {len(actors)}")
        print(f"{'#'*70}\n")
        
        return total_executed, total_failed
    
    def execute_federated_query(self, sparql_query, week_number):
        """Ejecuta una consulta federada para análisis global"""
        endpoint = f"{self.base_url}/repositories/BG_Supply_Chain"
        headers = {"Accept": "application/sparql-results+json"}
        
        try:
            response = self.session.post(
                endpoint, 
                data={"query": sparql_query}, 
                headers=headers
            )
            
            if response.status_code == 200:
                results = response.json()
                self._display_federated_results(results, week_number)
            else:
                print(f"✗ Error en consulta federada: {response.text}")
                
        except Exception as e:
            print(f"✗ Excepción en consulta federada: {e}")
    
    def _display_federated_results(self, results, week_number):
        """Muestra los resultados de la consulta federada"""
        if 'results' in results and 'bindings' in results['results']:
            bindings = results['results']['bindings']
            
            if bindings:
                data = bindings[0]
                
                print(f"\n📊 MÉTRICAS GLOBALES CADENA DE SUMINISTRO (Semana {week_number}):")
                print(f"   • Total actores: {data.get('totalActors', {}).get('value', 'N/A')}")
                print(f"   • Riesgo Bullwhip: {data.get('bullwhipRiskCount', {}).get('value', 'N/A')} actores")
                print(f"   • Riesgo Stockout: {data.get('stockoutRiskCount', {}).get('value', 'N/A')} actores")
                print(f"   • Costo total cadena: ${data.get('chainTotalCost', {}).get('value', 'N/A')}")
                print(f"   • Cobertura inventario promedio: {data.get('avgCoverage', {}).get('value', 'N/A')} semanas")

# Ejecutar simulación
if __name__ == "__main__":
    executor = BeerGameRuleExecutor()
    
    # Simular 4 semanas
    for week in range(1, 5):
        # Primero hacer dry run para probar
        if week == 1:
            print("🎯 PRUEBA INICIAL (DRY RUN)")
            executor.execute_federated_week_simulation(week, dry_run=True)
            print("\n" + "="*70)
            print("SI LA PRUEBA ES EXITOSA, EJECUTAR CON dry_run=False")
            print("="*70 + "\n")
            break  # Solo prueba la primera semana
        
        # Ejecución real
        executor.execute_federated_week_simulation(week, dry_run=False)
        time.sleep(2)  # Pausa entre semanas