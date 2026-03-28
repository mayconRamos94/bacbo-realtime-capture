import requests
import websocket
import json


def get_ws_url():
    # pega abas abertas no Chrome debug
    tabs = requests.get("http://localhost:9222/json").json()

    ws_debug_url = None

    for tab in tabs:
        if "start.bet" in tab.get("url", ""):
            ws_debug_url = tab["webSocketDebuggerUrl"]
            break

    if not ws_debug_url:
        ws_debug_url = tabs[0]["webSocketDebuggerUrl"]

    ws = websocket.create_connection(ws_debug_url)

    ws.send(json.dumps({
        "id": 1,
        "method": "Network.enable"
    }))

    print("👀 Capturando WebSocket...")

    while True:
        msg = json.loads(ws.recv())

        if "method" in msg and msg["method"] == "Network.webSocketCreated":
            url = msg["params"]["url"]

            if "evo-games.com" in url:
                print("🔥 WS CAPTURADO:")
                print(url)
                return url