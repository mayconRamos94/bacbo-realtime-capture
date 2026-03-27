import asyncio
from playwright.async_api import async_playwright


GAME_URL = "https://start.bet.br/live-casino/game/2630915?provider=Evolution&from=%2Flive-casino"


async def get_ws_url():
    async with async_playwright() as p:

        context = await p.chromium.launch_persistent_context(
    user_data_dir="C:\\Users\\a879950\\AppData\\Local\\Google\\Chrome\\User Data",
    headless=False,
    args=[
        "--profile-directory=Default"
    ]
)

        page = context.pages[0] if context.pages else await context.new_page()

        # 🔥 TESTE DE LOGIN
        print("👉 Testando sessão...")
        await page.goto("https://start.bet.br")
        await asyncio.sleep(5)

        print("URL atual:", page.url)

        cookies = await context.cookies()
        print("Cookies:", cookies)

        input("👉 Veja o navegador: está logado? Pressione ENTER para continuar...")

        # conecta no CDP
        cdp = await context.new_cdp_session(page)
        await cdp.send("Network.enable")

        ws_url = None

        def handle_ws(event):
            nonlocal ws_url

            url = event.get("url", "")

            if "evo-games.com" in url:
                ws_url = url
                print("WS capturado:", ws_url)

        cdp.on("Network.webSocketCreated", handle_ws)

        print("👉 Abrindo jogo...")
        await page.goto(GAME_URL)

        # espera carregar jogo + websocket
        for _ in range(30):
            if ws_url:
                break
            await asyncio.sleep(1)

        if not ws_url:
            await context.close()
            raise Exception("WebSocket URL not found")

        await context.close()
        return ws_url