# Context Knowledge Graph Design

## Overview

This extension adds **decision traceability** to the Beer Game federated knowledge graph by capturing complete decision contexts at the moment orders are placed.

## Motivation

The Beer Game demonstrates how local decision-making without visibility into the full supply chain leads to the **bullwhip effect**. Traditional event logs capture *what* happened, but Context Knowledge Graphs capture:

- **Why** decisions were made (rationale, perceived trends)
- **What information** was available (inventory, metrics, demand history)
- **What constraints** were active (policies, budget, guardrails)
- **What outcomes** resulted (actual vs expected, quality assessment)

This enables:
- Post-game analysis of decision quality
- Identification of bullwhip root causes
- Counterfactual "what if" scenarios
- AI player explainability
- Learning from successful patterns

## Architecture

### Core Classes
```turtle
bg:ContextSnapshot
    ├── bg:DecisionContext (subclass)
```

All context classes inherit from `bg:TemporalEntity`, ensuring:
- `bg:forWeek` links to specific week
- `bg:belongsTo` links to specific actor
- Temporal consistency via SHACL validation

### Decision Context Structure

Each `bg:DecisionContext` captures:

**State snapshots:**
- `bg:capturesInventoryState` → `bg:Inventory` instance
- `bg:capturesMetrics` → `bg:ActorMetrics` instance
- `bg:observedDemandHistory` → sequence of recent demands
- `bg:observedOrderHistory` → sequence of recent orders

**Decision rationale:**
- `bg:decisionRationale` - text explanation
- `bg:activePolicy` - policy in effect (conservative|aggressive|reactive|predictive)
- `bg:perceivedTrend` - trend perception (increasing|stable|decreasing|volatile)
- `bg:riskAssessment` - risk level (low|medium|high|critical)
- `bg:constraintsActive` - active guardrails

**Outcome tracking:**
- `bg:expectedOutcome` - prediction at decision time
- `bg:actualOutcome` - observed result (filled retrospectively)
- `bg:outcomeQuality` - quality assessment (optimal|good|suboptimal|poor)
- `bg:causedBullwhip` - boolean flag
- `bg:causedStockout` - boolean flag

**Counterfactual analysis:**
- `bg:alternativeContext` - links to alternative scenarios
- `bg:alternativeOrderQuantity` - alternative quantities considered

### Integration with Existing Model

Context KG extends but doesn't modify the core temporal model:
```
bg:Week5
   ├── bg:Inventory (Retailer, Week 5)
   ├── bg:ActorMetrics (Retailer, Week 5)
   ├── bg:DecisionContext (Retailer, Week 5)  ← NEW
   └── bg:Order (Retailer, Week 5)
              └── bg:basedOnContext → DecisionContext ← NEW LINK
```

## Usage Patterns

### 1. Creating Decision Contexts (Python)
```python
from SWRL_Rules.context_manager import create_decision_context

context = create_decision_context(
    actor="bg_retailer:Retailer",
    week="bg:Week5",
    inventory_state="bg_retailer:Inventory_Week5",
    metrics="bg_retailer:Metrics_Week5",
    rationale="Demand jumped 60→95. Ordering 120 to rebuild safety stock.",
    policy="reactive",
    trend="increasing",
    risk="medium"
)

# Link order to context
link_order_to_context(
    order="bg_retailer:Order_Week5",
    context=context
)
```

### 2. Querying Decision Audit Trail
```sparql
# Why did Retailer order 120 in Week 5?
SELECT ?rationale ?inventory ?backlog ?demandRate ?policy
WHERE {
    bg_retailer:Order_Week5 bg:basedOnContext ?ctx .
    ?ctx bg:decisionRationale ?rationale ;
         bg:activePolicy ?policy ;
         bg:capturesInventoryState ?inv ;
         bg:capturesMetrics ?metrics .
    ?inv bg:currentInventory ?inventory ;
         bg:backlog ?backlog .
    ?metrics bg:demandRate ?demandRate .
}
```

### 3. Post-Mortem Analysis

After simulation completes, retrospectively fill outcome data:
```python
update_decision_outcome(
    context="bg_retailer:Context_Week5",
    actual_outcome="Demand returned to 60, excess inventory",
    quality="suboptimal",
    caused_bullwhip=True,
    caused_stockout=False
)
```

## AI Player Integration

Context KG provides natural integration with AI players (Claude, GPT-4):
```python
class ClaudePlayer:
    def make_decision(self, game_state):
        # Claude generates decision with rationale
        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{
                "role": "user",
                "content": f"Current state: {game_state}\nDecide order quantity and explain why."
            }]
        )
        
        # Extract structured decision
        order_qty = extract_quantity(response)
        rationale = extract_rationale(response)
        perceived_trend = extract_trend(response)
        
        # Create context automatically
        context = create_decision_context(
            actor=self.actor_iri,
            week=game_state.current_week,
            inventory_state=game_state.inventory_iri,
            metrics=game_state.metrics_iri,
            rationale=rationale,  # From Claude's explanation
            trend=perceived_trend,  # From Claude's analysis
            policy=self.policy
        )
        
        return order_qty, context
```

## SHACL Validation

Context consistency enforced via SHACL:

- **Temporal alignment**: Context week must match captured entities' week
- **Actor consistency**: Context actor must match captured entities' actor
- **Completeness**: Context must capture both inventory and metrics
- **Referential integrity**: Orders should link to contexts

Violations trigger validation errors before data is committed.

## Federated Queries

Context KG works across federated repositories:
```sparql
# How did Retailer's Week 5 decision propagate upstream?
SELECT ?actor ?week ?rationale
WHERE {
    SERVICE <http://localhost:7200/repositories/retailer> {
        bg_retailer:Order_Week5 bg:orderQuantity ?retailerQty .
    }
    
    SERVICE <http://localhost:7200/repositories/wholesaler> {
        ?order bg:placedBy bg_wholesaler:Wholesaler ;
               bg:forWeek ?week ;
               bg:basedOnContext ?ctx .
        ?ctx bg:decisionRationale ?rationale .
        ?week bg:weekNumber ?wn .
        FILTER(?wn >= 6 && ?wn <= 8)
    }
}
```

## Benefits

### 1. Explainability
Every decision has full provenance: state, rationale, constraints.

### 2. Root Cause Analysis
Trace stockouts/bullwhip back to specific decisions and contexts.

### 3. Learning
Compare good vs poor decision contexts to identify patterns.

### 4. Counterfactual Reasoning
Explore "what if" scenarios by creating alternative contexts.

### 5. AI Transparency
AI player reasoning is captured and auditable.

## Future Extensions

### Causal Reasoning
Link contexts causally:
```turtle
bg:causedBy owl:ObjectProperty ;
    rdfs:domain bg:DecisionContext ;
    rdfs:range bg:DecisionContext .
```

### Multi-Agent Coordination
Capture inter-agent communication:
```turtle
bg:informedBy owl:ObjectProperty ;
    rdfs:comment "Context informed by another actor's shared data" .
```

### Temporal Queries
Advanced temporal reasoning:
```sparql
# Decisions made within 2 weeks of high backlog
```

## References

- HBR "When Supply Chains Become Autonomous" (Dec 2025)
- Temporal Knowledge Graphs (survey paper)
- Provenance ontologies (PROV-O)