from enum import Enum
from typing import Final, Optional, TypedDict
from dataclasses import dataclass
from frozendict import frozendict

@dataclass(frozen=True)
class HappinessGain:
	low: int
	medium: int
	high: int

@dataclass(frozen=True)
class HappinessConfig:
	level_up: HappinessGain = HappinessGain(5, 3, 2)
	vitamin: HappinessGain = HappinessGain(5, 3, 2)
	berry: HappinessGain = HappinessGain(10, 5, 2)
	battle: HappinessGain = HappinessGain(3, 2, 1)
	walk: int = 1
	faint: int = 1
	energy_powder_low: int = 5
	energy_powder_high: int = 10
	heal_powder_low: int = 5
	heal_powder_high: int = 10
	energy_root_low: int = 10
	energy_root_high: int = 15
	revival_herb_low: int = 15
	revival_herb_high: int = 20

class StatType(str, Enum):
	HP = "hp"
	ATTACK = "attack"
	DEFENSE = "defense"
	SPECIAL_ATTACK = "special-attack"
	SPECIAL_DEFENSE = "special-defense"
	SPEED = "speed"

class PokemonType(str, Enum):
	NORMAL = "normal"
	FIRE = "fire"
	WATER = "water"
	GRASS = "grass"
	ELECTRIC = "electric"
	ICE = "ice"
	FIGHTING = "fighting"
	POISON = "poison"
	GROUND = "ground"
	FLYING = "flying"
	PSYCHIC = "psychic"
	BUG = "bug"
	ROCK = "rock"
	GHOST = "ghost"
	DRAGON = "dragon"
	DARK = "dark"
	STEEL = "steel"
	FAIRY = "fairy"
	UNKNOWN = "unknown"

@dataclass(frozen=True)
class NatureModifier:
	increased: Optional[str]
	decreased: Optional[str]
	
	@property
	def is_neutral(self) -> bool:
		return self.increased is None and self.decreased is None

