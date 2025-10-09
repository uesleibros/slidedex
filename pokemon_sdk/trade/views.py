import discord
from typing import Optional
from utils.formatting import format_pokemon_display

class ConfirmTradeModal(discord.ui.Modal, title="Confirmação Final"):
    confirmation = discord.ui.TextInput(
        label="Digite CONFIRMAR para prosseguir",
        placeholder="CONFIRMAR",
        required=True,
        max_length=10
    )
    
    def __init__(self, view):
        super().__init__()
        self.view = view
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.upper() != "CONFIRMAR":
            await interaction.response.send_message(
                "Confirmação inválida. A trade não foi executada.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self.view.execute_trade()


class EmptyOfferModal(discord.ui.Modal, title="Oferta Vazia"):
    confirmation = discord.ui.TextInput(
        label="Digite SIM para confirmar oferta vazia",
        placeholder="SIM",
        required=True,
        max_length=3
    )
    
    def __init__(self, view, user_id):
        super().__init__()
        self.view = view
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.upper() != "SIM":
            await interaction.response.send_message(
                "Confirmação cancelada.",
                ephemeral=True
            )
            return
        
        success, error = await self.view.tm.confirm_offer(self.view.trade.trade_id, self.user_id)
        
        if not success:
            return await interaction.response.send_message(f"{error}", ephemeral=True)
        
        if self.view.trade.both_confirmed():
            modal = ConfirmTradeModal(self.view)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("Oferta confirmada!", ephemeral=True)
            await self.view.update_embed()


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
            from __main__ import bot
            
            initiator = await bot.fetch_user(int(self.trade.initiator_id))
            partner = await bot.fetch_user(int(self.trade.partner_id))
            
            for item in self.children:
                item.disabled = True
            
            embed = discord.Embed(
                title="Trade Expirada",
                description="O tempo limite foi atingido.",
                color=discord.Color.dark_gray()
            )
            
            try:
                await self.message.edit(embed=embed, view=self)
                await self.message.channel.send(
                    f"{initiator.mention} {partner.mention} A trade expirou por inatividade."
                )
            except:
                pass
    
    @discord.ui.button(label="Confirmar Oferta", style=discord.ButtonStyle.green, row=0)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        offer = self.trade.get_offer(user_id)
        
        is_empty = (
            len(offer.pokemon_ids) == 0 and
            len(offer.items) == 0 and
            offer.money == 0
        )
        
        if is_empty:
            modal = EmptyOfferModal(self, user_id)
            await interaction.response.send_modal(modal)
            return
        
        success, error = await self.tm.confirm_offer(self.trade.trade_id, user_id)
        
        if not success:
            return await interaction.response.send_message(f"{error}", ephemeral=True)
        
        if self.trade.both_confirmed():
            modal = ConfirmTradeModal(self)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("Oferta confirmada! Aguardando a outra parte.", ephemeral=True)
            await self.update_embed()
    
    @discord.ui.button(label="Cancelar Trade", style=discord.ButtonStyle.red, row=0)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        from __main__ import bot
        
        await self.tm.cancel_trade(self.trade.trade_id)
        
        initiator = await bot.fetch_user(int(self.trade.initiator_id))
        partner = await bot.fetch_user(int(self.trade.partner_id))
        
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Trade Cancelada",
            description=f"Cancelada por {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        await self.message.channel.send(
            f"{initiator.mention} {partner.mention} A trade foi cancelada."
        )
        
        self.stop()
    
    async def execute_trade(self):
        from __main__ import bot
        
        success, error = await self.tm.execute_trade(self.trade.trade_id, self.message.channel)
        
        initiator = await bot.fetch_user(int(self.trade.initiator_id))
        partner = await bot.fetch_user(int(self.trade.partner_id))
        
        for item in self.children:
            item.disabled = True
        
        if success:
            embed = await self._create_success_embed()
            await self.message.edit(embed=embed, view=self)
            
            await self.message.channel.send(
                f"{initiator.mention} {partner.mention} Trade realizada com sucesso!"
            )
        else:
            embed = discord.Embed(
                title="Erro na Trade",
                description=f"{error}",
                color=discord.Color.red()
            )
            await self.message.edit(embed=embed, view=self)
            
            await self.message.channel.send(
                f"{initiator.mention} {partner.mention} A trade falhou: {error}"
            )
        
        self.stop()
    
    async def _create_success_embed(self) -> discord.Embed:
        from __main__ import bot
        
        initiator = await bot.fetch_user(int(self.trade.initiator_id))
        partner = await bot.fetch_user(int(self.trade.partner_id))
        
        embed = discord.Embed(
            title="Trade Completada",
            description="A troca foi realizada com sucesso.",
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
                    pokemon_list.append(f"• Pokemon #{pid}")
            initiator_received.append(f"**Pokemon:**\n" + "\n".join(pokemon_list))
        
        if self.trade.initiator_offer.pokemon_ids:
            pokemon_list = []
            for pid in self.trade.initiator_offer.pokemon_ids:
                try:
                    poke = self.tm.tk.get_pokemon(self.trade.partner_id, pid)
                    pokemon_list.append(f"• {format_pokemon_display(poke, show_level=True)}")
                except:
                    pokemon_list.append(f"• Pokemon #{pid}")
            partner_received.append(f"**Pokemon:**\n" + "\n".join(pokemon_list))
        
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
        else:
            embed.add_field(
                name=f"{initiator.display_name} recebeu:",
                value="Nada",
                inline=False
            )
        
        if partner_received:
            embed.add_field(
                name=f"{partner.display_name} recebeu:",
                value="\n\n".join(partner_received),
                inline=False
            )
        else:
            embed.add_field(
                name=f"{partner.display_name} recebeu:",
                value="Nada",
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
                f"{initiator.display_name} **<->** {partner.display_name}\n\n"
                f"**Comandos:**\n"
                f"`.trade add pokemon <ID>` - Adicionar Pokemon\n"
                f"`.trade add item <nome> <quantidade>` - Adicionar Item\n"
                f"`.trade add money <valor>` - Adicionar Dinheiro\n"
                f"`.trade remove pokemon <ID>` - Remover Pokemon\n"
                f"`.trade clear` - Limpar sua oferta"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        initiator_offer_text = await self._format_offer(self.trade.initiator_offer)
        status_icon_init = "[OK]" if self.trade.initiator_offer.confirmed else "[...]"
        
        embed.add_field(
            name=f"{status_icon_init} {initiator.display_name}",
            value=initiator_offer_text or "Nada oferecido",
            inline=True
        )
        
        partner_offer_text = await self._format_offer(self.trade.partner_offer)
        status_icon_part = "[OK]" if self.trade.partner_offer.confirmed else "[...]"
        
        embed.add_field(
            name=f"{status_icon_part} {partner.display_name}",
            value=partner_offer_text or "Nada oferecido",
            inline=True
        )
        
        time_left = (self.trade.expires_at - discord.utils.utcnow()).total_seconds()
        minutes_left = int(time_left / 60)
        
        embed.set_footer(text=f"Expira em {minutes_left} minutos")
        
        return embed
    
    async def _format_offer(self, offer) -> str:
        parts = []
        
        if offer.pokemon_ids:
            parts.append(f"**Pokemon ({len(offer.pokemon_ids)}):**")
            for pid in offer.pokemon_ids[:5]:
                parts.append(f"ID #{pid}")
            
            if len(offer.pokemon_ids) > 5:
                parts.append(f"...e mais {len(offer.pokemon_ids) - 5}")
        
        if offer.items:
            parts.append(f"**Itens ({len(offer.items)}):**")
            for item_id, qty in list(offer.items.items())[:3]:
                item_name = await self.tm.pm.get_item_name(item_id)
                parts.append(f"{item_name} x{qty}")
            
            if len(offer.items) > 3:
                parts.append(f"...e mais {len(offer.items) - 3}")
        
        if offer.money > 0:
            parts.append(f"**Dinheiro:** {offer.money:,}")
        
        return "\n".join(parts) if parts else ""
