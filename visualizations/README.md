# Decision Timeline Dashboard

Interactive visualization of Beer Game decision contexts using V3.1 Context Knowledge Graph.

## Requirements

- GraphDB running on `http://localhost:7200`
- BG_Supply_Chain federated repository
- At least one simulation executed (contexts exist)

## Quick Start

### 1. Start CORS Proxy
```bash
cd visualizations
python proxy.py
```

### 2. Start Web Server (in another terminal)
```bash
cd visualizations
python -m http.server 8000
```

### 3. Open Dashboard
```bash
open http://localhost:8000/decision_timeline.html
```

## Features

- **Interactive Timeline:** Click decision points to explore contexts
- **Stats Dashboard:** Total decisions, avg amplification, bullwhip events
- **Color-coded Risk:** Low (🟢) → Medium (🟡) → High (🟠) → Critical (🔴)
- **Size-coded Amplification:** Larger circles = higher order/demand ratio
- **Context Details:** Full decision state, assessment, and outcome
- **Multi-actor View:** See all supply chain actors on one timeline
- **Outcome Tracking:** Quality badges, bullwhip indicators, stockout flags

## CORS Configuration

GraphDB blocks browser requests by default (CORS policy). Two solutions:

### Option 1: Use CORS Proxy (Default - Easy Setup)

The included `proxy.py` forwards browser requests to GraphDB with proper CORS headers.
```bash
python proxy.py  # Runs on :8001, forwards to GraphDB :7200
```

**Note:** `config.js` is pre-configured to use the proxy at `http://localhost:8001`.

### Option 2: Enable CORS in GraphDB (Production)

Edit `graphdb.properties` and restart GraphDB:
```properties
graphdb.workbench.cors.enable = true
graphdb.workbench.cors.origin = *
```

**Location of `graphdb.properties`:**
- macOS: `~/Library/Application Support/GraphDB/conf/graphdb.properties`
- Linux: `~/.graphdb/conf/graphdb.properties`
- Windows: `%APPDATA%\GraphDB\conf\graphdb.properties`

If using this option, update `config.js`:
```javascript
graphdb: {
    url: 'http://localhost:7200',  // Direct to GraphDB
    repository: 'BG_Supply_Chain'
}
```

## Dashboard Overview

### Stats Cards
- **Total Decisions:** Count across all actors
- **Avg Amplification:** Mean order/demand ratio
- **Bullwhip Events:** Decisions with amplification > 1.5x
- **Weeks Simulated:** Timeline span

### Timeline Visualization
- **X-axis:** Week numbers
- **Y-axis:** Supply chain actors (Retailer, Wholesaler, Distributor, Factory)
- **Circle color:** Risk level at decision time
- **Circle size:** Amplification factor (larger = more amplification)
- **Small dots:** Outcome quality indicator

### Context Detail Panel (Click to View)
- **Decision:** Order quantity, policy, amplification
- **State:** Inventory, backlog, coverage
- **Assessment:** Risk level, perceived trend, demand rate
- **Outcome:** Quality badge, bullwhip/stockout indicators, result description

## Technical Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Visualization:** D3.js v7 (loaded via CDN)
- **Data Source:** Direct SPARQL queries to GraphDB
- **CORS Proxy:** Python 3 http.server
- **No build tools required** - runs in any modern browser

## Files

- `decision_timeline.html` - Main dashboard (self-contained)
- `proxy.py` - CORS proxy server
- `css/timeline.css` - Styling and layout
- `js/config.js` - GraphDB connection and color schemes
- `js/queries.js` - SPARQL query functions
- `js/timeline.js` - D3.js visualization logic

## Troubleshooting

### No data showing
1. Ensure GraphDB is running: `curl http://localhost:7200/repositories`
2. Run a simulation to create contexts: `cd SWRL_Rules && python advanced_simulation_v3.py`
3. Check browser console (F12) for errors

### CORS errors
1. Ensure proxy is running on port 8001
2. Verify `config.js` points to `http://localhost:8001`
3. Check proxy terminal for error messages

### "Failed to fetch" errors
1. Verify GraphDB is accessible: `curl http://localhost:7200/repositories`
2. Ensure BG_Supply_Chain repository exists
3. Check that contexts were created (see query results in GraphDB Workbench)

## Example Queries

The dashboard uses these SPARQL queries (see `js/queries.js`):

- `fetchContexts()` - All decision contexts with full details
- `fetchActorStats()` - Aggregated statistics per actor

You can run these manually in GraphDB Workbench for debugging.

## Development

To modify the dashboard:

1. Edit files in `visualizations/`
2. Refresh browser (no build step needed)
3. Check browser console for JavaScript errors
4. Use GraphDB Workbench to test SPARQL queries

Color schemes and visual settings are in `js/config.js`.
