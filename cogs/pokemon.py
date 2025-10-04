import random
import discord
import aiopoke
from typing import Dict, List, Optional
from discord.ext import commands
from pokemon_sdk.calculations import iv_percent
from pokemon_sdk.calculations import calculate_stats
from pokemon_sdk.constants import STAT_KEYS
from utils.formatting import format_poke_id, format_pokemon_display
from helpers.flags import flags
from helpers.paginator import Paginator
from helpers.checks import requires_account, not_in_battle
from utils.canvas import compose_pokemon_async
from utils.preloaded import preloaded_info_backgrounds
from __main__ import toolkit, pm
from datetime import datetime

STAT_LABELS = {
	"hp": "HP", "attack": "Ataque", "defense": "Defesa",
	"special-attack": "Sp. Atk", "special-defense": "Sp. Def", "speed": "Velocidade",
}

class InfoView(discord.ui.View):
	def __init__(self, cog, user_id: int, all_pokemon_ids: list[int], current_index: int):
		super().__init__(timeout=180)
		self.cog = cog
		self.user_id = user_id
		self.all_pokemon_ids = all_pokemon_ids
		self.current_index = current_index
		self.update_buttons()

	def update_buttons(self):
		self.prev_pokemon.disabled = self.current_index == 0
		self.next_pokemon.disabled = self.current_index == len(self.all_pokemon_ids) - 1

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return interaction.user.id == self.user_id

	async def _update_info(self, interaction: discord.Interaction):
		pokemon_id = self.all_pokemon_ids[self.current_index]
		self.update_buttons()
		
		result = await self.cog._generate_info_embed(str(self.user_id), pokemon_id)
		if result:
			embed, files = result
			await interaction.response.edit_message(embed=embed, attachments=files, view=self)
		else:
			await interaction.response.edit_message(content="Erro ao carregar este Pokemon.", embed=None, attachments=[], view=self)

	@discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary)
	async def prev_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_index > 0:
			self.current_index -= 1
			await self._update_info(interaction)

	@discord.ui.button(label="Proximo", style=discord.ButtonStyle.secondary)
	async def next_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_index < len(self.all_pokemon_ids) - 1:
			self.current_index += 1
			await self._update_info(interaction)

async def generate_pokemon_embed(pokemons, start, end, total, current_page):
	desc_lines = []
	for p in pokemons:
		poke_id = p["id"]
		ivp = iv_percent(p["ivs"])
		desc_lines.append(
			f"`{format_poke_id(poke_id)}`　{format_pokemon_display(p, show_fav=True)}　•　Lv. {p['level']}　•　{ivp}%"
		)
	embed = discord.Embed(
		title="Seus Pokémon",
		description="\n".join(desc_lines) if desc_lines else "Sem resultados",
		color=discord.Color.pink()
	)
	embed.set_footer(text=f"Mostrando {start+1}–{end} de {total}")
	return embed

async def generate_info_embed(user_id: str, pokemon_id: int):
	try:
		user_pokemon = toolkit.get_pokemon(user_id, pokemon_id)
	except ValueError:
		return None

	pokemon: aiopoke.Pokemon = await pm.service.get_pokemon(user_pokemon["species_id"])
	
	base_stats = {s.stat.name: s.base_stat for s in pokemon.stats}
	stats = calculate_stats(base_stats, user_pokemon["ivs"], user_pokemon.get("evs", {}), user_pokemon["level"], user_pokemon["nature"])
	current_hp = user_pokemon.get("current_hp") if user_pokemon.get("current_hp") is not None else stats["hp"]

	iv_total = sum(user_pokemon["ivs"].values())
	iv_percent = round((iv_total / 186) * 100, 2)

	current_exp = user_pokemon.get("exp", 0)
	current_level = user_pokemon["level"]
	growth_type = user_pokemon.get("growth_type")

	exp_current_level = toolkit.get_exp_for_level(growth_type, current_level)

	if current_level >= 100:
		exp_next_level = exp_current_level
		exp_progress = 0
		exp_needed = 0
		exp_progress_percent = 100.0
	else:
		exp_next_level = toolkit.get_exp_for_level(growth_type, current_level + 1)
		exp_progress = current_exp - exp_current_level
		exp_needed = exp_next_level - exp_current_level
		exp_progress_percent = round((exp_progress / exp_needed) * 100, 1) if exp_needed > 0 else 0

	title = f"Level {user_pokemon['level']} {format_pokemon_display(user_pokemon, show_fav=True, show_poke=False)}"
	
	sprite_to_use = pokemon.sprites.front_shiny if user_pokemon['is_shiny'] else pokemon.sprites.front_default
	sprite_bytes = await sprite_to_use.read() if sprite_to_use else None
	
	files = []
	if sprite_bytes:
		buffer = await compose_pokemon_async(sprite_bytes, preloaded_info_backgrounds[user_pokemon['background']])
		img_file = discord.File(buffer, filename="pokemon.png")
		files.append(img_file)

	details_lines = [
		f"**ID do Pokemon:** {pokemon_id}",
		f"**ID da Espécie:** #{user_pokemon.get('species_id')} - {user_pokemon.get('name', 'Desconhecido').title()}",
		f"**Nível:** {current_level}",
		f"**Experiência:** {current_exp}/{exp_next_level} | Próximo: {exp_needed} XP ({exp_progress_percent}%)",
		f"**Natureza:** {user_pokemon['nature'].title()}",
		f"**Tipo de Crescimento:** {user_pokemon['growth_type'].replace('-', ' ').title()}",
		f"**Habilidade:** {str(user_pokemon.get('ability') or '-').replace('-', ' ').title()}",
		f"**Tipos:** {' / '.join(t.title() for t in user_pokemon['types'])}",
		f"**Região:** {user_pokemon['region'].replace('-', ' ').title()}",
		f"**Item Segurado:** {str(user_pokemon.get('held_item') or 'Nenhum').replace('-', ' ').title()}"
	]

	stats_lines = [f"**IV Total:** {iv_total}/186 ({iv_percent}%)"]
	for key in STAT_KEYS:
		base = base_stats.get(key, 0)
		iv = user_pokemon["ivs"].get(key, 0)
		ev = user_pokemon.get("evs", {}).get(key, 0)
		final = stats[key]
		
		if key == "hp":
			stats_lines.append(f"**HP:** {current_hp}/{final} | Base: {base} | IV: {iv} | EV: {ev}")
		else:
			stat_label = STAT_LABELS[key]
			stats_lines.append(f"**{stat_label}:** {final} | Base: {base} | IV: {iv} | EV: {ev}")

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
	
	embed.add_field(name="Informacoes Gerais", value="\n".join(details_lines), inline=False)
	
	embed.add_field(name="Estatisticas Finais", value="\n".join(stats_lines), inline=False)
	
	if moves_lines:
		embed.add_field(name=f"Movimentos Atuais ({len(moves_lines)}/4)", value="\n".join(moves_lines) if moves_lines else "Nenhum", inline=True)
	else:
		embed.add_field(name="Movimentos Atuais (0/4)", value="Nenhum movimento aprendido", inline=True)
		
	if future_moves_lines:
		embed.add_field(name="Proximos Movimentos", value="\n".join(future_moves_lines), inline=True)
	else:
		embed.add_field(name="Proximos Movimentos", value="Nenhum movimento disponivel", inline=True)

	caught_date = datetime.fromisoformat(user_pokemon['caught_at']).strftime('%d/%m/%Y as %H:%M')
	embed.set_footer(text=f"Capturado em {caught_date}")
	
	if files and any(f.filename == "pokemon.png" for f in files):
		embed.set_image(url="attachment://pokemon.png")

	return embed, files

