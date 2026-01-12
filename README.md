# Beer Distribution Game - Federated Knowledge Graphs with Temporal Simulation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![GraphDB](https://img.shields.io/badge/GraphDB-10.x-green.svg)](https://graphdb.ontotext.com/)

## 📄 Context

This repository implements the **Beer Distribution Game** using **Federated Knowledge Graphs + Temporal SPARQL Rules**, as a response to the Harvard Business Review article:

> **"When Supply Chains Become Autonomous"**  
> Carol Long, David Simchi-Levi, Andre P. Calmon, Flavio P. Calmon  
> Harvard Business Review, December 11, 2024  
> https://hbr.org/2024/12/when-supply-chains-become-autonomous

### The HBR Research Gap

The HBR research demonstrated that GenAI agents (GPT-5, Llama 4) can autonomously manage supply chains, achieving **67% cost reduction** vs. MBA students. However, their centralized orchestrator approach has critical limitations:

- ❌ **46% performance variance** across identical runs
- ❌ **Information overload** degrades advanced models
- ❌ **Implicit causal reasoning** (black box, non-auditable)
- ❌ **Centralized bottleneck** limits scalability

### Our Approach: Federated Temporal Knowledge Graphs

We replace the centralized orchestrator with **4 federated Knowledge Graphs** (one per supply chain actor), unified by:

✅ **Temporal state-based architecture** - Week-by-week system evolution  
✅ **Shared RDF/OWL ontology** - Common semantic model  
✅ **Federated SPARQL queries** - Distributed data access  
✅ **Explicit SPARQL rules** - Auditable causal logic  
✅ **No manual propagation** - Federation handles visibility  

**Key Innovation:** Each actor maintains their own temporal Knowledge Graph while querying a federated view (`BG_Supply_Chain`) for cross-actor data - **no single point of failure**.

---

## 🏗️ Architecture

### High-Level View

```
┌─────────────────────────────────────────────────────────┐
│         BG_Supply_Chain (FedX Federation)               │
│  Unified SPARQL endpoint for cross-actor queries        │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         │               │               │               │
         ▼               ▼               ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  BG_Retailer   │ │ BG_Wholesaler  │ │ BG_Distributor │ │  BG_Factory    │
│                │ │                │ │                │ │                │
│ Temporal Data: │ │ Temporal Data: │ │ Temporal Data: │ │ Temporal Data: │
│ • Week_1..N    │ │ • Week_1..N    │ │ • Week_1..N    │ │ • Week_1..N    │
│ • Inventory    │ │ • Inventory    │ │ • Inventory    │ │ • Inventory    │
│ • Demand       │ │ • Orders rcvd  │ │ • Orders rcvd  │ │ • Orders rcvd  │
│ • Orders       │ │ • Shipments    │ │ • Shipments    │ │ • Shipments    │
│ • Metrics      │ │ • Metrics      │ │ • Metrics      │ │ • Metrics      │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
         ↕                ↕                ↕                ↕
    Local writes    Local writes     Local writes     Local writes
    Federated reads Federated reads  Federated reads  Federated reads
```

### Temporal State Evolution

Each week captures complete system state:

```
Week N:
├── bg:Week_N (temporal anchor)
├── Inventory_WeekN (state)
├── CustomerDemand_WeekN (exogenous event)
├── ActorMetrics_WeekN (calculated metrics)
├── Order_WeekN (decisions made)
└── Shipment_WeekN (logistics)
```

**Key principle:** Week N+1 depends only on Week N state + business rules (Markovian).

---

## 🎯 V3 vs V2: Key Differences

This project has evolved through two major versions:

| Feature | V2 (Manual Propagation) | **V3 (Federated)** ✨ |
|---------|------------------------|----------------------|
| **Cross-repo visibility** | Manual Python copy | Automatic federation |
| **Orders propagation** | `propagate_orders_to_receivers()` | Federation query |
| **Shipments propagation** | `propagate_shipments_to_receivers()` | Federation query |
| **Data duplication** | Yes (orders/shipments copied) | **No** (single source) |
| **Execution time** | 2.3s | 3.8s (+65%) |
| **Code complexity** | High (8/10) | **Medium (6/10)** |
| **Scalability** | Linear (N²) | **Sublinear** |
| **Validation results** | 95% Retailer/Wholesaler | **100% Retailer, 95% Wholesaler** |

**🎉 V3 is now the default version** - Eliminates 200+ lines of manual propagation code while achieving better correctness.

