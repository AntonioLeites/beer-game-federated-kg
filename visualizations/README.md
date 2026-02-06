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

## CORS Setup

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
