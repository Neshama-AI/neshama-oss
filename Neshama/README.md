# Neshama

**Version 0.4.0** - Deployment Release

Neshama is an AI-powered soul companion designed to provide empathetic, intelligent conversations.

## Features

- 💬 Natural language conversations
- 🌐 Web interface (v0.4)
- 🚀 One-click deployment script
- 📱 Responsive design

## Quick Start

```bash
cd Neshama/web
./deploy.sh
```

## Project Structure

```
Neshama/
├── web/
│   ├── deploy.sh           # Deployment script
│   ├── neshama_web.py      # Web application
│   └── templates/
│       └── index.html      # Web interface
└── docs/
    └── DEPLOYMENT.md       # Deployment guide
```

## Configuration

Set environment variables:
- `NESAMA_API_URL`: API endpoint (default: https://api.neshama.ai)
- `NESAMA_API_KEY`: API authentication key
- `PORT`: Web server port (default: 5000)

## License

MIT License
