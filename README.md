# BacBo Real-Time Capture Service

Sistema de captura em tempo real dos resultados do jogo Bac Bo via WebSocket,
com reconexão automática, auto-recovery e estabilidade 24h/dia.

---

## Arquitetura

```
Chrome (jogo aberto com CDP ativo)
    ↓
mitmproxy (intercepta WebSocket → salva ws_url.txt)
    ↓
auto_refresh.py (renova sessão automaticamente via CDP)
    ↓
watchdog.py (garante que o processo nunca morre)
    ↓
main.py → ws_client.py (conecta, reconecta, auto-recovery)
    ↓
PostgreSQL (salva resultados)
    ↓
API REST (http://localhost:8000)
```

---

## Requisitos

- Python 3.11 ou 3.12
- Google Chrome instalado
- PostgreSQL rodando e acessível
- mitmproxy instalado (`pip install mitmproxy`)
- Proxy do Windows configurado em `127.0.0.1:8080`

---

## Instalação (feita uma única vez)

### 1. Criar e ativar o ambiente virtual

```powershell
python -m venv venv
venv\Scripts\activate
```

> Se aparecer erro de execução de scripts:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
> Depois rode o `activate` novamente.

### 2. Instalar dependências

```powershell
pip install fastapi uvicorn websockets asyncpg aiohttp python-dotenv requests websocket-client --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

> O `--trusted-host` é necessário porque o mitmproxy intercepta o SSL do pip.

### 3. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:5432/BANCO
ENDPOINT_URL=
```

> `ENDPOINT_URL` pode ficar vazio se não usar webhook externo.

### 4. Instalar certificado do mitmproxy (uma única vez)

Com o mitmproxy rodando, acesse no Chrome:

```
http://mitm.it
```

- Baixe o certificado para **Windows**
- Instale com duplo clique
- Escolha **"Usuário Atual"**
- Armazene em **"Autoridades de Certificação Raiz Confiáveis"**
- Conclua a instalação

### 5. Configurar proxy do Windows (uma única vez)

Vá em **Configurações → Rede e Internet → Proxy** e configure:
- Usar um servidor proxy: **Ativado**
- Endereço: `127.0.0.1`
- Porta: `8080`
- Clique em **Salvar**

---

## Como rodar (uso diário)

Você vai precisar de **4 terminais abertos** simultaneamente.

---

### Terminal 1 — mitmproxy

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
mitmproxy -s mitm_script.py --ssl-insecure
```

> O mitmproxy vai capturar automaticamente a URL do WebSocket e salvar em `ws_url.txt`.

---

### Terminal 2 — Chrome com CDP

> **Importante:** o Chrome precisa ser aberto com `--remote-debugging-port=9222` para o auto-refresh funcionar sem abrir janelas novas.

Primeiro, descubra o caminho do Chrome:
1. Pesquise `Chrome` na barra do Windows
2. Clique com botão direito → **Abrir local do arquivo**
3. Clique com botão direito no ícone → **Propriedades**
4. Copie o caminho do campo **Destino**

Agora abra o Chrome assim (substitua o caminho se necessário):

```powershell
taskkill /F /IM chrome.exe /T
Start-Process "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222"
```

> O `taskkill` garante que não há processos antigos do Chrome que bloqueiem o CDP.
> Após abrir o Chrome, acesse o site, faça login e abra o jogo **Bac Bo**.

---

### Terminal 3 — Poller (watchdog)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
python watchdog.py
```

> **Use sempre o `watchdog.py`** em vez do `main.py` direto.
> O watchdog reinicia o processo automaticamente se ele morrer por qualquer razão.

---

