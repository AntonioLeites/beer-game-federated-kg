# GraphDB SWRL Rules - Troubleshooting Guide

## Common Issues When Importing SWRL Rules

### Issue 1: "Syntax error in Turtle file"

**Symptom:**
```
Error parsing RDF: Unexpected token at line X
```

**Cause:** SWRL rules use a specific RDF/XML or Turtle syntax that can be finicky.

**Solution:**
1. **Ensure ontology is imported FIRST** (before SWRL rules)
2. **Check file encoding:** Must be UTF-8
3. **Verify namespace declarations:** All prefixes must be declared at top of file

```turtle
# These MUST be at the top of beer-game-swrl-rules.ttl
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .
@prefix bg: <http://beergame.org/ontology#> .
```

---

### Issue 2: "SWRL rules not firing"

**Symptom:** Rules imported successfully, but no inferred triples appear.

**Cause:** Reasoning not enabled or wrong reasoning profile.

**Solution:**

1. **Enable reasoning in repository settings:**
   - GraphDB Workbench → Setup → Repositories → [Your Repo] → Edit
   - Ruleset: Select **"RDFS-Plus (Optimized)"** or **"OWL-Horst (Optimized)"**
   - Click "Save"

2. **Trigger reasoning manually:**
   ```sparql
   # Force reasoning by querying inferred triples
   PREFIX bg: <http://beergame.org/ontology#>
   SELECT ?s ?p ?o
   FROM <http://www.ontotext.com/explicit>
   FROM <http://www.ontotext.com/implicit>
   WHERE { ?s ?p ?o }
   LIMIT 10
   ```

3. **Check if rules are loaded:**
   ```sparql
   PREFIX swrl: <http://www.w3.org/2003/11/swrl#>
   SELECT ?rule ?label
   WHERE {
     ?rule a swrl:Imp ;
           rdfs:label ?label .
   }
   ```
   Should return all 10 SWRL rules.

---

### Issue 3: "Built-in function not supported"

**Symptom:**
```
Unknown built-in: swrlb:divide
```

**Cause:** GraphDB uses a specific set of built-in functions.

**Solution:**

GraphDB supports these SWRL built-ins:
- ✅ `swrlb:add`, `swrlb:subtract`, `swrlb:multiply`, `swrlb:divide`
- ✅ `swrlb:greaterThan`, `swrlb:lessThan`, `swrlb:equal`
- ✅ `swrlb:mod`, `swrlb:pow`, `swrlb:abs`
- ❌ NOT: `swrlb:max`, `swrlb:min` (use workarounds)

**Workaround for unsupported functions:**
```turtle
# Instead of swrlb:max(?result, ?a, ?b)
# Use conditional logic:
[ a swrl:BuiltinAtom ;
  swrl:builtin swrlb:greaterThan ;
  swrl:arguments ( ?a ?b ) ]
# Then assign ?result = ?a in head
```

---

### Issue 4: "Variables not bound correctly"

**Symptom:** Rule head creates wrong triples or no triples.

**Cause:** Variable scope issues in SWRL body.

**Solution:**

1. **All variables in HEAD must appear in BODY:**
   ```turtle
   # ❌ WRONG - ?result not in body
   swrl:head (
       [ a swrl:DatavaluedPropertyAtom ;
         swrl:propertyPredicate bg:totalCost ;
         swrl:argument1 ?actor ;
         swrl:argument2 ?result ]  # Where does ?result come from?
   )
   
   # ✅ CORRECT - ?result computed in body
   swrl:body (
       ...
       [ a swrl:BuiltinAtom ;
         swrl:builtin swrlb:add ;
         swrl:arguments ( ?result ?a ?b ) ]  # ?result defined here
   )
   swrl:head (
       [ a swrl:DatavaluedPropertyAtom ;
         swrl:propertyPredicate bg:totalCost ;
         swrl:argument1 ?actor ;
         swrl:argument2 ?result ]
   )
   ```

2. **Use explicit variable bindings:**
   ```turtle
   # Good practice: define variables step-by-step
   [ a swrl:BuiltinAtom ;
     swrl:builtin swrlb:multiply ;
     swrl:arguments ( ?holdingTotal ?stock ?hCost ) ]
   [ a swrl:BuiltinAtom ;
     swrl:builtin swrlb:multiply ;
     swrl:arguments ( ?backlogTotal ?backlog ?bCost ) ]
   [ a swrl:BuiltinAtom ;
     swrl:builtin swrlb:add ;
     swrl:arguments ( ?totalCost ?holdingTotal ?backlogTotal ) ]
   ```

---

### Issue 5: "Performance degradation with reasoning"

