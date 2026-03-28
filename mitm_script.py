from mitmproxy import http

def request(flow: http.HTTPFlow):
    headers = flow.request.headers

    # detecta handshake websocket real
    if headers.get("Upgrade", "").lower() == "websocket":
        
        url = flow.request.pretty_url

        if "atlasbr.evo-games.com" in url and "bacbo" in url:
            
            ws_url = url.replace("https://", "wss://")

            # salva direto
            with open("ws_url.txt", "w") as f:
                f.write(ws_url)

            print("\n🔥 WS CAPTURADO COM SUCESSO")