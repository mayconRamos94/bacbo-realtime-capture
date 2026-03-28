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

🧩 Visão Geral

O sistema funciona em 2 partes:

Captura automática do WebSocket (mitmproxy)
Processamento dos dados (backend Python)

👉 A configuração abaixo é feita uma única vez

🚀 1. Instalar dependências
✅ Python
Instalar Python 3.10+
✅ Google Chrome
Utilizado para acessar o jogo
🚀 2. Instalar dependências do projeto

No terminal, dentro da pasta do projeto:

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
🚀 3. Configurar variáveis (.env)

Criar arquivo .env:

DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
ENDPOINT_URL=
🚀 4. Iniciar o capturador (mitmproxy)

No terminal:

mitmproxy -s mitm_script.py
🔐 5. Configurar proxy no sistema (IMPORTANTE)

👉 Essa etapa permite capturar a conexão do jogo

No Windows:
Abrir configurações de proxy
Configurar proxy manual:
Endereço: 127.0.0.1  
Porta: 8080

✔ salvar

🔐 6. Instalar certificado (necessário para HTTPS)

Com o mitmproxy rodando:

Acessar no navegador:
http://mitm.it
Baixar o certificado para Windows
Instalar:
escolher Usuário Atual
armazenar em:
👉 "Autoridades de Certificação Raiz Confiáveis"

✔ concluir instalação

🚀 7. Capturar a sessão do jogo
Abrir o navegador
Acessar o site do cassino
Fazer login
Abrir o jogo Bac Bo

👉 Nesse momento o sistema irá:

detectar automaticamente o WebSocket
salvar no arquivo ws_url.txt
🚀 8. Rodar o backend

Em outro terminal:

python main.py
📊 9. Verificar funcionamento

Acessar no navegador:

http://localhost:8000/health
http://localhost:8000/results
http://localhost:8000/stats
🔁 10. Teste de estabilidade (IMPORTANTE)

Para validar o funcionamento contínuo:

Atualizar o jogo (F5)
Ou fechar e abrir novamente

👉 O sistema deve:

capturar nova sessão automaticamente
reconectar
continuar recebendo dados
✅ Resultado esperado
Captura em tempo real
Reconexão automática
Sem necessidade de atualizar URL manual
Dados sendo salvos continuamente
⚠️ Observações
A configuração do proxy é feita apenas uma vez
Após isso, o sistema funciona automaticamente
Caso queira, posso auxiliar na configuração inicial