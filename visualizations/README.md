# Decision Timeline Dashboard

Interactive visualization of Beer Game decision contexts.

## Requirements

- GraphDB running on `http://localhost:7200`
- BG_Supply_Chain federated repository
- At least one simulation executed (contexts exist)

## Usage

1. Open `decision_timeline.html` in browser
2. Dashboard queries GraphDB automatically
3. Click decision points to see context details

## Features

- Timeline view of all decisions
- Risk levels color-coded
- Outcome quality indicators
- Context detail panel on click
- Multi-actor view with propagation

## Technical Stack

- Pure JavaScript (no build tools)
- D3.js v7 (loaded via CDN)
- Direct SPARQL queries to GraphDB


GraphDB blocks browser requests by default (CORS policy). Two solutions:

### Option 1: Enable CORS in GraphDB (recommended for production)

Edit `graphdb.properties`:
```
graphdb.workbench.cors.enable = true
graphdb.workbench.cors.origin = *
```
Then restart GraphDB.

### Option 2: Use CORS Proxy (quick setup)

```bash
# Terminal 1: Start CORS proxy
cd visualizations
python proxy.py

# Terminal 2: Start web server
python -m http.server 8000

# Open browser
open http://localhost:8000/decision_timeline.html
```

The proxy forwards requests from browser → GraphDB with proper CORS headers.

## CORS Setup

GraphDB blocks browser requests by default (CORS policy). Two solutions:

### Option 1: Enable CORS in GraphDB (recommended for production)

Edit `graphdb.properties`:
```properties
graphdb.workbench.cors.enable = true
graphdb.workbench.cors.origin = *
```

Then restart GraphDB.

Location of `graphdb.properties`:

- macOS: `~/Library/Application Support/GraphDB/conf/graphdb.properties`
- Linux: `~/.graphdb/conf/graphdb.properties`
- Windows: `%APPDATA%\GraphDB\conf\graphdb.properties`

### Option 2: Use CORS Proxy (quick setup - used by default)

```bash
# Terminal 1: Start CORS proxy
cd visualizations
python proxy.py

# Terminal 2: Start web server  
cd visualizations
python -m http.server 8000

# Open browser
open http://localhost:8000/decision_timeline.html
```

The proxy runs on port 8001 and forwards requests to GraphDB on port 7200 with proper CORS headers.

**Note:** `config.js` is configured to use the proxy (`http://localhost:8001`) by default.

## Screenshots

Dashboard shows:

- **Stats:** Total decisions, avg amplification, bullwhip events, weeks simulated
- **Timeline:** Interactive visualization with color-coded risk levels
- **Details:** Click any decision point to see complete context

Risk levels are color-coded:

- 🟢 Low (green)
- 🟡 Medium (yellow)  
- 🟠 High (orange)
- 🔴 Critical (red)

Circle size indicates amplification factor (larger = higher amplification).
