# Beer Distribution Game - Federated Knowledge Graph Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![GraphDB](https://img.shields.io/badge/GraphDB-10.x-green.svg)](https://graphdb.ontotext.com/)

## 📄 Research Context

This repository implements a **Federated Knowledge Graph infrastructure** for the **Beer Distribution Game**, responding to the Harvard Business Review article:

> **"When Supply Chains Become Autonomous"**  
> Carol Long, David Simchi-Levi, Andre P. Calmon, Flavio P. Calmon  
> Harvard Business Review, December 11, 2024  
> https://hbr.org/2024/12/when-supply-chains-become-autonomous

---

## 🎯 Research Question

### The HBR Experiment

The HBR research demonstrated that **4 AI agents** (GPT-5, Llama 4, Claude, etc.) playing the Beer Game autonomously achieved **67% cost reduction** compared to 4 human MBA students. However, their approach had critical limitations:

| HBR Results | Issue |
|-------------|-------|
| ✅ **67% cost reduction** | Good performance vs humans |
| ❌ **46% performance variance** | Highly inconsistent across runs |
| ❌ **Black-box reasoning** | Cannot audit why decisions were made |
| ❌ **Centralized orchestrator** | Single point of failure, bottleneck |
| ❌ **Information overload** | More data degraded advanced models |

**Key Problem:** The centralized orchestrator filtered and formatted information for the AI agents, creating:
- Arbitrary decisions about what data to share
- Unstructured text prompts (not semantic data)
- Implicit state in LLM memory (not explicit temporal state)
- No traceability of causal decisions

---

## 💡 Our Research Hypothesis

**Can a Federated Knowledge Graph platform enable BOTH human and AI players to achieve:**

1. ✅ **Better performance** - Maintain or exceed 67% cost reduction
2. ✅ **Lower variance** - Reduce 46% inconsistency to <30%
3. ✅ **Full auditability** - Every decision traceable to explicit rules
4. ✅ **Hybrid collaboration** - Humans + AI assistants working together
5. ✅ **No bottleneck** - Federated architecture scales without orchestrator

---

## 🏗️ Our Approach: Federated Temporal Knowledge Graphs

We replace the centralized orchestrator with **4 federated Knowledge Graphs** (one per supply chain actor), providing:

### Platform Capabilities

✅ **Structured temporal state (RDF/OWL)**
- Each week is an explicit entity with complete state snapshot
- Inventory, orders, shipments modeled as semantic triples
- No implicit memory - all state queryable and auditable

✅ **Federated SPARQL queries (distributed access)**
- Each actor maintains own KG while querying unified view
- Zero data duplication (single source of truth)
- No central orchestrator bottleneck

✅ **Explicit causal rules (auditable logic)**
- Business logic encoded as SPARQL UPDATE queries
- Every decision traceable to specific conditions
- Regulators/managers can inspect and tune thresholds

✅ **Player-agnostic interface**
- Platform supports algorithmic, AI, or human players
- All players access same structured information
- Decisions made via SPARQL queries, not unstructured prompts

---

## 🎮 Platform vs Players

### What This Project Provides

**This is NOT a simulation of the Beer Game.**  
**This IS a platform infrastructure where players (AI, human, or algorithmic) can make informed decisions.**

```
┌─────────────────────────────────────────────────────────┐
│         BG_Supply_Chain (Federated Platform)            │
│  - Structured temporal state (RDF/OWL)                  │
│  - Auditable queries (SPARQL)                           │
│  - Explicit business rules                              │
│  - Real-time visibility across actors                   │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
    Player 1         Player 2        Player 3        Player 4
    (Retailer)      (Wholesaler)   (Distributor)    (Factory)
         │               │               │               │
    Can be:         Can be:         Can be:         Can be:
    • Algorithm     • GPT-5         • Human         • Claude-3
    • Human         • Algorithm     • Llama-4       • Gemini
    • AI agent      • Human+AI      • Algorithm     • Human+AI
```

**Key Insight:** The platform provides infrastructure; **different players can be tested** to compare performance, variance, and explainability.

---

## 📊 Current Implementation: V3 Algorithmic Baseline

### Purpose: Platform Validation

V3 demonstrates that the federated platform works correctly using a simple algorithmic player (ORDER-UP-TO policy) replicated across all 4 actors.

**Why algorithmic first?**
- ✅ **Deterministic** - Validates platform correctness (no AI randomness)
- ✅ **Low variance** - <5% (proves federation is stable)
- ✅ **Auditable baseline** - Every decision traceable
- ✅ **Platform ready** - Infrastructure validated for AI experiments

### Results

| Actor | Accuracy | Variance | Status |
|-------|----------|----------|--------|
| Retailer | 100% | <1% | ✅ Perfect |
| Wholesaler | 95% | <2% | ✅ Excellent |
| Distributor | 75% | <3% | ⚠️ Expected lag |
| Factory | 70% | <5% | ⚠️ Expected lag |

**Key Achievement:** ✅ **Platform infrastructure validated** - Federation operational, zero duplication, ready for AI players

> 📊 **For detailed V3 results:** See [README_V3.md](./README_V3.md)

---

## 🚀 Experimental Roadmap

### Phase 1: Platform Validation ✅ (V3 - Complete)

- [x] Federated KG architecture working
- [x] Temporal state management
- [x] Algorithmic baseline tested (100% Retailer, 95% Wholesaler)
- [x] Visualization tools created
- [x] Documentation complete

