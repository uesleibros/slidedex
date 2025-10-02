import discord
import random
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from __main__ import pm, battle_tracker
from utils.canvas import compose_battle_async
from utils.preloaded import preloaded_textures
from utils.formatting import format_pokemon_display
from .pokemon import BattlePokemon
from .messages import BattleMessages
from .status import StatusHandler
from .helpers import MoveData, _hp_bar, _slug
from .engine import BattleEngine

class RaidBattle(BattleEngine):
    
    def __init__(
        self,
        boss_raw: Dict[str, Any],
        players: List[Tuple[str, Dict[str, Any]]],
        interaction: discord.Interaction
    ) -> None:
        super().__init__(battle_type="raid")
        
        self.boss_raw = boss_raw
        self.players_raw = players
        self.interaction = interaction
        self.message: Optional[discord.Message] = None
        self.boss: Optional[BattlePokemon] = None
        self.players: List[Tuple[str, BattlePokemon]] = []
        self.actions_view: Optional[RaidBattleView] = None
        self.player_actions: Dict[str, Optional[str]] = {}
        self.rewards_distributed = False
    
    async def setup(self) -> bool:
        b_api, b_spec = await asyncio.gather(
            pm.service.get_pokemon(self.boss_raw["species_id"]),
            pm.service.get_species(self.boss_raw["species_id"])
        )
        self.boss = BattlePokemon(self.boss_raw, b_api, b_spec)
        
        for user_id, pokemon_raw in self.players_raw:
            p_api, p_spec = await asyncio.gather(
                pm.service.get_pokemon(pokemon_raw["species_id"]),
                pm.service.get_species(pokemon_raw["species_id"])
            )
            player_pokemon = BattlePokemon(pokemon_raw, p_api, p_spec)
            self.players.append((user_id, player_pokemon))
            self.player_actions[user_id] = None
        
        self.battle_context.team1 = [p for _, p in self.players]
        self.battle_context.team2 = [self.boss]
        
        await self._preload_move_data()
        return True
    
    async def _preload_move_data(self) -> None:
        move_ids: Set[str] = set()
        for mv in self.boss.moves:
            move_ids.add(_slug(mv["id"]))
        for _, pokemon in self.players:
            for mv in pokemon.moves:
                move_ids.add(_slug(mv["id"]))
        
        if move_ids:
            await asyncio.gather(*[self._fetch_move(mid) for mid in move_ids if mid])
    
    async def _compose_image(self) -> discord.File:
        player_sprites = []
        for _, pokemon in self.players[:2]:
            if pokemon.sprites["back"]:
                sprite_bytes = await pokemon.sprites["back"].read()
                player_sprites.append(sprite_bytes)
        
        boss_sprite = await self.boss.sprites["front"].read() if self.boss.sprites["front"] else None
        
        buf = await compose_battle_async(
            player_sprites[0] if player_sprites else None,
            boss_sprite,
            preloaded_textures["battle"]
        )
        return discord.File(buf, filename="raid.png")
    
    def _build_embed(self) -> discord.Embed:
        boss_bar = _hp_bar(self.boss.current_hp, self.boss.stats["hp"])
        boss_hp_percent = (self.boss.current_hp / self.boss.stats["hp"] * 100) if self.boss.stats["hp"] > 0 else 0
        
        description = [
            f"**🔥 RAID BOSS 🔥**",
            f"{format_pokemon_display(self.boss.raw, bold_name=True)} {self.boss.status_tag()} Lv{self.boss.level}",
            f"{boss_bar} {max(0, self.boss.current_hp):,}/{self.boss.stats['hp']:,} ({boss_hp_percent:.1f}%)",
            "",
            "**👥 PARTICIPANTES:**"
        ]
        
        for user_id, pokemon in self.players:
            user_mention = f"<@{user_id}>"
            
            if pokemon.fainted:
                prefix = "💀"
                hp_info = "`DESMAIADO`"
            else:
                prefix = "🔵"
                hp_bar = _hp_bar(pokemon.current_hp, pokemon.stats["hp"])
                hp_percent = (pokemon.current_hp / pokemon.stats["hp"] * 100)
                hp_info = f"{hp_bar} `{pokemon.current_hp}/{pokemon.stats['hp']}` ({hp_percent:.0f}%)"
            
            action_status = ""
            if pokemon.fainted:
                action_status = ""
            elif self.player_actions.get(user_id):
                action_status = " ✅"
            else:
                action_status = " ⏳"
            
            description.append(
                f"{prefix} {user_mention}: **{pokemon.display_name}**{action_status}"
            )
            description.append(f"   {hp_info}")
        
        description.append("")
        
        if self.lines:
            description.extend(self.lines[-15:])
        
        embed = discord.Embed(
            title=f"⚔️ Raid Battle - Turno {self.turn}",
            description="\n".join(description),
            color=discord.Color.red()
        )
        
        embed.set_footer(text="Effex Engine v2.0 — Raid System")
        embed.set_image(url="attachment://raid.png")
        return embed
    
    async def start(self) -> None:
        self.actions_view = RaidBattleView(self)
        self.lines = [
            f"🔥 A raid contra {self.boss.display_name} começou!",
            f"💪 {len(self.players)} jogadores participando!",
            "",
            "⚔️ Escolha sua ação!"
        ]
        
        for user_id in [uid for uid, _ in self.players]:
            battle_tracker.add(user_id)
        
        self.message = await self.interaction.channel.send(
            embed=self._build_embed(),
            file=await self._compose_image(),
            view=self.actions_view
        )
        self.must_redraw_image = False
        
        mentions = " ".join([f"<@{uid}>" for uid, _ in self.players])
        await self.interaction.channel.send(
            f"⚔️ **RAID INICIADA!** {mentions}\n"
            f"É seu turno! Clique em **⚔️ Escolher Ação** para atacar!"
        )
    
    async def refresh(self) -> None:
        if not self.message:
            return
        
        embed = self._build_embed()
        
        if self.must_redraw_image:
            file = await self._compose_image()
            await self.message.edit(attachments=[file], embed=embed, view=self.actions_view)
            self.must_redraw_image = False
        else:
            await self.message.edit(embed=embed, view=self.actions_view)
    
    def _select_boss_move(self) -> str:
        available_moves = []
        
        for m in self.boss.moves:
            move_id = str(m["id"])
            pp = int(m.get("pp", 0))
            
            if pp <= 0:
                continue
            
            if self.boss.is_move_disabled(move_id):
                continue
            
            available_moves.append(m)
        
        if not available_moves:
            return "__struggle__"
        
        return str(random.choice(available_moves)["id"])
    
    def _all_actions_ready(self) -> bool:
        for uid, pokemon in self.players:
            if pokemon.fainted:
                continue
            
            if not self.player_actions.get(uid):
                return False
        
        return True
    
    async def _notify_action_progress(self) -> None:
        alive_players = [(uid, p) for uid, p in self.players if not p.fainted]
        
        if not alive_players:
            return
        
        waiting_for = [
            uid for uid, pokemon in alive_players 
            if not self.player_actions.get(uid)
        ]
        
        if len(waiting_for) == 0:
            return
        
        if len(waiting_for) == 1:
            await self.message.channel.send(
                f"⏰ <@{waiting_for[0]}>\n"
                f"**Todos estão aguardando você!** ⚔️"
            )
        elif len(waiting_for) < len(alive_players):
            ready_count = len(alive_players) - len(waiting_for)
            total_count = len(alive_players)
            
            progress_bar = "▰" * ready_count + "▱" * len(waiting_for)
            
            await self.message.channel.send(
                f"⏳ **Progresso:** {progress_bar} `{ready_count}/{total_count}` jogadores prontos!"
            )
    
    async def process_turn(self) -> None:
        async with self.lock:
            if self.ended:
                return
            
            self.lines = []
            
            for _, pokemon in self.players:
                pokemon.clear_turn_volatiles()
            self.boss.clear_turn_volatiles()
            
            boss_move_id = self._select_boss_move()
            
            if boss_move_id != "__struggle__":
                boss_move_data = await self._fetch_move(boss_move_id)
            else:
                boss_move_data = MoveData(
                    "Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, []
                )
            
            turn_queue = []
            
            for user_id, pokemon in self.players:
                if pokemon.fainted:
                    continue
                
                move_id = self.player_actions.get(user_id)
                if not move_id:
                    continue
                
                move_data = await self._fetch_move(move_id)
                priority = self._get_move_priority(move_data, pokemon)
                speed = pokemon.eff_stat("speed")
                
                turn_queue.append((priority, speed, "player", user_id, pokemon, move_id, move_data))
            
            boss_priority = self._get_move_priority(boss_move_data, self.boss)
            boss_speed = self.boss.eff_stat("speed")
            turn_queue.append((boss_priority, boss_speed, "boss", None, self.boss, boss_move_id, boss_move_data))
            
            turn_queue.sort(key=lambda x: (x[0], x[1]), reverse=True)
            
            for priority, speed, actor_type, user_id, pokemon, move_id, move_data in turn_queue:
                if pokemon.fainted:
                    continue
                
                if actor_type == "player":
                    alive_opponents = [p for p in [self.boss] if not p.fainted]
                    if not alive_opponents:
                        break
                    
                    target = alive_opponents[0]
                    
                    user_mention = f"<@{user_id}>"
                    self.lines.append(f"🔵 {user_mention}")
                    
                    result = await self._execute_turn_action(
                        True, move_id, move_data, pokemon, target
                    )
                    self.lines.extend(result)
                    
                    if self.boss.fainted:
                        await self._handle_victory()
                        await self.refresh()
                        return
                    
                    self.lines.append("")
                
                else:
                    alive_players = [(uid, p) for uid, p in self.players if not p.fainted]
                    if not alive_players:
                        break
                    
                    effect_data = self._get_effect_data(move_id)
                    is_multi_target = self._is_boss_multi_target(move_data, effect_data)
                    
                    self.lines.append(f"🔴 BOSS")
                    
                    if is_multi_target:
                        for target_uid, target_pokemon in alive_players:
                            if target_pokemon.fainted:
                                continue
                            
                            result = await self._execute_turn_action(
                                False, move_id, move_data, self.boss, target_pokemon
                            )
                            
                            target_mention = f"<@{target_uid}>"
                            self.lines.append(f"→ Alvo: {target_mention}")
                            self.lines.extend([f"  {line}" for line in result])
                    else:
                        target_uid, target_pokemon = random.choice(alive_players)
                        target_mention = f"<@{target_uid}>"
                        
                        result = await self._execute_turn_action(
                            False, move_id, move_data, self.boss, target_pokemon
                        )
                        
                        self.lines.append(f"→ Alvo: {target_mention}")
                        self.lines.extend(result)
                    
                    self.lines.append("")
            
            all_participants = [p for _, p in self.players] + [self.boss]
            
            for player_pokemon in [p for _, p in self.players]:
                player_effects = StatusHandler.end_of_turn_effects(player_pokemon, self.boss)
                if player_effects:
                    self.lines.extend(player_effects)
            
            boss_effects = StatusHandler.end_of_turn_effects(self.boss, self.players[0][1] if self.players else self.boss)
            if boss_effects:
                self.lines.extend(boss_effects)
            
            self.lines.append("")
            await self._process_end_of_turn(all_participants)
            await self._process_weather_effects(all_participants)
            await self._process_field_effects()
            
            if self.boss.fainted:
                await self._handle_victory()
            elif all(p.fainted for _, p in self.players):
                await self._handle_defeat()
            
            if not self.ended:
                self.turn += 1
                self.player_actions = {uid: None for uid, _ in self.players}
                self.lines.append("⚔️ Escolha sua próxima ação!")
            
            await self.refresh()
            
            if not self.ended:
                alive_players = [uid for uid, p in self.players if not p.fainted]
                
                if len(alive_players) == 1:
                    await self.message.channel.send(
                        f"⚔️ <@{alive_players[0]}>\n"
                        f"**Turno {self.turn}** - É seu turno! Você é o único sobrevivente!"
                    )
                elif len(alive_players) > 1:
                    mentions = " ".join([f"<@{uid}>" for uid in alive_players])
                    await self.message.channel.send(
                        f"⏳ **Turno {self.turn}** {mentions}\n"
                        f"Aguardando ações de **{len(alive_players)}** jogadores!"
                    )
    
    def _is_boss_multi_target(self, move_data: MoveData, effect_data: Dict[str, Any]) -> bool:
        from .targeting import TargetingSystem
        
        return TargetingSystem.is_multi_target_move(effect_data, move_data.name)
    
    async def _handle_victory(self) -> None:
        if self.rewards_distributed:
            return
        
        self.ended = True
        self.rewards_distributed = True
        
        self.lines.extend([
            "",
            "🎉 **VITÓRIA NA RAID!**",
            f"✨ {self.boss.display_name} foi derrotado!",
            ""
        ])
        
        base_exp = pm.repo.tk.calc_battle_exp(
            max(p.level for _, p in self.players),
            self.boss.level
        )
        
        raid_bonus = 2.0
        exp_per_player = int(base_exp * raid_bonus)
        
        self.lines.append(f"⭐ **RECOMPENSAS (Bônus Raid {raid_bonus}x):**")
        
        for user_id, pokemon in self.players:
            user_mention = f"<@{user_id}>"
            
            if pokemon.fainted:
                participation_exp = exp_per_player // 2
            else:
                participation_exp = exp_per_player
            
            player_party = pm.repo.tk.get_user_party(user_id)
            if player_party:
                pokemon_data = next((p for p in player_party if p["id"] == pokemon.raw["id"]), None)
                if pokemon_data:
                    exp_result = pm.repo.tk.add_exp(user_id, pokemon_data["id"], participation_exp)
                    
                    if exp_result.get("levels_gained"):
                        move_result = await pm.process_level_up(
                            user_id,
                            pokemon_data["id"],
                            exp_result["levels_gained"]
                        )
                        
                        level_msg = f" (+{exp_result['levels_gained']} níveis!)"
                    else:
                        level_msg = ""
                    
                    self.lines.append(f"  • {user_mention}: +{participation_exp} XP{level_msg}")
        
        if self.actions_view:
            self.actions_view.disable_all()
        
        await self.refresh()
        
        mentions = " ".join([f"<@{uid}>" for uid, _ in self.players])
        await self.message.channel.send(
            f"🎉 **VITÓRIA!** {mentions}\n"
            f"Parabéns! O **{self.boss.display_name}** foi derrotado!"
        )
        
        await self.cleanup()
    
    async def _handle_defeat(self) -> None:
        self.ended = True
        
        self.lines.extend([
            "",
            "😔 **DERROTA**",
            f"💀 Todos os jogadores foram derrotados!",
            f"O {self.boss.display_name} ainda tem {self.boss.current_hp:,}/{self.boss.stats['hp']:,} HP.",
            "Melhor sorte na próxima vez!"
        ])
        
        if self.actions_view:
            self.actions_view.disable_all()
        
        await self.refresh()
        
        mentions = " ".join([f"<@{uid}>" for uid, _ in self.players])
        await self.message.channel.send(
            f"💀 **DERROTA** {mentions}\n"
            f"O **{self.boss.display_name}** venceu a batalha!"
        )
        
        await self.cleanup()
    
    async def cleanup(self) -> None:
        for user_id, _ in self.players:
            battle_tracker.remove(user_id)
        
        self.move_cache.clear()
        self.effect_cache.clear()
        
        if self.actions_view:
            self.actions_view.stop()

