# API Documentation

## Base URL

http://localhost:8000

---

## Endpoints

### Health

GET /health

Response:
{"status": "ok"}

---

### Results

GET /results

Query params:
- limit (optional)

Response:
[
  {
    "winner": "Player",
    "playerScore": 6,
    "bankerScore": 5,
    "timestamp": 123456789
  }
]

---

### Stats

GET /stats

Query params:
- limit (optional)

Response:
{
  "total": 100,
  "player": 55,
  "banker": 45,
  "player_rate": 0.55,
  "banker_rate": 0.45
}

---

## Notes

- Data is deduplicated before saving
- Results represent actual game outcomes