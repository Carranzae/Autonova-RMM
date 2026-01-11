# 🚀 Autonova RMM

**Remote Monitoring & Management Ecosystem for Windows**

A high-performance RMM system for deep Windows diagnostics, cleaning, and repair, controlled from a cross-platform dashboard.

## 📐 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Admin PWA     │────▶│  Cloud Server   │◀────│  Client Agent   │
│   (The Pilot)   │     │   (The Brain)   │     │   (The Ghost)   │
│  React+Tailwind │     │  FastAPI+Redis  │     │  Python Binary  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📁 Project Structure

```
autonova-rmm/
├── app_client/          # Windows Agent (Python)
├── cloud_server/        # Backend API (FastAPI)
└── admin_pwa/           # Admin Dashboard (React)
```

## 🔧 Quick Start

### Cloud Server
```bash
cd cloud_server
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Client Agent
```bash
cd app_client
pip install -r requirements.txt
python -m src.main
```

### Admin PWA
```bash
cd admin_pwa
npm install
npm run dev
```

## 🔒 Security Features

- **mTLS/AES-256** encrypted WebSocket tunnel
- **JWT** authentication for admin commands
- **Zero-trace** uninstallation
- **UAC elevation** with privilege management

## 📋 Available Commands

| Command | Description |
|---------|-------------|
| `health_check` | CPU, Memory, Disk, Network analysis |
| `deep_clean` | Registry cleanup, temp purge |
| `sys_fix` | SFC, DISM, Network reset |
| `full_optimize` | All of the above in sequence |

## 📜 License

Proprietary - All Rights Reserved
