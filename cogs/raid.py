import random
import discord
import asyncio
from typing import Optional
from discord.ext import commands
from __main__ import pm, battle_tracker
from utils.preloaded import preloaded_backgrounds
from utils.canvas import compose_pokemon_async
from utils.formatting import format_pokemon_display
from pokemon_sdk.battle.raid import RaidBattle
from pokemon_sdk.constants import SHINY_ROLL
from helpers.checks import requires_account

class RaidJoinView(discord.ui.View):
    
    def __init__(self, author: discord.Member, boss_data: dict, message: discord.Message, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author = author
        self.boss_data = boss_data
        self.message = message
        self.participants: dict[str, dict] = {}
        self.max_participants = 4
        self.raid_started = False
        self.warning_sent = False
        self.countdown_task = None
    
    async def start_countdown(self):
        self.countdown_task = asyncio.create_task(self._countdown())
    
    async def _countdown(self):
        await asyncio.sleep(20)
        
        if not self.raid_started and self.participants and not self.warning_sent:
            self.warning_sent = True
            mentions = " ".join([f"<@{uid}>" for uid in self.participants.keys()])
            
            await self.message.channel.send(
                f"**ATENÇÃO** {mentions}\n"
                f"A raid começará em **10 SEGUNDOS**!\n"
                f"Prepare-se para a batalha!"
            )
    
    @discord.ui.button(style=discord.ButtonStyle.success, label="Participar", emoji="⚔️")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        if self.raid_started:
            return await interaction.response.send_message(
                "A raid já começou!",
                ephemeral=True
            )
        
        if len(self.participants) >= self.max_participants:
            return await interaction.response.send_message(
                "Raid cheia! (Máximo 4 jogadores)",
                ephemeral=True
            )
        
        if user_id in self.participants:
            return await interaction.response.send_message(
                "Você já está participando desta raid!",
                ephemeral=True
            )
        
        if battle_tracker.is_battling(user_id):
            return await interaction.response.send_message(
                "Você já está em uma batalha!",
                ephemeral=True
            )
        
        try:
            player_party = pm.repo.tk.get_user_party(user_id)
        except ValueError:
            player_party = None
        
        if not player_party:
            return await interaction.response.send_message(
                "Você não possui Pokémon na sua party!",
                ephemeral=True
            )
        
        await interaction.response.edit_message(
            view=PokemonSelectView(self, user_id, player_party)
        )
    
    async def add_participant(self, user_id: str, pokemon: dict, interaction: discord.Interaction):
        self.participants[user_id] = pokemon
        
        embed = interaction.message.embeds[0]
        
        participant_list = "\n".join([
            f"`{i+1}.` <@{uid}> — **{format_pokemon_display(pkmn, bold_name=True)}** `Lv{pkmn['level']}`"
            for i, (uid, pkmn) in enumerate(self.participants.items())
        ])
        
        base_description = embed.description.split("\n\n**👥")[0]
        
        embed.description = (
            f"{base_description}\n\n"
            f"**👥 Participantes ({len(self.participants)}/{self.max_participants}):**\n"
            f"{participant_list}"
        )
        
        if len(self.participants) == self.max_participants:
            embed.set_footer(text="Raid cheia! Aguarde o início...")
        else:
            embed.set_footer(text=f"{self.max_participants - len(self.participants)} vagas restantes • Clique em ⚔️ para participar")
        
        await interaction.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        if self.countdown_task and not self.countdown_task.done():
            self.countdown_task.cancel()
        
        if not self.raid_started and self.participants:
            await self._start_raid()
        elif not self.participants:
            for item in self.children:
                item.disabled = True
            
            embed = self.message.embeds[0]
            embed.color = discord.Color.dark_gray()
            embed.set_footer(text="Raid cancelada - Nenhum participante")
            
            await self.message.edit(embed=embed, view=self)
    
    async def _start_raid(self):
        if self.raid_started or not self.participants:
            return
        
        self.raid_started = True
        
        for item in self.children:
            item.disabled = True
        
        embed = self.message.embeds[0]
        embed.set_footer(text="Raid em andamento...")
        
        await self.message.edit(embed=embed, view=self)
        
        players = [(uid, pkmn) for uid, pkmn in self.participants.items()]
        
        battle = RaidBattle(self.boss_data, players, self.message)
        
        if not await battle.setup():
            return
        
        mentions = " ".join([f"<@{uid}>" for uid in self.participants.keys()])
        await self.message.channel.send(
            f"**RAID INICIADA!** {mentions}\n"
            f"A batalha contra **{format_pokemon_display(self.boss_data, bold_name=True)}** começou!"
        )
        
        await battle.start()

class PokemonSelectView(discord.ui.View):
    
    def __init__(self, parent_view: RaidJoinView, user_id: str, party: list):
        super().__init__(timeout=30.0)
        self.parent_view = parent_view
        self.user_id = user_id
        self.party = party
        
        available_pokemon = [p for p in party[:6] if p.get("current_hp", 0) > 0]
        
        if not available_pokemon:
            return
        
        for i, pokemon in enumerate(available_pokemon):
            button = discord.ui.Button(
                label=f"{format_pokemon_display(pokemon, show_poke=False, show_gender=False, show_hp=False)} Lv{pokemon['level']}",
                style=discord.ButtonStyle.primary,
                row=i // 3
            )
            button.callback = self._create_callback(pokemon)
            self.add_item(button)
        
        back_button = discord.ui.Button(
            label="Cancelar",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            row=2
        )
        back_button.callback = self._back_callback
        self.add_item(back_button)
    
    def _create_callback(self, pokemon: dict):
        async def callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.user_id:
                return await interaction.response.send_message(
                    "Esta não é sua seleção!",
                    ephemeral=True
                )
            
            await self.parent_view.add_participant(self.user_id, pokemon, interaction)
            
            await interaction.response.send_message(
                f"Você entrou na raid com **{format_pokemon_display(pokemon, bold_name=True)}**!",
                ephemeral=True
            )
            
            await interaction.message.edit(embed=interaction.message.embeds[0], view=self.parent_view)
        
        return callback
    
    async def _back_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "Esta não é sua seleção!",
                ephemeral=True
            )
        
        await interaction.response.edit_message(embed=interaction.message.embeds[0], view=self.parent_view)

