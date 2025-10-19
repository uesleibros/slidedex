from typing import Final, Dict, Any

LOCATIONS: Final[Dict[str, Any]] = {
	"pallet-town-area": {
		"name": "Pallet Town",
		"type": "town",
		"description": "Uma cidade tranquila e pacífica. Onde tudo começou.",
		"connections": {
			"kanto-route-1": { "time": 30 },
			"kanto-route-21": { "time": 60 }
		},
		"wild_encounters": False,
		"can_fly_to": True,
		"has_pokemon_center": False,
		"has_mart": False,
		"has_gym": False,
		"has_day_care": False,
		"has_game_corner": False,
		"has_safari_zone": False,
		"has_move_tutor": False,
		"gym_info": None,
		"mart_items": None,
		"required_hm": None,
		"required_events": [],
		"required_badge": None,
		"min_badges": None,
		"events": ["starter_choice", "pokedex_receive"]
	}
}