NATURES: Final[dict[str, tuple[Optional[str], Optional[str]]]] = {
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

REGIONS_GENERATION: Final[dict[str, str]] = {
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

class TypeEffectiveness(TypedDict):
	super_effective: frozenset[str]
	not_very_effective: frozenset[str]
	immune: frozenset[str]

TYPE_CHART: Final[dict[PokemonType, TypeEffectiveness]] = {
	PokemonType.NORMAL: {
		"super_effective": frozenset(),
		"not_very_effective": frozenset({"rock", "steel"}),
		"immune": frozenset({"ghost"})
	},
	PokemonType.FIRE: {
		"super_effective": frozenset({"grass", "ice", "bug", "steel"}),
		"not_very_effective": frozenset({"fire", "water", "rock", "dragon"}),
		"immune": frozenset()
	},
	PokemonType.WATER: {
		"super_effective": frozenset({"fire", "ground", "rock"}),
		"not_very_effective": frozenset({"water", "grass", "dragon"}),
		"immune": frozenset()
	},
	PokemonType.GRASS: {
		"super_effective": frozenset({"water", "ground", "rock"}),
		"not_very_effective": frozenset({"fire", "grass", "poison", "flying", "bug", "dragon", "steel"}),
		"immune": frozenset()
	},
	PokemonType.ELECTRIC: {
		"super_effective": frozenset({"water", "flying"}),
		"not_very_effective": frozenset({"electric", "grass", "dragon"}),
		"immune": frozenset({"ground"})
	},
	PokemonType.ICE: {
		"super_effective": frozenset({"grass", "ground", "flying", "dragon"}),
		"not_very_effective": frozenset({"fire", "water", "ice", "steel"}),
		"immune": frozenset()
	},
	PokemonType.FIGHTING: {
		"super_effective": frozenset({"normal", "ice", "rock", "dark", "steel"}),
		"not_very_effective": frozenset({"poison", "flying", "psychic", "bug", "fairy"}),
		"immune": frozenset({"ghost"})
	},
	PokemonType.POISON: {
		"super_effective": frozenset({"grass", "fairy"}),
		"not_very_effective": frozenset({"poison", "ground", "rock", "ghost"}),
		"immune": frozenset({"steel"})
	},
	PokemonType.GROUND: {
		"super_effective": frozenset({"fire", "electric", "poison", "rock", "steel"}),
		"not_very_effective": frozenset({"grass", "bug"}),
		"immune": frozenset({"flying"})
	},
	PokemonType.FLYING: {
		"super_effective": frozenset({"grass", "fighting", "bug"}),
		"not_very_effective": frozenset({"electric", "rock", "steel"}),
		"immune": frozenset()
	},
	PokemonType.PSYCHIC: {
		"super_effective": frozenset({"fighting", "poison"}),
		"not_very_effective": frozenset({"psychic", "steel"}),
		"immune": frozenset({"dark"})
	},
	PokemonType.BUG: {
		"super_effective": frozenset({"grass", "psychic", "dark"}),
		"not_very_effective": frozenset({"fire", "fighting", "poison", "flying", "ghost", "steel", "fairy"}),
		"immune": frozenset()
	},
	PokemonType.ROCK: {
		"super_effective": frozenset({"fire", "ice", "flying", "bug"}),
		"not_very_effective": frozenset({"fighting", "ground", "steel"}),
		"immune": frozenset()
	},
	PokemonType.GHOST: {
		"super_effective": frozenset({"psychic", "ghost"}),
		"not_very_effective": frozenset({"dark"}),
		"immune": frozenset({"normal"})
	},
	PokemonType.DRAGON: {
		"super_effective": frozenset({"dragon"}),
		"not_very_effective": frozenset({"steel"}),
		"immune": frozenset({"fairy"})
	},
	PokemonType.DARK: {
		"super_effective": frozenset({"psychic", "ghost"}),
		"not_very_effective": frozenset({"fighting", "dark", "fairy"}),
		"immune": frozenset()
	},
	PokemonType.STEEL: {
		"super_effective": frozenset({"ice", "rock", "fairy"}),
		"not_very_effective": frozenset({"fire", "water", "electric", "steel"}),
		"immune": frozenset()
	},
	PokemonType.FAIRY: {
		"super_effective": frozenset({"fighting", "dragon", "dark"}),
		"not_very_effective": frozenset({"fire", "poison", "steel"}),
		"immune": frozenset()
	},
}

TYPE_EMOJIS: Final[dict[PokemonType, str]] = {
	PokemonType.NORMAL: "<:normaltype:1426413368365027359>",
	PokemonType.FIRE: "<:firetype:1426412699780382813>",
	PokemonType.WATER: "<:watertype:1426414048811024445>",
	PokemonType.GRASS: "<:grasstype:1426413067171790930>",
	PokemonType.ELECTRIC: "<:electrictype:1426412453134078024>",
	PokemonType.ICE: "<:icetype:1426413247929782313>",
	PokemonType.FIGHTING: "<:fightingtype:1426412576333627484>",
	PokemonType.POISON: "<:poisontype:1426413473943785502>",
	PokemonType.GROUND: "<:groundtype:1426413157760630875>",
	PokemonType.FLYING: "<:flyingtype:1426412802402291813>",
	PokemonType.PSYCHIC: "<:psychictype:1426413565442523229>",
	PokemonType.BUG: "<:bugtype:1426412146551554068>",
	PokemonType.ROCK: "<:rocktype:1426413727242260591>",
	PokemonType.GHOST: "<:ghosttype:1426412982715420724>",
	PokemonType.DRAGON: "<:dragontype:1426412357017665566>",
	PokemonType.DARK: "<:darktype:1426412246891888731>",
	PokemonType.STEEL: "<:steeltype:1426413826001338449>",
	PokemonType.FAIRY: "<:fairytype:1426415748292808835>",
	PokemonType.UNKNOWN: "<:unknowntype:1426413949313749054>",
}

STAT_ALIASES: Final[dict[str, frozenset[str]]] = {
	"hp": frozenset({"hp"}),
	"atk": frozenset({"atk", "attack"}),
	"def": frozenset({"def", "defense"}),
	"sp_atk": frozenset({"sp_atk", "spa", "special-attack", "spatk", "sp_att", "spatt"}),
	"sp_def": frozenset({"sp_def", "spd", "special-defense", "spdef", "sp_defense"}),
	"speed": frozenset({"speed", "spe"}),
}

STAT_LABELS: Final[dict[str, str]] = {
	"hp": "HP",
	"attack": "Ataque",
	"defense": "Defesa",
	"special-attack": "Sp. Atk",
	"special-defense": "Sp. Def",
	"speed": "Velocidade",
}

STAT_KEYS: Final[tuple[str, ...]] = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")

HELD_ITEM_EFFECTS: Final[dict[str, dict]] = {
	"lucky-egg": {"exp_multiplier": 1.5},
	"exp-share": {"shares_exp": True},
	"soothe-bell": {"happiness_multiplier": 1.5},
	"macho-brace": {"ev_multiplier": 2.0, "speed_modifier": 0.5},
	"amulet-coin": {"money_multiplier": 2.0},
}

PARTY_LIMIT: Final[int] = 6
MOVES_LIMIT: Final[int] = 4
EV_PER_STAT_MAX: Final[int] = 255
EV_TOTAL_MAX: Final[int] = 510
HAPPINESS_MIN: Final[int] = 0
HAPPINESS_MAX: Final[int] = 255
MAX_LEVEL: Final[int] = 100
MIN_LEVEL: Final[int] = 1
SHINY_ROLL: Final[int] = 8192

SOOTHE_BELL_MULTIPLIER: Final[float] = 1.5
HAPPINESS: Final[HappinessConfig] = HappinessConfig()