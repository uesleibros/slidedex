import discord
from typing import Optional
from utils.formatting import format_pokemon_display

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
                    description="Tempo limite de 10 minutos atingido.",
                    color=discord.Color.dark_gray()
                )
                
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
        
        if offer.confirmed:
            await interaction.response.send_message(
                "Você já confirmou sua oferta! Aguardando a outra parte confirmar.",
                ephemeral=True
            )
            return
        
        is_empty = (
            len(offer.pokemon_ids) == 0 and
            len(offer.items) == 0 and
            offer.money == 0
        )
        
        if is_empty:
            await interaction.response.send_message(
                "Você não adicionou nada à sua oferta. Tem certeza que quer confirmar uma oferta vazia? Use o botão novamente para confirmar.",
                ephemeral=True
            )
            
            success, error = await self.tm.confirm_offer(self.trade.trade_id, user_id)
            
            if not success:
                return await interaction.followup.send(f"{error}", ephemeral=True)
            
            await self.update_embed()
            return
        
        success, error = await self.tm.confirm_offer(self.trade.trade_id, user_id)
        
        if not success:
            return await interaction.response.send_message(f"{error}", ephemeral=True)
        
        await interaction.response.send_message(
            "Oferta confirmada com sucesso!",
            ephemeral=True
        )
        
        await self.update_embed()
    
    @discord.ui.button(label="Executar Trade", style=discord.ButtonStyle.blurple, row=0, disabled=True)
    async def execute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.trade.both_confirmed():
            await interaction.response.send_message(
                "Ambas as partes precisam confirmar antes de executar a trade!",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            "Executando a trade...",
            ephemeral=True
        )
        
        await self.execute_trade()
    
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
            description=f"A trade foi cancelada por {interaction.user.mention}.",
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
                description=f"A trade não pôde ser concluída.\n\n**Motivo:** {error}",
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
            title="Trade Concluída com Sucesso",
            description="Os itens foram trocados entre os jogadores.",
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
                    pokemon_list.append(f"• Pokemon ID #{pid}")
            initiator_received.append("**Pokemon recebidos:**\n" + "\n".join(pokemon_list))
        
        if self.trade.partner_offer.items:
            items_list = []
            for item_id, qty in self.trade.partner_offer.items.items():
                item_name = await self.tm.pm.get_item_name(item_id)
                items_list.append(f"• {item_name} x{qty}")
            initiator_received.append("**Itens recebidos:**\n" + "\n".join(items_list))
        
        if self.trade.partner_offer.money > 0:
            initiator_received.append(f"**Dinheiro recebido:**\n{self.trade.partner_offer.money:,}")
        
        if self.trade.initiator_offer.pokemon_ids:
            pokemon_list = []
            for pid in self.trade.initiator_offer.pokemon_ids:
                try:
                    poke = self.tm.tk.get_pokemon(self.trade.partner_id, pid)
                    pokemon_list.append(f"• {format_pokemon_display(poke, show_level=True)}")
                except:
                    pokemon_list.append(f"• Pokemon ID #{pid}")
            partner_received.append("**Pokemon recebidos:**\n" + "\n".join(pokemon_list))
        
        if self.trade.initiator_offer.items:
            items_list = []
            for item_id, qty in self.trade.initiator_offer.items.items():
                item_name = await self.tm.pm.get_item_name(item_id)
                items_list.append(f"• {item_name} x{qty}")
            partner_received.append("**Itens recebidos:**\n" + "\n".join(items_list))
        
        if self.trade.initiator_offer.money > 0:
            partner_received.append(f"**Dinheiro recebido:**\n{self.trade.initiator_offer.money:,}")
        
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
        
        embed.set_footer(text="Trade concluída")
        
        return embed
    
    async def update_embed(self):
        if not self.message:
            return
        
        embed = await self._create_trade_embed()
        
        for item in self.children:
            if hasattr(item, 'custom_id') or item.label == "Executar Trade":
                if self.trade.both_confirmed():
                    item.disabled = False
                    item.style = discord.ButtonStyle.green
                else:
                    item.disabled = True
                    item.style = discord.ButtonStyle.blurple
        
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
        seconds_left = max(0, int(time_left % 60))
        
        if self.trade.both_confirmed():
            color = discord.Color.green()
            status = "Pronto para executar! Clique no botão 'Executar Trade' para finalizar."
        elif self.trade.initiator_offer.confirmed or self.trade.partner_offer.confirmed:
            color = discord.Color.orange()
            if self.trade.initiator_offer.confirmed:
                status = f"Aguardando {partner.mention} confirmar a oferta."
            else:
                status = f"Aguardando {initiator.mention} confirmar a oferta."
        else:
            color = discord.Color.blue()
            status = "Adicione itens usando os comandos abaixo e clique em 'Confirmar Oferta'."
        
        embed = discord.Embed(
            title="Sistema de Trocas",
            description=f"**{initiator.display_name}** está trocando com **{partner.display_name}**",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Como adicionar itens:",
            value=(
                "**Pokemon:**\n"
                "`.trade add pokemon <ID>` - Adiciona um Pokemon\n"
                "`.trade add pokemon <ID1> <ID2> <ID3>` - Adiciona vários\n\n"
                "**Itens:**\n"
                "`.trade add item <nome> <quantidade>` - Adiciona itens\n\n"
                "**Dinheiro:**\n"
                "`.trade add money <valor>` - Adiciona dinheiro\n\n"
                "**Remover:**\n"
                "`.trade remove pokemon <ID>` - Remove um Pokemon\n"
                "`.trade clear` - Limpa toda sua oferta"
            ),
            inline=False
        )
        
        initiator_status = "CONFIRMADO" if self.trade.initiator_offer.confirmed else "AGUARDANDO"
        initiator_offer_text = await self._format_offer(self.trade.initiator_offer)
        
        embed.add_field(
            name=f"Oferta de {initiator.display_name} - [{initiator_status}]",
            value=initiator_offer_text or "*Nenhum item adicionado*",
            inline=True
        )
        
        partner_status = "CONFIRMADO" if self.trade.partner_offer.confirmed else "AGUARDANDO"
        partner_offer_text = await self._format_offer(self.trade.partner_offer)
        
        embed.add_field(
            name=f"Oferta de {partner.display_name} - [{partner_status}]",
            value=partner_offer_text or "*Nenhum item adicionado*",
            inline=True
        )
        
        embed.add_field(
            name="Status da Trade:",
            value=status,
            inline=False
        )
        
        embed.set_footer(text=f"Tempo restante: {minutes_left}m {seconds_left}s")
        
        return embed
    
    async def _format_offer(self, offer) -> str:
        parts = []
        
        if offer.pokemon_ids:
            parts.append(f"**Pokemon:** {len(offer.pokemon_ids)} no total")
            for i, pid in enumerate(offer.pokemon_ids[:5], 1):
                parts.append(f"  {i}. ID #{pid}")
            
            if len(offer.pokemon_ids) > 5:
                parts.append(f"  ... e mais {len(offer.pokemon_ids) - 5} Pokemon")
        
        if offer.items:
            total_items = sum(offer.items.values())
            parts.append(f"\n**Itens:** {total_items} unidades no total")
            count = 0
            for item_id, qty in offer.items.items():
                if count >= 5:
                    remaining = len(offer.items) - 5
                    parts.append(f"  ... e mais {remaining} tipos de item")
                    break
                item_name = await self.tm.pm.get_item_name(item_id)
                parts.append(f"  • {item_name} x{qty}")
                count += 1
        
        if offer.money > 0:
            parts.append(f"\n**Dinheiro:** {offer.money:,}")
        
        return "\n".join(parts) if parts else ""