> 📖 **For V3 technical deep-dive:** See **[README_V3.md](./README_V3.md)** for:
> - Zero duplication architecture
> - Federation query patterns
> - Complete validation results (Retailer: 100%, Wholesaler: 95%)
> - Visualization guide
> - Performance benchmarks
> - Troubleshooting

---

## 📁 Repository Structure

```
beer-game-federated-kg/
│
├── 📊 Data Files (Turtle/RDF)
│   ├── beer_game_ontology.ttl           # Shared ontology (classes, properties)
│   ├── beer_game_shacl.ttl              # SHACL validation constraints
│   │
│   ├── beer_game_retailer_kg_v3.ttl     # V3: Retailer Week 1 initial state
│   ├── beer_game_wholesaler_kg_v3.ttl   # V3: Wholesaler Week 1 initial state
│   ├── beer_game_distributor_kg_v3.ttl  # V3: Distributor Week 1 initial state
│   ├── beer_game_factory_kg_v3.ttl      # V3: Factory Week 1 initial state
│   │
│   └── *_v2.ttl                          # V2 files (archived)
│
├── 🎮 Simulation Engine
│   └── SWRL_Rules/
│       ├── advanced_simulation_v3.py              # V3 orchestrator (default)
│       ├── temporal_beer_game_rules_v3.py         # V3 SPARQL rules
│       ├── clean_temporal_data.py                 # Cleanup utility
│       └── diagnose_rules.py                      # Debugging tool
│
├── 📊 Analysis & Visualization
│   ├── compare_results_v3.py            # V3 validation (with lag)
│   ├── compare_results_v4.py            # V3 validation (no lag)
│   ├── compare_results_graph_V3.py      # Visualization generator V3
│   ├── compare_results_graph_V4.py      # Visualization generator V4
│   │
│   └── beer_game_dashboard_*.png        # Generated graphs
│
├── 📈 Results (golden report)
│   └── Examples/
│         └── reports/
│         │   └──  v3_spike_pattern_weeks2-6_validated.json        # V3 Spike + 6 Weeks
│         └── visualizations/
│             ├── beer_game_dashboard_2026-01-11.png              # dashboard
│             ├── beer_game_2026-01-10_retailer.png 
│             ├── beer_game_2026-01-10_wholesaler.png
│             ├── beer_game_2026-01-10_distributor.png 
│             └── beer_game_2026-01-10_factory.png
│
├── 📚 Documentation
│   ├── README.md                         # This file (overview, quick start)
│   ├── README_V3.md                      # V3 technical deep-dive
│   ├── DESIGN_RATIONALE_UPDATED.md      # Architecture decisions
│   ├── graphdb_troubleshooting.md       # GraphDB setup guide
│   └── sap_kg_architecture_options.md   # SAP integration paths
│
└── 🐍 Python Environment
    └── beer-game/                        # Virtual environment
```

### File Naming Convention

- **`*_v3.ttl`**: Current implementation (V3 federated architecture)
- **`*_v2.ttl`**: Previous version (manual propagation, archived)
- **`*.ttl`** (no version): Ontology/SHACL (version-agnostic)

---

## 🚀 Quick Start (V3)

### Prerequisites

1. **Ontotext GraphDB Free** (or commercial)
   - Download: https://graphdb.ontotext.com/
   - Installation: https://graphdb.ontotext.com/documentation/10/quick-start-guide.html
   
2. **Python 3.13+**
   ```bash
   python --version  # Should be 3.13+
   ```

3. **Python dependencies**
   ```bash
   python -m venv beer-game
   source beer-game/bin/activate  # On Windows: beer-game\Scripts\activate
   pip install requests rdflib matplotlib seaborn pandas
   ```

---

### Step 1: Start GraphDB

Start GraphDB server:
```bash
# Assuming GraphDB installed in ~/graphdb
cd ~/graphdb
./bin/graphdb -d
```

GraphDB Workbench will be available at: `http://localhost:7200`

---

### Step 2: Create Repositories

**Via GraphDB Workbench UI:**

1. Open `http://localhost:7200`
2. Go to **Setup** → **Repositories** → **Create new repository**
3. Create 5 repositories:

| Repository ID | Type | Ruleset |
|---------------|------|---------|
| `BG_Retailer` | GraphDB Free | OWL-Horst (Optimized) |
| `BG_Wholesaler` | GraphDB Free | OWL-Horst (Optimized) |
| `BG_Distributor` | GraphDB Free | OWL-Horst (Optimized) |
| `BG_Factory` | GraphDB Free | OWL-Horst (Optimized) |
| `BG_Supply_Chain` | **FedX Federation** | - |

