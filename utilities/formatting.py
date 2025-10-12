from typing import Optional
from dataclasses import dataclass
from sdk.constants import NATURES, HAPPINESS_MAX
from sdk.items.constants import ITEM_EMOJIS
from utilities.pokemon_emojis import get_app_emoji

@dataclass
class DisplayConfig:
	bold_name: bool = False
	show_nick: bool = True
	show_gender: bool = True
	show_poke: bool = True
	show_fav: bool = False
	show_hp: bool = True
	show_status: bool = True
	show_item: bool = True

class PokemonEmojis:
	SHINY = "<:shiny:1426407359151996939>"
	MALE = "<:sign_male:1426401235606700165>"
	FEMALE = "<:sign_female:1426401284994367539>"
	GENDERLESS = "<:keroppiquestion2:1424099265797689395>"
	FAINTED = "<:fntstatus:1424616601801723914>"
	HELD_ITEM = "<:item_held:1426403303725469717>"
	FAVORITE = "❤️"

STATUS_TAGS = {
	"burn": "🔥",
	"poison": "☠️",
	"paralysis": "⚡",
	"sleep": "💤",
	"freeze": "❄️"
}

def format_nature_info(nature: str) -> str:
	nature_key = nature.title()
	
	if nature_key not in NATURES:
		return nature_key
	
	increased, decreased = NATURES[nature_key]
	
	if increased is None and decreased is None:
		return f"{nature_key} (Neutra)"
	
	stat_translation = {
		"attack": "Ataque",
		"defense": "Defesa",
		"special-attack": "Atq. Esp.",
		"special-defense": "Def. Esp.",
		"speed": "Velocidade"
	}
	
	inc = stat_translation.get(increased, increased)
	dec = stat_translation.get(decreased, decreased)
	
	return f"{nature_key} (+10% {inc}, -10% {dec})"

def format_item_display(item_id: Optional[str], bold_name: Optional[bool] = False) -> str:
	if not item_id:
		return "Nenhum item"

	emoji = ITEM_EMOJIS.get(item_id, "📦")
	name = pm.item_manager.get_item_name(item_id)

	if bold_name:
		return f"{emoji} **{name}**"
	else:
		return f"{emoji} {name}"

def format_pokemon_display(pokemon: dict, **kwargs) -> str:
	config = DisplayConfig(**kwargs)
	parts = []
	
	if pokemon.get("is_shiny", False):
		parts.append(PokemonEmojis.SHINY)
	
	if config.show_poke:
		emoji = get_app_emoji(f"p_{pokemon['species_id']}")
		if emoji:
			parts.append(emoji)
	
	parts.append(_format_name(pokemon, config.bold_name, config.show_nick))
	
	if config.show_status:
		status_tag = _get_status_tag(pokemon)
		if status_tag:
			parts.append(status_tag)
	
	if config.show_hp and pokemon.get("current_hp", 0) == 0:
		parts.append(PokemonEmojis.FAINTED)
	
	if config.show_gender:
		gender_emoji = _get_gender_emoji(pokemon)
		if gender_emoji:
			parts.append(gender_emoji)
	
	if config.show_item and pokemon.get("held_item"):
		parts.append(PokemonEmojis.HELD_ITEM)
	
	if config.show_fav and pokemon.get("is_favorite", False):
		parts.append(PokemonEmojis.FAVORITE)
	
	return " ".join(filter(None, parts))

def _format_name(pokemon: dict, bold: bool, show_nick: bool) -> str:
	name = pokemon.get("name", f"#{pokemon['species_id']}").title()
	
	if bold:
		name = f"**{name}**"
	
	if show_nick and pokemon.get("nickname"):
		return f"{name} ({pokemon['nickname']})"
	
	return name

def _get_status_tag(pokemon: dict) -> Optional[str]:
	status = pokemon.get("status", {})
	status_name = status.get("name", "")
	return STATUS_TAGS.get(status_name)

def _get_gender_emoji(pokemon: dict) -> Optional[str]:
	gender = pokemon.get("gender", "Genderless")
	
	if gender == "Male":
		return PokemonEmojis.MALE
	elif gender == "Female":
		return PokemonEmojis.FEMALE
	elif gender == "Genderless":
		return PokemonEmojis.GENDERLESS
	
	return None