# Beer Distribution Game - Federated Knowledge Graphs Implementation

## 📄 Context

This repository implements the Beer Distribution Game using **Federated Knowledge Graphs + SWRL Rules + GenAI Agents**, as a response to the Harvard Business Review article:

> **"When Supply Chains Become Autonomous"**  
> Carol Long, David Simchi-Levi, Andre P. Calmon, Flavio P. Calmon  
> Harvard Business Review, December 11, 2024

The HBR research showed that GenAI agents (GPT-5, Llama 4) can autonomously manage supply chains, achieving **67% cost reduction** vs. MBA students. However, their centralized orchestrator approach has limitations:
- ❌ 46% performance variance
- ❌ Information overload degrades advanced models
- ❌ Implicit (non-auditable) causal reasoning

**Our approach:** Replace the centralized orchestrator with **4 federated Knowledge Graphs** (one per actor), unified by:
- Shared RDF/OWL ontology
- Federated SPARQL queries
- Explicit SWRL causal rules

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│              SHARED ONTOLOGY (RDF/OWL)                   │
│  bg:Actor | bg:Order | bg:Inventory | bg:Shipment       │
└────────────────────────┬─────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  KG_RETAILER  │ │ KG_WHOLESALER │ │ KG_DISTRIBUTOR│
│               │ │               │ │               │
│ Local Facts:  │ │ Local Facts:  │ │ Local Facts:  │
│ • Inventory:12│ │ • Inventory:12│ │ • Inventory:12│
│ • Demand: 4   │ │ • Orders rcvd │ │ • Orders rcvd │
│               │ │               │ │               │
│ Fed. Queries: │ │ Fed. Queries: │ │ Fed. Queries: │
│ → Wholesaler  │ │ → REAL demand │ │ → Total       │
│   lead time   │ │   (Retailer)  │ │   pipeline    │
└───────────────┘ └───────────────┘ └───────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                  ┌───────────────┐
                  │  KG_FACTORY   │
                  │               │
                  │ Local Facts:  │
                  │ • Inventory:12│
                  │ • Production  │
                  │               │
                  │ Fed. Queries: │
                  │ → Aggregate   │
                  │   supply chain│
                  └───────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│           SWRL CAUSAL RULES (Shared Layer)               │
│                                                           │
│ Rule 1: IF order/realDemand > 1.3 THEN bullwhipRisk=HIGH│
│ Rule 2: IF bullwhipRisk THEN capOrder = realDemand*1.2  │
│ Rule 3: IF inventory < leadTime*demand THEN stockoutRisk│
│ Rule 4: Propagate REAL demand, not inflated orders      │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
beer-game-federated-kg/
│
├── ontology/
│   ├── beer-game-ontology.ttl      # Shared ontology (classes, properties)
│   ├── beer-game-swrl-rules.ttl    # SWRL causal rules
│   └── beer-game-shacl.ttl         # SHACL validation constraints
│
├── kg-retailer/
│   ├── data/
│   │   └── retailer-week1.ttl      # Initial state (Week 1)
│   └── sparql-queries/
│       └── query-wholesaler-leadtime.rq
│
├── kg-wholesaler/
│   ├── data/
│   │   └── wholesaler-week1.ttl
│   └── sparql-queries/
│       └── query-real-demand.rq    # CRITICAL: Query Retailer's actual demand
│
├── kg-distributor/
│   ├── data/
│   │   └── distributor-week1.ttl
│   └── sparql-queries/
│       └── query-bullwhip-detection.rq
│
├── kg-factory/
│   ├── data/
│   │   └── factory-week1.ttl
│   └── sparql-queries/
│       └── query-total-pipeline-demand.rq
│
├── simulation/
│   ├── beer-game-runner.py         # Main simulation loop
│   ├── genai-agents.py             # GPT-5/Llama 4 integration
│   └── results/
│       └── week-by-week-costs.csv
│
├── docker/
│   ├── docker-compose-graphdb.yml  # Ontotext GraphDB setup
│   ├── docker-compose-jena.yml     # Apache Jena Fuseki (open-source)
│   └── docker-compose-rdfox.yml    # RDFox (high-performance)
│
├── docs/
│   ├── hbr-article-analysis.md     # Detailed analysis of HBR research
│   ├── architecture-comparison.md  # Centralized vs. Federated
│   └── swrl-rules-explained.md     # Guide to each causal rule
│
└── README.md
```

---

## 🚀 Quick Start

### Option 1: Using Ontotext GraphDB (Recommended for Production)

**Prerequisites:**
- Docker & Docker Compose
- Ontotext GraphDB license (or free edition)

**Steps:**

1. **Start GraphDB instances** (4 separate repositories):
```bash
cd docker
docker-compose -f docker-compose-graphdb.yml up -d
```

This starts:
- `http://localhost:7200` → Retailer KG
- `http://localhost:7201` → Wholesaler KG
- `http://localhost:7202` → Distributor KG
- `http://localhost:7203` → Factory KG