class RaidBattleView(discord.ui.View):
    __slots__ = ('battle',)
    
    def __init__(self, battle: RaidBattle, timeout: float = 300.0) -> None:
        super().__init__(timeout=timeout)
        self.battle = battle
    
    async def on_timeout(self) -> None:
        if not self.battle.ended:
            self.battle.ended = True
            self.disable_all()
            
            await self.battle.cleanup()
            
            if self.battle.message:
                mentions = " ".join([f"<@{uid}>" for uid, _ in self.battle.players])
                await self.battle.message.reply(
                    content=f"**Raid expirada!** {mentions}\n"
                    f"A raid foi encerrada por inatividade (5 minutos)."
                )
    
    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True
    
    @discord.ui.button(style=discord.ButtonStyle.primary, label="Escolher Ação", emoji="⚔️")
    async def choose_action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_id = str(interaction.user.id)
        
        player_data = next(((uid, p) for uid, p in self.battle.players if uid == user_id), None)
        
        if not player_data:
            return await interaction.response.send_message(
                "Você não está participando desta raid!",
                ephemeral=True
            )
        
        uid, pokemon = player_data
        
        if pokemon.fainted:
            return await interaction.response.send_message(
                "Seu Pokémon está desmaiado!",
                ephemeral=True
            )
        
        if self.battle.player_actions.get(user_id):
            return await interaction.response.send_message(
                "Você já escolheu sua ação este turno!",
                ephemeral=True
            )
        
        await interaction.response.edit_message(
            view=RaidMovesView(self.battle, user_id, pokemon)
        )

