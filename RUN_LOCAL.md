# AgentTrade — Local Run Guide

## Requirements
- Python 3.10 or higher
- Internet (live data ke liye)

## Step 1: Setup

```bash
# Project folder mein jao
cd Multi-agent-trading-strategy-

# Virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac / Linux)
source .venv/bin/activate

# Install packages
pip install -r requirements.txt

# Config file
copy .env.example .env          # Windows
# cp .env.example .env          # Mac/Linux
```

## Step 2: Run Server

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Step 3: Open Dashboard

Browser mein open karo:

**http://127.0.0.1:8000**

## Common Errors

### 1. `ModuleNotFoundError: No module named 'fastapi'`
```bash
pip install -r requirements.txt
```

### 2. Port already in use
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001
```
Phir open: http://127.0.0.1:8001

### 3. `static/index.html` not found
Confirm folder structure:
```
Multi-agent-trading-strategy-/
  app/main.py
  static/index.html
  requirements.txt
```

### 4. Scan fails / empty results
- Internet on hona chahiye
- MrNasdog / Binance public APIs reachable honi chahiye
- Pehli scan 20-40 seconds le sakti hai

## Quick Test
Server start hone ke baad terminal mein:
```bash
curl http://127.0.0.1:8000/health
```
Response mein `"status":"ok"` aana chahiye.