**Symptom:** Queries become very slow after enabling SWRL reasoning.

**Cause:** SWRL reasoning can be computationally expensive, especially with many rules.

**Solution:**

1. **Use optimized reasoning profile:**
   - Prefer **"RDFS-Plus (Optimized)"** over "OWL 2 RL"
   - OWL 2 RL is more expressive but slower

2. **Disable unused rules:**
   ```sparql
   # Delete specific rule if not needed
   PREFIX swrl: <http://www.w3.org/2003/11/swrl#>
   DELETE WHERE {
     bg:DemandSmoothingRule ?p ?o .
   }
   ```

3. **Use explicit reasoning (on-demand):**
   - Don't enable automatic reasoning
   - Run reasoning manually when needed:
     ```bash
     curl -X POST http://localhost:7200/repositories/BeerGame_Retailer/rdf-graphs/service?infer=true
     ```

4. **Batch updates:**
   - Instead of updating triples one-by-one, batch them
   - Reasoning triggers once after batch completes

---

### Issue 6: "Cannot import SWRL rules file"

**Symptom:**
```
Import failed: Malformed RDF document
```

**Cause:** File encoding, line endings, or special characters.

**Solution:**

1. **Check file encoding:**
   ```bash
   file -I beer-game-swrl-rules.ttl
   # Should show: charset=utf-8
   ```

2. **Convert line endings (if needed):**
   ```bash
   # Convert Windows (CRLF) to Unix (LF)
   dos2unix beer-game-swrl-rules.ttl
   ```

3. **Remove BOM (Byte Order Mark):**
   ```bash
   # Check for BOM
   hexdump -C beer-game-swrl-rules.ttl | head -n 1
   # If shows "ef bb bf" at start, remove it:
   sed '1s/^\xEF\xBB\xBF//' < beer-game-swrl-rules.ttl > fixed.ttl
   ```

4. **Import via API instead of UI:**
   ```bash
   curl -X POST http://localhost:7200/repositories/BeerGame_Retailer/statements \
     -H "Content-Type: application/x-turtle" \
     --data-binary @beer-game-swrl-rules.ttl
   ```

---

### Issue 7: "Federated queries fail inside SWRL rules"

**Symptom:** Rules work locally but fail when using SERVICE (federated queries).

**Cause:** SWRL reasoning happens at triple-store level, doesn't support SERVICE.

**Solution:**

**Don't use federated queries inside SWRL rules.** Instead:

1. **Pre-materialize data** via regular SPARQL UPDATE:
   ```sparql
   # Copy actual demand from Retailer to Wholesaler
   PREFIX bg: <http://beergame.org/ontology#>
   INSERT {
     bg_wholesaler:Wholesaler_Beta bg:actualDemandFromRetailer ?demand .
   }
   WHERE {
     SERVICE <http://localhost:7200/repositories/BeerGame_Retailer> {
       ?d a bg:CustomerDemand ;
          bg:actualDemand ?demand .
     }
   }
   ```

2. **Then SWRL rules operate on local data:**
   ```turtle
   # Rule uses local copy of actualDemandFromRetailer
   bg:OrderCappingRule a swrl:Imp ;
       swrl:body (
           [ a swrl:DatavaluedPropertyAtom ;
             swrl:propertyPredicate bg:actualDemandFromRetailer ;
             swrl:argument1 ?actor ;
             swrl:argument2 ?realDemand ]
           ...
       )
   ```

3. **Orchestrate with Python/JavaScript:**
   ```python
   # Simulation loop handles federation
   real_demand = query_retailer_kg("SELECT ?demand ...")
   
   # Update wholesaler KG with materialized demand
   update_wholesaler_kg(f"""
       INSERT DATA {{
           bg_wholesaler:Wholesaler_Beta bg:actualDemandFromRetailer {real_demand} .
       }}
   """)
   
   # Now SWRL rules can fire using local data
   ```

---

## Testing SWRL Rules Individually

### Test Rule 1: Bullwhip Detection

**Setup data:**
```turtle
PREFIX bg: <http://beergame.org/ontology#>

# Create an order that should trigger bullwhip
bg:TestOrder a bg:Order ;
    bg:orderQuantity "10"^^xsd:integer ;  # Order 10 units
    bg:weekNumber "1"^^xsd:integer ;
    bg:placedBy bg:TestActor .

bg:TestDemand a bg:CustomerDemand ;
    bg:actualDemand "4"^^xsd:integer ;  # But real demand is only 4
    bg:weekNumber "1"^^xsd:integer .

bg:TestActor a bg:Actor .
```

