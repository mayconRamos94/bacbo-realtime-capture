import asyncio
from playwright.async_api import async_playwright


GAME_URL = "https://start.bet.br/live-casino/game/2630915?provider=Evolution&from=%2Flive-casino"


async def get_ws_url():
    async with async_playwright() as p:

        context = await p.chromium.launch_persistent_context(
            user_data_dir="C:\\Users\\a879950\\AppData\\Local\\Google\\Chrome\\User Data",
            headless=False
        )

        page = await context.new_page()

        ws_url = None

        def handle_ws(ws):
            nonlocal ws_url
            if "evo-games.com" in ws.url:
                ws_url = ws.url

        page.on("websocket", handle_ws)

        await page.goto(GAME_URL)

        # espera capturar
        for _ in range(30):
            if ws_url:
                break
            await asyncio.sleep(1)

        await context.close()

        if not ws_url:
            raise Exception("WebSocket URL not found")

        return ws_url