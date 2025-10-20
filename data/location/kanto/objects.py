from typing import Final, Dict, Any

LOCATIONS: Final[Dict[str, Any]] = {
	"pallet-town-area": {
		"name": "Pallet Town",
		"type": "town",
		"connections": {
			"kanto-route-1-area": {
				"time": 30,
				"method": "walk"
			}
		},
		"encounters": {
			"walk": None,
			"surf": "water",
			"fish": "water"
		},
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
	},
	"kanto-route-1-area": {
		"name": "Rota 1",
		"type": "route",
		"connections": {
			"pallet-town-area": {
				"time": 30,
				"method": "walk"
			},
			"viridian-city-area": {
				"time": 150,
				"method": "walk"
			}
		},
		"encounters": {
			"walk": "grass",
			"surf": None,
			"fish": None
		},
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
		"events": []
	},
	"viridian-city-area": {
		"name": "Viridian City",
		"type": "city",
		"connections": {
			"kanto-route-1-area": {
				"time": 30,
				"method": "walk"
			}
		},
		"encounters": {
			"walk": None,
			"surf": None,
			"fish": None
		},
		"can_fly_to": True,
		"has_pokemon_center": True,
		"has_mart": True,
		"has_gym": True,
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
		"events": []
	}
}