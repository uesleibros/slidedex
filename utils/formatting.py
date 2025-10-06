from utils.pokemon_emojis import get_app_emoji
from typing import Optional
from pokemon_sdk.constants import HAPPINESS_MAX, NATURES
from pokemon_sdk.battle.constants import STATUS_TAGS

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

def format_happiness_status(happiness: int) -> str:
	current_friendship = happiness
	percent = int((current_friendship / HAPPINESS_MAX) * 100)
	if percent >= 80:
		status = "Muito feliz"
	elif percent >= 60:
		status = "Feliz"
	elif percent >= 40:
		status = "Normal"
	else:
		status = "Triste"
	return f"{happiness}/{HAPPINESS_MAX} | {percent}% ({status})"

def fmt_name(s: str) -> str:
	return s.replace("-", " ").title()

def format_poke_id(pid: int) -> str:
	return str(pid).zfill(3)

def format_pokemon_display(
	pokemon: dict, bold_name: Optional[bool] = False, show_nick: Optional[bool] = True, 
	show_gender: Optional[bool] = True, show_poke: Optional[bool] = True, show_fav: Optional[bool] = False,
	show_hp: Optional[bool] = True, show_status: Optional[bool] = True
) -> str:
	parts: list = []

	if pokemon.get("is_shiny", False):
		parts.append("<:shinystar:1422797880036429855>")

	if show_poke:
		emoji = get_app_emoji(f"p_{pokemon['species_id']}")
		parts.append(emoji)

	name = pokemon.get("name", f"#{pokemon['species_id']}").title()
	gender = ""
	
	if bold_name:
		name = f"**{name}**"
	
	if pokemon.get("nickname") and show_nick:
		parts.append(f"{name} ({pokemon['nickname']})")
	else:
		parts.append(name)

	if show_status:
		tags = []
		status = pokemon.get("status")
		if status and isinstance(status, dict):
			status_name = status.get("name")
			if status_name and status_name in STATUS_TAGS:
				tags.append(STATUS_TAGS[status_name])
		parts.append(f" [{'/'.join(tags)}]" if tags else "")

	if show_hp:
		current_hp = pokemon.get("current_hp")
		if current_hp == 0:
			parts.append("<:DEAD:1424144690625777785>")

	if show_gender:
		if pokemon["gender"] != "Genderless":
			gender = "<:sign_male:1422816545029099621>" if pokemon["gender"] == "Male" else "<:sign_female:1422816627136663582>"
		else:
			gender = "<:keroppiquestion2:1424099265797689395>"
		parts.append(gender)

	if show_fav and pokemon["is_favorite"]:
		parts.append("❤️")

	return " ".join(parts)