**BG_Supply_Chain Configuration:**
- Type: **FedX Federation**
- Members: `BG_Retailer`, `BG_Wholesaler`, `BG_Distributor`, `BG_Factory`
- Enable **service as bound join** ✅

---

### Step 3: Load V3 Data

**Load ontology to all 4 actor repositories:**

```bash
# From project root
for repo in BG_Retailer BG_Wholesaler BG_Distributor BG_Factory; do
    curl -X POST http://localhost:7200/repositories/$repo/statements \
      -H "Content-Type: application/x-turtle" \
      --data-binary @beer_game_ontology.ttl
done
```

**Load SHACL validation shapes:**

```bash
for repo in BG_Retailer BG_Wholesaler BG_Distributor BG_Factory; do
    curl -X POST http://localhost:7200/repositories/$repo/statements \
      -H "Content-Type: application/x-turtle" \
      --data-binary @beer_game_shacl.ttl
done
```

**Load V3 actor-specific initial states (Week 1):**

```bash
curl -X POST http://localhost:7200/repositories/BG_Retailer/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_retailer_kg_v3.ttl

curl -X POST http://localhost:7200/repositories/BG_Wholesaler/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_wholesaler_kg_v3.ttl

curl -X POST http://localhost:7200/repositories/BG_Distributor/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_distributor_kg_v3.ttl

curl -X POST http://localhost:7200/repositories/BG_Factory/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_factory_kg_v3.ttl
```

**Verify data loaded:**

```bash
# Should return ~100-150 triples per repository
curl http://localhost:7200/repositories/BG_Retailer/size
```

---

### Step 4: Run V3 Simulation

```bash
cd SWRL_Rules
python advanced_simulation_v3.py
```

**Interactive prompts:**

```
Choose demand pattern:
  1. Stable (constant 4 units)
  2. Spike (12 units at week 3)          ← Recommended for bullwhip demo
  3. Increasing (gradual growth)
  4. Random (2-8 units)
Enter choice (1-4, default=1): 2

Number of weeks (default=4): 6
```

**Output:**

```
======================================================================
⚙️  EXECUTING RULES FOR WEEK 2 (V3 - Federated)
======================================================================

→ Executing: DEMAND RATE SMOOTHING (with federated demand queries)
      📊 Customer demand for Retailer_Alpha: 4.0
      📦 Federated orders (Week 1 → lag) for Wholesaler_Beta: 4.0
   ✓ Rule 'DEMAND RATE SMOOTHING' executed on BG_Retailer [HTTP 204]
   ...

→ Executing: CREATE SHIPMENTS (V3 federated version)
      📦 Federated query found 1 incoming orders for Wholesaler_Beta
         - 4 units from Retailer_Alpha
         ✓ Created shipment: 4 units to Retailer_Alpha
   ...

📊 WEEK 2 SUMMARY:
  Retailer:
    Inventory: 8
    Backlog: 0
    Coverage: 2.0 weeks
    Demand rate: 4.0
    Suggested order: 4
    Orders placed: 1 | received: 0
    Shipments created: 0
    Total cost: $8.00
...

📄 Report saved to: beer_game_report_20260111_223938.json
```

---

### Step 5: Generate Visualizations

```bash
# Generate all graphs (dashboard + individual actors)
python compare_results_graph_V3.py beer_game_report_20260111_*.json
```

**Output files:**
- `beer_game_dashboard_2026-01-11.png` - Overview dashboard
- `beer_game_2026-01-11_retailer.png` - Retailer analysis
- `beer_game_2026-01-11_wholesaler.png` - Wholesaler analysis
- `beer_game_2026-01-11_distributor.png` - Distributor analysis
- `beer_game_2026-01-11_factory.png` - Factory analysis

**Example dashboard:**

![Dashboard](beer_game_dashboard_2026-01-11.png)

---

### Step 6: Validate Results

```bash
# Compare with theoretical (accounts for 1-week lag)
python compare_results_v3.py beer_game_report_20260111_*.json
```

**Expected output:**

```
==============================================================================================================
🎯 RETAILER
==============================================================================================================
Week   Metric               Theoretical     Actual          Diff            Status    
--------------------------------------------------------------------------------------------------------------
2      Inventory            8.00            8.00            0.00            ✅ MATCH   
2      Demand Rate          4.00            4.00            0.00            ✅ MATCH   
2      Suggested Order      4.00            4.00            0.00            ✅ MATCH   
...
Overall: 15/15 metrics ✅ MATCH
```

---

### Step 7: Clean Up (Optional)

To reset simulation and start fresh:

```bash
python clean_temporal_data.py
```

This removes Week 2+ data while preserving Week 1 initial state.

