import asyncio
from curl_cffi import requests

urls = [f"https://pokeapi.co/api/v2/move/{i}/" for i in range(1, 351)]

async def fetch(session, url):
    r = await session.get(url, impersonate="chrome")
    data = r.json()
    for e in data["effect_entries"]:
        if e["language"]["name"] == "en":
            return e["short_effect"]
    return ""

async def main():
    async with requests.AsyncSession() as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        print("\n".join(results))

asyncio.run(main())