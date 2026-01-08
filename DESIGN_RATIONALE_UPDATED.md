# Design Rationale for the Temporal Beer Game Knowledge Graph

## Core Design Philosophy

This Knowledge Graph employs a **temporal state-based architecture** specifically engineered for causal analysis in supply chain simulations. Unlike traditional semantic graphs that focus on rich relationship semantics, this design prioritizes temporal tracking and state evolution to model dynamic systems behavior.

---

## Key Design Decisions

### 1. Temporal Primacy Over Relationship Semantics

The graph structures data around weekly states rather than semantic relationships. Each week (`bg:Week_1`, `bg:Week_2`, etc.) serves as an anchor point for capturing the complete system state at discrete time intervals. This enables:

- Clear before/after comparisons for causal analysis
- Easy reconstruction of the system's evolution over time
- Natural modeling of delays and lag effects inherent in supply chains

### 2. Uniform Connection Pattern

All temporal entities use two consistent relationships:
- `bg:belongsTo` → Links entities to their respective actors (Retailer, Wholesaler, etc.)
- `bg:forWeek` → Anchors entities to specific time points

This uniformity creates a predictable query pattern and simplifies federated queries across multiple actors in the supply chain.

### 3. State-Based Rather Than Event-Based

Each week contains a complete snapshot of relevant entities:
- Inventory state (current levels, backlog)
- Customer demand (actual consumption)
- Orders placed (decisions made)
- Shipments in transit (pipeline visibility)
- Performance metrics (calculated indicators)
- Internal data (private actor information)

This approach treats each week as a system state vector rather than a collection of disconnected events.

---

## Advantages for Supply Chain Simulation

### Causal Analysis
The temporal structure naturally supports cause-effect investigation:
- Demand in Week N influences Inventory in Week N
- Orders in Week N cause Shipments in Week N+2 (2-week delay)
- Inventory levels affect ordering decisions in subsequent weeks

### Bullwhip Effect Tracking
By maintaining weekly states, the graph can quantify:
- Amplification of demand variability upstream
- Inventory oscillation patterns
- Order volatility metrics

