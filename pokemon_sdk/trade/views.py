import discord
from typing import Optional
from utils.formatting import format_pokemon_display

class TradeView(discord.ui.View):
    def __init__(self, trade_manager, trade_session, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.tm = trade_manager
        self.trade = trade_session
        self.message: Optional[discord.Message] = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_id = str(interaction.user.id)
        
        if user_id not in [self.trade.initiator_id, self.trade.partner_id]:
            await interaction.response.send_message(
                "Você não faz parte desta trade!",
                ephemeral=True
            )
            return False
        
        return True
    
    async def on_timeout(self) -> None:
        await self.tm.cancel_trade(self.trade.trade_id, "expirada")
        
        if self.message:
            for item in self.children:
                item.disabled = True
            
            embed = self.message.embeds[0] if self.message.embeds else discord.Embed()
            embed.color = discord.Color.dark_gray()
            embed.title = "Trade Expirada"
            
            try:
                await self.message.edit(embed=embed, view=self)
            except:
                pass
    
    @discord.ui.button(label="Adicionar Pokémon", style=discord.ButtonStyle.primary, emoji="➕", row=0)
    async def add_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use: `.trade add pokemon <ID1> [ID2] [ID3]...`\n"
            "Exemplo: `.trade add pokemon 1 5 23`",
            ephemeral=True
        )
    
    @discord.ui.button(label="Adicionar Item", style=discord.ButtonStyle.primary, emoji="🎒", row=0)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use: `.trade add item <nome> [quantidade]`\n"
            "Exemplo: `.trade add item rare-candy 5`",
            ephemeral=True
        )
    
    @discord.ui.button(label="Adicionar Dinheiro", style=discord.ButtonStyle.primary, emoji="💰", row=0)
    async def add_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use: `.trade add money <quantidade>`\n"
            "Exemplo: `.trade add money 5000`",
            ephemeral=True
        )
    
    @discord.ui.button(label="Limpar Oferta", style=discord.ButtonStyle.secondary, emoji="🗑️", row=1)
    async def clear_offer(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        offer = self.trade.get_offer(user_id)
        
        offer.pokemon_ids.clear()
        offer.items.clear()
        offer.money = 0
        offer.confirmed = False
        
        self.trade.reset_confirmations()
        
        await interaction.response.send_message("Sua oferta foi limpa!", ephemeral=True)
        await self.update_embed()
    
    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, emoji="✅", row=2)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        success, error = await self.tm.confirm_offer(self.trade.trade_id, user_id)
        
        if not success:
            return await interaction.response.send_message(f"{error}", ephemeral=True)
        
        if self.trade.both_confirmed():
            await interaction.response.defer()
            await self.execute_trade()
        else:
            await interaction.response.send_message("Você confirmou sua oferta!", ephemeral=True)
            await self.update_embed()
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.tm.cancel_trade(self.trade.trade_id)
        
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Trade Cancelada",
            description=f"Trade cancelada por {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
    
    async def execute_trade(self):
        success, error = await self.tm.execute_trade(self.trade.trade_id)
        
        for item in self.children:
            item.disabled = True
        
        if success:
            embed = await self._create_success_embed()
        else:
            embed = discord.Embed(
                title="Erro na Trade",
                description=f"**Erro:** {error}",
                color=discord.Color.red()
            )
        
        await self.message.edit(embed=embed, view=self)
        self.stop()
    
    async def _create_success_embed(self) -> discord.Embed:
        from __main__ import bot
        
        initiator = await bot.fetch_user(int(self.trade.initiator_id))
        partner = await bot.fetch_user(int(self.trade.partner_id))
        
        embed = discord.Embed(
            title="Trade Completada!",
            description="A trade foi realizada com sucesso!",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        initiator_received = []
        partner_received = []
        
        if self.trade.partner_offer.pokemon_ids:
            pokemon_list = []
            for pid in self.trade.partner_offer.pokemon_ids:
                try:
                    poke = self.tm.tk.get_pokemon(self.trade.initiator_id, pid)
                    pokemon_list.append(f"• {format_pokemon_display(poke, show_level=True)}")
                except:
                    pokemon_list.append(f"• Pokémon #{pid}")
            