---

## 📊 V3 Results Summary

### Validation (Spike Pattern, Weeks 2-6)

| Actor | Overall Score | Key Achievement |
|-------|--------------|-----------------|
| **Retailer** | **100%** ✅ | All 15 metrics perfect match |
| **Wholesaler** | **95%** ✅ | 11/12 metrics match |
| **Distributor** | 75% ⚠️ | Expected lag dampening |
| **Factory** | 70% ⚠️ | Expected lag dampening |

**Key Insights:**
- ✅ **Federation working perfectly** - Zero data duplication achieved
- ✅ **Retailer/Wholesaler production-ready** - 95%+ accuracy
- ⚠️ **Distributor/Factory lag expected** - Models realistic information delays
- ✅ **Bullwhip effect visible** - Demand variability amplification confirmed

> 📊 **For detailed results:** See [README_V3.md](./README_V3.md) → Validation Results section

---

## 🎮 How the Simulation Works

### Core Simulation Loop (V3)

```python
for week in range(2, num_weeks + 1):
    # 1. Create temporal anchor
    create_week_entities(week)
    
    # 2. Generate exogenous event (customer demand)
    demand = generate_customer_demand(week, pattern="spike")
    
    # 3. Execute business rules (SPARQL) with federation
    execute_week_rules(week)
    #   ├─ DEMAND RATE SMOOTHING (federated query for orders)
    #   ├─ UPDATE INVENTORY (federated query for arriving shipments)
    #   ├─ INVENTORY COVERAGE CALCULATION
    #   ├─ STOCKOUT RISK DETECTION
    #   ├─ ORDER-UP-TO POLICY
    #   ├─ CREATE ORDERS
    #   ├─ CREATE SHIPMENTS (federated query for incoming orders)
    #   ├─ BULLWHIP DETECTION
    #   └─ TOTAL COST CALCULATION
    
    # 4. No propagation needed - federation handles visibility! ✨
    
    # 5. Capture results
    report = get_week_summary(week)
```

**V3 Difference:** Steps 4 (manual propagation) **eliminated** - federation queries handle all cross-repo visibility automatically.

### Business Rules (SPARQL)

All business logic is encoded as **SPARQL UPDATE queries** in `temporal_beer_game_rules_v3.py`:

**Example: Federated Order Query (V3)**

```sparql
# Query incoming orders via BG_Supply_Chain federation
SELECT ?placedBy ?qty
WHERE {
    ?order a bg:Order ;
           bg:forWeek bg:Week_3 ;
           bg:receivedBy bg_wholesaler:Wholesaler_Beta ;
           bg:placedBy ?placedBy ;
           bg:orderQuantity ?qty .
}
# Executed on: http://localhost:7200/repositories/BG_Supply_Chain
# FedX automatically routes to source repositories
```

**Why SPARQL rules?**
- ✅ **Auditable**: Can trace exact conditions that fired
- ✅ **Modifiable**: Change thresholds without recompiling
- ✅ **Explainable**: "Why did this order get capped?" → Point to rule
- ✅ **Federated**: Queries across repositories seamlessly

---

## 🔬 Key Innovations vs. HBR Study

### 1. Federated Architecture (No Central Orchestrator)

**HBR Approach:**
```
Central Orchestrator (Bottleneck)
    ↓
Decides what data to share
    ↓
Sends to agents
```

**Our V3 Approach:**
```
BG_Supply_Chain (Stateless Federation)
    ↑ Query when needed
Each agent maintains own KG
    ↓ Write locally
No bottleneck, zero duplication
```

**Benefits:**
- ✅ Scales linearly (add actor = add repository)
- ✅ No single point of failure
- ✅ Agents query exactly what they need
- ✅ Privacy-preserving (actors share selectively)

---

### 2. Temporal State Architecture

**Traditional Event-Based:**
```
Event log: [Order1, Shipment1, Demand1, ...]
→ Must replay to reconstruct state
```

**Our State-Based:**
```
Week 3 snapshot:
├── Complete inventory state
├── All orders placed
├── All shipments in transit
├── Calculated metrics
→ Direct state comparison (Week 3 vs Week 2)
```

**Benefits:**
- ✅ Causal analysis ("What caused inventory drop?")
- ✅ Time-series queries ("Show demand over 10 weeks")
- ✅ Counterfactual reasoning ("What if demand spiked Week 2?")

---

### 3. Explicit Causal Rules (Auditable Logic)

**HBR Approach (GPT-5):**
```
Prompt → Black box reasoning → Decision
(Cannot audit WHY decision was made)
```

