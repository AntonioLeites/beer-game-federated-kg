# Beer Distribution Game - Federated Knowledge Graph Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![GraphDB](https://img.shields.io/badge/GraphDB-10.x-green.svg)](https://graphdb.ontotext.com/)

## 📄 Research Context

This repository implements a **Federated Knowledge Graph platform** for the **Beer Distribution Game**, motivated by the Harvard Business Review article:

> **"When Supply Chains Become Autonomous"**  
> Carol Long, David Simchi-Levi, Andre P. Calmon, Flavio P. Calmon  
> Harvard Business Review, December 11, 2025  
> https://hbr.org/2024/12/when-supply-chains-become-autonomous

The HBR study showed that AI agents can outperform humans in supply chain coordination. However, it relied on a **centralized, black-box orquestration layer**.  

This project investigates how such autonomy can be made **scalable, auditable, explainable, and reproducible** by externalizing decision-making into **Federated Knowledge Graphs**.

---

## 🎯 Research Question

### The HBR Experiment

The HBR study demonstrated that **four AI agents** (GPT-5, Llama 4, Claude, etc.) playing the Beer Game autonomously achieved **67% cost reduction** compared to four human MBA students. 

However, the approach exhibited critical limitations:

| HBR Results | Issue |
|-------------|-------|
| ✅ **67% cost reduction** | Strong performance vs humans |
| ❌ **46% performance variance** | Highly inconsistent across runs |
| ❌ **Black-box reasoning** | Decisions not auditable |
| ❌ **Centralized orchestrator** | Bottleneck and single point of failure,  |
| ❌ **Information overload** | More data degraded advanced models |

**Root cause:** a centralized orchestrator filtered, summarized, and formatted information for the agents, leading to:

- Arbitrary decisions about what data to share
- Unstructured text prompts instead of semantic data
- Implicit state stored in LLM memory
- No traceability of causal decisions

---

## 💡 Research Hypothesis

Can a **Federated Knowledge Graph platform** enable both **human and AI players** to achieve:

