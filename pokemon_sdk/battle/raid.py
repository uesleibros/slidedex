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
from .helpers import MoveData, _hp_bar
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
        from .helpers import _slug
        
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
    
    def _generate_hp_display(self, pokemon: BattlePokemon, prefix: str = "") -> str:
        bar = _hp_bar(pokemon.current_hp, pokemon.stats["hp"])
        hp_percent = (pokemon.current_hp / pokemon.stats["hp"] * 100) if pokemon.stats["hp"] > 0 else 0
        
        display = f"{prefix}{format_pokemon_display(pokemon.raw, bold_name=True)} {pokemon.status_tag()} Lv{pokemon.level}\n"
        display += f"{bar} {max(0, pokemon.current_hp)}/{pokemon.stats['hp']} ({hp_percent:.1f}%)"
        
        return display
    
    def _build_embed(self) -> discord.Embed:
        description = [
            f"**🔥 RAID BOSS 🔥**",
            self._generate_hp_display(self.boss),
            "",
            "**👥 JOGADORES:**"
        ]
        
        for user_id, pokemon in self.players:
            user_mention = f"<@{user_id}>"
            prefix = "🔵 " if not pokemon.fainted else "💀 "
            
            action_status = ""
            if self.player_actions.get(user_id):
                action_status = " ✅"
            elif not pokemon.fainted:
                action_status = " ⏳"
            
            description.append(
                f"{prefix}{user_mention}: {pokemon.display_name}{action_status}"
            )
        
        description.append("")
        
        if self.lines:
            description.extend(self.lines[-20:])
        
        embed = discord.Embed(
            title=f"Raid Battle - Turno {self.turn}",
            description="\n".join(description),
            color=discord.Color.red()
        )
        
        embed.set_footer(text="Effex Engine v1.6 — Multi Battle")
        embed.set_image(url="attachment://raid.png")
        return embed
    
    async def start(self) -> None:
        self.actions_view = RaidBattleView(self)
        self.lines = [
            f"🔥 A raid contra {self.boss.display_name} começou!",
            f"💪 {len(self.players)} jogadores estão participando!"
        ]
        
        for user_id in [uid for uid, _ in self.players]:
            battle_tracker.add(user_id)
        
        self.message = await self.interaction.channel.send(
            embed=self._build_embed(),
            file=await self._compose_image(),
            view=self.actions_view
        )
        self.must_redraw_image = False
    
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
        from .helpers import _slug
        
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
                    self.lines.append(f"🔵 **{user_mention}**")
                    
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
                    
                    self.lines.append(f"🔴 **BOSS**")
                    
                    if is_multi_target:
                        for target_uid, target_pokemon in alive_players:
                            if target_pokemon.fainted:
                                continue
                            
                            result = await self._execute_turn_action(
                                False, move_id, move_data, self.boss, target_pokemon
                            )
                            
                            target_mention = f"<@{target_uid}>"
                            self.lines.append(f"   → Alvo: {target_mention}")
                            self.lines.extend(result)
                    else:
                        target_uid, target_pokemon = random.choice(alive_players)
                        target_mention = f"<@{target_uid}>"
                        
                        result = await self._execute_turn_action(
                            False, move_id, move_data, self.boss, target_pokemon
                        )
                        
                        self.lines.append(f"   → Alvo: {target_mention}")
                        self.lines.extend(result)
                    
                    self.lines.append("")
            
            all_participants = [p for _, p in self.players] + [self.boss]
            
            end_turn_effects = StatusHandler.end_of_turn_effects(self.boss, *[p for _, p in self.players])
            if end_turn_effects:
                self.lines.extend(end_turn_effects)
            
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
            
            await self.refresh()
    
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
        
        await self.cleanup()
    
    async def _handle_defeat(self) -> None:
        self.ended = True
        
        self.lines.extend([
            "",
            "😔 **DERROTA**",
            f"💀 Todos os jogadores foram derrotados por {self.boss.display_name}!",
            "Melhor sorte na próxima vez!"
        ])
        
        if self.actions_view:
            self.actions_view.disable_all()
        
        await self.refresh()
        
        await self.cleanup()
    
    async def cleanup(self) -> None:
        for user_id, _ in self.players:
            battle_tracker.remove(user_id)
        
        self.move_cache.clear()
        self.effect_cache.clear()
        
        if self.actions_view:
            self.actions_view.stop()

class RaidBattleView(discord.ui.View):
    
    def __init__(self, battle: RaidBattle, timeout: float = 300.0) -> None:
        super().__init__(timeout=timeout)
        self.battle = battle
    
    async def on_timeout(self) -> None:
        if not self.battle.ended:
            self.battle.ended = True
            self.disable_all()
            
            await self.battle.cleanup()
            
            if self.battle.message:
                await self.battle.message.reply(
                    content="Raid Expirada!\nA raid foi encerrada por inatividade."
                )
    
    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True
    
    @discord.ui.button(style=discord.ButtonStyle.primary, label="Escolher Ação", emoji="⚔️")
    async def choose_action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_id = str(interaction.user.id)
        
        player_data = next((p for uid, p in self.battle.players if uid == user_id), None)
        if not player_data:
            return await interaction.response.send_message(
                "Você não está participando desta raid!",
                ephemeral=True
            )
        
        _, pokemon = next((uid, p) for uid, p in self.battle.players if uid == user_id)
        
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
        
        await interaction.response.edit_message(view=RaidMovesView(self.battle, user_id, pokemon))

class RaidMovesView(discord.ui.View):
    
    def __init__(self, battle: RaidBattle, user_id: str, pokemon: BattlePokemon):
        super().__init__(timeout=60.0)
        self.battle = battle
        self.user_id = user_id
        self.pokemon = pokemon
        
        for move in pokemon.moves[:4]:
            move_id = move.get("id")
            move_name = move.get("name", move_id)
            pp = move.get("pp", 0)
            pp_max = move.get("pp_max", pp)
            
            button = discord.ui.Button(
                label=f"{move_name.replace('-', ' ').title()} ({pp}/{pp_max})",
                style=discord.ButtonStyle.primary,
                disabled=(pp <= 0)
            )
            button.callback = self._create_callback(move_id)
            self.add_item(button)
        
        back_button = discord.ui.Button(
            label="Voltar",
            style=discord.ButtonStyle.secondary,
            emoji="↩️"
        )
        back_button.callback = self._back_callback
        self.add_item(back_button)
    
    def _create_callback(self, move_id: str):
        async def callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.user_id:
                return await interaction.response.send_message(
                    "Não é sua vez!",
                    ephemeral=True
                )
            
            self.battle.player_actions[self.user_id] = move_id
            
            await interaction.response.send_message(
                f"Ação escolhida! Aguardando outros jogadores...",
                ephemeral=True
            )
            
            await interaction.message.edit(view=RaidBattleView(self.battle))
            
            if all(self.battle.player_actions.get(uid) for uid, p in self.battle.players if not p.fainted):
                await self.battle.process_turn()
        
        return callback
    
    async def _back_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(
                "Não é sua vez!",
                ephemeral=True
            )
        
        await interaction.response.edit_message(view=RaidBattleView(self.battle))
