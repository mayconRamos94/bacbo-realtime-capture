# BacBo Real-Time Capture Service

## Overview
This service captures Bac Bo game events in real time via WebSocket, processes the data, and stores it for further analysis.

The system is already running and being actively developed, with focus on low latency and data reliability.

---

## Features
- Real-time event capture via WebSocket
- Automatic reconnection and fault handling
- Event processing and filtering
- PostgreSQL persistence
- Structured data ready for analysis

---

## Tech Stack
- Python (asyncio)
- WebSocket
- PostgreSQL (asyncpg)

---

## Current Status
In progress

Current capabilities:
- Real-time capture working
- Data persistence implemented
- Stable connection handling

Next steps:
- API for data exposure
- Pattern detection (streaks, trends)
- Visualization layer

---

## Running Locally (Optional)

If you want to run the project locally:

```bash
python -m venv venv
source venv/Scripts/activate  # Windows (Git Bash)
pip install -r requirements.txt
python main.py