2. **Load ontology + data**:
```bash
# Load shared ontology to all 4 repos
curl -X POST http://localhost:7200/repositories/BeerGame_Retailer/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @ontology/beer-game-ontology.ttl

# Repeat for ports 7201, 7202, 7203...

# Load actor-specific data
curl -X POST http://localhost:7200/repositories/BeerGame_Retailer/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @kg-retailer/data/retailer-week1.ttl
```

3. **Enable SWRL reasoning** (GraphDB):
```bash
# Via GraphDB Workbench UI:
# Setup → Repositories → BeerGame_Retailer → Reasoning: Enable RDFS+
# Import SWRL rules via Rules → Import → beer-game-swrl-rules.ttl
```

4. **Run simulation**:
```bash
cd simulation
python beer-game-runner.py --weeks 100 --model gpt-5
```

---

### Option 2: Using Apache Jena Fuseki (Open Source)

**For developers wanting free, lightweight option:**

```bash
cd docker
docker-compose -f docker-compose-jena.yml up -d
```

**Note:** Jena has limited SWRL support. For full SWRL reasoning, use GraphDB or RDFox.

---

### Option 3: Using RDFox (High Performance)

**For speed-critical applications:**

```bash
cd docker
docker-compose -f docker-compose-rdfox.yml up -d
```

RDFox excels at:
- ✅ Ultra-fast materialization (parallel algorithms)
- ✅ SWRL + nonmonotonic negation
- ✅ Real-time reasoning (100s updates/sec)

---

## 🎮 How the Simulation Works

### Week 1: Initial State

Each actor starts with:
- **Inventory:** 12 units
- **Backlog:** 0 units
- **Customer demand:** 4 units/week (stable)

### Decision Cycle (Each Week)

1. **Retailer Agent (GPT-5):**
   - Observes customer demand: 4 units
   - Current inventory: 12 units
   - Queries Wholesaler KG: `SELECT ?leadTime` → Gets 2 weeks
   - Decision: Order 4 units (matches demand)

2. **Wholesaler Agent (Llama 4):**
   - Receives Retailer's order: 4 units
   - **CRITICAL:** Queries Retailer KG for REAL demand:
     ```sparql
     SELECT ?realDemand WHERE {
       SERVICE <http://localhost:7200/repositories/BeerGame_Retailer> {
         ?demand a bg:CustomerDemand ;
                 bg:actualDemand ?realDemand .
       }
     }
     # Returns: 4 units (not the inflated order!)
     ```
   - SWRL rule validates: `4 / 4 = 1.0` → No bullwhip risk
   - Decision: Order 4 units from Distributor

3. **Distributor Agent (Claude):**
   - Receives Wholesaler's order: 4 units
   - Queries federated KG to detect amplification:
     ```sparql
     SELECT ?wholesalerOrder ?realDemand 
            (?wholesalerOrder / ?realDemand as ?amp)
     WHERE {
       ?order bg:orderQuantity ?wholesalerOrder .
       SERVICE <...Retailer> { ?d bg:actualDemand ?realDemand }
     }
     ```
   - SWRL rule: `IF amp > 1.3 THEN cap order`
   - Decision: Order 4 units from Factory

4. **Factory Agent (GPT-5):**
   - Receives Distributor's order: 4 units
   - Queries total supply chain pipeline:
     ```sparql
     SELECT (SUM(?qty) as ?totalPipeline)
     WHERE {
       { ?s1 a bg:Shipment ; bg:shippedQuantity ?qty }
       UNION
       { ?o1 a bg:Order ; bg:orderQuantity ?qty }
     }
     ```
   - Decision: Produce 4 units

### What Prevents Bullwhip Effect?

**Traditional Beer Game (Humans):**
- Retailer orders 4 → Wholesaler panics, orders 6
- Distributor sees 6, orders 9 → Factory produces 12
- **Result:** 12 produced for 4 actual demand = 3x overproduction!

**Federated KG + SWRL (This Implementation):**
- Wholesaler queries REAL demand (4), not just Retailer's order
- SWRL rule caps orders at `realDemand * 1.2 = 4.8`
- **Result:** 4-5 produced for 4 actual demand = stable!

---

## 📊 Expected Results

Based on HBR study + federated KG improvements:

| Approach | Total Cost | Bullwhip Amplitude | Performance Variance |
|----------|------------|-------------------|---------------------|
| **MBA Students** (HBR baseline) | 100 | High (3-5x) | N/A |
| **HBR Best** (Llama 4 + orchestrator) | 33 (-67%) | Low (1.5x) | 37% |
| **Federated KG** (this repo) | **~25** (-75%)* | Very Low (1.2x) | **<20%** |

*Estimated based on combining HBR's guardrail improvements with federated causal reasoning.

---

## 🔬 Key Innovations vs. HBR Study

### 1. **Explicit Causal Reasoning**

**HBR approach:** Implicit in GPT-5's reasoning (black box)
```
Prompt: "Minimize costs. Current demand: 4. Your inventory: 12. Decide order quantity."
→ GPT-5 thinks internally, outputs: "Order 5 units"
```

