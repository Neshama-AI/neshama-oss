# Neshama Workflow System

A visual workflow automation system for the Neshama Agent Framework.

## Architecture Overview

```
Neshama/workflow/
├── workflow_editor/    # Visual Workflow Editor (Frontend)
│   ├── index.html      # Main editor page
│   ├── css/
│   │   └── editor.css  # Editor styles
│   └── js/
│       ├── editor.js   # Main editor logic
│       ├── canvas.js   # Canvas implementation
│       └── nodes/       # Node components
│           ├── trigger.js
│           ├── action.js
│           ├── condition.js
│           └── transform.js
├── workflow_engine/    # Workflow Execution Engine (Backend)
│   ├── engine.py       # Main engine
│   ├── parser.py       # Workflow parser
│   ├── executor.py     # Node executor
│   ├── scheduler.py    # Task scheduler
│   └── storage.py      # Storage module
└── workflows/          # Pre-built templates
    ├── daily_briefing.yaml
    ├── weather_reminder.yaml
    ├── weekly_summary.yaml
    └── welcome_flow.yaml
```

## Quick Start

### Frontend

Simply open `workflow_editor/index.html` in a browser:

```bash
# Using Python
python -m http.server 8080

# Or open directly
open workflow_editor/index.html
```

### Backend

```bash
cd workflow_engine

# Install dependencies
pip install pyyaml apscheduler

# Run the engine
python engine.py
```

## Node Types

### 1. Trigger Nodes
- **Schedule Trigger**: Cron-based scheduling (e.g., `0 8 * * *`)
- **Event Trigger**: Keyword or intent-based
- **Webhook Trigger**: HTTP endpoint trigger

### 2. Action Nodes
- Send messages
- Call skills
- Get information
- Generate content
- Call external APIs

### 3. Condition Nodes
- If/Else branches
- Loops
- Delays

### 4. Transform Nodes
- Variable assignment
- Format conversion
- Data extraction

## Workflow JSON Format

```json
{
  "name": "Workflow Name",
  "trigger": {
    "type": "schedule",
    "cron": "0 8 * * *"
  },
  "nodes": [
    {
      "id": "node_1",
      "type": "action",
      "action": "get_weather",
      "params": {"city": "Beijing"}
    }
  ],
  "edges": [
    {"from": "node_1", "to": "node_2"}
  ]
}
```

## Features

- [x] Visual drag-and-drop workflow editor
- [x] Node connection with input/output ports
- [x] Double-click to edit node parameters
- [x] Right-click context menu
- [x] Canvas zoom and pan
- [x] Grid alignment
- [x] Local storage persistence
- [x] Export/Import workflows
- [x] Cron expression support
- [x] Pre-built workflow templates
- [x] Python execution engine

## License

MIT License