### Federated Simulation Support
Each supply chain actor maintains their own temporal graph with identical structure, enabling:
- Privacy preservation (actors share only what's necessary)
- Distributed decision-making
- **Coordinated queries without centralized control** ✨

---

## Rationale for Semantic Simplicity

The minimal relationship vocabulary (`belongsTo`, `forWeek`) was deliberately chosen because:

1. **Focus on Temporal Dynamics**: The primary research question involves "how states evolve over time" rather than "what relationships exist between entities"
2. **Query Performance**: Simple, uniform patterns enable efficient SPARQL queries across large temporal sequences
3. **Extensibility**: The base structure can accommodate new entity types without schema modifications
4. **Interoperability**: Consistent patterns facilitate data exchange between different supply chain actors

---

## Architecture: Rule-Based vs Procedural Logic

### Design Principle: Separation of Event Generation and Business Logic

A critical architectural decision separates the simulation into two distinct components:

#### Component 1: Simulation Orchestrator (`advanced_simulation_v2.py`)

**Responsibilities:**
- Generate exogenous events (customer demand)
- Create temporal anchors (Week entities)
- Orchestrate rule execution sequence
- Collect and report results

**What it does NOT do:**
- Calculate inventory updates
- Make ordering decisions
- Compute metrics
- Apply business policies

**Rationale:** The orchestrator represents forces external to the supply chain (customer behavior, time progression) but delegates all internal system dynamics to the Knowledge Graph.

#### Component 2: Business Rules Engine (`temporal_beer_game_rules_v2.py`)

**Responsibilities:**
- Implement all Beer Game business logic as SPARQL rules
- Calculate state transitions (inventory updates)
- Apply decision policies (order-up-to)
- Compute derived metrics (coverage, costs)
- Detect conditions (stockout risk, bullwhip)

**Rationale:** Encoding business logic as SPARQL rules makes it:
1. **Auditable** - The "why" behind decisions is explicit
2. **Modifiable** - Change strategies without recompiling
3. **Analyzable** - Rules themselves become data
4. **Reusable** - Same logic applies across different simulators

---

## Rule Categories and Execution Order

### Category 1: State Computation Rules (Core Dynamics)

These rules implement the fundamental Beer Game mechanics:

**A. UPDATE INVENTORY**
```sparql
# Calculates: new_inventory = previous + arriving_shipments - demand
# Updates: bg:currentInventory, bg:backlog
# Dependencies: Previous inventory, shipments with arrivalWeek = current, demand
```

**B. CREATE ORDERS FROM SUGGESTED**
```sparql
# Generates order documents based on suggestedOrderQuantity
# Creates: bg:Order entities
# Dependencies: ActorMetrics with suggestedOrderQuantity
```

**C. CREATE SHIPMENTS FROM ORDERS**
```sparql
# Generates shipments responding to received orders
# Creates: bg:Shipment entities with calculated arrivalWeek
# Dependencies: Orders received, actor shippingDelay
```

**Execution Order:** These must run sequentially within each week.

### Category 2: Metric Calculation Rules (Derived State)

These rules compute indicators from base state:

**D. INVENTORY COVERAGE CALCULATION**
```sparql
# Calculates: coverage = currentInventory / demandRate
# Purpose: "How many weeks of supply do I have?"
```

**E. DEMAND RATE SMOOTHING**
```sparql
# Applies: exponential smoothing to perceived demand
# Purpose: Models how actors perceive demand (not reality)
```

**F. TOTAL COST CALCULATION**
```sparql
# Sums: (inventory * holdingCost) + (backlog * backlogCost)
# Purpose: Primary performance metric of Beer Game
```

**Execution Order:** Can run in parallel after state computation.

### Category 3: Analysis Rules (Pattern Detection)

These rules identify interesting conditions:

**G. STOCKOUT RISK DETECTION**
```sparql
# Detects: inventoryCoverage < totalLeadTime
# Flags: Potential stock-out situations
```

**H. BULLWHIP DETECTION**
```sparql
# Detects: orderQuantity / actualDemand > 1.3
# Flags: Demand amplification (bullwhip effect)
```

**Execution Order:** Must run after metrics are calculated.

### Category 4: Policy Rules (Decision Logic)

These rules implement ordering strategies:

**I. ORDER-UP-TO POLICY**
```sparql
# Calculates: suggestedOrderQuantity = targetStock - currentInventory
# Where: targetStock = demandRate * (leadTime + reviewPeriod)
# Purpose: Classic order-up-to policy from Beer Game
```

**J. ORDER CAPPING (Optional)**
```sparql
# Limits: orders when bullwhip detected
# Purpose: Guardrail against over-ordering
```

**Execution Order:** Must run after metrics but before order creation.

---

## Data Type Design: IRIs vs Literals

### Design Decision: Dual Representation of Time

Time references use different representations depending on their semantic role:

#### Structural Time References (IRIs)
```turtle
bg_retailer:Inventory_Week2
    bg:forWeek bg:Week_2 .  # IRI - structural relationship
```

**Usage:** `bg:forWeek` always references a `bg:Week` instance

**Rationale:**
- Enables grouping queries ("all entities for Week 2")
- Supports aggregation across entity types
- Provides temporal navigation structure

#### Temporal Data Values (Literals)
```turtle
bg_retailer:Shipment_Week2_FromWholesaler
    bg:arrivalWeek "4"^^xsd:integer .  # Literal - data value
```

**Usage:** `bg:arrivalWeek`, `bg:completionWeek`, etc. use integers

**Rationale:**
- These are data attributes, not structural relationships
- Simplifies arithmetic (no need to lookup weekNumber)
- Future weeks may not exist as instances yet
- Avoids circular dependencies in creation order

### The `bg:Week` Instance Role

`bg:Week_N` instances serve as temporal snapshots and aggregation points, not as date representations:

```turtle
bg:Week_2 a bg:Week ;
    bg:weekNumber "2"^^xsd:integer ;
    rdfs:label "Week 2" .
    
# Week instances aggregate temporal data
bg_retailer:Retailer_Alpha
    bg:hasMetrics bg_retailer:Metrics_Week2 .
    
bg_retailer:Metrics_Week2
    bg:forWeek bg:Week_2 ;  # Links to snapshot
    bg:demandRate "4.5"^^xsd:decimal .
```

**Creation Pattern:**
- `Week_1` created in initial TTL
- `Week_N` created when simulation reaches week N
- Referenced before creation in data values (`arrivalWeek = 5` when only `Week_2` exists)

---

## Simulation Flow: From Events to States

### Weekly Cycle

```
Week N Simulation:

┌─────────────────────────────────────────────────┐
│ 1. CREATE TEMPORAL ANCHOR                       │
│    - Create bg:Week_N instance                  │
│    - Create ActorMetrics & Inventory snapshots  │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│ 2. GENERATE EXOGENOUS EVENTS                    │
│    - Create bg:CustomerDemand (external force)  │
│    [Orchestrator responsibility]                │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│ 3. EXECUTE BUSINESS RULES (in order)            │
│    A. DEMAND RATE SMOOTHING                     │
│    B. UPDATE INVENTORY                          │
│    C. INVENTORY COVERAGE CALCULATION            │
│    D. STOCKOUT RISK DETECTION                   │
│    E. ORDER-UP-TO POLICY                        │
│    F. CREATE ORDERS FROM SUGGESTED              │
│    G. CREATE SHIPMENTS FROM ORDERS              │
│    H. BULLWHIP DETECTION                        │
│    I. TOTAL COST CALCULATION                    │
│    [Rules Engine responsibility]                │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│ 4. CAPTURE STATE SNAPSHOT                       │
│    - All entities linked to bg:Week_N           │
│    - Ready for next iteration                   │
└─────────────────────────────────────────────────┘
```

### Dependencies Between Rules

```
CustomerDemand (external)
    ↓
DEMAND RATE SMOOTHING
    ↓
demandRate (updated)
    ↓
    ├──→ INVENTORY COVERAGE CALCULATION
    │       ↓
    │    inventoryCoverage
    │       ↓
    │    STOCKOUT RISK DETECTION
    │
    └──→ ORDER-UP-TO POLICY
            ↓
         suggestedOrderQuantity
            ↓
         CREATE ORDERS
            ↓
         Orders (generated)
            ↓
         CREATE SHIPMENTS
            ↓
         Shipments (generated)
            ↓
         BULLWHIP DETECTION
```

**Design Implication:** Rules must execute in dependency order, but within categories they can be parallelized.

---

## Federated Architecture: Actor Autonomy

### Principle: Distributed Knowledge, Coordinated Actions

Each actor maintains a separate Knowledge Graph repository:

```
BG_Retailer:
├── bg:Week_1, Week_2, Week_3...
├── bg:Inventory (per week)
├── bg:CustomerDemand (per week)
├── bg:Orders (placed to Wholesaler)
├── bg:Shipments (from Wholesaler)
└── bg:ActorMetrics (per week)

BG_Wholesaler:
├── bg:Week_1, Week_2, Week_3...
├── bg:Inventory (per week)
├── bg:Orders (received from Retailer, placed to Distributor)
├── bg:Shipments (from Distributor, to Retailer)
└── bg:ActorMetrics (per week)

... (Distributor, Factory similar structure)
```

### Repository Configuration (GraphDB)

All individual actor repositories share identical configuration for consistency.

**Repository Type:** GraphDB Free (RDF4J SailRepository with SHACL)  
**Repository IDs:** `BG_Retailer`, `BG_Wholesaler`, `BG_Distributor`, `BG_Factory`

#### Complete Configuration (Turtle)

```turtle
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.
@prefix shacl: <http://rdf4j.org/config/sail/shacl#>.

[] a rep:Repository ;
    rep:repositoryID "BG_Retailer" ;  # or BG_Wholesaler, BG_Distributor, BG_Factory
    rdfs:label "Beer Game - Retailer Knowledge Graph" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "rdf4j:ShaclSail" ;
            sail:delegate [
                sail:sailType "graphdb:Sail" ;
                
                # Repository Settings
                graphdb:read-only "false" ;
                
                # Inference and Validation
                graphdb:ruleset "owl-horst-optimized" ;
                graphdb:disable-sameAs "true" ;
                graphdb:check-for-inconsistencies "false" ;
                
                # Indexing
                graphdb:entity-id-size "32" ;
                graphdb:enable-context-index "true" ;
                graphdb:enablePredicateList "true" ;
                graphdb:enable-fts-index "false" ;
                
                # Queries and Updates
                graphdb:query-timeout "0" ;  # No timeout
                graphdb:throw-QueryEvaluationException-on-timeout "false" ;
                graphdb:query-limit-results "0" ;  # No limit
                
                # Storage
                graphdb:repository-type "file-repository" ;
                graphdb:storage-folder "storage" ;
                graphdb:entity-index-size "10000000" ;
                graphdb:in-memory-literal-properties "true" ;
                graphdb:enable-literal-index "true" ;
            ] ;
            
            # SHACL Validation Configuration
            shacl:validationEnabled "true" ;
            shacl:cacheSelectNodes "true" ;
            shacl:dashDataShapes "true" ;
            shacl:parallelValidation "true" ;
            shacl:rdfsSubClassReasoning "true" ;
            shacl:eclipseRdf4jShaclExtensions "true" ;
            shacl:validationResultsLimitTotal "1000000" ;
            shacl:validationResultsLimitPerConstraint "1000" ;
            shacl:transactionalValidationLimit "500000" ;
        ]
    ] .
```

#### Key Configuration Choices

**Inference: OWL-Horst (Optimized)**
```
graphdb:ruleset "owl-horst-optimized"
```
- Provides property inheritance and type inference
- Supports property chains and transitivity
- Optimized for performance
- More powerful than RDFS-Plus while remaining tractable

**Rationale:**
- Enables `bg:belongsTo` chains across weeks
- Type inference for entity classification
- Sufficient for temporal modeling without full OWL2 complexity
- Fast query performance for federated queries

**SameAs Handling:**
```
graphdb:disable-sameAs "true"
```
- Disabled because we use explicit URIs for all entities
- No entity merging needed in this domain
- Improves query performance

**Consistency Checking:**
```
graphdb:check-for-inconsistencies "false"
```
- Disabled for write performance
- SHACL validation handles data quality
- Temporal data naturally grows without contradictions

**Indexing Configuration:**
```
graphdb:entity-id-size "32"           # 32-bit IDs (sufficient for simulation)
graphdb:enable-context-index "true"   # Essential for GRAPH queries
graphdb:enablePredicateList "true"    # Optimizes property queries
graphdb:enable-fts-index "false"      # Not needed for temporal queries
```

**Rationale:**
- **32-bit IDs:** Supports ~4 billion statements (sufficient for weeks of simulation)
- **Context index:** Required for federated GRAPH queries
- **Predicate list:** Optimizes `?s ?p ?o` patterns common in rules
- **FTS disabled:** No text search needed; temporal queries use exact matches

**SHACL Validation:**
```
shacl:validationEnabled "true"
shacl:parallelValidation "true"
shacl:rdfsSubClassReasoning "true"
```

**Rationale:**
- Validates data integrity during simulation
- Catches missing `bg:forWeek` or `bg:belongsTo` properties
- Parallel validation improves performance
- RDFS reasoning enables validation on subclasses

**Query Configuration:**
```
graphdb:query-timeout "0"              # No timeout (long simulations)
graphdb:query-limit-results "0"        # No result limit
```

**Rationale:**
- Temporal queries can be complex (multi-week aggregations)
- No timeout prevents premature termination
- No result limits for complete state snapshots

#### Repository-Specific Settings

**BG_Retailer:**
```turtle
rep:repositoryID "BG_Retailer" ;
rdfs:label "Beer Game - Retailer Knowledge Graph" ;
```
Endpoint: `http://localhost:7200/repositories/BG_Retailer`

**BG_Wholesaler:**
```turtle
rep:repositoryID "BG_Wholesaler" ;
rdfs:label "Beer Game - Wholesaler Knowledge Graph" ;
```
Endpoint: `http://localhost:7200/repositories/BG_Wholesaler`

**BG_Distributor:**
```turtle
rep:repositoryID "BG_Distributor" ;
rdfs:label "Beer Game - Distributor Knowledge Graph" ;
```
Endpoint: `http://localhost:7200/repositories/BG_Distributor`

**BG_Factory:**
```turtle
rep:repositoryID "BG_Factory" ;
rdfs:label "Beer Game - Factory Knowledge Graph" ;
```
Endpoint: `http://localhost:7200/repositories/BG_Factory`

#### Federation Repository Configuration

**BG_Supply_Chain (FedX Federation):**

*Note: Federation configuration is managed through GraphDB Workbench UI, not config files.*

```
Repository Type: FedX Federation
Repository ID: BG_Supply_Chain
Description: "Federated view of all Beer Game actors"

Federation Members:
├── BG_Retailer
├── BG_Wholesaler
├── BG_Distributor
└── BG_Factory

FedX Options:
✓ Include inferred: default
✓ Enable service as bound join: enabled
✓ Log queries: disabled (enable for debugging)
✗ Debug query plan: disabled (enable for optimization)

Query timeout: 30 seconds
Bound join block size: 15
Join worker threads: 4
Left join worker threads: 4
Union worker threads: 4
```

**Rationale for FedX configuration:**
- **Service as bound join:** Optimizes queries by pushing filters to source repos
- **Worker threads (4 each):** Balances parallelism with resource constraints
- **Timeout (30s):** Sufficient for complex temporal queries
- **Bound join block size (15):** Efficient batching for cross-repo queries

### Cross-Repository References

Orders and Shipments create links across repositories:

```turtle
# In BG_Retailer:
bg_retailer:Order_Week2_ToWholesaler
    bg:placedBy bg_retailer:Retailer_Alpha ;
    bg:receivedBy bg_wholesaler:Wholesaler_Beta .  # Cross-repo reference

# In BG_Wholesaler:
bg_wholesaler:Order_Week2_FromRetailer
    bg:placedBy bg_retailer:Retailer_Alpha ;  # Received this order
    bg:receivedBy bg_wholesaler:Wholesaler_Beta .
```

---

## **NEW: Federated Query Architecture** ✨

### Evolution from Manual Propagation to Federated Queries

**Original Implementation (v1-v2):**
- Manual propagation of Orders and Shipments between repositories
- `propagate_orders_to_receivers()` method
- `propagate_shipments_to_receivers()` method
- Data duplication across repositories

**New Architecture (v3 - federated-queries branch):**
- **BG_Supply_Chain** federation repository aggregates all actor data
- **Read queries** execute on federated view
- **Write operations** execute on individual repositories
- **Zero manual propagation** - federation handles visibility automatically

### Federated Repository Configuration

**BG_Supply_Chain (FedX Federation):**
```
Federation Members:
├── BG_Retailer
├── BG_Wholesaler
├── BG_Distributor
└── BG_Factory

Configuration:
- Type: FedX (SPARQL Federation)
- Include inferred: default
- Enable service as bound join: enabled
- Query timeout: configurable
- Join optimization: enabled
```

### Query Flow Architecture

```
┌─────────────────────────────────────────┐
│   BG_Supply_Chain (Federation Layer)    │
│                                          │
│  Provides unified view of all repos     │
│  Used for: Complex READ queries         │
└─────────────────────────────────────────┘
         ↑         ↑         ↑         ↑
         │  Query  │  Query  │  Query  │
         │         │         │         │
    ┌────┴────┬────┴────┬────┴────┬────┴────┐
    │         │         │         │          │
┌───▼───┐ ┌──▼───┐ ┌───▼───┐ ┌───▼────┐    │
│  BG   │ │  BG  │ │  BG   │ │  BG    │    │
│Retail │ │Whole │ │Distri │ │Factory │    │
│  er   │ │saler │ │ butor │ │        │    │
└───────┘ └──────┘ └───────┘ └────────┘    │
    ↓        ↓         ↓          ↓         │
  WRITE    WRITE     WRITE      WRITE   ←───┘
 (Local)  (Local)   (Local)    (Local)
```

### Example: UPDATE INVENTORY with Federation

**Before (Manual Propagation):**
```python
# 1. Wholesaler creates shipment in BG_Wholesaler
create_shipment(BG_Wholesaler, shipment_data)

# 2. Manual propagation to receiver
propagate_shipments_to_receivers(week)
# Copies shipment to BG_Retailer

# 3. Retailer queries local repo for arriving shipments
query(BG_Retailer, "SELECT ?qty WHERE { ?shipment ... }")
```

**After (Federated Query):**
```python
# 1. Wholesaler creates shipment in BG_Wholesaler (unchanged)
create_shipment(BG_Wholesaler, shipment_data)

# 2. Retailer queries federated view (sees all shipments automatically)
query(BG_Supply_Chain, """
    SELECT ?qty WHERE {
        ?shipment bg:shippedTo bg_retailer:Retailer_Alpha ;
                  bg:arrivalWeek ?currentWeek ;
                  bg:shippedQuantity ?qty .
    }
""")
# Federation automatically routes query to BG_Wholesaler

# 3. Retailer updates local inventory
update(BG_Retailer, "UPDATE inventory += total")
```

### Benefits vs HBR Centralized Approach

| Aspect | HBR Centralized | Our Federated KG |
|--------|-----------------|------------------|
| **Architecture** | Single orchestrator | Distributed repositories |
| **Data visibility** | Central database | Federated queries |
| **Scalability** | Bottleneck | Linear scaling |
| **Explainability** | Black box (LLM) | Auditable SPARQL rules |
| **Failure resilience** | Single point of failure | No single point of failure |
| **Privacy** | All data centralized | Each actor controls own data |
| **Query capability** | Limited to what orchestrator shares | Agents query network directly |

### Rule Execution with Federation

**Read-Heavy Rules** (use BG_Supply_Chain):
- UPDATE INVENTORY (query arriving shipments across all repos)
- DEMAND RATE SMOOTHING (could query historical demand if needed)
- CREATE SHIPMENTS (query orders from downstream actors)

**Write-Only Rules** (use individual repos):
- CREATE ORDERS
- INVENTORY COVERAGE CALCULATION
- ORDER-UP-TO POLICY
- TOTAL COST CALCULATION

### Coordination Mechanism

**v2 (Manual):**
```python
# Explicit coordination via propagation
1. CREATE ORDERS (in sender repo)
2. propagate_orders_to_receivers()  # Manual copy
3. CREATE SHIPMENTS (finds orders in local repo)
4. propagate_shipments_to_receivers()  # Manual copy
```

**v3 (Federated):**
```python
# Implicit coordination via federation
1. CREATE ORDERS (in sender repo)
2. CREATE SHIPMENTS (queries BG_Supply_Chain, automatically sees orders)
# No manual propagation needed!
```

### Implementation Strategy

**Phase 1: Separate Query/Update** (current implementation)
```python
# Query phase (federated)
arriving_shipments = query(BG_Supply_Chain, shipments_query)

# Update phase (local)
update(BG_Retailer, f"UPDATE inventory += {sum(arriving_shipments)}")
```

**Phase 2: SPARQL SERVICE** (future enhancement)
```sparql
# Single SPARQL query with SERVICE clause
UPDATE BG_Retailer {
    ?inv bg:currentInventory ?newInv
}
WHERE {
    ?inv bg:forWeek bg:Week_5 .
    
    # Query remote shipments using SERVICE
    SERVICE <http://localhost:7200/repositories/BG_Supply_Chain> {
        SELECT (SUM(?qty) as ?total) WHERE {
            ?shipment bg:shippedTo ?localActor ;
                      bg:arrivalWeek 5 ;
                      bg:shippedQuantity ?qty .
        }
    }
    
    BIND(?oldInv + ?total - ?demand AS ?newInv)
}
```

---

## Demonstration Value for LinkedIn Post

### Key Message Alignment

**LinkedIn Post Claims:**
> "Federated Knowledge Graphs: Instead of one orchestrator, give each agent its own Knowledge Graph"

**Our Implementation:**
✅ Each actor has independent repository  
✅ Shared ontology (beer_game_ontology.ttl)  
✅ Federated queries via BG_Supply_Chain  

> "Agents query federated network for specific data only"

**Our Implementation:**
✅ Rules query BG_Supply_Chain for cross-actor data  
✅ Local queries stay in local repos  
✅ No unnecessary data sharing  

> "Explicit SWRL rules encode causal logic"

**Our Implementation:**
✅ All business logic in SPARQL rules  
✅ Auditable (can trace exact rule that fired)  
✅ Modifiable without recompilation  

> "No single point of failure → scales to complex multi-tier chains"

**Our Implementation:**
✅ Each repo operates independently  
✅ Federation layer is stateless (can be replicated)  
✅ Add new tier = add new repository  

> "Estimated impact: >75% cost reduction"

**Our Results:**
- Bullwhip detection working ✅
- Stockout prevention ✅
- Optimal ordering policies ✅
- Ready to benchmark vs HBR results

---

## Future Semantic Enrichment Pathways

While the current design optimizes for temporal analysis, it can be enhanced with semantic richness through:

### Layer 1: Relationship Specialization
```turtle
# Add specific relationships while maintaining temporal structure
bg_retailer:Retailer_Alpha
    bg:holdsInventory [ a bg:Inventory ;
                       bg:forWeek bg:Week_1 ] ;
    
    bg:experiencesDemand [ a bg:CustomerDemand ;
                          bg:forWeek bg:Week_1 ] ;
    
    bg:placesOrder [ a bg:Order ;
                    bg:forWeek bg:Week_1 ] .
```

### Layer 2: Causal Relationship Annotation
```turtle
# Explicit causal links between states
bg_retailer:Inventory_Week1
    bg:causes bg_retailer:Order_Week2 ;
    bg:causedBy bg_retailer:Demand_Week1 .
```

### Layer 3: Decision Logic Encoding
```turtle
# Embed decision rules within the graph
bg_retailer:OrderingPolicy
    bg:basedOn bg:InventoryCoverage ;
    bg:triggerThreshold "2.0"^^xsd:decimal ;
    bg:appliesTo bg_retailer:Retailer_Alpha .
```

---

## Conclusion

This Knowledge Graph represents a **purpose-built temporal modeling framework** rather than a general-purpose semantic graph. Its simplicity is its strength—providing a clean, scalable structure for analyzing supply chain dynamics, causal relationships, and temporal patterns in multi-agent simulations.

The design intentionally trades semantic richness for temporal clarity, creating a foundation that can be semantically enriched as needed while maintaining robust support for the core analytical requirements of the Beer Game simulation.

**The federated architecture demonstrates a critical evolution beyond centralized AI orchestration:** by distributing knowledge across actor-specific repositories and enabling coordinated access through federation, we achieve **scalability**, **explainability**, and **resilience** that centralized approaches cannot match.

This architecture directly addresses the limitations identified in the HBR study while maintaining the performance benefits of autonomous agent-based supply chain management.
