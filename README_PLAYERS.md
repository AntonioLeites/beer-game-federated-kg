# Player System - V4 AI Integration

## Overview

The Player System enables **algorithmic, AI, and human players** to compete in the Beer Game using the same federated Knowledge Graph platform.

**Key Innovation:** All players access identical structured data from the KG, ensuring fair comparison and full auditability.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         BG_Supply_Chain (Federated Platform)            │
│             - Temporal state (RDF/OWL)                  │
│             - SPARQL query interface                    │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
    AlgorithmicPlayer  GPT4Player  ClaudePlayer  HumanPlayer
         │               │               │               │
         └───────────────┴───────────────┴───────────────┘
                         │
                    [Base Player]
                 observe() → decide() → act()
```

---

## Player Types

### 1. **Algorithmic Player** (V3 Baseline)

**File:** `algorithmic_player.py`

**Policy:** ORDER-UP-TO (deterministic)

```python
target_inventory = demand_rate × 3
suggested_order = target - inventory + backlog
final_order = max(0, suggested_order)
```

**Characteristics:**
- ✅ Deterministic (0% variance)
- ✅ Fully auditable
- ✅ V3 validated (100% Retailer accuracy)

**Variants:**
- `AlgorithmicPlayer` - Standard (3 weeks coverage)
- `ConservativeAlgorithmicPlayer` - High safety stock (4 weeks)
- `AggressiveAlgorithmicPlayer` - Lean inventory (2 weeks)

---

### 2. **AI Player** (V4 - GPT-4, Claude, etc)

**Files:** 
- `ai_player.py` (abstract base)
- `gpt4_player.py` (GPT-4 implementation)
- `claude_player.py` (TODO)

**Decision Process:**
1. Query structured state from KG (inventory, backlog, demand_rate, alerts)
2. Build prompt with historical context
3. Call LLM API
4. Parse response (`ORDER: X | REASON: ...`)
5. Log decision with full reasoning

**Characteristics:**
- ⚠️ Non-deterministic (variance depends on temperature)
- ✅ Explainable (reasoning logged)
- ✅ Auditable (full prompt + response)
- 🎯 Research goal: <30% variance

**Variants:**
- `GPT4Player` - Standard
- `GPT4ConservativePlayer` - Modified system prompt (prioritize safety stock)
- `GPT4AggressivePlayer` - Modified system prompt (minimize inventory)

---

### 3. **Human Player** (V6 - Future)

**File:** `human_player.py` (TODO)

**Interface:** Web dashboard showing:
- Current state (inventory, backlog, coverage)
- Demand trend chart
- Incoming shipments table
- Risk alerts
- Optional AI suggestion

**Characteristics:**
- ⚠️ Slow (2-5 minutes per decision)
- ⚠️ High variance (emotional, strategic diversity)
- ✅ Augmented with KG data
- ✅ Optional AI assistant

---

## Usage

### Example 1: All Algorithmic (V3 Baseline)

```python
from algorithmic_player import AlgorithmicPlayer
from game_orchestrator import GameOrchestrator

players = {
    'Retailer': AlgorithmicPlayer(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer"
    ),
    'Wholesaler': AlgorithmicPlayer(...),
    'Distributor': AlgorithmicPlayer(...),
    'Factory': AlgorithmicPlayer(...)
}

orchestrator = GameOrchestrator(players, demand_pattern="spike")
report = orchestrator.simulate_weeks(start_week=2, num_weeks=5)

print(f"Total cost: ${report['metrics']['total_cost']:.2f}")
# Expected: ~$25-30 (V3 baseline)
```

---

### Example 2: Mixed (Algo + AI)

```python
from algorithmic_player import AlgorithmicPlayer
from gpt4_player import GPT4Player
import os

players = {
    'Retailer': GPT4Player(
        actor_uri="http://beergame.org/retailer#Retailer_Alpha",
        role="Retailer",
        kg_endpoint="BG_Retailer",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7
    ),
    'Wholesaler': AlgorithmicPlayer(...),
    'Distributor': AlgorithmicPlayer(...),
    'Factory': AlgorithmicPlayer(...)
}

orchestrator = GameOrchestrator(players, demand_pattern="spike")
report = orchestrator.simulate_weeks(start_week=2, num_weeks=5)

# Analyze GPT-4 reasoning
retailer_decisions = report['player_decisions']['Retailer']
for decision in retailer_decisions:
    print(f"Week {decision['week']}: {decision['decision']} units")
    print(f"Reasoning: {decision['reasoning']}")