class Raid(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.preloaded_backgrounds = preloaded_backgrounds
    
    @commands.command(name="raid", aliases=["rd"])
    @requires_account()
    async def raid_command(self, ctx: commands.Context, level_start: Optional[int] = 50, level_end: Optional[int] = 70) -> None:
        is_shiny = random.randint(1, SHINY_ROLL // 2) == 1
        
        raid_pool = list(range(144, 152)) + list(range(243, 252)) + [382, 383, 384]
        pokemon_id = random.choice(raid_pool)
        
        poke = await pm.service.get_pokemon(str(pokemon_id))
        species = await pm.service.get_species(poke.id)
        
        is_legendary = bool(getattr(species, "is_legendary", False))
        is_mythical = bool(getattr(species, "is_mythical", False))
        habitat_name = (
            species.habitat.name if species.habitat 
            else ("rare" if (is_legendary or is_mythical) else "grassland")
        )
        
        sprite = poke.sprites.front_shiny if is_shiny and poke.sprites.front_shiny else poke.sprites.front_default
        sprite_bytes = await sprite.read() if sprite else None
        
        level = random.randint(level_start, level_end)
        
        boss = await pm.generate_temp_pokemon(
            owner_id="raid_boss",
            species_id=poke.id,
            level=level,
            on_party=False,
            shiny=is_shiny
        )
        
        boss["base_stats"]["hp"] = int(boss["base_stats"]["hp"] * 3)
        boss["current_hp"] = boss["base_stats"]["hp"]
        
        buffer = await compose_pokemon_async(sprite_bytes, self.preloaded_backgrounds[habitat_name])
        file = discord.File(fp=buffer, filename="raid.png")
        
        title = "⚡ RAID SHINY LENDÁRIA ⚡" if is_shiny else "🔥 RAID LENDÁRIA 🔥"
        
        desc = (
            f"**{format_pokemon_display(boss, bold_name=True)}** `Lv{level}`\n"
            "\n\n"
            f"**Tempo de Entrada:** `30 segundos`\n"
            f"**Participantes:** `0/{4}`\n"
            f"**HP do Boss:** `{boss['base_stats']['hp']:,}`\n"
            f"**Recompensa:** `XP Bônus 2x`"
        )
        
        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.gold() if is_shiny else discord.Color.red()
        )
        embed.set_image(url="attachment://raid.png")
        embed.set_footer(text="⚔️ Clique no botão abaixo para participar da raid!")
        
        del poke
        del species
        
        message = await ctx.send(embed=embed, file=file)
        
        view = RaidJoinView(ctx.author, boss, message)
        await message.edit(view=view)
        
        await view.start_countdown()

async def setup(bot: commands.Bot):
    await bot.add_cog(Raid(bot))
