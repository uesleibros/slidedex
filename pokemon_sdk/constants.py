NATURES = {
	"Hardy": (None, None),
	"Lonely": ("attack", "defense"),
	"Brave": ("attack", "speed"),
	"Adamant": ("attack", "special-attack"),
	"Naughty": ("attack", "special-defense"),
	"Bold": ("defense", "attack"),
	"Docile": (None, None),
	"Relaxed": ("defense", "speed"),
	"Impish": ("defense", "special-attack"),
	"Lax": ("defense", "special-defense"),
	"Timid": ("speed", "attack"),
	"Hasty": ("speed", "defense"),
	"Serious": (None, None),
	"Jolly": ("speed", "special-attack"),
	"Naive": ("speed", "special-defense"),
	"Modest": ("special-attack", "attack"),
	"Mild": ("special-attack", "defense"),
	"Quiet": ("special-attack", "speed"),
	"Bashful": (None, None),
	"Calm": ("special-defense", "attack"),
	"Gentle": ("special-defense", "defense"),
	"Sassy": ("special-defense", "speed"),
	"Careful": ("special-defense", "special-attack"),
	"Quirky": (None, None)
}

REGIONS_GENERATION = {
	"generation-i": "Kanto",
	"generation-ii": "Johto",
	"generation-iii": "Hoenn",
	"generation-iv": "Sinnoh",
	"generation-v": "Unova",
	"generation-vi": "Kalos",
	"generation-vii": "Alola",
	"generation-viii": "Galar",
	"generation-ix": "Paldea"
}

TYPE_CHART = {
	"normal":   {"super": set(),                              "not": {"rock","steel"},                "immune": {"ghost"}},
	"fire":     {"super": {"grass","ice","bug","steel"},      "not": {"fire","water","rock","dragon"},"immune": set()},
	"water":    {"super": {"fire","ground","rock"},           "not": {"water","grass","dragon"},      "immune": set()},
	"grass":    {"super": {"water","ground","rock"},          "not": {"fire","grass","poison","flying","bug","dragon","steel"}, "immune": set()},
	"electric": {"super": {"water","flying"},                 "not": {"electric","grass","dragon"},   "immune": {"ground"}},
	"ice":      {"super": {"grass","ground","flying","dragon"},"not": {"fire","water","ice","steel"},"immune": set()},
	"fighting": {"super": {"normal","ice","rock","dark","steel"}, "not": {"poison","flying","psychic","bug","fairy"}, "immune": {"ghost"}},
	"poison":   {"super": {"grass","fairy"},                  "not": {"poison","ground","rock","ghost"}, "immune": {"steel"}},
	"ground":   {"super": {"fire","electric","poison","rock","steel"}, "not": {"grass","bug"}, "immune": {"flying"}},
	"flying":   {"super": {"grass","fighting","bug"},         "not": {"electric","rock","steel"},     "immune": set()},
	"psychic":  {"super": {"fighting","poison"},              "not": {"psychic","steel"},             "immune": {"dark"}},
	"bug":      {"super": {"grass","psychic","dark"},         "not": {"fire","fighting","poison","flying","ghost","steel","fairy"}, "immune": set()},
	"rock":     {"super": {"fire","ice","flying","bug"},      "not": {"fighting","ground","steel"},   "immune": set()},
	"ghost":    {"super": {"psychic","ghost"},                "not": {"dark"},                        "immune": {"normal"}},
	"dragon":   {"super": {"dragon"},                         "not": {"steel"},                       "immune": {"fairy"}},
	"dark":     {"super": {"psychic","ghost"},                "not": {"fighting","dark","fairy"},     "immune": set()},
	"steel":    {"super": {"ice","rock","fairy"},             "not": {"fire","water","electric","steel"}, "immune": set()},
	"fairy":    {"super": {"fighting","dragon","dark"},       "not": {"fire","poison","steel"},       "immune": set()},
}

STAT_ALIASES = {
	"hp": ["hp"],
	"atk": ["atk","attack"],
	"def": ["def","defense"],
	"sp_atk": ["sp_atk","spa","special-attack","spatk","sp_att","spatt"],
	"sp_def": ["sp_def","spd","special-defense","spdef","sp_defense"],
	"speed": ["speed","spe"]
}

VERSION_GROUPS = ("firered-leafgreen", "emerald", "ruby-sapphire")
STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")

SHINY_ROLL = 8192
HAPPINESS_MAX = 255
