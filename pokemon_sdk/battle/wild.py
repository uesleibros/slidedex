import discord
import random
import asyncio
from __main__ import pm
from typing import List, Dict, Any, Optional, Set
from utils.canvas import compose_battle_async
from utils.preloaded import preloaded_textures
from utils.formatting import format_pokemon_display
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .messages import BattleMessages
from .damage import DamageCalculator
from .effects import EffectHandler
from .status import StatusHandler
from .capture import CaptureSystem
from .helpers import SwitchView, MovesView, MoveData, _normalize_move, _hp_bar, _slug
from .pokeballs import PokeBallSystem, BallType

class WildBattle:
    def __init__(self, player_party: List[Dict[str, Any]], wild: Dict[str, Any], user_id: str, interaction: discord.Interaction) -> None:
        self.user_id = user_id
        self.interaction = interaction
        self.player_party_raw = player_party
        self.active_player_idx = 0
        self.wild_raw = wild
        self.ended = False
        self.turn = 1
        self.message: Optional[discord.Message] = None
        self.lock = asyncio.Lock()
        self.player_team: List[BattlePokemon] = []
        self.wild: Optional[BattlePokemon] = None
        self.actions_view: Optional[WildBattleView] = None
        self.lines: List[str] = []
        self.must_redraw_image = True
        self.move_cache: Dict[str, MoveData] = {}
        self.effect_cache: Dict[str, Dict[str, Any]] = {}
        self.weather = {"type": None, "turns": 0}
        self.field = {"spikes_player": 0, "spikes_wild": 0, "trick_room": 0, "gravity": 0}
        self.damage_calculator = DamageCalculator(self.weather)
        self.effect_handler = EffectHandler()
        self.ball_type = BallType.POKE_BALL
        self.location_type = "normal"
        self.time_of_day = "day"
    
    @property
    def player_active(self) -> BattlePokemon:
        return self.player_team[self.active_player_idx]
    
    async def setup(self):
        w_api, w_spec = await asyncio.gather(
            pm.service.get_pokemon(self.wild_raw["species_id"]),
            pm.service.get_species(self.wild_raw["species_id"])
        )
        self.wild = BattlePokemon(self.wild_raw, w_api, w_spec)
        
        party_coros = []
        for p in self.player_party_raw:
            party_coros.extend([
                pm.service.get_pokemon(p["species_id"]),
                pm.service.get_species(p["species_id"])
            ])
        
        party_data = await asyncio.gather(*party_coros)
        for i in range(0, len(party_data), 2):
            self.player_team.append(BattlePokemon(
                self.player_party_raw[i // 2],
                party_data[i],
                party_data[i + 1]
            ))
        
        await self._warm_moves()
    
    async def _warm_moves(self):
        ids: Set[str] = set()
        for mv in self.wild.moves:
            ids.add(_slug(mv["id"]))
        for p in self.player_team:
            for mv in p.moves:
                ids.add(_slug(mv["id"]))
        
        if ids:
            await asyncio.gather(*[self._fetch_move(mid) for mid in ids if mid])
    
    async def _compose_image(self):
        pb = await self.player_active.sprites["back"].read() if self.player_active.sprites["back"] else None
        ef = await self.wild.sprites["front"].read() if self.wild.sprites["front"] else None
        buf = await compose_battle_async(pb, ef, preloaded_textures["battle"])
        return discord.File(buf, filename="battle.png")
    
    def _hp_line(self, p: BattlePokemon) -> str:
        bar = _hp_bar(p.current_hp, p.stats["hp"])
        hp_percent = (p.current_hp / p.stats["hp"] * 100) if p.stats["hp"] > 0 else 0
        base_line = f"{format_pokemon_display(p.raw, bold_name=True)} {p.status_tag()} Lv{p.level}\n{bar} {max(0, p.current_hp)}/{p.stats['hp']} ({hp_percent:.1f}%)"

        stage_info = []
        if p.stages.get("accuracy", 0) != 0:
            acc = p.stages["accuracy"]
            stage_info.append(f"ACC: {acc:+d}")
        if p.stages.get("evasion", 0) != 0:
            eva = p.stages["evasion"]
            stage_info.append(f"EVA: {eva:+d}")
        
        if stage_info:
            base_line += f" [{' | '.join(stage_info)}]"
        return base_line
    
    def _embed(self) -> discord.Embed:
        desc_parts = [
            self._hp_line(self.player_active),
            "**VS**",
            self._hp_line(self.wild),
            ""
        ]
        
        weather_icons = {"sun": "☀️", "rain": "🌧️", "hail": "❄️", "sandstorm": "🌪️"}
        if self.weather["type"] and self.weather["turns"] > 0:
            desc_parts.append(f"{weather_icons.get(self.weather['type'], '🌤️')} {self.weather['type'].title()} ({self.weather['turns']} turnos)")
        
        field_effects = []
        if self.field.get("trick_room", 0) > 0:
            field_effects.append(f"🔄 Trick Room")
        if self.field.get("gravity", 0) > 0:
            field_effects.append(f"⬇️ Gravity")
        
        if field_effects:
            desc_parts.extend(field_effects)
            desc_parts.append("")
        
        if self.lines:
            desc_parts.extend(self.lines[-15:])
        
        embed = discord.Embed(
            title=f"Batalha Selvagem - Turno {self.turn}",
            description="\n".join(desc_parts),
            color=discord.Color.green()
        )
        
        embed.set_footer(text="Effex Engine v1.4 — alpha")
        embed.set_image(url="attachment://battle.png")
        return embed
    
    async def start(self):
        self.actions_view = WildBattleView(self)
        self.lines = ["A batalha começou!"]
        self.message = await self.interaction.channel.send(
            embed=self._embed(),
            file=await self._compose_image(),
            view=self.actions_view
        )
        self.must_redraw_image = False
    
    async def refresh(self):
        if not self.message:
            return
        embed = self._embed()
        if self.must_redraw_image:
            file = await self._compose_image()
            await self.message.edit(attachments=[file], embed=embed, view=self.actions_view)
            self.must_redraw_image = False
        else:
            await self.message.edit(embed=embed, view=self.actions_view)
    
    async def _fetch_move(self, move_id: str) -> MoveData:
        key = _slug(move_id)
        if not key:
            raise ValueError("move_id vazio")
        if key in self.move_cache:
            return self.move_cache[key]
        
        mv = await pm.service.get_move(key)
        md = _normalize_move(mv)
        self.move_cache[key] = md
        
        from data.effect_mapper import effect_mapper
        effect_text = getattr(mv, "effect_entries", [])
        for entry in effect_text:
            if entry.language.name == "en":
                self.effect_cache[key] = effect_mapper.get(entry.short_effect, {})
                break
        
        if key not in self.effect_cache:
            self.effect_cache[key] = {}
        
        return md
    
    def _get_effect_data(self, move_id: str) -> Dict[str, Any]:
        return self.effect_cache.get(_slug(move_id), {})
    
    async def _use_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, move_id_for_pp: Optional[str]) -> List[str]:
        is_struggle = move_id_for_pp == "__struggle__"
        
        if move_id_for_pp and not is_struggle:
            pp = user.get_pp(move_id_for_pp)
            if pp is not None and pp <= 0:
                return [f"❌ {user.display_name} não tem PP!"]
            user.dec_pp(move_id_for_pp)
            user.volatile["last_move_used"] = move_id_for_pp
        
        effect_data = self._get_effect_data(move_id_for_pp or "tackle")
        
        if target.volatile.get("protect"):
            if md.dmg_class != "status":
                return [BattleMessages.protected(target.display_name)]
        
        if md.accuracy is not None and not effect_data.get("bypass_accuracy", False):
            acc = md.accuracy
            if user.volatile.get("mind_reader_target") == target:
                acc = None
                user.volatile["mind_reader_target"] = None
            
            if acc is not None and random.randint(1, 100) > int(acc):
                return [BattleMessages.miss(user.display_name, md.name)]
        
        if md.dmg_class == "status" or md.power == 0:
            return await self._apply_status_move(user, target, md, effect_data)
        
        lines = []
        multi_hit = effect_data.get("multi_hit", {})
        hits = 1
        if multi_hit:
            min_hits = multi_hit.get("min", 1)
            max_hits = multi_hit.get("max", 1)
            if max_hits > 1:
                hits = random.randint(min_hits, max_hits)
        
        total_damage = 0
        first_tm, first_crit = 1.0, False
        
        for i in range(hits):
            if target.fainted:
                break
            
            dmg, tm, crit = await self.damage_calculator.calculate(user, target, md, effect_data)
            if i == 0:
                first_tm, first_crit = tm, crit
            
            if tm == 0.0 and not is_struggle:
                return [BattleMessages.no_effect(user.display_name, md.name)]
            
            if target.status["name"] == "freeze" and md.type_name.lower() == "fire" and dmg > 0:
                target.status = {"name": None, "counter": 0}
                lines.append(f"🔥 {target.display_name} descongelou!")
            
            actual = target.take_damage(dmg)
            total_damage += actual
            
            if target.fainted:
                if target.volatile.get("destiny_bond"):
                    user.current_hp = 0
                    lines.append(f"👻 Destiny Bond ativado! {user.display_name} também caiu!")
                break
        
        if is_struggle:
            main_line = f"💢 {user.display_name} não tem PP!"
            lines.append(main_line)
            lines.append(f"Usou **Struggle**! ({total_damage} de dano)")
        else:
            lines.append(BattleMessages.damage(user.display_name, md.name, total_damage))
        
        detail_line = BattleMessages.details(hits if hits > 1 else None, first_crit, first_tm)
        if detail_line:
            lines.append(detail_line)
        
        if target.fainted:
            lines.append(BattleMessages.fainted(target.display_name))
        
        if is_struggle:
            struggle_recoil = max(1, int(user.stats["hp"] * BattleConstants.STRUGGLE_RECOIL_RATIO))
            actual_recoil = user.take_damage(struggle_recoil, ignore_substitute=True)
            lines.append(BattleMessages.recoil(user.display_name, actual_recoil))
        elif effect_data.get("recoil"):
            recoil_dmg = max(1, int(total_damage * effect_data["recoil"]))
            actual_recoil = user.take_damage(recoil_dmg, ignore_substitute=True)
            lines.append(BattleMessages.recoil(user.display_name, actual_recoil))
        
        if effect_data.get("drain"):
            drain_hp = max(1, int(total_damage * effect_data["drain"]))
            actual_drain = user.heal(drain_hp)
            if actual_drain > 0:
                lines.append(BattleMessages.drain(user.display_name, actual_drain))
        
        for effect in effect_data.get("effects", []):
            effect_lines = self.effect_handler.apply_effect(user, target, effect, total_damage)
            if effect_lines:
                lines.extend(effect_lines)
        
        return lines
    
    async def _apply_status_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, effect_data: Dict[str, Any]) -> List[str]:
        lines = [f"✨ {user.display_name} usou **{md.name}**!"]
        changed = False
        
        effects = effect_data.get("effects", [])
        
        if effects:
            for effect in effects:
                result = self.effect_handler.apply_effect(user, target, effect, 0)
                if result:
                    changed = True
                    lines.extend(result)
        elif md.stat_changes:
            for stat_tuple in md.stat_changes:
                stat = stat_tuple[0]
                stages = stat_tuple[1]
                is_self_buff = stat_tuple[2] if len(stat_tuple) > 2 else (stages > 0)
                
                pokemon_target = user if is_self_buff else target
                effect = {"type": "stat_change", "stat": stat, "stages": stages}
                result = self.effect_handler.apply_effect(user, pokemon_target, effect, 0)
                if result:
                    changed = True
                    lines.extend(result)
        
        if not changed:
            lines.append(BattleMessages.failed())
        
        return lines
    
    async def _act(self, player_side: bool, mv_id: str, md: MoveData) -> List[str]:
        user = self.player_active if player_side else self.wild
        target = self.wild if player_side else self.player_active
        
        block, pre = StatusHandler.check_pre_action(user)
        if block:
            return pre
        
        conf_block, conf = StatusHandler.check_confusion(user)
        if conf_block:
            return pre + conf
        
        return pre + conf + await self._use_move(user, target, md, mv_id)
    
    def _enemy_pick(self) -> str:
        opts = [m for m in self.wild.moves if int(m.get("pp", 0)) > 0]
        return str(random.choice(opts)["id"]) if opts else "__struggle__"
    
    async def handle_player_move(self, move_id: str):
        async with self.lock:
            if self.ended:
                return
            
            self.lines = []
            
            pmd = await self._fetch_move(move_id)
            eid = self._enemy_pick()
            
            if eid != "__struggle__":
                emd = await self._fetch_move(eid)
            else:
                emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
            
            ps = self.player_active.eff_stat("speed")
            es = self.wild.eff_stat("speed")
            
            if pmd.priority != emd.priority:
                order = ["player", "enemy"] if pmd.priority > emd.priority else ["enemy", "player"]
            elif ps != es:
                order = ["player", "enemy"] if ps > es else ["enemy", "player"]
            else:
                order = random.choice([["player", "enemy"], ["enemy", "player"]])
            
            for side in order:
                if self.player_active.fainted or self.wild.fainted:
                    break
                
                if side == "player":
                    self.lines.extend(await self._act(True, move_id, pmd))
                    if self.wild.fainted:
                        await self._on_win()
                        await self.refresh()
                        return
                else:
                    if self.lines:
                        self.lines.append("")
                    self.lines.extend(await self._act(False, eid, emd))
                    if self.player_active.fainted:
                        await self._on_faint()
                        await self.refresh()
                        return
            
            end_turn = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
            if end_turn:
                self.lines.append("")
                self.lines.extend(end_turn)
            
            if self.weather["type"] and self.weather["turns"] > 0:
                self.weather["turns"] -= 1
                if self.weather["turns"] == 0:
                    self.lines.append(f"🌤️ O clima voltou ao normal!")
                    self.weather["type"] = None
                elif self.weather["type"] == "hail":
                    for p, prefix in [(self.player_active, "🔵"), (self.wild, "🔴")]:
                        if not p.fainted and "ice" not in p.types:
                            dmg = max(1, int(p.stats["hp"] * BattleConstants.HAIL_DAMAGE_RATIO))
                            actual = p.take_damage(dmg, ignore_substitute=True)
                            self.lines.append(f"❄️ {prefix} {p.display_name} sofreu {actual} de dano da granizo!")
            
            if self.wild.fainted:
                await self._on_win()
            elif self.player_active.fainted:
                await self._on_faint()
            
            if not self.ended:
                self.turn += 1
            
            await self.refresh()
    
    async def switch_active(self, new_index: int, consume_turn: bool = True):
        async with self.lock:
            if self.ended or new_index == self.active_player_idx:
                return
            if not (0 <= new_index < len(self.player_team)) or self.player_team[new_index].fainted:
                return
            
            self.lines = []
            old_name = self.player_active.display_name
            self.active_player_idx = new_index
            self.must_redraw_image = True
            
            self.lines.extend([
                f"🔄 {old_name} voltou!",
                f"🔵 Vamos lá, {self.player_active.display_name}!"
            ])
            
            if consume_turn:
                self.lines.append("")
                eid = self._enemy_pick()
                if eid != "__struggle__":
                    emd = await self._fetch_move(eid)
                else:
                    emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
                
                self.lines.extend(await self._act(False, eid, emd))
                
                end_turn = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
                if end_turn:
                    self.lines.append("")
                    self.lines.extend(end_turn)
                
                if self.player_active.fainted:
                    await self._on_faint()
                
                if not self.ended:
                    self.turn += 1
            
            await self.refresh()
    
    async def attempt_capture(self, ball_type: str = BallType.POKE_BALL) -> bool:
        if self.player_active.fainted:
            self.lines = ["Seu Pokémon está desmaiado!"]
            if self.actions_view:
                self.actions_view.force_switch_mode = True
            await self.refresh()
            return False

        already_caught = pm.repo.tk.has_caught_species(self.user_id, self.wild.species_id)
        success, shakes, ball_modifier = CaptureSystem.attempt_capture_gen3(
            wild=self.wild,
            ball_type=self.ball_type,
            turn=self.turn,
            time_of_day=self.time_of_day,
            location_type=self.location_type,
            already_caught=already_caught
        )
        
        ball_emoji = PokeBallSystem.get_ball_emoji(ball_type)
        ball_name = PokeBallSystem.get_ball_name(ball_type)
        
        if success:
            xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
            pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
            pm.repo.tk.add_pokemon(
                owner_id=self.user_id,
                species_id=self.wild_raw["species_id"],
                ivs=self.wild_raw["ivs"],
                nature=self.wild_raw["nature"],
                ability=self.wild_raw["ability"],
                gender=self.wild_raw["gender"],
                shiny=self.wild_raw.get("is_shiny", False),
                level=self.wild_raw["level"],
                is_legendary=self.wild_raw["is_legendary"],
                is_mythical=self.wild_raw["is_mythical"],
                types=self.wild_raw["types"],
                region=self.wild_raw["region"],
                stats=self.wild_raw["stats"],
                exp=self.wild_raw.get("exp", 0),
                moves=self.wild_raw.get("moves", []),
                nickname=self.wild_raw.get("nickname"),
                name=self.wild_raw.get("name"),
                current_hp=self.wild_raw.get("current_hp"),
                on_party=pm.repo.tk.can_add_to_party(self.user_id)
            )
            self.ended = True
            bonus_text = ""
            if ball_modifier > 1.0:
                bonus_text = f" (Bônus {ball_modifier:.1f}x)"
            
            self.lines = [
                f"🎉 **CAPTURA!**",
                f"{ball_emoji} Capturado com {ball_name}!{bonus_text}",
                f"✨ {self.wild.display_name} foi adicionado à sua Pokédex!",
                f"⭐ {self.player_active.display_name} ganhou {xp} XP!"
            ]
            if self.actions_view:
                self.actions_view.disable_all()
            await self.refresh()
            await self.interaction.channel.send(
                f"🎉 **Capturou {self.wild.display_name}!** ⭐ {self.player_active.display_name} +{xp} XP"
            )
            return True
        else:
            self.lines = []
            shake_text = f"{ball_emoji} " * shakes if shakes > 0 else ""
            self.lines.append(f"💢 {shake_text}Escapou! ({shakes}x)")
            self.lines.append("")
            
            eid = self._enemy_pick()
            if eid != "__struggle__":
                emd = await self._fetch_move(eid)
            else:
                emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
            
            self.lines.extend(await self._act(False, eid, emd))
            
            end_turn = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
            if end_turn:
                self.lines.append("")
                self.lines.extend(end_turn)
            
            if self.player_active.fainted:
                await self._on_faint()
            
            if not self.ended:
                self.turn += 1
            
            await self.refresh()
            return False
    
    async def _on_win(self):
        xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
        pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
        self.ended = True
        self.lines.extend([
            "",
            f"🏆 **VITÓRIA!**",
            f"⭐ {self.player_active.display_name} +{xp} XP!"
        ])
        if self.actions_view:
            self.actions_view.disable_all()
        await self.refresh()
        await self.interaction.channel.send(
            f"🏆 **Vitória!** ⭐ {self.player_active.display_name} +{xp} XP"
        )
    
    async def _on_faint(self):
        alive = [p for p in self.player_team if not p.fainted]
        
        if not alive:
            self.ended = True
            self.lines.extend([
                "",
                f"😔 **DERROTA**",
                f"Todos os seus pokémon desmaiaram!"
            ])
            if self.actions_view:
                self.actions_view.disable_all()
            await self.refresh()
            await self.interaction.channel.send("💀 **Derrota!**")
            return
        
        self.lines.extend(["", f"Escolha outro Pokémon!"])
        if self.actions_view:
            self.actions_view.force_switch_mode = True
    
    async def cleanup(self):
        self.move_cache.clear()
        self.effect_cache.clear()
        if self.actions_view:
            self.actions_view.stop()

