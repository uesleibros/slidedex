import discord
from discord.ext import commands
from typing import Dict
from collections import defaultdict
from __main__ import pm
from utils.pokemon_emojis import get_app_emoji
from helpers.checks import requires_account
from helpers.paginator import Paginator

class Pokedex(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="pokedex", aliases=["dex", "pd"])
    @requires_account()
    async def pokedex(self, ctx: commands.Context, user: discord.Member = None):
        user = user or ctx.author
        user_id = str(user.id)

        all_pokemon = pm.tk.get_user_pokemon(user_id)

        captured_species: Dict[int, Dict] = defaultdict(lambda: {"count": 0, "shiny_count": 0})
        for poke in all_pokemon:
            sid = poke["species_id"]
            captured_species[sid]["count"] += 1
            if poke.get("is_shiny", False):
                captured_species[sid]["shiny_count"] += 1

        total_species = 386
        captured_count = len(captured_species)
        total_pokemon = len(all_pokemon)
        total_shinies = sum(v["shiny_count"] for v in captured_species.values())

        # pega todas as espécies de uma vez
        all_species = pm.service.get_all_species(1, total_species)
        species_map = {s.id: s for s in all_species}

        pokedex_entries = []
        for sid in range(1, total_species + 1):
            pokedex_entries.append({
                "species_id": sid,
                "captured": sid in captured_species,
                "count": captured_species.get(sid, {}).get("count", 0),
                "shiny_count": captured_species.get(sid, {}).get("shiny_count", 0)
            })

        title_user = "Sua Pokédex" if user_id == str(ctx.author.id) else f"Pokédex de {user.display_name}"

        async def generate_pokedex_embed(items, start, end, total, page):
            embed = discord.Embed(
                title=title_user,
                description=f"Capturados: {captured_count}/{total_species} ({(captured_count / total_species * 100):.1f}%)\n"
                            f"Shinies: {total_shinies}",
                color=discord.Color.pink()
            )

            for entry in items:
                sid = entry["species_id"]
                species = species_map.get(sid)
                emoji = get_app_emoji(f"p_{sid}")
                name = species.name.title() if species else f"Pokémon #{sid}"

                field_name = f"{emoji} {name} #{sid}"

                if entry["captured"]:
                    shiny_text = f" | ✨ {entry['shiny_count']}x" if entry["shiny_count"] > 0 else ""
                    field_value = f":white_check_mark: Capturado: {entry['count']}x{shiny_text}"
                else:
                    field_value = ":x: Não capturado ainda!"

                embed.add_field(name=field_name, value=field_value, inline=True)

            embed.set_footer(text=f"Mostrando {start + 1}–{end} de {total_species}")
            return embed

        view = Paginator(
            items=pokedex_entries,
            user_id=ctx.author.id,
            embed_generator=generate_pokedex_embed,
            page_size=20,
            current_page=0
        )

        embed = await view.get_embed()
        await ctx.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Pokedex(bot))