**Expected result (after reasoning):**
```sparql
SELECT ?actor ?hasBullwhip ?amplification
WHERE {
  ?actor bg:hasBullwhipRisk ?hasBullwhip .
  ?order bg:orderAmplification ?amplification .
}
# Should return:
# ?actor = bg:TestActor
# ?hasBullwhip = true
# ?amplification = 2.5 (10/4 = 2.5 > 1.3 threshold)
```

### Test Rule 7: Cost Calculation

**Setup data:**
```turtle
bg:TestInventory a bg:Inventory ;
    bg:currentInventory "20"^^xsd:integer ;
    bg:backlog "5"^^xsd:integer ;
    bg:holdingCost "0.50"^^xsd:decimal ;
    bg:backlogCost "1.00"^^xsd:decimal .

bg:TestActor a bg:Actor .
```

**Expected result:**
```sparql
SELECT ?actor ?totalCost
WHERE {
  ?actor bg:totalCost ?totalCost .
}
# Should return:
# ?totalCost = 15.0
# Calculation: (20 * 0.50) + (5 * 1.00) = 10 + 5 = 15
```

---

## Debugging SWRL Rules

### Enable GraphDB Debug Logging

1. Edit `graphdb.properties`:
   ```properties
   # Enable SWRL debug logging
   log4j.logger.com.ontotext.trree.reasoning=DEBUG
   log4j.logger.com.ontotext.trree.swrl=TRACE
   ```

2. Restart GraphDB

3. Check logs in `logs/main.log`:
   ```bash
   tail -f logs/main.log | grep SWRL
   ```

### Manual Rule Testing with SPARQL

Instead of relying on SWRL, test logic with pure SPARQL:

```sparql
# Equivalent to Bullwhip Detection Rule
PREFIX bg: <http://beergame.org/ontology#>

SELECT ?actor ?order ?amplification
WHERE {
  ?order a bg:Order ;
         bg:orderQuantity ?qty ;
         bg:weekNumber ?week ;
         bg:placedBy ?actor .
  
  ?demand a bg:CustomerDemand ;
          bg:weekNumber ?week ;
          bg:actualDemand ?realDemand .
  
  FILTER(?realDemand > 0)
  BIND(?qty / ?realDemand AS ?amplification)
  FILTER(?amplification > 1.3)
}
```

If this query returns results, but the SWRL rule doesn't fire, the issue is with SWRL syntax/reasoning, not logic.

---

## Alternative: RDFox vs GraphDB

If SWRL issues persist in GraphDB, consider **RDFox**:

**Advantages of RDFox:**
- ✅ **Faster reasoning** (parallel algorithms)
- ✅ **Better SWRL support** (nonmonotonic negation)
- ✅ **Clearer error messages**
- ✅ **Built-in debugging tools**

**RDFox SWRL syntax is slightly different:**
```datalog
# RDFox uses Datalog syntax (cleaner)
[BullwhipDetection:
    Order(?order),
    orderQuantity(?order, ?qty),
    weekNumber(?order, ?week),
    placedBy(?order, ?actor),
    CustomerDemand(?demand),
    weekNumber(?demand, ?week),
    actualDemand(?demand, ?realDemand),
    ?realDemand > 0,
    ?ratio = ?qty / ?realDemand,
    ?ratio > 1.3
    ->
    hasBullwhipRisk(?actor, true),
    orderAmplification(?order, ?ratio)
]
```

**Migration guide available in:** `docs/rdfox-migration.md`

---

## Quick Reference: Import Order

**Correct sequence for GraphDB:**

1. ✅ Create repository (with reasoning enabled)
2. ✅ Import `beer-game-ontology.ttl` (classes, properties)
3. ✅ Import actor data files (`retailer-week1.ttl`, etc.)
4. ✅ Import `beer-game-swrl-rules.ttl` (rules)
5. ✅ Import `beer-game-shacl.ttl` (validation, optional)
6. ✅ Run test query to verify reasoning

**If you get errors, delete repository and start over** (don't try to fix incrementally).

---

## Support Resources

- **GraphDB SWRL Documentation:** https://graphdb.ontotext.com/documentation/free/reasoning.html
- **W3C SWRL Spec:** https://www.w3.org/Submission/SWRL/
- **Stack Overflow Tag:** `[graphdb] [swrl]`
- **This repo's issues:** [GitHub Issues](link-to-your-repo/issues)

---

## Still Having Issues?

Open a GitHub issue with:
1. ✅ GraphDB version (`Help → About`)
2. ✅ Full error message (copy from Workbench)
3. ✅ Minimal example data that reproduces issue
4. ✅ Query you expect to work

We'll help debug! 🚀