### Terminal 4 — Auto-refresh de sessão

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
python auto_refresh.py
```

> Monitora o token da sessão e recarrega a aba do jogo automaticamente via CDP
> quando o token estiver próximo de expirar — sem abrir janelas novas.

---

## Verificar que está funcionando

### Terminal 3 (poller) deve mostrar:

```
[URL] Primeira URL capturada: wss://atlasbr.evo-games.com/...
[WS] Conectando (tentativa 1/5) → wss://atlasbr.evo-games.com/...
[WS] Conexão estabelecida ✓
[WS] Primeira mensagem recebida — conexão estável ✓
RESULT -> Banker | P:5 vs B:7
Event saved successfully
```

### Terminal 4 (auto-refresh) deve mostrar:

```
[AUTO-REFRESH] CDP ativo na porta 9222 ✓
[AUTO-REFRESH] Primeiro token detectado ✓
...
[AUTO-REFRESH] Aba do jogo encontrada — recarregando via CDP...
[AUTO-REFRESH] Aba recarregada com sucesso ✓
[AUTO-REFRESH] Novo token detectado (anterior tinha 420s) ✓
```

---

## API disponível

| Endpoint | Descrição |
|----------|-----------|
| `http://localhost:8000/health` | Status do serviço |
| `http://localhost:8000/results` | Últimos 50 resultados |
| `http://localhost:8000/stats` | Estatísticas (Player/Banker) |

---

## Monitorar logs em tempo real

```powershell
Get-Content bacbo_poller.log -Wait -Tail 50
```

A cada 5 minutos aparece o health log:

```
[HEALTH] Uptime: 01h23m45s | Último RESULT: 12s atrás | Tentativas: 0/5
```

---

## Sistema de reconexão e auto-recovery

O poller tem 2 modos de operação automática:

### Modo NORMAL (tentativas 1 a 5)
Reconecta com backoff exponencial: 2s → 4s → 8s → 16s → 30s.
Se uma URL nova chegar do mitmproxy durante o backoff, acorda imediatamente.

### Modo RECOVERY (após 5 falhas consecutivas)
Para de tentar com a URL atual e aguarda o mitmproxy capturar uma sessão nova (até 60s).

```
CONECTA
  → falha → tentativa 1/5
  → falha → tentativa 2/5
  → ...
  → falha → tentativa 5/5
  → RECOVERY: aguarda nova URL (60s)
      → URL nova chegou → CONECTA (zera contadores)
      → timeout        → tenta com URL atual → reinicia ciclo
```

---

## Auto-refresh de sessão

O `auto_refresh.py` usa o Chrome DevTools Protocol (CDP) para renovar a sessão automaticamente:

| Situação | Ação |
|----------|------|
| Achou aba do jogo | Recarrega ela (`Page.reload`) |
| Não achou aba do jogo, CDP ativo | Navega aba existente para o jogo |
| CDP não disponível | Abre nova janela como fallback |

> O tempo padrão de renovação é **7 minutos**. Para ajustar, edite `TOKEN_MAX_AGE_SECONDS` no `auto_refresh.py`.

---

## Logs

| Arquivo | Descrição |
|---------|-----------|
| `bacbo_poller.log` | Log principal do poller (10MB × 5 arquivos rotativos) |
| `watchdog.log` | Log do watchdog (reinicializações do processo) |
| `auto_refresh.log` | Log do auto-refresh de sessão |

---

## Estrutura do projeto

```
bacbo-improved/
├── main.py                     # Entry point
├── watchdog.py                 # Guarda-cão: reinicia o processo se morrer
├── auto_refresh.py             # Renovação automática de sessão via CDP
├── mitm_script.py              # Script do mitmproxy (captura WS URL)
├── .env                        # Variáveis de ambiente (criar manualmente)
├── ws_url.txt                  # Gerado automaticamente pelo mitmproxy
├── bacbo_poller.log            # Gerado automaticamente
├── watchdog.log                # Gerado automaticamente
├── auto_refresh.log            # Gerado automaticamente
└── app/
    ├── api/
    │   └── routes.py           # Endpoints REST
    ├── capture/
    │   └── ws_client.py        # Poller WebSocket com auto-recovery
    ├── config/
    │   └── settings.py         # Leitura do .env
    ├── domain/
    │   └── event_processor.py  # Processamento e deduplicação de eventos
    ├── service/
    │   └── session_service.py  # Captura de sessão via Chrome debug
    ├── storage/
    │   ├── database.py         # Pool PostgreSQL
    │   └── event_repository.py # Persistência e envio ao endpoint
    └── utils/
        └── logger.py           # Logger com arquivo rotativo
```