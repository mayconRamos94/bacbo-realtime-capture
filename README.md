# BacBo Stream Pro

Projeto com:
- WebSocket resiliente
- PostgreSQL (asyncpg)
- Envio para endpoint
- Logs estruturados

## Rodar

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

Configure o PostgreSQL em app/storage/database.py

python app/main.py
