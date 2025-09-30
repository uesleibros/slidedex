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

VERSION_GROUPS = ("firered-leafgreen", "emerald", "ruby-sapphire")
STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
SHINY_ROLL = 8192