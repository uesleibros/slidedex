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
    
    @discord.ui.button(label="Como Adicionar Pokémon", style=discord.ButtonStyle.primary, row=0)
    async def add_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use: `!trade add pokemon <ID1> [ID2] [ID3]...`\n"
            "Exemplo: `!trade add pokemon 1 5 23`",
            ephemeral=True
        )
    
    @discord.ui.button(label="Como Adicionar Item", style=discord.ButtonStyle.primary, row=0)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use: `!trade add item <nome> [quantidade]`\n"
            "Exemplo: `!trade add item rare-candy 5`",
            ephemeral=True
        )
    
    @discord.ui.button(label="Como Adicionar Dinheiro", style=discord.ButtonStyle.primary, row=0)
    async def add_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use: `!trade add money <quantidade>`\n"
            "Exemplo: `!trade add money 5000`",
            ephemeral=True
        )
    
    @discord.ui.button(label="Limpar Oferta", style=discord.ButtonStyle.secondary, row=1)
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
    
    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, row=2)
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
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, row=2)
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
        success, error = await self.tm.execute_trade(self.trade.trade_id, self.message.channel)
        
        for item in self.children:
            item.disabled = True
        
        if success:
            embed = await self._create_success_embed()
            await self.message.edit(embed=embed, view=self)
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
            initiator_received.append(f"**Pokémon:**\n" + "\n".join(pokemon_list))
        
        if self.trade.initiator_offer.pokemon_ids:
            pokemon_list = []
            for pid in self.trade.initiator_offer.pokemon_ids:
                try:
                    poke = self.tm.tk.get_pokemon(self.trade.partner_id, pid)
                    pokemon_list.append(f"• {format_pokemon_display(poke, show_level=True)}")
                except:
                    pokemon_list.append(f"• Pokémon #{pid}")
            partner_received.append(f"**Pokémon:**\n" + "\n".join(pokemon_list))
        
        if self.trade.partner_offer.items:
            items_list = []
            for item_id, qty in self.trade.partner_offer.items.items():
                item_name = await self.tm.pm.get_item_name(item_id)
                items_list.append(f"• {item_name} x{qty}")
            initiator_received.append(f"**Itens:**\n" + "\n".join(items_list))
        
        if self.trade.initiator_offer.items:
            items_list = []
            for item_id, qty in self.trade.initiator_offer.items.items():
                item_name = await self.tm.pm.get_item_name(item_id)
                items_list.append(f"• {item_name} x{qty}")
            partner_received.append(f"**Itens:**\n" + "\n".join(items_list))
        
        if self.trade.partner_offer.money > 0:
            initiator_received.append(f"**Dinheiro:** {self.trade.partner_offer.money:,}")
        
        if self.trade.initiator_offer.money > 0:
            partner_received.append(f"**Dinheiro:** {self.trade.initiator_offer.money:,}")
        
        if initiator_received:
            embed.add_field(
                name=f"{initiator.display_name} recebeu:",
                value="\n\n".join(initiator_received),
                inline=False
            )
        
        if partner_received:
            embed.add_field(
                name=f"{partner.display_name} recebeu:",
                value="\n\n".join(partner_received),
                inline=False
            )
        
        return embed
    
    async def update_embed(self):
        if not self.message:
            return
        
        embed = await self._create_trade_embed()
        
        try:
            await self.message.edit(embed=embed, view=self)
        except:
            pass
    
    async def _create_trade_embed(self) -> discord.Embed:
        from __main__ import bot
        
        initiator = await bot.fetch_user(int(self.trade.initiator_id))
        partner = await bot.fetch_user(int(self.trade.partner_id))
        
        embed = discord.Embed(
            title="Trade em Andamento",
            description=(
                f"**{initiator.display_name}** <-> **{partner.display_name}**\n\n"
                f"Use os botões abaixo ou comandos para adicionar itens à trade."
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        initiator_offer_text = await self._format_offer(self.trade.initiator_offer)
        embed.add_field(
            name=f"{'[OK]' if self.trade.initiator_offer.confirmed else '[...]'} {initiator.display_name}",
            value=initiator_offer_text or "*Nada oferecido*",
            inline=True
        )
        
        partner_offer_text = await self._format_offer(self.trade.partner_offer)
        embed.add_field(
            name=f"{'[OK]' if self.trade.partner_offer.confirmed else '[...]'} {partner.display_name}",
            value=partner_offer_text or "*Nada oferecido*",
            inline=True
        )
        
        status_text = ""
        if self.trade.both_confirmed():
            status_text = "**Ambos confirmaram! Processando...**"
        elif self.trade.initiator_offer.confirmed:
            status_text = f"Aguardando {partner.mention} confirmar"
        elif self.trade.partner_offer.confirmed:
            status_text = f"Aguardando {initiator.mention} confirmar"
        else:
            status_text = "Aguardando confirmações"
        
        embed.add_field(
            name="Status",
            value=status_text,
            inline=False
        )
        
        time_left = (self.trade.expires_at - discord.utils.utcnow()).total_seconds()
        minutes_left = int(time_left / 60)
        
        embed.set_footer(text=f"Trade expira em {minutes_left} minutos | ID: {self.trade.trade_id}")
        
        return embed
    
    async def _format_offer(self, offer) -> str:
        parts = []
        
        if offer.pokemon_ids:
            parts.append(f"**Pokémon ({len(offer.pokemon_ids)}):**")
            for pid in offer.pokemon_ids[:5]:
                parts.append(f"• ID #{pid}")
            
            if len(offer.pokemon_ids) > 5:
                parts.append(f"*...e mais {len(offer.pokemon_ids) - 5}*")
        
        if offer.items:
            parts.append(f"\n**Itens ({len(offer.items)}):**")
            for item_id, qty in list(offer.items.items())[:5]:
                item_name = await self.tm.pm.get_item_name(item_id)
                parts.append(f"• {item_name} x{qty}")
            
            if len(offer.items) > 5:
                parts.append(f"*...e mais {len(offer.items) - 5}*")
        
        if offer.money > 0:
            parts.append(f"\n**Dinheiro:**\n{offer.money:,}")
        
        return "\n".join(parts) if parts else ""
