import io
import discord
import aiopoke
from discord.ext import commands
from __main__ import toolkit, pm
from pokemon_sdk.calculations import calculate_stats
from pokemon_sdk.constants import STAT_KEYS
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
			await interaction.response.edit_message(content="Erro ao carregar este Pokémon.", embed=None, attachments=[], view=self)

	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
	async def prev_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_index > 0:
			self.current_index -= 1
			await self._update_info(interaction)

	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
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

		title = f"Level {user_pokemon['level']} {format_pokemon_display(user_pokemon, show_fav=True, show_poke=False)}"
		
		sprite_to_use = pokemon.sprites.front_shiny if user_pokemon['is_shiny'] else pokemon.sprites.front_default
		sprite_bytes = await sprite_to_use.read() if sprite_to_use else None
		
		files = []
		if sprite_bytes:
			buffer = await compose_pokemon_async(sprite_bytes, preloaded_info_backgrounds[user_pokemon['background']])
			img_file = discord.File(buffer, filename="pokemon.png")
			files.append(img_file)

		stats_lines = [f"**{STAT_LABELS[key]}:** {stats[key]} (IV {user_pokemon['ivs'].get(key, 0)})" for key in STAT_KEYS]
		stats_lines[0] = f"**HP:** {current_hp}/{stats['hp']} (IV {user_pokemon['ivs'].get('hp', 0)})"

		moves_lines = [f"**{move['id'].replace('-', ' ').title()}** ({move['pp']}/{move['pp_max']} PP)" for move in user_pokemon.get("moves", [])]
		
		future_moves = []
		learned_move_names = set()
		for move_version in pokemon.moves:
			for detail in move_version.version_group_details:
				if detail.move_learn_method.name == 'level-up' and detail.level_learned_at > user_pokemon['level']:
					if move_version.move.name not in learned_move_names:
						future_moves.append((detail.level_learned_at, move_version.move.name))
						learned_move_names.add(move_version.move.name)
		future_moves.sort()
		future_moves_lines = [f"**Lv. {lvl}:** {name.replace('-', ' ').title()}" for lvl, name in future_moves[:5]]

		embed = discord.Embed(title=title, color=discord.Color.blurple())
		embed.add_field(name="Detalhes", value=(f"**ID da Espécie:** {user_pokemon.get("species_id")}\n**XP:** {user_pokemon['exp']}\n**Natureza:** {user_pokemon['nature']}\n**Gênero:** {user_pokemon.get('gender','N/A')}\n**Habilidade:** {str(user_pokemon.get('ability') or '-').title()}\n**Tipos:** {' / '.join(t.title() for t in user_pokemon['types'])}\n**Região:** {user_pokemon['region']}\n**Item:** {str(user_pokemon.get('held_item') or '-').title()}"), inline=False)
		embed.add_field(name="IV Geral", value=f"**{iv_total}/186 ({iv_percent}%)**", inline=False)
		embed.add_field(name="Estatísticas", value="\n".join(stats_lines), inline=False)
		if moves_lines:
			embed.add_field(name="Movimentos Atuais", value="\n".join(moves_lines), inline=True)
		if future_moves_lines:
			embed.add_field(name="Próximos Movimentos", value="\n".join(future_moves_lines), inline=True)

		embed.set_footer(text=f"ID: {pokemon_id} • Capturado em {datetime.fromisoformat(user_pokemon['caught_at']).strftime('%d/%m/%Y às %H:%M')}")
		
		if files and any(f.filename == "pokemon.png" for f in files):
			embed.set_image(url="attachment://pokemon.png")

		return embed, files

	@commands.cooldown(3, 5, commands.BucketType.user)
	@commands.command(name="info", aliases=["i", "inf"])
	async def info_command(self, ctx: commands.Context, pokemon_id: Optional[int] = None) -> None:
		user_id = str(ctx.author.id)
		all_pokemons = toolkit.get_user_pokemon(user_id)
		
		if not all_pokemons:
			await ctx.send("Você não possui nenhum Pokémon!")
			return
			
		all_pokemon_ids = [p['id'] for p in all_pokemons]
		
		current_pokemon_id = pokemon_id
		if current_pokemon_id is None:
			party = toolkit.get_user_party(user_id)
			current_pokemon_id = party[0]['id'] if party else all_pokemon_ids[0]
		
		if current_pokemon_id not in all_pokemon_ids:
			await ctx.send("Você não possui um Pokémon com este ID.")
			return

		current_index = all_pokemon_ids.index(current_pokemon_id)
		
		result = await self._generate_info_embed(user_id, current_pokemon_id)
		if result:
			embed, files = result
			view = InfoView(self, ctx.author.id, all_pokemon_ids, current_index)
			await ctx.send(embed=embed, files=files, view=view)
		else:
			await ctx.send("Não pude encontrar esse Pokémon!")


async def setup(bot: commands.Bot) -> None:

	await bot.add_cog(Info(bot))
