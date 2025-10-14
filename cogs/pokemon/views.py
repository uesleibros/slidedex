import discord
from sdk.calculations import iv_percent, calculate_stats
from sdk.constants import STAT_KEYS, STAT_LABELS
from sdk.items.constants import ITEM_EMOJIS
from utilities.formatting import format_pokemon_display, format_happiness_status, format_nature_info, format_item_display
from typing import Dict, List
from sdk.toolkit import Toolkit

class PokemonListLayout(discord.ui.LayoutView):
	def __init__(self, pokemons: List, current_page: int = 0, per_page: int = 20):
		super().__init__()
		self.pokemons = pokemons
		self.per_page = per_page
		self.current_page = current_page
		self.total_pages = (len(pokemons) - 1) // per_page + 1

		self.build_page()

	def build_page(self):
		self.clear_items()

		start_idx = self.current_page * self.per_page
		end_idx = min(start_idx + self.per_page, len(self.pokemons))
		page_pokemons = self.pokemons[start_idx:end_idx]

		container: discord.ui.Container = discord.ui.Container()
		container.add_item(discord.ui.TextDisplay(
			"### Seus Pokémon"
		))
		container.add_item(discord.ui.Separator())

		for pokemon in page_pokemons:			
			container.add_item(discord.ui.TextDisplay(
				f"`{str(pokemon['id']).zfill(3)}`　{format_pokemon_display(pokemon, show_fav=True)}　•　Lv. {pokemon['level']}　•　{iv_percent(pokemon['ivs'])}%"
			))

		container.add_item(discord.ui.Separator())

		container.add_item(discord.ui.TextDisplay(
			f"-# Mostrando {start_idx+1}–{end_idx} de {self.total_pages}"
		))

		self.add_item(container)

		action_row: discord.ui.ActionRow = discord.ui.ActionRow()
		
		prev_button: discord.ui.Button = discord.ui.Button(
			emoji="◀️",
			style=discord.ButtonStyle.secondary,
			disabled=self.current_page == 0,
			custom_id="prev_page"
		)
		prev_button.callback = self.previous_page
		action_row.add_item(prev_button)
		
		next_button: discord.ui.Button = discord.ui.Button(
			emoji="▶️",
			style=discord.ButtonStyle.secondary,
			disabled=self.current_page >= self.total_pages - 1,
			custom_id="next_page"
		)
		next_button.callback = self.next_page
		action_row.add_item(next_button)
		
		self.add_item(action_row)

	async def previous_page(self, interaction: discord.Interaction):		
		self.current_page -= 1
		self.build_page()
		await interaction.response.edit_message(view=self)

	async def next_page(self, interaction: discord.Interaction):		
		self.current_page += 1
		self.build_page()
		await interaction.response.edit_message(view=self)

