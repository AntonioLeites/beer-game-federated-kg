from temporal_beer_game_rules import TemporalBeerGameRuleExecutor

# Crear executor
executor = TemporalBeerGameRuleExecutor()

# Ejecutar solo la regla INVENTORY COVERAGE en BG_Retailer
print("Ejecutando regla INVENTORY COVERAGE...")
success = executor.execute_rule(
    "INVENTORY COVERAGE CALCULATION (Fixed)", 
    "BG_Retailer", 
    dry_run=False
)

print(f"\n✓ Success: {success}")

# Verificar resultado
if success:
    print("\nVerifica con esta query en GraphDB:")
    print("""
    PREFIX bg: <http://beergame.org/ontology#>
    SELECT ?metrics ?coverage WHERE {
      ?metrics a bg:ActorMetrics ;
               bg:forWeek bg:Week_2 ;
               bg:inventoryCoverage ?coverage .
    }
    """)