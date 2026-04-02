# BacBo Real-Time Capture Service

Sistema de captura em tempo real dos resultados do jogo Bac Bo via WebSocket,
com reconexão automática, auto-recovery e estabilidade 24h/dia.

---

## Arquitetura

```
Chrome (jogo aberto)
    ↓
mitmproxy (intercepta WebSocket → salva ws_url.txt)
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
pip install fastapi uvicorn websockets asyncpg aiohttp python-dotenv --trusted-host pypi.org --trusted-host files.pythonhosted.org
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

---

## Como rodar (uso diário)

Você vai precisar de **3 terminais abertos** simultaneamente.

### Terminal 1 — mitmproxy

```powershell
venv\Scripts\activate
mitmproxy -s mitm_script.py --mode upstream:http://SEU_PROXY:PORTA --ssl-insecure
```

> Substitua `SEU_PROXY:PORTA` pelo endereço do seu proxy.
> O mitmproxy vai capturar automaticamente a URL do WebSocket e salvar em `ws_url.txt`.

### Terminal 2 — Chrome com proxy

Primeiro descubra o caminho exato do Chrome na sua máquina:

1. Clique na **barra de pesquisa do Windows** e digite `Chrome`
2. O Google Chrome vai aparecer nos resultados — **clique com o botão direito**
3. Clique em **"Abrir local do arquivo"**
4. Na pasta que abrir, **clique com o botão direito no ícone do Chrome**
5. Clique em **"Propriedades"**
6. Copie o caminho que aparece no campo **"Destino"**
   - Exemplo: `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`

Agora rode no PowerShell com o caminho que você copiou:

```powershell
Start-Process "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" -ArgumentList "--proxy-server=http://127.0.0.1:8080", "--ignore-certificate-errors"
```

> Exemplo real:
> ```powershell
> Start-Process "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" -ArgumentList "--proxy-server=http://127.0.0.1:8080", "--ignore-certificate-errors"
> ```
Aguarde a janela google abrir
Após abrir o Chrome:
1. Acesse o site do cassino
2. Faça login
3. Abra o jogo **Bac Bo**
4. O mitmproxy captura a URL automaticamente → `ws_url.txt` é criado

### Terminal 3 — Poller (watchdog)

```powershell
venv\Scripts\activate
python watchdog.py
```

> **Use sempre o `watchdog.py`** em vez do `main.py` direto.
> O watchdog reinicia o processo automaticamente se ele morrer por qualquer razão.

---

## Verificar que está funcionando

Nos primeiros segundos você deve ver no Terminal 3:

```
[URL] Primeira URL capturada: wss://atlasbr.evo-games.com/...
[WS] Conectando (tentativa 1/5) → wss://atlasbr.evo-games.com/...
[WS] Conexão estabelecida ✓
[RESULT] BANKER | P:3 vs B:7
Event saved successfully
```

### API disponível

| Endpoint | Descrição |
|----------|-----------|
| `http://localhost:8000/health` | Status do serviço |
| `http://localhost:8000/results` | Últimos 50 resultados |
| `http://localhost:8000/stats` | Estatísticas (Player/Banker) |

---

## Monitorar em tempo real

Em um quarto terminal, para acompanhar o log:

```powershell
Get-Content bacbo_poller.log -Wait -Tail 50
```

A cada 5 minutos aparece o health log confirmando que está vivo:

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
- Se nova URL chegar → reconecta imediatamente, zera contadores
- Se timeout de 60s → tenta mais uma vez com a URL atual e reinicia o ciclo

```
CONECTA
  → falha → tentativa 1/5
  → falha → tentativa 2/5
  → falha → tentativa 3/5
  → falha → tentativa 4/5
  → falha → tentativa 5/5
  → RECOVERY: aguarda nova URL (60s)
      → URL nova chegou → CONECTA (zera contadores)
      → timeout        → tenta com URL atual → reinicia ciclo
```

---

## Chrome: abrir ou fechar?

| Situação | Comportamento |
|----------|---------------|
| Chrome **aberto** em background | 24h sem intervenção ✅ |
| Chrome **fechado** | Funciona até a sessão expirar, depois precisa abrir de novo ⚠️ |

**Recomendação:** deixe o Chrome aberto em segundo plano com a aba do jogo.
Assim quando a sessão renovar, o mitmproxy captura automaticamente sem intervenção.

---

## Logs

| Arquivo | Descrição |
|---------|-----------|
| `bacbo_poller.log` | Log principal do poller (10MB × 5 arquivos rotativos) |
| `watchdog.log` | Log do watchdog (reinicializações do processo) |

---

## Estrutura do projeto

```
bacbo-improved/
├── main.py                     # Entry point
├── watchdog.py                 # Guarda-cão: reinicia o processo se morrer
├── mitm_script.py              # Script do mitmproxy (captura WS URL)
├── .env                        # Variáveis de ambiente (criar manualmente)
├── ws_url.txt                  # Gerado automaticamente pelo mitmproxy
├── bacbo_poller.log            # Gerado automaticamente
├── watchdog.log                # Gerado automaticamente
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