### Phase 2: AI Player Experiments 🔄 (V4 - Planned)

**Goal:** Test platform with 4 AI agents accessing structured KG data

**Hypothesis:**
- Performance: ≥67% cost reduction (match or exceed HBR)
- Variance: <30% (better than HBR's 46%)
- Explainability: 100% auditable (vs HBR's black box)

**Players to test:**
- GPT-5 (OpenAI)
- Claude-3 (Anthropic)
- Llama-4 (Meta)
- Gemini (Google)

### Phase 3: Diverse Strategy Experiments 🔄 (V5 - Planned)

| Setup | Retailer | Wholesaler | Distributor | Factory | Research Question |
|-------|----------|------------|-------------|---------|------------------|
| Baseline | Algorithm | Algorithm | Algorithm | Algorithm | Platform validation ✅ |
| Homogeneous AI | GPT-5 | GPT-5 | GPT-5 | GPT-5 | Single AI type variance |
| Heterogeneous AI | GPT-5 | Claude-3 | Llama-4 | Gemini | AI diversity impact |
| Mixed | Algorithm | GPT-5 | Algorithm | Claude-3 | Hybrid performance |
| Human+AI | Human | AI assistant | Human | AI assistant | Augmented decisions |

### Phase 4: Human Player Experiments 🔄 (V6 - Planned)

**Setups:**
1. **4 Humans** (MIT baseline replication)
2. **4 Humans + KG dashboards** (augmented with platform)
3. **2 Humans + 2 AIs** (collaborative teams)
4. **4 Humans + AI assistants** (AI suggests, human decides)

---

## 🔬 Platform vs HBR: Key Advantages

| Feature | HBR (Centralized) | Our Platform (Federated) |
|---------|-------------------|-------------------------|
| **Architecture** | Central orchestrator | Federated KGs (4 repos) |
| **Data format** | Unstructured text | Structured RDF/OWL |
| **State** | Implicit (LLM memory) | Explicit (temporal entities) |
| **Access** | Orchestrator filters | Direct SPARQL queries |
| **Traceability** | Black box ❌ | Auditable ✅ |
| **Bottleneck** | Yes ❌ | No ✅ |
| **Variance** | 46% ⚠️ | <5% (algo), <30%? (AI) |
| **Player types** | AI only | Algo, AI, Human, Hybrid |

---

## 🚀 Quick Start (V3 Algorithmic Baseline)

### Prerequisites

1. **Ontotext GraphDB Free**
   - Download: https://graphdb.ontotext.com/
   
2. **Python 3.13+**
   ```bash
   python -m venv beer-game
   source beer-game/bin/activate
   pip install requests rdflib matplotlib seaborn pandas
   ```

### Setup

```bash
# 1. Start GraphDB
cd ~/graphdb
./bin/graphdb -d

# 2. Create repositories (via UI at http://localhost:7200)
#    - BG_Retailer, BG_Wholesaler, BG_Distributor, BG_Factory (GraphDB Free)
#    - BG_Supply_Chain (FedX Federation of above 4)

# 3. Load data
for repo in BG_Retailer BG_Wholesaler BG_Distributor BG_Factory; do
    curl -X POST http://localhost:7200/repositories/$repo/statements \
      -H "Content-Type: application/x-turtle" \
      --data-binary @beer_game_ontology.ttl
    
    curl -X POST http://localhost:7200/repositories/$repo/statements \
      -H "Content-Type: application/x-turtle" \
      --data-binary @beer_game_${repo#BG_}_kg_v3.ttl
done

# 4. Run simulation
cd SWRL_Rules
python advanced_simulation_v3.py
# Choose: 2 (spike), 6 (weeks)

# 5. Generate visualizations
python compare_results_graph_V3.py beer_game_report_*.json
```

**Output:** Dashboard + 4 actor graphs showing 100% Retailer accuracy

---

## 📁 Repository Structure

```
beer-game-federated-kg/
│
├── 📊 Platform Data
│   ├── beer_game_ontology.ttl           # Shared ontology
│   ├── beer_game_*_kg_v3.ttl             # V3 initial states
│
├── 🎮 Simulation (V3 Algorithmic)
│   └── SWRL_Rules/
│       ├── advanced_simulation_v3.py
│       ├── temporal_beer_game_rules_v3.py
│
├── 🤖 AI Players (V4 - TODO)
│   └── ai_players/
│       ├── gpt5_player.py
│       ├── claude3_player.py
│
├── 📊 Analysis
│   ├── compare_results_v3.py
│   ├── compare_results_graph_V3.py
│
└── 📚 Documentation
    ├── README.md (this file)
    ├── README_V3.md (technical deep-dive)
```

---

## 🤝 Contributing

We welcome:
- 🤖 AI player implementations
- 🎨 Human dashboards
- 📊 Analysis tools
- 🧪 Experiments

---

## 📚 Documentation

- [README.md](./README.md) - Research context, platform overview
- [README_V3.md](./README_V3.md) - V3 technical details

---

## 📖 References

1. Long, C., et al. (2024). "When Supply Chains Become Autonomous." *HBR*.
2. Forrester, J.W. (1961). *Industrial Dynamics*. MIT Press.

---

**Research Status:** V3 Platform validated ✅ → Ready for AI experiments (V4)

*Last updated: January 11, 2026*