```

---

### Example 3: All AI (Homogeneous)

```python
players = {
    'Retailer': GPT4Player(..., temperature=0.7),
    'Wholesaler': GPT4Player(..., temperature=0.7),
    'Distributor': GPT4Player(..., temperature=0.7),
    'Factory': GPT4Player(..., temperature=0.7)
}

# Research question: Does team coordination emerge?
# Expected variance: <30% (goal)
```

---

### Example 4: Heterogeneous AI

```python
players = {
    'Retailer': GPT4Player(...),           # GPT-4
    'Wholesaler': ClaudePlayer(...),       # Claude-3
    'Distributor': LlamaPlayer(...),       # Llama-4
    'Factory': GeminiPlayer(...)           # Gemini
}

# Research question: Does AI diversity help or hurt?
```

---

## Experimental Setup

### Variance Test (Replicate HBR Study)

```python
from experiment_algo_vs_gpt4 import run_variance_test

# Run 10 iterations of each setup
results = run_variance_test(api_key, num_runs=10)

print(f"Algorithmic variance: {results['algorithmic']['variance_pct']:.1f}%")
# Expected: ~0% (deterministic)

print(f"GPT-4 variance: {results['gpt4']['variance_pct']:.1f}%")
# Goal: <30% (vs HBR's 46%)
```

---

## Key Metrics

| Metric | Algorithmic (V3) | GPT-4 (V4 Goal) | HBR Baseline |
|--------|-----------------|----------------|--------------|
| **Total Cost** | $25-30 | <$30 | $100 (MBA) |
| **Variance** | <5% | **<30%** | 46% ⚠️ |
| **Explainability** | High ✅ | High ✅ | Low ❌ |
| **Auditability** | 100% ✅ | 100% ✅ | 0% ❌ |

---

## Implementation Status

| Player Type | Status | File |
|------------|--------|------|
| **Algorithmic** | ✅ Complete | `algorithmic_player.py` |
| **GPT-4** | ✅ Complete | `gpt4_player.py` |
| **Claude-3** | 🔄 Planned | `claude_player.py` |
| **Llama-4** | 🔄 Planned | `llama_player.py` |
| **Gemini** | 🔄 Planned | `gemini_player.py` |
| **Human** | ⏭️ Future | `human_player.py` |

---

## Adding New Players

### Step 1: Inherit from AIPlayer

```python
from ai_player import AIPlayer

class MyLLMPlayer(AIPlayer):
    def _call_llm(self, prompt: str) -> str:
        # Implement your LLM API call
        response = my_llm_api.complete(prompt)
        return response.text
    
    def get_player_type(self) -> str:
        return "my_llm_v1"
```

### Step 2: Test Standalone

```python
player = MyLLMPlayer(
    actor_uri="http://beergame.org/retailer#Retailer_Alpha",
    role="Retailer",
    kg_endpoint="BG_Retailer",
    api_key="..."
)

# Mock observation
observation = {
    'current': {'week': 3, 'inventory': 8, 'backlog': 0, ...},
    'history': [...],
    'alerts': []
}

decision = player.decide(observation)
print(f"Decision: {decision}")
print(f"Reasoning: {player.get_last_reasoning()}")
```

### Step 3: Integrate into Experiment

```python
players = {
    'Retailer': MyLLMPlayer(...),
    'Wholesaler': AlgorithmicPlayer(...),
    ...
}

orchestrator = GameOrchestrator(players)
report = orchestrator.simulate_weeks(2, 5)
```

---

## Next Steps

1. **Run baseline experiments** - Validate algorithmic player matches V3
2. **Test GPT-4 player** - Measure variance vs baseline
3. **Compare models** - GPT-4 vs Claude vs Llama
4. **Publish results** - Paper comparing platform to HBR study

---

## Files Overview

```
players/
├── base_player.py              # Abstract interface
├── algorithmic_player.py       # V3 baseline (ORDER-UP-TO)
├── ai_player.py                # Abstract AI player base
├── gpt4_player.py              # GPT-4 implementation
├── claude_player.py            # TODO
└── human_player.py             # TODO

game/
├── game_orchestrator.py        # Multi-player coordinator
└── metrics.py                  # Performance analysis

experiments/
├── experiment_algo_vs_gpt4.py  # Baseline vs AI comparison
└── experiment_variance.py      # Variance measurement
```

---

## Requirements

```bash
pip install requests rdflib openai anthropic
```

**API Keys needed:**
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## References

- HBR Study: "When Supply Chains Become Autonomous" (2024)
- V3 Platform Validation: [README_V3.md](./README_V3.md)
- Beer Game Original: Forrester, J.W. (1961)

---

*Last updated: January 11, 2026*
