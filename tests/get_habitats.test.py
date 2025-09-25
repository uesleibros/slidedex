import asyncio
from curl_cffi import requests

async def fetch_all_habitats():
    async with requests.AsyncSession() as session:
        resp = await session.get("https://pokeapi.co/api/v2/pokemon-habitat/")
        data = resp.json()
        habitats = [h["name"] for h in data["results"]]
        return habitats

async def main():
    habitats = await fetch_all_habitats()
    print("Habitats disponíveis na PokeAPI:", habitats)

asyncio.run(main())