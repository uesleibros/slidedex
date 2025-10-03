import io
import discord
import aiopoke
from discord.ext import commands
from __main__ import toolkit, pm
from pokemon_sdk.calculations import calculate_stats
from pokemon_sdk.constants import STAT_KEYS, VERSION_GROUPS
from datetime import datetime
from utils.formatting import format_pokemon_display
from utils.canvas import compose_pokemon_async
from utils.preloaded import preloaded_info_backgrounds
from typing import Optional

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

class Info(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	async def _generate_info_embed(self, user_id: str, pokemon_id: int):
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
		
		ev_total = sum(user_pokemon.get("evs", {}).values())

		current_exp = user_pokemon.get("exp", 0)
		current_level = user_pokemon["level"]
		exp_needed = toolkit.exp_to_next_level(current_level)
		exp_progress_percent = round((current_exp / exp_needed) * 100, 1) if exp_needed > 0 else 100

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
			f"**Especie:** #{user_pokemon.get('species_id')} - {user_pokemon.get('name', 'Desconhecido').title()}",
			f"**Nivel:** {current_level}",
			f"**Experiencia:** {current_exp}/{exp_needed} ({exp_progress_percent}%)",
			f"**Natureza:** {user_pokemon['nature'].title()}",
			f"**Genero:** {user_pokemon.get('gender', 'N/A')}",
			f"**Habilidade:** {str(user_pokemon.get('ability') or '-').replace('-', ' ').title()}",
			f"**Tipos:** {' / '.join(t.title() for t in user_pokemon['types'])}",
			f"**Regiao:** {user_pokemon['region'].replace('-', ' ').title()}",
			f"**Item Segurado:** {str(user_pokemon.get('held_item') or 'Nenhum').replace('-', ' ').title()}"
		]

		stats_lines = []
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

		iv_lines = [
			f"**Total:** {iv_total}/186 ({iv_percent}%)",
			f"**HP:** {user_pokemon['ivs'].get('hp', 0)}/31",
			f"**Ataque:** {user_pokemon['ivs'].get('attack', 0)}/31",
			f"**Defesa:** {user_pokemon['ivs'].get('defense', 0)}/31",
			f"**Sp. Atk:** {user_pokemon['ivs'].get('special-attack', 0)}/31",
			f"**Sp. Def:** {user_pokemon['ivs'].get('special-defense', 0)}/31",
			f"**Velocidade:** {user_pokemon['ivs'].get('speed', 0)}/31"
		]

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
		
		embed.add_field(name=f"Individual Values (IVs)", value="\n".join(iv_lines), inline=True)
		embed.add_field(name=f"Effort Values (EVs) - Total: {ev_total}/510", value=f"**HP:** {user_pokemon.get('evs', {}).get('hp', 0)}/255\n**Ataque:** {user_pokemon.get('evs', {}).get('attack', 0)}/255\n**Defesa:** {user_pokemon.get('evs', {}).get('defense', 0)}/255\n**Sp. Atk:** {user_pokemon.get('evs', {}).get('special-attack', 0)}/255\n**Sp. Def:** {user_pokemon.get('evs', {}).get('special-defense', 0)}/255\n**Velocidade:** {user_pokemon.get('evs', {}).get('speed', 0)}/255", inline=True)
		
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
		
		result = await self._generate_info_embed(user_id, current_pokemon_id)
		if result:
			embed, files = result
			view = InfoView(self, ctx.author.id, all_pokemon_ids, current_index)
			await ctx.send(embed=embed, files=files, view=view)
		else:
			await ctx.send("Nao pude encontrar esse Pokemon!")


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Info(bot))