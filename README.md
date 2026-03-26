# BacBo Real-Time Capture Service

## Overview

This service captures Bac Bo game events in real time via WebSocket, processes them, ensures data consistency, and exposes the results through an API.

---

## Features

- Real-time event capture via WebSocket
- Automatic reconnection
- Duplicate event prevention
- PostgreSQL persistence
- API endpoints for data access

---

## Tech Stack

- Python (asyncio)
- WebSocket
- FastAPI
- PostgreSQL (asyncpg)

---

## Project Structure

app/
  api/
  capture/
  domain/
  storage/
  config/
  utils/
main.py

---

## How to Run

### 1. Create virtual environment

python -m venv venv

---

### 2. Activate environment

Windows (cmd/powershell):
venv\Scripts\activate

Git Bash:
source venv/Scripts/activate

---

### 3. Install dependencies

pip install -r requirements.txt

---

### 4. Configure environment

Create a `.env` file based on `.env.example`

Example:

WS_URL=wss://...
DATABASE_URL=postgresql://postgres:postgres@localhost:5440/bacbo
ENDPOINT_URL=

---

### 5. Run the application

python main.py

---

## API Endpoints

### Health

GET /health

Response:
{"status": "ok"}

---

### Results

GET /results?limit=50

Returns latest events

---

### Stats

GET /stats?limit=100

Returns aggregated data:
- total
- player wins
- banker wins
- win rates