from utils.pokemon_emojis import get_app_emoji
from typing import Optional

def fmt_name(s: str) -> str:
	return s.replace("-", " ").title()

def format_poke_id(pid: int) -> str:
	return str(pid).zfill(3)

def format_pokemon_display(pokemon: dict, bold_name: Optional[bool] = False, show_nick: Optional[bool] = True, show_gender: Optional[bool] = True) -> str:
	parts: list = []

	if pokemon.get("is_shiny", False):
		parts.append("<:shinystar:1422797880036429855>")

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

	if show_gender:
		if pokemon["gender"] != "Genderless":
			gender = "<:sign_male:1422816545029099621>" if pokemon["gender"] == "Male" else "<:sign_female:1422816627136663582>"
		else:
			gender = ":grey_question:"
		parts.append(gender)


	return " ".join(parts)