- ✅ Comparable or **Better performance** - (≥67% cost reduction)
- ✅ **Lower variance** - ( <30%, vs HBR's 46%)
- ✅ **Full auditability**  of decisions
- ✅ **Human-AI collaboration** 
- ✅ **Scalability** without a centralized orchestrator

---
## 🧠 Core Platform Innovations

The core contribution of this repository is **not an AI agent**, but an infrastructure that makes
decision-making: 

- Explicit
- Auditable
- Reproducible
- Comparable across humans and machines.

Cognition is externalized from LLM memory into an **explicit, queryable, temporal Knowledge Graph**.



### 1️⃣ Federated Architecture (No Central Orchestrator)

The centralized orchestrator used in the HBR study is replaced by a **stateless federation layer** built on **GraphDB FedX**.

Architecture principles:

- Four independent Knowledge Graphs:
  - Retailer
  - Wholesaler
  - Distributor
  - Factory
- One federated endpoint BG_Supply_Chain
- Local writes, federated reads
- No message passing, no data duplication
- No single point of failure

Federation replaces:

- Manual propagation of orders and shipments
- Orchestrator-controlled data visibility
- Centralized filtering and summarization

Each actor queries **exactly the information it needs**, when it needs it.

### 2️⃣ Temporal State-Based Modeling (Markovian)

The platform uses a **state-based temporal model**, not an event-log.

Each week is a first-class RDF entity capturing the complete system snapshot:

- Inventory
- Orders
- Shipments
- Calculated metrics

**Key principle (Markovian):**

>Week N+1 depends only on the complete state of Week N plus explicit business rules.

This enables:

- Direct causal analysis
- Time-series queries across actors
- Counterfactual reasoning ("_what if demand spiked earlier?_")


### 3️⃣ Explicit Causal Logic via SPARQL Rules

All business logic is encoded as **SPARQL UPDATE rules**, not embedded in code or LLM prompts. 

Examples include:

- Demand-rate smoothing
- Inventory coverage calculation
- Order-up-to policies
- Bullwhip detection
- Cost calculation

**Why SPARQL rules?**

- **Auditable:** every decision is traceable to a rule
- **Explainable:** " _why was this happen?_" → inspect the rule
- **Modifiable:** tune thresholds without code changes
- **Federated:** rules query across repositories transparently

This directly replaces black-box reasoning in LLM-only approaches.


---

### 4️⃣ Player-agnostic interface

This Platform is **not tied to a player type:**  

Supported players:

- Algorithmic policies
- AI agents (GPT‑5, Claude‑4.5, Gemini, Llama‑4)
- Human players
- Hybrid human + AI assistants

All players:

- Access the same structured data
- Query via SPARQL
- Operate on explicit temporal state

### 5️⃣ Deterministic Algorithmic Baseline (V3)

Before introducing AI agents, the platform is validated using a **deterministic ORDER-UP-TO policy policy**  replicated across all actors.

**Why algorithmic first?**

- **Deterministic** - Validates correctness 
- Very **low variance** (<5%)
- **Fully Auditable** 
- **No AI randomness** masking platform issues 


---

## 🎮 Platform vs Players

This project is **not a fixed Beer Game simulation**.

It is a **research platform** where different players can be plugged in and compared.

```

┌─────────────────────────────────────────────────────────┐
│         BG_Supply_Chain (Federated Platform)            │
│             - Temporal state (RDF/OWL)                  │
│             - Federated SPARQL access                   │
│             - Explicit causal rules                     │                
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
     Retailer       Wholesaler      Distributor       Factory


```
---

## 📊 Current Implementation- V3 (Platform Validation)



### Results (Spike Pattern)

| Actor | Accuracy | Variance | Status |
|-------|----------|----------|--------|
| Retailer | 100% | <1% | ✅ Perfect |
| Wholesaler | 95% | <2% | ✅ Excellent |
| Distributor | 75% | <3% | ⚠️ Expected lag |
| Factory | 70% | <5% | ⚠️ Expected lag |

**Key Achievement:** 
  the federated platform is validated and ready for AI and human experiments

> 🚀 **Quick Start:** See [Setup Instructions](#-quick-start-v3-algorithmic-baseline) 
> to run the V3 baseline yourself.

For full details, see [README_V3.md](./README_V3.md)

---

## ⚙️ V3 Execution Model

Each simulated week executes the following lifecycle:

1. Create temporal anchor (_Week N_)
2. Generate exogenous demand
3. Execute federated SPARQL business rules
4. Persist new local state
5. Query federated view for analysis


  ❌ No manual propagation of orders or shipments  
  ✅ Federation handles all cross-actor visibility


---
## 📊 Empirical Validation & Emergent Behavior

Even with a simple algorithmic policy, the platform reproduces known supply-chain dynamics:

- Bullwhip effect under demand spikes
- Information lag dampening upstream
- Cost amplification across tiers

This confirms the platform captures **real system behavior**,
not a toy or scripted simulation.

**Reproducibility:** All V3 results are deterministic and can be replicated 
by following the setup instructions. Raw data and validation scripts included.

---
## 🚀 Experimental Roadmap

### Phase 1: Platform Validation ✅ (V3)

- [x] Federated KG architecture working
- [x] Temporal state management
- [x] Deterministic baseline tested

### Phase 2: AI Player Experiments 🔄 (V4)

**Goals:** 

- Match or exceed HBR Performance
- Reduce Variance below 30%
- Achieve full explainability

Planned players: GPT-5, Claude-4.5, Llama-4, Gemini

### Phase 3: Strategy Diversity 🔄 (V5)

- Homogeneous AI
- Heterogeneous AI
- Mixed algorithmic + AI
- Human + AI collaboration

### Phase 4: Human Experiments 🔄 (V6)

- 4 Humans (MIT baseline replication)
- Humans + KG dashboards
- Mixed humans/AI teams

---

## 🔬 Platform vs HBR: Key Advantages

| Feature | HBR (Centralized) | This Platform (Federated) |
|---------|-------------------|-------------------------|
| Architecture | Central orchestrator | Federated KGs  |
| Data format | Unstructured text | RDF/OWL |
| State | Implicit (LLM memory) | Explicit temporal state |
| Traceability | ❌ Black box  | ✅ Auditable  |
| Bottleneck | ❌ Yes  | ✅ No |
| Player types | AI only | Algo, AI, Human, Hybrid |

---


## 📁 Repository Structure

```
beer-game-federated-kg/
├── Data/
├── SWRL_Rules/
├── Analysis/
├── AI Players/        # V4 – Planned
├── Documentation/
│   ├── README_V3.md
│   └── DESIGN_RATIONALE_UPDATED.md
```

---
## 🧭 Summary

This repository provides a **validated Federated Knowledge Graph platform** for studying decision-making in supply chains.

- V3 establishes a deterministic, auditable baseline
- V4+ will evaluate AI, human, and hybrid players
- The core contribution is an **explainable, federated, temporal decision infrastructure**

---
**Research Status:**
 V3 Platform validated → Ready for AI experiments (V4)

---

## 📖 References

- Long, C., et al. (2024). "When Supply Chains Become Autonomous." *HBR*.
- Forrester, J.W. (1961). *Industrial Dynamics*. MIT Press.

---

*Last updated: January 11, 2026*
