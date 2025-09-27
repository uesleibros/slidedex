from discord.ext import commands
from utils.pokemon_emojis import get_app_emoji
from pokemon_sdk.calculations import iv_percent
from __main__ import toolkit
from aiopoke import AiopokeClient
from utils.formatting import format_poke_id
import discord

aio_client = AiopokeClient()

class Pokemon(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	@commands.command(name="pokemon", aliases=["p", "pk", "pkm"])
	async def pokemon_command(self, ctx: commands.Context) -> None:
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return

		pokemons = toolkit.get_user_pokemon(user_id)
		desc_lines = []

		for p in pokemons:
			poke_id = p["id"]
			poke = await aio_client.get_pokemon(p["species_id"])
			emoji = get_app_emoji(f"p_{p['species_id']}")
			shiny = "✨ " if p.get("is_shiny", False) else ""
			nickname = f" ({p['nickname']})" if p.get("nickname") else poke.name.title()
			status = ":dagger:" if p.get("on_party", False) else ''
			gender = ":male_sign:" if p["gender"] == "Male" else ":female_sign:"
			level = p["level"]
			ivs = p["ivs"]
			iv_percent_ = iv_percent(ivs)
			desc_lines.append(
				f"`{format_poke_id(poke_id)}`　{emoji}{shiny} **{nickname}** {gender} {status}　•　Lv. {level}　•　{iv_percent_}%"
			)

		embed = discord.Embed(
			title=f"Pokémon de {ctx.author.display_name}",
			description="\n".join(desc_lines),
			color=discord.Color.pink()
		)
		await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))