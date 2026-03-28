from mitmproxy import http

def request(flow: http.HTTPFlow):
    if flow.request.method == "GET":
        url = flow.request.pretty_url

        # garante que é websocket handshake
        if "Upgrade" in flow.request.headers:
            if "websocket" in flow.request.headers.get("Upgrade", "").lower():
                
                if "atlasbr.evo-games.com" in url and "bacbo" in url:
                    
                    ws_url = url.replace("https://", "wss://")

                    print("\n🔥 WS BACBO REAL:")
                    print(ws_url)

                    with open("ws_url.txt", "w") as f:
                        f.write(ws_url)