class PokemonInfoLayout(discord.ui.LayoutView):
	__slots__ = ('current_pokemon', 'current_index', 'total_pages', 'tk', 'show_iv', 'show_future_moves', '_cached_stats', '_cached_future_moves', '_pokemon_data')
	
	def __init__(self, current_pokemon: Dict, current_index: int, total_pages: int, tk: Toolkit):
		super().__init__()
		self.current_pokemon = current_pokemon
		self.current_index = current_index
		self.total_pages = total_pages
		self.tk = tk
		self.show_iv = True
		self.show_future_moves = False
		self._cached_stats = None
		self._cached_future_moves = None
		self._pokemon_data = None
		
		self.build_page()

	def _get_stats(self):
		if self._cached_stats is None:
			cp = self.current_pokemon
			self._cached_stats = calculate_stats(cp['base_stats'], cp["ivs"], cp.get("evs", {}), cp["level"], cp["nature"])
		return self._cached_stats

	def _get_future_moves(self):
		if self._cached_future_moves is None:
			if self._pokemon_data is None:
				self._pokemon_data = self.tk.api.get_pokemon(self.current_pokemon["species_id"])
			self._cached_future_moves = self.tk.api.get_future_moves(self._pokemon_data, self.current_pokemon["level"])
		return self._cached_future_moves

	def build_page(self):
		self.clear_items()
		
		cp = self.current_pokemon
		stats = self._get_stats()
		current_hp = cp.get("current_hp") if cp.get("current_hp") is not None else stats["hp"]
		
		ivs = cp["ivs"]
		iv_total = sum(ivs.values())
		iv_percent = round(iv_total * 100 / 186, 2)
		
		evs = cp.get("evs", {})
		ev_total = sum(evs.values())
		ev_percent = round(ev_total * 100 / 510, 2)
		
		level = cp["level"]
		growth_type = cp.get("growth_type")
		current_exp = cp.get("exp", 0)
		
		exp_current = self.tk.get_exp_for_level(growth_type, level)
		
		if level >= 100:
			exp_next = exp_current
			exp_needed = 0
			exp_percent = 100.0
		else:
			exp_next = self.tk.get_exp_for_level(growth_type, level + 1)
			exp_needed = exp_next - exp_current
			exp_percent = round((current_exp - exp_current) * 100 / exp_needed, 1) if exp_needed > 0 else 0

		container = discord.ui.Container()
		container.add_item(discord.ui.TextDisplay(
			f"### Level {level} {format_pokemon_display(cp, show_fav=True, show_poke=False)}\n"
			f"<:emojigg_ID:1424200976557932685> **ID do Pokemon:** {cp['id']}\n"
			f"<:emojigg_ID:1424200976557932685> **ID da Espécie:** {cp['species_id']}\n"
		))

		container.add_item(discord.ui.Separator())
		
		stats_section = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://stats.png"))
		stats_section.add_item(discord.ui.TextDisplay(
			f"<:CometShard:1424200074463805551> **Experiência:** {current_exp}/{exp_next} | Próximo: {exp_needed} XP ({exp_percent}%)\n"
			f":leaves: **Natureza:** {format_nature_info(cp['nature'])}\n"
			f"<:speechbubble_heart:1424195141199204467> **Amizade:** {format_happiness_status(cp['happiness'])}\n"
			f":kite: **Tipo de Crescimento:** {growth_type.replace('-', ' ').title()}\n"
			f"🧬 **Habilidade:** {str(cp.get('ability') or '-').replace('-', ' ').title()}\n"
			f":rock: **Tipos:** {' / '.join([t.title() for t in cp['types']])}\n"
			f"<:research_encounter:1424202205757444096> **Região:** {cp['region'].replace('-', ' ').title()}\n"
			f":empty_nest: **Item Segurado:** {format_item_display(cp.get('held_item'))}\n"
			f"🧺 **Capturado com**: {ITEM_EMOJIS.get(cp.get('caught_with'), 'poke-ball')}"
		))
		container.add_item(stats_section)
		container.add_item(discord.ui.Separator())

		base_stats = cp['base_stats']
		
		if self.show_iv:
			stats_lines = [f"<:stats:1424204552910929920> **IV Total:** {iv_total}/186 ({iv_percent}%)"]
			stats_data = ivs
			stat_label_prefix = "IV"
			thumbnail = "attachment://iv.png"
		else:
			stats_lines = [f"<:stats:1424204552910929920> **EV Total:** {ev_total}/510 ({ev_percent}%)"]
			stats_data = evs
			stat_label_prefix = "EV"
			thumbnail = "attachment://ev.png"
		
		for key in STAT_KEYS:
			base = base_stats.get(key, 0)
			value = stats_data.get(key, 0)
			final = stats[key]
			
			if key == "hp":
				stats_lines.append(f"<:stats:1424204552910929920> **HP:** {current_hp}/{final} | Base: {base} | {stat_label_prefix}: {value}")
			else:
				stats_lines.append(f"<:stats:1424204552910929920> **{STAT_LABELS[key]}:** {final} | Base: {base} | {stat_label_prefix}: {value}")
		
		stats_section = discord.ui.Section(accessory=discord.ui.Thumbnail(thumbnail))
		stats_section.add_item(discord.ui.TextDisplay('\n'.join(stats_lines)))
		container.add_item(stats_section)

		stats_action_row = discord.ui.ActionRow()
		toggle_stats_button = discord.ui.Button(
			style=discord.ButtonStyle.secondary,
			label="Mostrar EVs" if self.show_iv else "Mostrar IVs",
			custom_id="toggle_stats"
		)
		toggle_stats_button.callback = self.toggle_stats
		stats_action_row.add_item(toggle_stats_button)
		container.add_item(stats_action_row)

		container.add_item(discord.ui.Separator())

		if self.show_future_moves:
			future_moves = self._get_future_moves()
			moves_lines = [f"**Lv. {lvl}:** {name.replace('-', ' ').title()}" for lvl, name in future_moves[:8]]
			thumbnail = "attachment://future_moves.png"
		else:
			moves_lines = [f"**{move['id'].replace('-', ' ').title()}** ({move['pp']}/{move['pp_max']} PP)" for move in cp.get("moves", [])]
			thumbnail = "attachment://special_move.png"

		moves_section = discord.ui.Section(accessory=discord.ui.Thumbnail(thumbnail))
		moves_section.add_item(discord.ui.TextDisplay('\n'.join(moves_lines)))
		container.add_item(moves_section)
		
		moves_action_row = discord.ui.ActionRow()
		toggle_future_moves_button = discord.ui.Button(
			style=discord.ButtonStyle.secondary,
			label="Mostrar Movimentos Atuais" if self.show_future_moves else "Mostrar Próximos Movimentos",
			custom_id="toggle_future_moves"
		)
		toggle_future_moves_button.callback = self.toggle_future_moves
		moves_action_row.add_item(toggle_future_moves_button)
		container.add_item(moves_action_row)
		
		container.add_item(discord.ui.Separator())
		container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://pokemon.png")))
		container.add_item(discord.ui.Separator())
		container.add_item(discord.ui.TextDisplay(f"-# Pokémon {self.current_index + 1} de {self.total_pages}"))

		self.add_item(container)

	async def toggle_stats(self, interaction: discord.Interaction):
		self.show_iv = not self.show_iv
		self.build_page()
		await interaction.response.edit_message(view=self)
	
	async def toggle_future_moves(self, interaction: discord.Interaction):
		self.show_future_moves = not self.show_future_moves
		self.build_page()
		await interaction.response.edit_message(view=self)