class RaidMovesView(discord.ui.View):
    __slots__ = ('battle', 'user_id', 'pokemon')
    
    def __init__(self, battle: RaidBattle, user_id: str, pokemon: BattlePokemon, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.battle = battle
        self.user_id = user_id
        self.pokemon = pokemon
        
        for mv in pokemon.moves[:4]:
            key = _slug(mv["id"])
            md = battle.move_cache.get(key)
            label_text = (md.name if md else key.replace("-", " ").title())
            pp, pp_max = int(mv.get("pp", 0)), int(mv.get("pp_max", 35))
            
            btn = discord.ui.Button(
                style=discord.ButtonStyle.primary if pp > 0 else discord.ButtonStyle.secondary,
                label=f"{label_text} ({pp}/{pp_max})",
                disabled=(pp <= 0)
            )
            btn.callback = self._cb(mv["id"])
            self.add_item(btn)
        
        back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar", emoji="↩️")
        back.callback = self._back_cb
        self.add_item(back)
    
    def _cb(self, move_id: str):
        async def callback(i: discord.Interaction):
            if str(i.user.id) != self.user_id:
                return await i.response.send_message("Não é sua vez!", ephemeral=True)
            
            self.battle.player_actions[self.user_id] = move_id
            
            await i.response.send_message(
                f"Ação escolhida! Aguardando outros jogadores...",
                ephemeral=True
            )
            
            await i.message.edit(view=RaidBattleView(self.battle))
            
            await self.battle._notify_action_progress()
            
            if self.battle._all_actions_ready():
                await self.battle.process_turn()
        
        return callback
    
    async def _back_cb(self, i: discord.Interaction):
        if str(i.user.id) != self.user_id:
            return await i.response.send_message("Não é sua vez!", ephemeral=True)
        
        await i.response.edit_message(view=RaidBattleView(self.battle))
