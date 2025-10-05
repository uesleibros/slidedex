from typing import Dict, List
from pokemon_sdk.calculations import iv_percent

def analyze_pokemons(pokemons: List[Dict]) -> Dict:
	stats = {
		"event": 0,
		"rare": 0,
		"iv_80_90": 0,
		"iv_90_100": 0,
		"iv_100": 0,
		"shiny": 0,
		"favorite": 0
	}
	
	for p in pokemons:
		if p.get("is_event") or p.get("event"):
			stats["event"] += 1
		
		if p.get("is_legendary") or p.get("is_mythical"):
			stats["rare"] += 1
		
		ivp = iv_percent(p["ivs"])
		if ivp == 100:
			stats["iv_100"] += 1
		elif ivp >= 90:
			stats["iv_90_100"] += 1
		elif ivp >= 80:
			stats["iv_80_90"] += 1
		
		if p.get("is_shiny"):
			stats["shiny"] += 1
		
		if p.get("is_favorite"):
			stats["favorite"] += 1
	
	return stats