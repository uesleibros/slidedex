import random
from typing import Dict, List, Optional
import discord
from discord.ext import commands
from pokemon_sdk.calculations import iv_percent
from utils.formatting import format_poke_id, format_pokemon_display
from helpers.flags import flags
from helpers.paginator import Paginator
from helpers.checks import requires_account
from __main__ import toolkit

async def generate_pokemon_embed(pokemons, start, end, total, current_page):
	desc_lines = []
	for p in pokemons:
		poke_id = p["id"]
		fav = f" ❤️" if p["is_favorite"] else ''
		if p["gender"] != "Genderless":
			gender = ":male_sign:" if p["gender"] == "Male" else ":female_sign:"
		else:
			gender = ":grey_question:"
		ivp = iv_percent(p["ivs"])
		desc_lines.append(
			f"`{format_poke_id(poke_id)}`　{format_pokemon_display(p)} {gender}{fav}　•　Lv. {p['level']}　•　{ivp}%"
		)
	embed = discord.Embed(
		title="Seus Pokémon",
		description="\n".join(desc_lines) if desc_lines else "Sem resultados",
		color=discord.Color.pink()
	)
	embed.set_footer(text=f"Mostrando {start+1}–{end} de {total}")
	return embed

def apply_filters(pokemons: List[Dict], flags) -> List[Dict]:
	res = pokemons
	if flags.get("box") and not flags.get("party"):
		res = [p for p in res if not p.get("on_party", False)]
	if flags.get("party") and not flags.get("box"):
		res = [p for p in res if p.get("on_party", False)]
	if flags.get("shiny"):
		res = [p for p in res if p.get("is_shiny", False)]
	if flags.get("legendary"):
		res = [p for p in res if p.get("is_legendary", False)]
	if flags.get("mythical"):
		res = [p for p in res if p.get("is_mythical", False)]
	if flags.get("favorite"):
		res = [p for p in res if p.get("is_favorite")]
	if flags.get("gender"):
		res = [p for p in res if p["gender"].lower() == flags.get("gender")]
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
		}
		res.sort(key=keymap[flags.get("sort")], reverse=bool(flags.get("reverse")))
	if flags.get("limit") is not None and flags.get("limit") > 0:
		res = res[:flags.get("limit")]
	return res

class Pokemon(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	# Filter
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

	# Sort
	@flags.add_flag("--reverse", action="store_true")
	@flags.add_flag("--random", action="store_true")
	@flags.add_flag("--sort", type=str)

	# IV
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

	# Skip/Page Size
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
			"  --region <nome...>      Filtra por região de origem da espécie\n\n"

			"ESPECIAL\n"
			"  --legendary             Filtra apenas espécies lendárias\n"
			"  --mythical              Filtra apenas espécies míticas\n\n"

			"FILTRAGEM NUMÉRICA\n"
			"  --min_iv N              Seleciona apenas Pokémon com IV total >= N (valor em %)\n"
			"  --max_iv N              Seleciona apenas Pokémon com IV total <= N (valor em %)\n"
			"  --min_level N           Seleciona apenas Pokémon com level >= N\n"
			"  --max_level N           Seleciona apenas Pokémon com level <= N\n"
			"  --level <N...>          Filtra por levels exatos (aceita vários)\n\n"

			"FILTRAGEM POR IV INDIVIDUAL\n"
			"  --hpiv <N...>           IV exato de HP\n"
			"  --atkiv <N...>          IV exato de Attack\n"
			"  --defiv <N...>          IV exato de Defense\n"
			"  --spatkiv <N...>        IV exato de Special Attack\n"
			"  --spdefiv <N...>        IV exato de Special Defense\n"
			"  --spdiv <N...>          IV exato de Speed\n"
			"  --iv <N...>             IV total em % exato (ex.: 100 = perfeitos)\n\n"

			"ORDENAÇÃO\n"
			"  --sort <campo>          Define critério de ordenação: iv | level | id | name | species\n"
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
			"  .pokemon --atkiv 31 --spdiv 31\n"
			"  .pokemon --random --limit 5\n"
			"  .pokemon --page 2 --page_size 10"
		)
	)
	@requires_account()
	async def pokemon_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)

		pokemons = toolkit.get_user_pokemon(user_id)
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
	async def favorite_pokemon(self, ctx, pokemon_id: int):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		try:
			is_favorite = toolkit.toggle_favorite(user_id, pokemon_id)
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			
			emoji = "❤️" if is_favorite else "💔"
			action = "favoritado" if is_favorite else "removido dos favoritos"
			
			await ctx.send(f"{emoji} {format_pokemon_display(pokemon, bold_name=True)} foi {action}!")
			
		except ValueError:
			return

	@commands.command(name="nickname", aliases=["nick"])
	async def set_nickname(self, ctx, pokemon_id: int, *, nickname: Optional[str] = None):
		user_id = str(ctx.author.id)
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

async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))
