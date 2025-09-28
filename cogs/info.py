import aiopoke
from discord.ext import commands
from __main__ import toolkit, pm
from pokemon_sdk.calculations import calculate_stats
from PIL import Image
from datetime import datetime
from utils.canvas import compose_pokemon
from utils.preloaded import preloaded_info_backgrounds
from curl_cffi import requests
import io
import discord

STAT_ORDER = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
STAT_LABELS = {
	"hp": "HP",
	"attack": "Ataque",
	"defense": "Defesa",
	"special-attack": "Sp. Atk",
	"special-defense": "Sp. Def",
	"speed": "Velocidade",
}

class Info(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name="info", aliases=["i", "inf"])
	async def info_command(self, ctx: commands.Context, pokemon_id: int) -> None:
		user_id = str(ctx.author.id)
		try:
			user_pokemon = toolkit.get_pokemon(user_id, pokemon_id)
		except ValueError:
			await ctx.send(content="Não pude encontrar esse pokémon!")
			return

		pokemon: aiopoke.Pokemon = await pm.service.get_pokemon(user_pokemon["species_id"])
		
		base_stats = {s.stat.name: s.base_stat for s in pokemon.stats}
		ivs = user_pokemon["ivs"]
		evs = user_pokemon.get("evs", {k: 0 for k in base_stats})
		level = user_pokemon["level"]
		nature = user_pokemon["nature"]
		stats = calculate_stats(base_stats, ivs, evs, level, nature)
		current_hp = user_pokemon["current_hp"] if user_pokemon.get("current_hp") is not None else stats["hp"]

		iv_total = sum(ivs.values())
		iv_percent = round((iv_total / 186) * 100, 2)

		name_display = user_pokemon["nickname"] if user_pokemon.get("nickname") else pokemon.name.title()
		title = f"Level {level} {name_display} {'✨' if user_pokemon['is_shiny'] else ''}"

		types = " / ".join(t.type.name.title() for t in sorted(pokemon.types, key=lambda x: x.slot))
		if user_pokemon['is_shiny']:
			sprite_bytes = await pokemon.sprites.front_shiny.read()
		else:
			sprite_bytes = await pokemon.sprites.front_default.read()

		buffer = compose_pokemon(sprite_bytes, preloaded_info_backgrounds[user_pokemon['background']])
		img_file = discord.File(buffer, filename="pokemon.png")

		cry_url = pokemon.cries.latest
		cry_file = None
		if cry_url:
			async with requests.AsyncSession() as session:
				resp = await session.get(cry_url)
				if resp.status_code == 200:
					cry_bytes = io.BytesIO(resp.content)
					cry_ext = "ogg" if cry_url.endswith(".ogg") else "wav"
					cry_file = discord.File(cry_bytes, filename=f"cry.{cry_ext}")

		stats_lines = []
		for key in STAT_ORDER:
			label = STAT_LABELS[key]
			val = stats[key]
			ivv = ivs.get(key, 0)
			if key == "hp":
				stats_lines.append(f"**{label}:** {current_hp}/{val} (IV {ivv})")
			else:
				stats_lines.append(f"**{label}:** {val} (IV {ivv})")

		embed = discord.Embed(title=title, color=discord.Color.blurple())
		embed.add_field(
			name="Detalhes",
			value=(
				f"**XP:** {user_pokemon['exp']}\n"
				f"**Natureza:** {nature}\n"
				f"**Gênero:** {user_pokemon.get('gender','Genderless')}\n"
				f"**Habilidade:** {str(user_pokemon.get('ability') or '-').title()}\n"
				f"**Tipos:** {types}\n"
				f"**Item:** {str(user_pokemon.get('held_item') or '-').title()}"
			),
			inline=False
		)
		embed.add_field(
			name="IV Geral",
			value=f"**{iv_total}/186 ({iv_percent}%)**",
			inline=False
		)
		embed.add_field(
			name="Estatísticas",
			value="\n".join(stats_lines),
			inline=False
		)

		embed.set_footer(text=(
			f"Exibindo pokémon {pokemon_id}.\n"
			f"Capturado em {datetime.fromisoformat(user_pokemon['caught_at']).strftime('%d/%m/%Y às %H:%M:%S')}"
		))

		if ctx.author.avatar:
			embed.set_thumbnail(url=ctx.author.avatar.url)
		if img_file:
			embed.set_image(url="attachment://pokemon.png")

		del pokemon
		
		if cry_file:
			await ctx.send(embed=embed, files=[img_file, cry_file])
		else:
			await ctx.send(embed=embed, file=img_file)

async def setup(bot: commands.Bot) -> None:

	await bot.add_cog(Info(bot))


