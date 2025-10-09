import discord
from typing import Optional
from utils.formatting import format_pokemon_display

class ConfirmTradeModal(discord.ui.Modal, title="Confirmação Final"):
    confirmation = discord.ui.TextInput(
        label="Digite CONFIRMAR para executar",
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
                "Confirmação inválida.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self.view.execute_trade()


class EmptyOfferModal(discord.ui.Modal, title="Oferta Vazia"):
    confirmation = discord.ui.TextInput(
        label="Digite SIM para confirmar sem itens",
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
        
        await interaction.response.send_message("Oferta confirmada!", ephemeral=True)
        await self.view.update_embed()


class TradeView(discord.ui.View):
    def __init__(self, trade_manager, trade_session, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.tm = trade_manager
        self.trade = trade_session
        self.message: Optional[discord.Message] = None
        self.completed = False
    
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
        if self.completed:
            return
            
        await self.tm.cancel_trade(self.trade.trade_id, "expirada")
        
        if self.message:
            from __main__ import bot
            
            try:
                initiator = await bot.fetch_user(int(self.trade.initiator_id))
                partner = await bot.fetch_user(int(self.trade.partner_id))
                
                for item in self.children:
                    item.disabled = True
                
                embed = discord.Embed(
                    title="Trade Expirada",
                    description="Tempo limite atingido.",
                    color=discord.Color.dark_gray()
                )
                
                await self.message.edit(embed=embed, view=self)
                await self.message.channel.send(
                    f"{initiator.mention} {partner.mention} A trade expirou."
                )
            except:
                pass
    
    @discord.ui.button(label="Confirmar Oferta", style=discord.ButtonStyle.green, row=0)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        offer = self.trade.get_offer(user_id)
        
        if offer.confirmed:
            if self.trade.both_confirmed():
                modal = ConfirmTradeModal(self)
                await interaction.response.send_modal(modal)
            else:
                await interaction.response.send_message(
                    "Você já confirmou! Aguardando a outra parte.",
                    ephemeral=True
                )
            return
        
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
            await interaction.response.send_message(
                "Oferta confirmada! Aguardando a outra parte.",
                ephemeral=True
            )
            await self.update_embed()
    
    @discord.ui.button(label="Cancelar Trade", style=discord.ButtonStyle.red, row=0)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        from __main__ import bot
        
        self.completed = True
        await self.tm.cancel_trade(self.trade.trade_id)
        
        initiator = await bot.fetch_user(int(self.trade.initiator_id))
        partner = await bot.fetch_user(int(self.trade.partner_id))
        
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="Trade Cancelada",
            description=f"Cancelada por {interaction.user.mention}.",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
        await self.message.channel.send(
            f"{initiator.mention} {partner.mention} A trade foi cancelada."
        )
        
        self.stop()
    
    async def execute_trade(self):
        from __main__ import bot
        
        self.completed = True
        
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
                description=f"**Motivo:** {error}",
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
            title="Trade Concluída",
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
                    pokemon_list.append(f"{format_pokemon_display(poke, show_level=True)}")
                except:
                    pokemon_list.append(f"Pokemon #{pid}")
            initiator_received.append("**Pokemon:**\n" + "\n".join(pokemon_list))
        
        if self.trade.partner_offer.items:
            items_list = []
            for item_id, qty in self.trade.partner_offer.items.items():
                item_name = await self.tm.pm.get_item_name(item_id)
                items_list.append(f"{item_name} x{qty}")
            initiator_received.append("**Itens:**\n" + "\n".join(items_list))
        
        if self.trade.partner_offer.money > 0:
            initiator_received.append(f"**Dinheiro:** {self.trade.partner_offer.money:,}")
        
        if self.trade.initiator_offer.pokemon_ids:
            pokemon_list = []
            for pid in self.trade.initiator_offer.pokemon_ids:
                try:
                    poke = self.tm.tk.get_pokemon(self.trade.partner_id, pid)
                    pokemon_list.append(f"{format_pokemon_display(poke, show_level=True)}")
                except:
                    pokemon_list.append(f"Pokemon #{pid}")
            partner_received.append("**Pokemon:**\n" + "\n".join(pokemon_list))
        
        if self.trade.initiator_offer.items:
            items_list = []
            for item_id, qty in self.trade.initiator_offer.items.items():
                item_name = await self.tm.pm.get_item_name(item_id)
                items_list.append(f"{item_name} x{qty}")
            partner_received.append("**Itens:**\n" + "\n".join(items_list))
        
        if self.trade.initiator_offer.money > 0:
            partner_received.append(f"**Dinheiro:** {self.trade.initiator_offer.money:,}")
        
        embed.add_field(
            name=f"{initiator.display_name} recebeu:",
            value="\n\n".join(initiator_received) if initiator_received else "Nada",
            inline=False
        )
        
        embed.add_field(
            name=f"{partner.display_name} recebeu:",
            value="\n\n".join(partner_received) if partner_received else "Nada",
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
        
        time_left = (self.trade.expires_at - discord.utils.utcnow()).total_seconds()
        minutes_left = max(0, int(time_left / 60))
        
        if self.trade.both_confirmed():
            color = discord.Color.gold()
            status = "Ambos confirmaram! Clique em 'Confirmar Oferta' para finalizar."
        elif self.trade.initiator_offer.confirmed or self.trade.partner_offer.confirmed:
            color = discord.Color.orange()
            status = "Aguardando confirmação..."
        else:
            color = discord.Color.blue()
            status = "Adicione itens e confirme quando pronto."
        
        embed = discord.Embed(
            title="Sistema de Trade",
            description=f"{initiator.display_name} **<->** {partner.display_name}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Comandos:",
            value=(
                "`.trade add pokemon <ID>`\n"
                "`.trade add item <nome> <qtd>`\n"
                "`.trade add money <valor>`\n"
                "`.trade remove pokemon <ID>`\n"
                "`.trade clear`"
            ),
            inline=False
        )
        
        initiator_status = "[OK]" if self.trade.initiator_offer.confirmed else "[...]"
        initiator_offer_text = await self._format_offer(self.trade.initiator_offer)
        
        embed.add_field(
            name=f"{initiator_status} {initiator.display_name}",
            value=initiator_offer_text or "Nada oferecido",
            inline=True
        )
        
        partner_status = "[OK]" if self.trade.partner_offer.confirmed else "[...]"
        partner_offer_text = await self._format_offer(self.trade.partner_offer)
        
        embed.add_field(
            name=f"{partner_status} {partner.display_name}",
            value=partner_offer_text or "Nada oferecido",
            inline=True
        )
        
        embed.add_field(
            name="Status:",
            value=status,
            inline=False
        )
        
        embed.set_footer(text=f"Expira em {minutes_left} minutos")
        
        return embed
    
    async def _format_offer(self, offer) -> str:
        parts = []
        
        if offer.pokemon_ids:
            parts.append(f"**Pokemon ({len(offer.pokemon_ids)}):**")
            for i, pid in enumerate(offer.pokemon_ids[:3], 1):
                parts.append(f"{i}. ID #{pid}")
            
            if len(offer.pokemon_ids) > 3:
                parts.append(f"...+{len(offer.pokemon_ids) - 3} mais")
        
        if offer.items:
            total = sum(offer.items.values())
            parts.append(f"\n**Itens ({total}):**")
            count = 0
            for item_id, qty in offer.items.items():
                if count >= 3:
                    parts.append(f"...+{len(offer.items) - 3} tipos")
                    break
                item_name = await self.tm.pm.get_item_name(item_id)
                parts.append(f"{item_name} x{qty}")
                count += 1
        
        if offer.money > 0:
            parts.append(f"\n**Dinheiro:**\n{offer.money:,}")
        
        return "\n".join(parts) if parts else ""
