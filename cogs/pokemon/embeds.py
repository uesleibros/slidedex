import discord
from sdk.calculations import iv_percent, calculate_stats
from sdk.constants import STAT_KEYS, STAT_LABELS, TYPE_EMOJIS
from utilities.formatting import format_pokemon_display, format_happiness_status, format_nature_info, format_item_display
from typing import Optional

async def generate_pokemon_embed(pokemons, start, end, total, current_page, user: Optional[discord.Member] = None):
	desc_lines = []
	for p in pokemons:
		poke_id = p["id"]
		ivp = iv_percent(p["ivs"])
		desc_lines.append(
			f"`{poke_id}`　{format_pokemon_display(p, show_fav=True)}　•　Lv. {p['level']}　•　{ivp}%"
		)

	if user:
		title = f"Pokémon de {user.display_name}"
	else:
		title = "Seus Pokémon"

	embed = discord.Embed(
		title=title,
		description="\n".join(desc_lines) if desc_lines else "Sem resultados",
		color=discord.Color.pink()
	)
	embed.set_footer(text=f"Mostrando {start+1}–{end} de {total}")
	return embed

async def generate_info_embed(user_pokemon: dict, pokemon: dict, start, end, total, current_page, user: Optional[discord.Member] = None):
	pokemon_id = user_pokemon["id"]
	base_stats = {s.stat.name: s.base_stat for s in pokemon.stats}
	stats = calculate_stats(base_stats, user_pokemon["ivs"], user_pokemon.get("evs", {}), user_pokemon["level"], user_pokemon["nature"])
	current_hp = user_pokemon.get("current_hp") if user_pokemon.get("current_hp") is not None else stats["hp"]

	iv_total = sum(user_pokemon["ivs"].values())
	iv_percent_val = round((iv_total / 186) * 100, 2)

	current_exp = user_pokemon.get("exp", 0)
	current_level = user_pokemon["level"]
	growth_type = user_pokemon.get("growth_type")

	exp_current_level = tk.get_exp_for_level(growth_type, current_level)

	if current_level >= 100:
		exp_next_level = exp_current_level
		exp_progress = 0
		exp_needed = 0
		exp_progress_percent = 100.0
	else:
		exp_next_level = tk.get_exp_for_level(growth_type, current_level + 1)
		exp_progress = current_exp - exp_current_level
		exp_needed = exp_next_level - exp_current_level
		exp_progress_percent = round((exp_progress / exp_needed) * 100, 1) if exp_needed > 0 else 0

	title = f"Level {user_pokemon['level']} {format_pokemon_display(user_pokemon, show_fav=True, show_poke=False)}"
	
	sprite_bytes = pm.service.get_pokemon_sprite(user_pokemon)[0]
	
	files = []
	if sprite_bytes:
		buffer = await compose_pokemon_async(sprite_bytes, preloaded_info_backgrounds[user_pokemon['background']])
		img_file = discord.File(buffer, filename="pokemon.png")
		files.append(img_file)

	details_lines = [
		f"<:emojigg_ID:1424200976557932685> **ID do Pokemon:** {pokemon_id}",
		f"<:emojigg_ID:1424200976557932685> **ID da Espécie:** #{user_pokemon.get('species_id')}",
		f"<:level:1424200489637118042> **Nível:** {current_level}",
		f"<:CometShard:1424200074463805551> **Experiência:** {current_exp}/{exp_next_level} | Próximo: {exp_needed} XP ({exp_progress_percent}%)",
		f":leaves: **Natureza:** {format_nature_info(user_pokemon['nature'])}",
		f"<:speechbubble_heart:1424195141199204467> **Amizade:** {format_happiness_status(user_pokemon['happiness'])}",
		f":kite: **Tipo de Crescimento:** {user_pokemon['growth_type'].replace('-', ' ').title()}",
		f"🧬 **Habilidade:** {str(user_pokemon.get('ability') or '-').replace('-', ' ').title()}",
		f":rock: **Tipos:** {' / '.join(TYPE_EMOJIS.get(t, TYPE_EMOJIS['unknown']) for t in user_pokemon['types'])}",
		f"<:research_encounter:1424202205757444096> **Região:** {user_pokemon['region'].replace('-', ' ').title()}",
		f":empty_nest: **Item Segurado:** {format_item_display(user_pokemon.get('held_item'))}\n"
		f"🧺 **Capturado com**: {ITEM_EMOJIS.get(user_pokemon.get('caught_with'), 'poke-ball')}"
	]

	stats_lines = [f"<:stats:1424204552910929920> **IV Total:** {iv_total}/186 ({iv_percent_val}%)"]
	for key in STAT_KEYS:
		base = base_stats.get(key, 0)
		iv = user_pokemon["ivs"].get(key, 0)
		ev = user_pokemon.get("evs", {}).get(key, 0)
		final = stats[key]
		
		if key == "hp":
			stats_lines.append(f"<:stats:1424204552910929920> **HP:** {current_hp}/{final} | Base: {base} | IV: {iv} | EV: {ev}")
		else:
			stat_label = STAT_LABELS[key]
			stats_lines.append(f"<:stats:1424204552910929920> **{stat_label}:** {final} | Base: {base} | IV: {iv} | EV: {ev}")

	moves_lines = []
	for move in user_pokemon.get("moves", []):
		move_name = move['id'].replace('-', ' ').title()
		moves_lines.append(f"**{move_name}** ({move['pp']}/{move['pp_max']} PP)")
	
	future_moves = pm.service.get_future_moves(pokemon, user_pokemon['level'])
	future_moves_lines = []
	for lvl, name in future_moves[:8]:
		move_name = name.replace('-', ' ').title()
		future_moves_lines.append(f"**Lv. {lvl}:** {move_name}")

	embed = discord.Embed(title=title, color=discord.Color.blurple())
	
	embed.add_field(name="Informações Gerais", value="\n".join(details_lines), inline=False)
	embed.add_field(name="Estatísticas Finais", value="\n".join(stats_lines), inline=False)
	
	if moves_lines:
		embed.add_field(name=f"Movimentos Atuais ({len(moves_lines)}/4)", value="\n".join(moves_lines) if moves_lines else "Nenhum", inline=True)
	else:
		embed.add_field(name="Movimentos Atuais (0/4)", value="Nenhum movimento aprendido", inline=True)
		
	if future_moves_lines:
		embed.add_field(name="Próximos Movimentos", value="\n".join(future_moves_lines), inline=True)
	else:
		embed.add_field(name="Próximos Movimentos", value="Nenhum movimento disponivel", inline=True)

	caught_date = datetime.fromisoformat(user_pokemon['caught_at']).strftime('%d/%m/%Y às %H:%M')
	embed.set_footer(text=f"Capturado em {caught_date}")
	
	if files and any(f.filename == "pokemon.png" for f in files):
		embed.set_image(url="attachment://pokemon.png")

	return embed, files