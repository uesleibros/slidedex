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

STAT_LABELS = {
	"hp": "HP",
	"attack": "Ataque",
	"defense": "Defesa",
	"special-attack": "Sp. Atk",
	"special-defense": "Sp. Def",
	"speed": "Velocidade",
}

VERSION_GROUPS = ("firered-leafgreen", "emerald", "ruby-sapphire")
STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")

SHINY_ROLL = 8192
HAPPINESS_MAX = 255

CATEGORY_NAMES = {
	"items": "Itens",
	"pokeballs": "Poké Balls",
	"berries": "Berries",
	"tms_hms": "TMs & HMs",
	"key_items": "Itens Chave"
}

CATEGORY_ORDER = ["items", "pokeballs", "berries", "tms_hms", "key_items"]

HEALING_ITEMS = [
	"potion", "super-potion", "hyper-potion", "max-potion",
	"full-restore", "fresh-water", "soda-pop", "lemonade",
	"moomoo-milk", "energy-powder", "energy-root", "berry-juice",
	"sweet-heart"
]

REVIVE_ITEMS = ["revive", "max-revive", "revival-herb"]

VITAMINS = ["hp-up", "protein", "iron", "carbos", "calcium", "zinc"]

PP_RECOVERY = ["ether", "max-ether", "elixir", "max-elixir"]

PP_BOOST = ["pp-up", "pp-max"]

EVOLUTION_STONES = [
	"fire-stone", "water-stone", "thunder-stone", "leaf-stone",
	"moon-stone", "sun-stone", "shiny-stone", "dusk-stone",
	"dawn-stone", "ice-stone"
]

BERRIES = [
	"oran-berry", "sitrus-berry", "pecha-berry", "cheri-berry",
	"chesto-berry", "rawst-berry", "aspear-berry", "persim-berry",
	"lum-berry", "leppa-berry", "aguav-berry", "figy-berry",
	"iapapa-berry", "mago-berry", "wiki-berry", "enigma-berry",
	"liechi-berry", "ganlon-berry", "salac-berry", "petaya-berry",
	"apicot-berry", "lansat-berry", "starf-berry", "pomeg-berry",
	"kelpsy-berry", "qualot-berry", "hondew-berry", "grepa-berry",
	"tamato-berry", "cornn-berry", "magost-berry", "rabuta-berry",
	"nomel-berry", "spelon-berry", "pamtre-berry", "watmel-berry",
	"durin-berry", "belue-berry", "occa-berry", "passho-berry",
	"wacan-berry", "rindo-berry", "yache-berry", "chople-berry",
	"kebia-berry", "shuca-berry", "coba-berry", "payapa-berry",
	"tanga-berry", "charti-berry", "kasib-berry", "haban-berry",
	"colbur-berry", "babiri-berry", "chilan-berry", "roseli-berry"
]

POKEBALLS = [
	"poke-ball", "great-ball", "ultra-ball", "master-ball",
	"safari-ball", "level-ball", "lure-ball", "moon-ball",
	"friend-ball", "love-ball", "heavy-ball", "fast-ball",
	"sport-ball", "premier-ball", "repeat-ball", "timer-ball",
	"nest-ball", "net-ball", "dive-ball", "luxury-ball",
	"heal-ball", "quick-ball", "dusk-ball", "cherish-ball"
]

BATTLE_USABLE_ITEMS = POKEBALLS + HEALING_ITEMS + REVIVE_ITEMS + BERRIES + PP_RECOVERY