**Federated KG approach:** Explicit SWRL rules (auditable)
```turtle
[BullwhipDetection:
    (?order bg:orderQuantity ?qty)
    (?demand bg:actualDemand ?realDemand)
    swrlb:divide(?ratio, ?qty, ?realDemand)
    swrlb:greaterThan(?ratio, 1.3)
    -> (?actor bg:hasBullwhipRisk "true"^^xsd:boolean)
]
```

**Why it matters:**
- Regulators can audit: "Why did you cap this order?"
- Supply chain managers can tune rules
- Failures are debuggable (trace SPARQL queries)

---

### 2. **Self-Directed Data Queries**

**HBR approach:** Central orchestrator decides what data to share
```python
# Orchestrator code (pseudocode)
if actor == "Wholesaler":
    share(currentWeek.demand)  # Orchestrator's decision
```

**Federated KG approach:** Agents query exactly what they need
```sparql
# Wholesaler decides to query:
SELECT ?realDemand WHERE {
  SERVICE <http://retailer.kg/sparql> {
    ?demand bg:actualDemand ?realDemand .
  }
}
```

**Why it matters:**
- No bottleneck (orchestrator processing all requests)
- Agents adapt queries based on context
- New agents can join without reconfiguring orchestrator

---

### 3. **Dynamic Guardrails**

**HBR approach:** Static budget constraints
```
budgetLimit = $10,000  # Fixed for entire simulation
```

**Federated KG approach:** Context-aware SWRL rules
```turtle
[BudgetIncrease:
    (?actor bg:hasStockoutRisk "true"^^xsd:boolean)
    (?actor bg:inventoryCoverage ?coverage)
    swrlb:lessThan(?coverage, 2.0)
    (?actor bg:budgetConstraint ?normalBudget)
    swrlb:multiply(?newBudget, ?normalBudget, 1.5)
    -> (?actor bg:budgetConstraint ?newBudget)
]
```

**Why it matters:**
- Budget increases when stockout risk is high (emergency)
- Budget decreases when overstocked (prevents waste)
- Adapts to supply chain conditions dynamically

---

## 🛠️ Extending the Implementation

### Adding a 5th Actor (Supplier)

1. Create `kg-supplier/data/supplier-week1.ttl`
2. Define in ontology:
```turtle
bg:Supplier a owl:Class ;
    rdfs:subClassOf bg:Actor .
```
3. Update Factory to order from Supplier:
```turtle
bg_factory:Factory_Delta bg:ordersFrom bg_supplier:Supplier_Epsilon .
```
4. Add SWRL rule for raw material constraints

---

### Integrating with SAP

**Path 1: SAP HANA Cloud KG Engine (Q1 2025 GA)**
```python
# Instead of GraphDB endpoints, use HANA Cloud
import hdbcli

conn = hdbcli.connect(host='hana-cloud.sap', port=443)
cursor = conn.cursor()

# Execute SPARQL via SQL
cursor.execute("""
    SELECT * FROM SPARQL_TABLE('
        PREFIX bg: <http://beergame.org/ontology#>
        SELECT ?demand WHERE {
            ?d bg:actualDemand ?demand .
        }
    ')
""")
```

**Path 2: GraphDB + SAP Datasphere**
```
SAP S/4HANA (MM/PP) 
    → SAP Datasphere (integration) 
    → GraphDB (RDF store + SPARQL endpoints)
    → Federated queries
    → GenAI agents (BTP AI Core)
```

---

## 📚 References

1. Long, C., Simchi-Levi, D., Calmon, A.P., & Calmon, F.P. (2024). "When Supply Chains Become Autonomous." *Harvard Business Review*, December 11, 2024.
2. Forrester, J.W. (1961). "Industrial Dynamics" - Original Beer Game research
3. W3C SWRL: https://www.w3.org/Submission/SWRL/
4. Ontotext GraphDB: https://graphdb.ontotext.com/
5. RDFox: https://www.oxfordsemantic.tech/product
6. Apache Jena Fuseki: https://jena.apache.org/documentation/fuseki2/

---

## 🤝 Contributing

This is an open-source research project. Contributions welcome:
- 🐛 Bug fixes
- 📊 New SWRL rules
- 🎨 Visualization dashboards
- 🚀 Performance optimizations
- 📄 Documentation improvements

**How to contribute:**
1. Fork the repo
2. Create feature branch: `git checkout -b feature/new-swrl-rule`
3. Commit changes with clear messages
4. Submit Pull Request with benchmark results

---

## 📧 Contact

For questions, collaborations, or SAP integration inquiries:
- LinkedIn: [Your Profile]
- GitHub Issues: [Link to repo issues]
- Email: [Your email]

---

## 📜 License

MIT License - Free to use, modify, and distribute with attribution.

---

**Built with:** RDF, OWL, SWRL, SPARQL, Python, Docker, and a passion for semantic supply chains. 🚀
