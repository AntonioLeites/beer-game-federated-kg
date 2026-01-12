# Known Issues - V3 Federated Queries

## Critical Bug: Backlog not persisting in UPDATE INVENTORY

### Status: DEBUGGING IN PROGRESS

### Symptoms:
- Retailer Week 3: Expected backlog = 8, Actual = 0
- All other weeks: backlog remains 0 when should accumulate
- Inventory calculation works correctly (newInv = 0 ✅)
- Only backlog value fails to persist

### Evidence:
1. ✅ Manual SPARQL UPDATE works correctly (backlog = 8 inserted)
2. ✅ Query calculation returns correct value (newBacklog = 8)
3. ✅ Rule executes (inventoryProcessed = true)
4. ❌ Backlog value in KG = 0 (should be 8)

### Debug Queries Executed:

```sparql
# Manual UPDATE - WORKS ✅
DELETE { ?inv bg:backlog ?old }
INSERT { ?inv bg:backlog 8 }
WHERE { ?inv bg:forWeek bg:Week_3 }
# Result: backlog = 8 ✅

# Calculation query - WORKS ✅
# Returns: newBacklog = 8 ✅

# After Python execution - FAILS ❌
# Result: backlog = 0 ❌
```

### Hypotheses Tested:

1. ❌ Variable name collision in DELETE/INSERT - Fixed, still fails
2. ❌ Type casting issue (decimal vs integer) - Fixed with xsd:integer(), still fails
3. ❌ Subquery scope issue - Fixed, still fails
4. ❌ FILTER blocking execution - inventoryProcessed=true shows it runs
5. ❌ Cleanup removing values - cleanup only touches temp properties

### Current Theory:

The INSERT statement executes but inserts `0` instead of calculated value `8`.
Possible causes:
- Variable binding order in SPARQL
- GraphDB transaction isolation
- Python request handling dropping part of INSERT
- Silent SPARQL evaluation error in IF() expression

### Next Steps:

1. Add debug logging to Python execute_rule() to capture exact SPARQL sent
2. Enable GraphDB query logging to see what's received
3. Test with simplified UPDATE (hardcoded values)
4. Compare exact SPARQL string between manual (works) and Python (fails)

### Workaround:

None available. Backlog is critical for Beer Game simulation accuracy.

### Impact:

- Theoretical vs Actual comparison shows major discrepancies
- Suggested orders incorrect (depend on backlog)
- Total costs incorrect
- Bullwhip effect not properly simulated

### Date: 2026-01-10
### Assignee: Needs investigation
