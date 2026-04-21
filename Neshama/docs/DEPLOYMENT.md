# Neshama Deployment Guide v0.4

## Prerequisites

- Python 3.8+
- Linux server (Ubuntu 20.04+ recommended)
- Nginx (optional, for production)
- systemd

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/Neshama-AI/neshama-oss.git
cd neshama-oss/Neshama/web
```

### 2. Configure Environment
```bash
export NESAMA_API_URL="https://api.neshama.ai"
export NESAMA_API_KEY="your-api-key"
export PORT=5000
```

### 3. Run Deployment
```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

## Systemd Service Setup

Create `/etc/systemd/system/neshama-web.service`:
```ini
[Unit]
Description=Neshama Web Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/neshama/web
Environment="NESAMA_API_URL=https://api.neshama.ai"
ExecStart=/usr/bin/python3 neshama_web.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable neshama-web
sudo systemctl start neshama-web
```

## Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Check logs
```bash
sudo journalctl -u neshama-web -f
```

### Verify health
```bash
curl http://localhost:5000/health
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check |
| `/api/chat` | POST | Chat API |

## Update Procedure

```bash
cd /opt/neshama
git pull origin master
./deploy.sh
```