class WildBattleView(discord.ui.View):
    def __init__(self, battle: WildBattle, timeout=180.0):
        super().__init__(timeout=timeout)
        self.battle = battle
        self.user_id = battle.user_id
        self.force_switch_mode = False
    
    def disable_all(self):
        for item in self.children:
            item.disabled = True
    
    @discord.ui.button(style=discord.ButtonStyle.primary, label="Lutar", emoji="⚔️")
    async def fight(self, i: discord.Interaction, b: discord.ui.Button):
        if str(i.user.id) != self.user_id:
            return await i.response.send_message("Não é sua batalha!", ephemeral=True)
        if self.battle.ended:
            return await i.response.send_message("Batalha encerrada.", ephemeral=True)
        if self.force_switch_mode:
            return await i.response.edit_message(view=SwitchView(self.battle, force_only=True))
        await i.response.edit_message(view=MovesView(self.battle))
    
    @discord.ui.button(style=discord.ButtonStyle.primary, label="Trocar", emoji="🔄")
    async def switch(self, i: discord.Interaction, b: discord.ui.Button):
        if str(i.user.id) != self.user_id:
            return await i.response.send_message("Não é sua batalha!", ephemeral=True)
        if self.battle.ended:
            return await i.response.send_message("Batalha encerrada.", ephemeral=True)
        await i.response.edit_message(view=SwitchView(self.battle))
    
    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
    async def capture(self, i: discord.Interaction, b: discord.ui.Button):
        if str(i.user.id) != self.user_id:
            return await i.response.send_message("Não é sua batalha!", ephemeral=True)
        if self.battle.ended:
            return await i.response.send_message("Batalha encerrada.", ephemeral=True)
        if self.force_switch_mode or self.battle.player_active.fainted:
            return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
        await i.response.defer()
        await self.battle.attempt_capture()