**Our Approach (SPARQL):**
```sparql
IF inventory < 2 * demandRate THEN stockoutRisk = true
IF demandRate / expectedDemand > 1.3 THEN bullwhipRisk = true
IF bullwhipRisk THEN suggestedOrder = MIN(order, expectedDemand * 1.2)
```

**Benefits:**
- ✅ Regulators can audit rules
- ✅ Supply chain managers can tune thresholds
- ✅ Failures are debuggable (trace SPARQL execution)
- ✅ Rules evolve independently of agents

---

## 🛠️ Advanced Usage

### Querying Temporal Data (V3 Federation)

**Example: Get inventory history across all actors**

```sparql
PREFIX bg: <http://beergame.org/ontology#>

SELECT ?actor ?week ?inventory
WHERE {
    SERVICE <http://localhost:7200/repositories/BG_Supply_Chain> {
        ?inv a bg:Inventory ;
             bg:forWeek ?weekEntity ;
             bg:belongsTo ?actor ;
             bg:currentInventory ?inventory .
        
        ?weekEntity bg:weekNumber ?week .
    }
}
ORDER BY ?actor ?week
```

Run via GraphDB Workbench or:

```bash
curl -X POST http://localhost:7200/repositories/BG_Supply_Chain \
  -H "Content-Type: application/sparql-query" \
  --data-binary @query.rq
```

---

## 📚 Documentation

- **[README.md](./README.md)** (this file): Overview, quick start, context
- **[README_V3.md](./README_V3.md)**: V3 technical deep-dive, validation, troubleshooting
- **[DESIGN_RATIONALE_UPDATED.md](./DESIGN_RATIONALE_UPDATED.md)**: Architecture decisions
- **[graphdb_troubleshooting.md](./graphdb_troubleshooting.md)**: Common GraphDB issues
- **[sap_kg_architecture_options.md](./sap_kg_architecture_options.md)**: SAP integration paths

---

## 🤝 Contributing

Contributions welcome! Areas of interest:

- 🐛 **Bug fixes**: Especially V3 federation edge cases
- 📊 **New SPARQL rules**: Different ordering policies, risk models
- 🎨 **Visualization**: Enhanced dashboards, animations
- 🚀 **Performance**: Optimize federated queries (V3 is 65% slower than V2)
- 📄 **Documentation**: Tutorials, examples
- 🧪 **Testing**: Unit tests for rules, integration tests

**How to contribute:**

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/beer-game-federated-kg.git

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes, test with V3
python SWRL_Rules/advanced_simulation_v3.py

# 4. Commit with clear messages
git commit -m "feat: Add dynamic lead time adjustment rule"

# 5. Push and create Pull Request
git push origin feature/your-feature-name
```

---

## 📧 Contact & Community

- **GitHub Issues**: [Report bugs or request features](https://github.com/AntonioLeites/beer-game-federated-kg/issues)
- **LinkedIn**: [Antonio Leites](https://www.linkedin.com/in/your-profile)
- **Discussions**: [GitHub Discussions](https://github.com/AntonioLeites/beer-game-federated-kg/discussions)

For SAP-specific inquiries or enterprise collaborations, please reach out via LinkedIn.

---

## 📜 License

**MIT License**

```
Copyright (c) 2026 Antonio Leites

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

See [LICENSE](./LICENSE) file for full text.

---

## 🙏 Acknowledgments

- **HBR Research Team**: Carol Long, David Simchi-Levi, Andre P. Calmon, Flavio P. Calmon
- **MIT Beer Game**: Jay Forrester (original system dynamics research)
- **Ontotext GraphDB**: For excellent federated SPARQL support (FedX)
- **W3C Semantic Web Community**: For RDF, OWL, SPARQL standards

---

## 📖 References

1. Long, C., et al. (2024). "When Supply Chains Become Autonomous." *Harvard Business Review*.
2. Forrester, J.W. (1961). *Industrial Dynamics*. MIT Press.
3. W3C SPARQL 1.1 Query Language: https://www.w3.org/TR/sparql11-query/
4. W3C SHACL: https://www.w3.org/TR/shacl/
5. Ontotext GraphDB FedX: https://graphdb.ontotext.com/documentation/10/fedx.html

---

**Built with:** 🐍 Python, 🔷 RDF/OWL, 🔍 SPARQL, 🏛️ GraphDB, and a commitment to explainable AI in supply chains.

**Current Version:** ✅ V3 Federated Architecture (stable)  
**Previous Version:** V2 Manual Propagation (archived in `v2-manual-propagation` branch)

---

*Last updated: January 11, 2026*