def apply_filters(pokemons: List[Dict], flags) -> List[Dict]:
	res = pokemons
	
	if flags.get("favorite"):
		res = [p for p in res if p.get("is_favorite")]
	if flags.get("shiny"):
		res = [p for p in res if p.get("is_shiny", False)]
	if flags.get("legendary"):
		res = [p for p in res if p.get("is_legendary", False)]
	if flags.get("mythical"):
		res = [p for p in res if p.get("is_mythical", False)]
	if flags.get("gender"):
		res = [p for p in res if p["gender"].lower() == flags.get("gender").lower()]
	
	if flags.get("min_iv") is not None:
		res = [p for p in res if iv_percent(p["ivs"]) >= flags.get("min_iv")]
	if flags.get("max_iv") is not None:
		res = [p for p in res if iv_percent(p["ivs"]) <= flags.get("max_iv")]
	
	if flags.get("min_level") is not None:
		res = [p for p in res if p["level"] >= flags.get("min_level")]
	if flags.get("max_level") is not None:
		res = [p for p in res if p["level"] <= flags.get("max_level")]
	if flags.get("level"):
		levels = [int(v) for group in flags["level"] for v in group]
		res = [p for p in res if p["level"] in levels]
	
	if flags.get("hpiv"):
		hp_values = [int(v) for group in flags["hpiv"] for v in group]
		res = [p for p in res if p["ivs"]["hp"] in hp_values]
	if flags.get("atkiv"):
		atk_values = [int(v) for group in flags["atkiv"] for v in group]
		res = [p for p in res if p["ivs"]["attack"] in atk_values]
	if flags.get("defiv"):
		def_values = [int(v) for group in flags["defiv"] for v in group]
		res = [p for p in res if p["ivs"]["defense"] in def_values]
	if flags.get("spatkiv"):
		spatk_values = [int(v) for group in flags["spatkiv"] for v in group]
		res = [p for p in res if p["ivs"]["special-attack"] in spatk_values]
	if flags.get("spdefiv"):
		spdef_values = [int(v) for group in flags["spdefiv"] for v in group]
		res = [p for p in res if p["ivs"]["special-defense"] in spdef_values]
	if flags.get("spdiv"):
		spd_values = [int(v) for group in flags["spdiv"] for v in group]
		res = [p for p in res if p["ivs"]["speed"] in spd_values]
	if flags.get("iv"):
		iv_values = [int(v) for group in flags["iv"] for v in group]
		res = [p for p in res if int(iv_percent(p["ivs"])) in iv_values]
	
	if flags.get("min_ev") is not None:
		res = [p for p in res if sum(p.get("evs", {}).values()) >= flags.get("min_ev")]
	if flags.get("max_ev") is not None:
		res = [p for p in res if sum(p.get("evs", {}).values()) <= flags.get("max_ev")]
	
	if flags.get("hpev"):
		hp_values = [int(v) for group in flags["hpev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("hp", 0) in hp_values]
	if flags.get("atkev"):
		atk_values = [int(v) for group in flags["atkev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("attack", 0) in atk_values]
	if flags.get("defev"):
		def_values = [int(v) for group in flags["defev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("defense", 0) in def_values]
	if flags.get("spatkev"):
		spatk_values = [int(v) for group in flags["spatkev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("special-attack", 0) in spatk_values]
	if flags.get("spdefev"):
		spdef_values = [int(v) for group in flags["spdefev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("special-defense", 0) in spdef_values]
	if flags.get("spedev"):
		spd_values = [int(v) for group in flags["spedev"] for v in group]
		res = [p for p in res if p.get("evs", {}).get("speed", 0) in spd_values]
	
	if flags.get("species") is not None:
		species = [int(s) for group in flags["species"] for s in group]
		res = [p for p in res if p.get("species_id") in species]
	
	if flags.get("name"):
		names = [n.lower() for group in flags["name"] for n in group]
		res = [
			p for p in res
			if any(q in (p.get("name", "")).lower() for q in names)
		]
	
	if flags.get("type"):
		types = [t.lower() for group in flags["type"] for t in group]
		res = [p for p in res if any(ptype.lower() in types for ptype in p["types"])]
	
	if flags.get("region"):
		regions = [r.lower() for group in flags["region"] for r in group]
		res = [
			p for p in res
			if any(q in (p.get("region", "")).lower() for q in regions)
		]
	
	if flags.get("nickname"):
		nicks = [n.lower() for group in flags["nickname"] for n in group]
		res = [
			p for p in res
			if any(q in (p.get("nickname", "") or "").lower() for q in nicks)
		]
	
	if flags.get("nature"):
		natures = [n.lower() for group in flags["nature"] for n in group]
		res = [p for p in res if any(p["nature"].lower() == nat for nat in natures)]
	
	if flags.get("ability"):
		abilities = [a.lower() for group in flags["ability"] for a in (group if isinstance(group, list) else [group])]
		res = [p for p in res if any(p["ability"].lower() == ab for ab in abilities)]
	
	if flags.get("held_item"):
		held_items = [h.lower() for group in flags["held_item"] for h in (group if isinstance(group, list) else [group])]
		res = [p for p in res if p.get("held_item") and any(p["held_item"].lower() == hi for hi in held_items)]
	
	if flags.get("move"):
		moves = [m.lower().replace(" ", "-") for group in flags["move"] for m in group]
		res = [
			p for p in res
			if any(
				move_id.lower() in moves 
				for move in p.get("moves", []) 
				for move_id in [move.get("id", "")]
			)
		]
	
	if flags.get("no_nickname"):
		res = [p for p in res if not p.get("nickname")]
	if flags.get("has_nickname"):
		res = [p for p in res if p.get("nickname")]
	
	if flags.get("no_held_item"):
		res = [p for p in res if not p.get("held_item")]
	if flags.get("has_held_item"):
		res = [p for p in res if p.get("held_item")]
	
	if flags.get("fainted"):
		res = [p for p in res if p.get("current_hp", 0) <= 0]
	if flags.get("healthy"):
		max_hp = lambda p: p.get("base_stats", {}).get("hp", 0)
		res = [p for p in res if p.get("current_hp", 0) >= max_hp(p)]
	
	if flags.get("growth_type"):
		growth_types = [g.lower() for group in flags["growth_type"] for g in group]
		res = [p for p in res if p.get("growth_type", "").lower() in growth_types]
	
	if flags.get("min_exp") is not None:
		res = [p for p in res if p.get("exp", 0) >= flags.get("min_exp")]
	if flags.get("max_exp") is not None:
		res = [p for p in res if p.get("exp", 0) <= flags.get("max_exp")]
	if flags.get("exp"):
		exp_values = [int(v) for group in flags["exp"] for v in group]
		res = [p for p in res if p.get("exp", 0) in exp_values]
	
	if flags.get("exp_percent") is not None:
		percent_values = [int(v) for group in flags["exp_percent"] for v in group]
		filtered = []
		for p in res:
			progress = toolkit.get_exp_progress(p.get("growth_type", "medium"), p.get("exp", 0))
			if int(progress["progress_percent"]) in percent_values:
				filtered.append(p)
		res = filtered
	
	if flags.get("background"):
		backgrounds = [b.lower() for group in flags["background"] for b in group]
		res = [p for p in res if p.get("background", "").lower() in backgrounds]
	
	if flags.get("min_move_count") is not None:
		res = [p for p in res if len(p.get("moves", [])) >= flags.get("min_move_count")]
	if flags.get("max_move_count") is not None:
		res = [p for p in res if len(p.get("moves", [])) <= flags.get("max_move_count")]
	if flags.get("move_count"):
		counts = [int(v) for group in flags["move_count"] for v in group]
		res = [p for p in res if len(p.get("moves", [])) in counts]
	
	if flags.get("triple_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) >= 3]
	if flags.get("quad_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) >= 4]
	if flags.get("penta_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) >= 5]
	if flags.get("hexa_31"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 31) == 6]
	
	if flags.get("triple_0"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 0) >= 3]
	if flags.get("quad_0"):
		res = [p for p in res if sum(1 for v in p["ivs"].values() if v == 0) >= 4]
	
	if flags.get("duplicates"):
		species_count = {}
		for p in pokemons:
			sid = p["species_id"]
			species_count[sid] = species_count.get(sid, 0) + 1
		res = [p for p in res if species_count.get(p["species_id"], 0) > 1]
	
	if flags.get("unique"):
		species_count = {}
		for p in pokemons:
			sid = p["species_id"]
			species_count[sid] = species_count.get(sid, 0) + 1
		res = [p for p in res if species_count.get(p["species_id"], 0) == 1]
	
	return res

def apply_sort_limit(pokemons: List[Dict], flags) -> List[Dict]:
	res = list(pokemons)
	if flags.get("random"):
		random.shuffle(res)
	elif flags.get("sort"):
		keymap = {
			"iv": lambda p: iv_percent(p["ivs"]),
			"level": lambda p: p["level"],
			"id": lambda p: p["id"],
			"name": lambda p: (p.get("nickname") or p.get("name", "")).lower(),
			"species": lambda p: p["species_id"],
			"ev": lambda p: sum(p.get("evs", {}).values()),
			"hp": lambda p: p.get("current_hp", 0),
			"exp": lambda p: p.get("exp", 0),
			"growth": lambda p: p.get("growth_type", ""),
		}
		res.sort(key=keymap.get(flags.get("sort"), lambda p: p["id"]), reverse=bool(flags.get("reverse")))
	if flags.get("limit") is not None and flags.get("limit") > 0:
		res = res[:flags.get("limit")]
	return res

class ConfirmationView(discord.ui.View):
	def __init__(self, user_id: int, timeout: int = 60):
		super().__init__(timeout=timeout)
		self.user_id = user_id
		self.value = None

	@discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return await interaction.response.send_message("Esta confirmação não é para você!", ephemeral=True)
		self.value = True
		self.stop()
		await interaction.response.defer()

	@discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return await interaction.response.send_message("Esta confirmação não é para você!", ephemeral=True)
		self.value = False
		self.stop()
		await interaction.response.defer()

	async def on_timeout(self):
		self.value = False
		for item in self.children:
			item.disabled = True

def analyze_pokemons(pokemons: List[Dict]) -> Dict:
	stats = {
		"event": 0,
		"rare": 0,
		"iv_80_90": 0,
		"iv_90_100": 0,
		"iv_100": 0,
		"shiny": 0,
		"favorite": 0
	}
	
	for p in pokemons:
		if p.get("is_event") or p.get("event"):
			stats["event"] += 1
		
		if p.get("is_legendary") or p.get("is_mythical"):
			stats["rare"] += 1
		
		ivp = iv_percent(p["ivs"])
		if ivp == 100:
			stats["iv_100"] += 1
		elif ivp >= 90:
			stats["iv_90_100"] += 1
		elif ivp >= 80:
			stats["iv_80_90"] += 1
		
		if p.get("is_shiny"):
			stats["shiny"] += 1
		
		if p.get("is_favorite"):
			stats["favorite"] += 1
	
	return stats

class Pokemon(commands.Cog):
	""" Comandos relacionado a Pokémon. """
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@flags.add_flag("--page", nargs="?", type=int, default=0)
	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str,  nargs="+", action="append")
	@flags.add_flag("--region", "--r", type=str, nargs="+", action="append")
	@flags.add_flag("--gender", type=str)
	@flags.add_flag("--shiny", action="store_true")
	@flags.add_flag("--legendary", action="store_true")
	@flags.add_flag("--mythical", action="store_true")
	@flags.add_flag("--party", action="store_true")
	@flags.add_flag("--box", action="store_true")
	@flags.add_flag("--favorite", action="store_true")
	@flags.add_flag("--held_item", nargs="+", action="append")
	@flags.add_flag("--nature", nargs="+", action="append")
	@flags.add_flag("--ability", nargs="+", action="append")
	@flags.add_flag("--species", nargs="+", action="append", type=int)
	@flags.add_flag("--reverse", action="store_true")
	@flags.add_flag("--random", action="store_true")
	@flags.add_flag("--sort", type=str)
	@flags.add_flag("--min_iv", type=int)
	@flags.add_flag("--max_iv", type=int)
	@flags.add_flag("--min_level", type=int)
	@flags.add_flag("--max_level", type=int)
	@flags.add_flag("--level", nargs="+", action="append")
	@flags.add_flag("--hpiv", nargs="+", action="append")
	@flags.add_flag("--atkiv", nargs="+", action="append")
	@flags.add_flag("--defiv", nargs="+", action="append")
	@flags.add_flag("--spatkiv", nargs="+", action="append")
	@flags.add_flag("--spdefiv", nargs="+", action="append")
	@flags.add_flag("--spdiv", nargs="+", action="append")
	@flags.add_flag("--iv", nargs="+", action="append")
	@flags.add_flag("--min_ev", type=int)
	@flags.add_flag("--max_ev", type=int)
	@flags.add_flag("--hpev", nargs="+", action="append")
	@flags.add_flag("--atkev", nargs="+", action="append")
	@flags.add_flag("--defev", nargs="+", action="append")
	@flags.add_flag("--spatkev", nargs="+", action="append")
	@flags.add_flag("--spdefev", nargs="+", action="append")
	@flags.add_flag("--spedev", nargs="+", action="append")
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
	@flags.add_flag("--fainted", action="store_true")
	@flags.add_flag("--healthy", action="store_true")
	@flags.add_flag("--growth_type", nargs="+", action="append")
	@flags.add_flag("--min_exp", type=int)
	@flags.add_flag("--max_exp", type=int)
	@flags.add_flag("--exp", nargs="+", action="append")
	@flags.add_flag("--exp_percent", nargs="+", action="append")
	@flags.add_flag("--background", nargs="+", action="append")
	@flags.add_flag("--min_move_count", type=int)
	@flags.add_flag("--max_move_count", type=int)
	@flags.add_flag("--move_count", nargs="+", action="append")
	@flags.add_flag("--triple_31", action="store_true")
	@flags.add_flag("--quad_31", action="store_true")
	@flags.add_flag("--penta_31", action="store_true")
	@flags.add_flag("--hexa_31", action="store_true")
	@flags.add_flag("--triple_0", action="store_true")
	@flags.add_flag("--quad_0", action="store_true")
	@flags.add_flag("--duplicates", action="store_true")
	@flags.add_flag("--unique", action="store_true")
	@flags.add_flag("--page_size", type=int, default=20)
	@flags.add_flag("--limit", type=int)
	@commands.cooldown(3, 5, commands.BucketType.user)
	@flags.command(
		name="pokemon",
		aliases=["p", "pk", "pkm", "pkmn"],
		help=(
			"Lista os Pokémon do usuário com suporte a filtros, ordenação e paginação.\n\n"
			"BÁSICO\n"
			"  --party                 Lista apenas Pokémon que estão na party\n"
			"  --box                   Lista apenas Pokémon que estão na box\n"
			"  --shiny                 Filtra apenas Pokémon shiny\n"
			"  --favorite              Filtra apenas Pokémon marcados como favoritos\n"
			"  --gender <valor>        Filtra por gênero: male | female | genderless\n"
			"  --species <ID...>       Filtra por species IDs específicos (um ou mais)\n"
			"  --name <texto...>       Filtra pelo nome da espécie contendo o texto\n"
			"  --nickname <texto...>   Filtra pelo nickname contendo o texto\n"
			"  --nature <nome...>      Filtra por nature(s) específicas\n"
			"  --ability <nome...>     Filtra por ability(ies) específicas\n"
			"  --held_item <nome...>   Filtra por item segurado\n"
			"  --type <nome...>        Filtra por tipos do Pokémon (aceita múltiplos)\n"
			"  --region <nome...>      Filtra por região de origem da espécie\n"
			"  --move <nome...>        Filtra por movimento específico\n\n"
			"ESPECIAL\n"
			"  --legendary             Filtra apenas espécies lendárias\n"
			"  --mythical              Filtra apenas espécies míticas\n"
			"  --no_nickname           Pokémon sem nickname\n"
			"  --has_nickname          Pokémon com nickname\n"
			"  --no_held_item          Pokémon sem item segurado\n"
			"  --has_held_item         Pokémon com item segurado\n"
			"  --fainted               Pokémon desmaiados (HP = 0)\n"
			"  --healthy               Pokémon com HP cheio\n"
			"  --duplicates            Apenas espécies duplicadas\n"
			"  --unique                Apenas espécies únicas\n\n"
			"FILTRAGEM NUMÉRICA\n"
			"  --min_iv N              Seleciona apenas Pokémon com IV total >= N (valor em %)\n"
			"  --max_iv N              Seleciona apenas Pokémon com IV total <= N (valor em %)\n"
			"  --min_level N           Seleciona apenas Pokémon com level >= N\n"
			"  --max_level N           Seleciona apenas Pokémon com level <= N\n"
			"  --level <N...>          Filtra por levels exatos (aceita vários)\n"
			"  --min_ev N              Seleciona apenas Pokémon com EV total >= N\n"
			"  --max_ev N              Seleciona apenas Pokémon com EV total <= N\n\n"
			"FILTRAGEM POR IV INDIVIDUAL\n"
			"  --hpiv <N...>           IV exato de HP\n"
			"  --atkiv <N...>          IV exato de Attack\n"
			"  --defiv <N...>          IV exato de Defense\n"
			"  --spatkiv <N...>        IV exato de Special Attack\n"
			"  --spdefiv <N...>        IV exato de Special Defense\n"
			"  --spdiv <N...>          IV exato de Speed\n"
			"  --iv <N...>             IV total em % exato (ex.: 100 = perfeitos)\n\n"
			"FILTRAGEM POR EV INDIVIDUAL\n"
			"  --hpev <N...>           EV exato de HP\n"
			"  --atkev <N...>          EV exato de Attack\n"
			"  --defev <N...>          EV exato de Defense\n"
			"  --spatkev <N...>        EV exato de Special Attack\n"
			"  --spdefev <N...>        EV exato de Special Defense\n"
			"  --spedev <N...>         EV exato de Speed\n\n"
			"FILTRAGEM AVANÇADA DE IVs\n"
			"  --triple_31             Pelo menos 3 IVs perfeitos (31)\n"
			"  --quad_31               Pelo menos 4 IVs perfeitos (31)\n"
			"  --penta_31              Pelo menos 5 IVs perfeitos (31)\n"
			"  --hexa_31               6 IVs perfeitos (31)\n"
			"  --triple_0              Pelo menos 3 IVs em 0\n"
			"  --quad_0                Pelo menos 4 IVs em 0\n\n"
			"EXPERIÊNCIA E CRESCIMENTO\n"
			"  --growth_type <tipo>    Tipo de crescimento: slow | medium | fast | medium-slow | slow-then-very-fast | fast-then-very-slow\n"
			"  --min_exp N             Experiência mínima\n"
			"  --max_exp N             Experiência máxima\n"
			"  --exp <N...>            Experiência exata\n"
			"  --exp_percent <N...>    Percentual de progresso no nível (0-100)\n\n"
			"MOVIMENTOS E VISUAL\n"
			"  --min_move_count N      Número mínimo de movimentos\n"
			"  --max_move_count N      Número máximo de movimentos\n"
			"  --move_count <N...>     Número exato de movimentos\n"
			"  --background <tipo>     Background específico\n\n"
			"ORDENAÇÃO\n"
			"  --sort <campo>          Define critério de ordenação: iv | level | id | name | species | ev | hp | exp | growth\n"
			"  --reverse               Inverte a ordem de ordenação\n"
			"  --random                Embaralha a ordem (ignora sort)\n\n"
			"PAGINAÇÃO E LIMITES\n"
			"  --page N                Define a página inicial (1-based, padrão: 1)\n"
			"  --page_size N           Define o número de Pokémon por página (padrão: 20)\n"
			"  --limit N               Define um limite máximo de Pokémon retornados\n\n"
			"EXEMPLOS\n"
			"  .pokemon --party\n"
			"  .pokemon --box --shiny\n"
			"  .pokemon --species 25 133 --min_iv 85 --sort level --reverse\n"
			"  .pokemon --type fire flying --region kalos\n"
			"  --hexa_31 --shiny\n"
			"  .pokemon --growth_type slow medium-slow\n"
			"  .pokemon --exp_percent 90 95 100\n"
			"  .pokemon --duplicates --sort species\n"
			"  .pokemon --triple_31 --min_level 50"
		)
	)
	@requires_account()
	async def pokemon_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		page_size = flags.get("page_size") if flags.get("page_size") and flags.get("page_size", 20) > 0 else 20
		view = Paginator(
			items=pokemons,
			user_id=ctx.author.id,
			embed_generator=generate_pokemon_embed,
			page_size=page_size,
			current_page=flags.get("page", 0)
		)
		embed = await view.get_embed()
		await ctx.send(embed=embed, view=view)

	@commands.command(name="favorite", aliases=["fav"])
	@requires_account()
	async def favorite_pokemon(self, ctx, pokemon_id: int):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		try:
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			if pokemon.get("is_favorite"):
				return await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True)} já está nos favoritos!")
			
			toolkit.toggle_favorite(user_id, pokemon_id)
			await ctx.send(f"❤️ {format_pokemon_display(pokemon, bold_name=True)} foi adicionado aos favoritos!")
		except ValueError:
			return

	@commands.command(name="unfavourite", aliases=["unfav", "unfavorite"])
	@requires_account()
	async def unfavourite_pokemon(self, ctx, pokemon_id: int):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		try:
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			if not pokemon.get("is_favorite"):
				return await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True)} já não está nos favoritos!")
			
			toolkit.toggle_favorite(user_id, pokemon_id)
			await ctx.send(f"💔 {format_pokemon_display(pokemon, bold_name=True)} foi removido dos favoritos!")
		except ValueError:
			return

	@commands.command(name="nickname", aliases=["nick"])
	@requires_account()
	async def set_nickname(self, ctx, pokemon_id: int, *, nickname: Optional[str] = None):
		user_id = str(ctx.author.id)
		if nickname:
			nickname = nickname.strip()
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		if nickname and len(nickname) > 20:
			return await ctx.send("O nickname deve ter no máximo 20 caracteres!")
		
		try:
			toolkit.set_nickname(user_id, pokemon_id, nickname)
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			
			if nickname:
				await ctx.send(f"Nickname definido como **{nickname}** para o {format_pokemon_display(pokemon, bold_name=True, show_nick=False)}!")
			else:
				await ctx.send(f"Nickname do {format_pokemon_display(pokemon, bold_name=True)} removido!")
		except ValueError:
			return

	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str, nargs="+", action="append")
	@flags.add_flag("--region", "--r", type=str, nargs="+", action="append")
	@flags.add_flag("--gender", type=str)
	@flags.add_flag("--shiny", action="store_true")
	@flags.add_flag("--legendary", action="store_true")
	@flags.add_flag("--mythical", action="store_true")
	@flags.add_flag("--party", action="store_true")
	@flags.add_flag("--box", action="store_true")
	@flags.add_flag("--favorite", action="store_true")
	@flags.add_flag("--held_item", nargs="+", action="append")
	@flags.add_flag("--nature", nargs="+", action="append")
	@flags.add_flag("--ability", nargs="+", action="append")
	@flags.add_flag("--species", nargs="+", action="append", type=int)
	@flags.add_flag("--reverse", action="store_true")
	@flags.add_flag("--random", action="store_true")
	@flags.add_flag("--sort", type=str)
	@flags.add_flag("--min_iv", type=int)
	@flags.add_flag("--max_iv", type=int)
	@flags.add_flag("--min_level", type=int)
	@flags.add_flag("--max_level", type=int)
	@flags.add_flag("--level", nargs="+", action="append")
	@flags.add_flag("--hpiv", nargs="+", action="append")
	@flags.add_flag("--atkiv", nargs="+", action="append")
	@flags.add_flag("--defiv", nargs="+", action="append")
	@flags.add_flag("--spatkiv", nargs="+", action="append")
	@flags.add_flag("--spdefiv", nargs="+", action="append")
	@flags.add_flag("--spdiv", nargs="+", action="append")
	@flags.add_flag("--iv", nargs="+", action="append")
	@flags.add_flag("--min_ev", type=int)
	@flags.add_flag("--max_ev", type=int)
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
	@flags.add_flag("--growth_type", nargs="+", action="append")
	@flags.add_flag("--min_exp", type=int)
	@flags.add_flag("--max_exp", type=int)
	@flags.add_flag("--exp", nargs="+", action="append")
	@flags.add_flag("--exp_percent", nargs="+", action="append")
	@flags.add_flag("--background", nargs="+", action="append")
	@flags.add_flag("--min_move_count", type=int)
	@flags.add_flag("--max_move_count", type=int)
	@flags.add_flag("--move_count", nargs="+", action="append")
	@flags.add_flag("--triple_31", action="store_true")
	@flags.add_flag("--quad_31", action="store_true")
	@flags.add_flag("--penta_31", action="store_true")
	@flags.add_flag("--hexa_31", action="store_true")
	@flags.add_flag("--triple_0", action="store_true")
	@flags.add_flag("--quad_0", action="store_true")
	@flags.add_flag("--duplicates", action="store_true")
	@flags.add_flag("--unique", action="store_true")
	@flags.add_flag("--limit", type=int)
	@flags.command(
		name="favoriteall",
		aliases=["favall"],
		help=(
			"Marca todos os Pokémon que correspondem aos filtros como favoritos.\n\n"
			"Aceita as mesmas flags de filtro do comando .pokemon\n\n"
			"EXEMPLOS\n"
			"  .favoriteall --shiny\n"
			"  .favoriteall --species 25 --min_iv 90\n"
			"  .favoriteall --legendary --box"
		)
	)
	@requires_account()
	async def favoriteall_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		pokemons_to_fav = [p for p in pokemons if not p.get("is_favorite")]
		
		if not pokemons_to_fav:
			return await ctx.send("Todos os Pokémon encontrados já estão favoritados!")

		stats = analyze_pokemons(pokemons_to_fav)
		
		message_parts = [f"Você tem certeza que quer **favoritar {len(pokemons_to_fav)}** pokémon?"]
		
		details = []
		if stats["event"] > 0:
			details.append(f"• **{stats['event']}** Pokémon de Eventos")
		if stats["rare"] > 0:
			details.append(f"• **{stats['rare']}** Pokémon Raros (Lendários e Míticos)")
		if stats["shiny"] > 0:
			details.append(f"• **{stats['shiny']}** Pokémon Shiny")
		if stats["iv_100"] > 0:
			details.append(f"• **{stats['iv_100']}** Pokémon com **IV = 100%**")
		if stats["iv_90_100"] > 0:
			details.append(f"• **{stats['iv_90_100']}** Pokémon com **IV ≥ 90%, < 100%**")
		if stats["iv_80_90"] > 0:
			details.append(f"• **{stats['iv_80_90']}** Pokémon com **IV ≥ 80%, < 90%**")
		
		if details:
			message_parts.append("\n**Incluindo:**")
			message_parts.extend(details)
		
		message_parts.append("\n-# *Você tem 60 segundos para confirmar.*")
		
		view = ConfirmationView(ctx.author.id, timeout=60)
		message = await ctx.send("\n".join(message_parts), view=view)
		
		await view.wait()
		
		if view.value is None or view.value is False:
			for item in view.children:
				item.disabled = True
			await message.edit(content="**Operação cancelada ou com tempo limite esgotado.**", view=None)
			return

		pokemon_ids = [p["id"] for p in pokemons_to_fav]
		updated = toolkit.bulk_update_pokemon(user_id, pokemon_ids, {"is_favorite": True})
		count = len(updated)

		if count == 0:
			result_text = "Não foi possível favoritar nenhum Pokémon!"
		else:
			result_text = f"❤️ **{count}** Pokémon foram favoritados!"
		
		for item in view.children:
			item.disabled = True
		
		await message.edit(content=result_text, view=None)

	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str, nargs="+", action="append")
	@flags.add_flag("--region", "--r", type=str, nargs="+", action="append")
	@flags.add_flag("--gender", type=str)
	@flags.add_flag("--shiny", action="store_true")
	@flags.add_flag("--legendary", action="store_true")
	@flags.add_flag("--mythical", action="store_true")
	@flags.add_flag("--party", action="store_true")
	@flags.add_flag("--box", action="store_true")
	@flags.add_flag("--favorite", action="store_true")
	@flags.add_flag("--held_item", nargs="+", action="append")
	@flags.add_flag("--nature", nargs="+", action="append")
	@flags.add_flag("--ability", nargs="+", action="append")
	@flags.add_flag("--species", nargs="+", action="append", type=int)
	@flags.add_flag("--reverse", action="store_true")
	@flags.add_flag("--random", action="store_true")
	@flags.add_flag("--sort", type=str)
	@flags.add_flag("--min_iv", type=int)
	@flags.add_flag("--max_iv", type=int)
	@flags.add_flag("--min_level", type=int)
	@flags.add_flag("--max_level", type=int)
	@flags.add_flag("--level", nargs="+", action="append")
	@flags.add_flag("--hpiv", nargs="+", action="append")
	@flags.add_flag("--atkiv", nargs="+", action="append")
	@flags.add_flag("--defiv", nargs="+", action="append")
	@flags.add_flag("--spatkiv", nargs="+", action="append")
	@flags.add_flag("--spdefiv", nargs="+", action="append")
	@flags.add_flag("--spdiv", nargs="+", action="append")
	@flags.add_flag("--iv", nargs="+", action="append")
	@flags.add_flag("--min_ev", type=int)
	@flags.add_flag("--max_ev", type=int)
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
	@flags.add_flag("--growth_type", nargs="+", action="append")
	@flags.add_flag("--min_exp", type=int)
	@flags.add_flag("--max_exp", type=int)
	@flags.add_flag("--exp", nargs="+", action="append")
	@flags.add_flag("--exp_percent", nargs="+", action="append")
	@flags.add_flag("--background", nargs="+", action="append")
	@flags.add_flag("--min_move_count", type=int)
	@flags.add_flag("--max_move_count", type=int)
	@flags.add_flag("--move_count", nargs="+", action="append")
	@flags.add_flag("--triple_31", action="store_true")
	@flags.add_flag("--quad_31", action="store_true")
	@flags.add_flag("--penta_31", action="store_true")
	@flags.add_flag("--hexa_31", action="store_true")
	@flags.add_flag("--triple_0", action="store_true")
	@flags.add_flag("--quad_0", action="store_true")
	@flags.add_flag("--duplicates", action="store_true")
	@flags.add_flag("--unique", action="store_true")
	@flags.add_flag("--limit", type=int)
	@flags.command(
		name="unfavouriteall",
		aliases=["unfavall", "unfavoriteall"],
		help=(
			"Remove todos os Pokémon que correspondem aos filtros dos favoritos.\n\n"
			"Aceita as mesmas flags de filtro do comando .pokemon\n\n"
			"EXEMPLOS\n"
			"  .unfavouriteall --favorite\n"
			"  .unfavouriteall --species 25 --max_iv 50\n"
			"  .unfavouriteall --box --min_level 1 --max_level 10"
		)
	)
	@requires_account()
	async def unfavouriteall_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		pokemons_to_unfav = [p for p in pokemons if p.get("is_favorite")]
		
		if not pokemons_to_unfav:
			return await ctx.send("Nenhum dos Pokémon encontrados está favoritado!")

		stats = analyze_pokemons(pokemons_to_unfav)
		
		message_parts = [f"Você tem certeza que quer **desfavoritar {len(pokemons_to_unfav)}** pokémon?"]
		
		details = []
		if stats["event"] > 0:
			details.append(f"• **{stats['event']}** Pokémon de Eventos")
		if stats["rare"] > 0:
			details.append(f"• **{stats['rare']}** Pokémon Raros (Lendários e Míticos)")
		if stats["shiny"] > 0:
			details.append(f"• **{stats['shiny']}** Pokémon Shiny")
		if stats["iv_100"] > 0:
			details.append(f"• **{stats['iv_100']}** Pokémon com **IV = 100%**")
		if stats["iv_90_100"] > 0:
			details.append(f"• **{stats['iv_90_100']}** Pokémon com **IV ≥ 90%, < 100%**")
		if stats["iv_80_90"] > 0:
			details.append(f"• **{stats['iv_80_90']}** Pokémon com **IV ≥ 80%, < 90%**")
		
		if details:
			message_parts.append("\n**Incluindo:**")
			message_parts.extend(details)
		
		message_parts.append("\n-# *Você tem 60 segundos para confirmar.*")
		
		view = ConfirmationView(ctx.author.id, timeout=60)
		message = await ctx.send("\n".join(message_parts), view=view)
		
		await view.wait()
		
		if view.value is None or view.value is False:
			for item in view.children:
				item.disabled = True
			await message.edit(content="**Operação cancelada ou com tempo limite esgotado.**", view=None)
			return

		pokemon_ids = [p["id"] for p in pokemons_to_unfav]
		updated = toolkit.bulk_update_pokemon(user_id, pokemon_ids, {"is_favorite": False})
		count = len(updated)

		if count == 0:
			result_text = "Não foi possível desfavoritar nenhum Pokémon!"
		else:
			result_text = f"💔 **{count}** Pokémon foram removidos dos favoritos!"
		
		for item in view.children:
			item.disabled = True
		
		await message.edit(content=result_text, view=None)

	@flags.add_flag("newname", nargs="+")
	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str, nargs="+", action="append")
	@flags.add_flag("--region", "--r", type=str, nargs="+", action="append")
	@flags.add_flag("--gender", type=str)
	@flags.add_flag("--shiny", action="store_true")
	@flags.add_flag("--legendary", action="store_true")
	@flags.add_flag("--mythical", action="store_true")
	@flags.add_flag("--party", action="store_true")
	@flags.add_flag("--box", action="store_true")
	@flags.add_flag("--favorite", action="store_true")
	@flags.add_flag("--held_item", nargs="+", action="append")
	@flags.add_flag("--nature", nargs="+", action="append")
	@flags.add_flag("--ability", nargs="+", action="append")
	@flags.add_flag("--species", nargs="+", action="append", type=int)
	@flags.add_flag("--reverse", action="store_true")
	@flags.add_flag("--random", action="store_true")
	@flags.add_flag("--sort", type=str)
	@flags.add_flag("--min_iv", type=int)
	@flags.add_flag("--max_iv", type=int)
	@flags.add_flag("--min_level", type=int)
	@flags.add_flag("--max_level", type=int)
	@flags.add_flag("--level", nargs="+", action="append")
	@flags.add_flag("--hpiv", nargs="+", action="append")
	@flags.add_flag("--atkiv", nargs="+", action="append")
	@flags.add_flag("--defiv", nargs="+", action="append")
	@flags.add_flag("--spatkiv", nargs="+", action="append")
	@flags.add_flag("--spdefiv", nargs="+", action="append")
	@flags.add_flag("--spdiv", nargs="+", action="append")
	@flags.add_flag("--iv", nargs="+", action="append")
	@flags.add_flag("--min_ev", type=int)
	@flags.add_flag("--max_ev", type=int)
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
	@flags.add_flag("--growth_type", nargs="+", action="append")
	@flags.add_flag("--min_exp", type=int)
	@flags.add_flag("--max_exp", type=int)
	@flags.add_flag("--exp", nargs="+", action="append")
	@flags.add_flag("--exp_percent", nargs="+", action="append")
	@flags.add_flag("--background", nargs="+", action="append")
	@flags.add_flag("--min_move_count", type=int)
	@flags.add_flag("--max_move_count", type=int)
	@flags.add_flag("--move_count", nargs="+", action="append")
	@flags.add_flag("--triple_31", action="store_true")
	@flags.add_flag("--quad_31", action="store_true")
	@flags.add_flag("--penta_31", action="store_true")
	@flags.add_flag("--hexa_31", action="store_true")
	@flags.add_flag("--triple_0", action="store_true")
	@flags.add_flag("--quad_0", action="store_true")
	@flags.add_flag("--duplicates", action="store_true")
	@flags.add_flag("--unique", action="store_true")
	@flags.add_flag("--limit", type=int)
	@flags.command(
		name="nicknameall",
		aliases=["nickall"],
		help=(
			"Define o mesmo nickname para todos os Pokémon que correspondem aos filtros.\n\n"
			"Aceita as mesmas flags de filtro do comando .pokemon\n\n"
			"EXEMPLOS\n"
			"  .nicknameall Campeão --species 25\n"
			"  .nicknameall Shiny --shiny\n"
			"  .nicknameall clear --box (remove nickname de todos na box)"
		)
	)
	@requires_account()
	async def nicknameall_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		nickname = " ".join(flags.get("newname", []))
		
		if nickname.lower() == "clear":
			nickname = ""
		
		if nickname and len(nickname) > 20:
			return await ctx.send("O nickname deve ter no máximo 20 caracteres!")
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		stats = analyze_pokemons(pokemons)
		
		action_text = f"renomear **{len(pokemons)}** pokémon para `{nickname}`" if nickname else f"remover nicknames de **{len(pokemons)}** pokémon"
		
		message_parts = [f"Você tem certeza que quer {action_text}?"]
		
		details = []
		if stats["event"] > 0:
			details.append(f"• **{stats['event']}** Pokémon de Eventos")
		if stats["rare"] > 0:
			details.append(f"• **{stats['rare']}** Pokémon Raros (Lendários e Míticos)")
		if stats["shiny"] > 0:
			details.append(f"• **{stats['shiny']}** Pokémon Shiny")
		if stats["favorite"] > 0:
			details.append(f"• **{stats['favorite']}** Pokémon Favoritados")
		if stats["iv_100"] > 0:
			details.append(f"• **{stats['iv_100']}** Pokémon com **IV = 100%**")
		if stats["iv_90_100"] > 0:
			details.append(f"• **{stats['iv_90_100']}** Pokémon com **IV ≥ 90%, < 100%**")
		if stats["iv_80_90"] > 0:
			details.append(f"• **{stats['iv_80_90']}** Pokémon com **IV ≥ 80%, < 90%**")
		
		if details:
			message_parts.append("\n**Incluindo:**")
			message_parts.extend(details)
		
		message_parts.append("\n-# *Você tem 60 segundos para confirmar.*")
		
		view = ConfirmationView(ctx.author.id, timeout=60)
		message = await ctx.send("\n".join(message_parts), view=view)
		
		await view.wait()
		
		if view.value is None or view.value is False:
			for item in view.children:
				item.disabled = True
			await message.edit(content="**Operação cancelada ou com tempo limite esgotado.**", view=None)
			return
		
		pokemon_ids = [p["id"] for p in pokemons]
		updated = toolkit.bulk_update_pokemon(user_id, pokemon_ids, {"nickname": nickname if nickname else None})
		count = len(updated)

		if count == 0:
			result_text = "Não foi possível alterar o nickname de nenhum Pokémon!"
		else:
			action = f"alterado para **{nickname}**" if nickname else "removido"
			result_text = f"Nickname {action} para **{count}** Pokémon!"
		
		for item in view.children:
			item.disabled = True
		
		await message.edit(content=result_text, view=None)

	@commands.command(name="heal")
	@requires_account()
	@not_in_battle()
	async def heal_party_command(self, ctx: commands.Context) -> None:
		user_id: str = str(ctx.author.id)
		party = toolkit.get_user_party(user_id)
		if not party:
			return await ctx.send("Seu time está vazio.")
		
		toolkit.heal_party(user_id)
		await ctx.send("Todos os pokémon do seu time estão curados (HP e PP).")

	@commands.cooldown(3, 5, commands.BucketType.user)
	@commands.command(name="info", aliases=["i", "inf"])
	async def info_command(self, ctx: commands.Context, pokemon_id: Optional[int] = None) -> None:
		user_id = str(ctx.author.id)
		all_pokemons = toolkit.get_user_pokemon(user_id)
		
		if not all_pokemons:
			await ctx.send("Voce nao possui nenhum Pokemon!")
			return
			
		all_pokemon_ids = [p['id'] for p in all_pokemons]
		
		current_pokemon_id = pokemon_id
		if current_pokemon_id is None:
			party = toolkit.get_user_party(user_id)
			current_pokemon_id = party[0]['id'] if party else all_pokemon_ids[0]
		
		if current_pokemon_id not in all_pokemon_ids:
			await ctx.send("Voce nao possui um Pokemon com este ID.")
			return

		current_index = all_pokemon_ids.index(current_pokemon_id)
		
		result = await generate_info_embed(user_id, current_pokemon_id)
		if result:
			embed, files = result
			view = InfoView(self, ctx.author.id, all_pokemon_ids, current_index)
			await ctx.send(embed=embed, files=files, view=view)
		else:
			await ctx.send("Nao pude encontrar esse Pokemon!")

async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))

