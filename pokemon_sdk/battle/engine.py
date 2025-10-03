import discord
import random
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .messages import BattleMessages
from .damage import DamageCalculator
from .effects import EffectHandler
from .status import StatusHandler
from .helpers import MoveData, _normalize_move, _slug
from .targeting import TargetingSystem, TargetType, BattleContext

class BattleEngine:
    
    def __init__(self, battle_type: str = "single"):
        self.ended = False
        self.turn = 1
        self.lock = asyncio.Lock()
        self.lines: List[str] = []
        self.must_redraw_image = True
        self.move_cache: Dict[str, MoveData] = {}
        self.effect_cache: Dict[str, Dict[str, Any]] = {}
        self.weather = {"type": None, "turns": 0}
        self.field = {
            "spikes_player": 0, 
            "spikes_wild": 0, 
            "trick_room": 0, 
            "gravity": 0,
            "mud_sport": 0,
            "water_sport": 0
        }
        self.damage_calculator = DamageCalculator(self.weather)
        self.effect_handler = EffectHandler()
        self.battle_context = BattleContext(battle_type=battle_type)
    
    def _find_first_available_pokemon(self, team: List[BattlePokemon]) -> Optional[int]:
        for idx, pokemon in enumerate(team):
            if not pokemon.fainted:
                return idx
        return None
    
    def _validate_party(self, team: List[BattlePokemon]) -> bool:
        return any(not p.fainted for p in team)
    
    def _has_remaining_pokemon(self, team: List[BattlePokemon]) -> bool:
        return any(not p.fainted for p in team)
    
    def _generate_hp_display(self, pokemon: BattlePokemon, show_stages: bool = True) -> str:
        from .helpers import _hp_bar
        from utils.formatting import format_pokemon_display
        
        bar = _hp_bar(pokemon.current_hp, pokemon.stats["hp"])
        hp_percent = (pokemon.current_hp / pokemon.stats["hp"] * 100) if pokemon.stats["hp"] > 0 else 0
        base_display = (
            f"{format_pokemon_display(pokemon.raw, bold_name=True)} "
            f"{pokemon.status_tag()} Lv{pokemon.level}\n"
            f"{bar} {max(0, pokemon.current_hp)}/{pokemon.stats['hp']} ({hp_percent:.1f}%)"
        )

        if show_stages:
            stage_modifications = []
            for stat_key in ["atk", "def", "sp_atk", "sp_def", "speed"]:
                stage_value = pokemon.stages.get(stat_key, 0)
                if stage_value != 0:
                    stat_abbrev = stat_key.upper().replace("_", "")
                    stage_modifications.append(f"{stat_abbrev}: {stage_value:+d}")
            
            if pokemon.stages.get("accuracy", 0) != 0:
                stage_modifications.append(f"ACC: {pokemon.stages['accuracy']:+d}")
            if pokemon.stages.get("evasion", 0) != 0:
                stage_modifications.append(f"EVA: {pokemon.stages['evasion']:+d}")
            
            if stage_modifications:
                base_display += f" [{' | '.join(stage_modifications)}]"
        
        return base_display
    
    def _select_ai_move(self, pokemon: BattlePokemon) -> str:
        available_moves = []
        
        for m in pokemon.moves:
            move_id = str(m["id"])
            pp = int(m.get("pp", 0))
            
            if pp <= 0:
                continue
            
            if pokemon.is_move_disabled(move_id):
                continue
            
            available_moves.append(m)
        
        if not available_moves:
            return "__struggle__"
        
        return str(random.choice(available_moves)["id"])
    
    def _determine_turn_order(
        self,
        move1: MoveData,
        pokemon1: BattlePokemon,
        move2: MoveData,
        pokemon2: BattlePokemon
    ) -> List[str]:
        priority1 = self._get_move_priority(move1, pokemon1)
        priority2 = self._get_move_priority(move2, pokemon2)
        
        if priority1 != priority2:
            return ["first", "second"] if priority1 > priority2 else ["second", "first"]
        
        speed1 = pokemon1.eff_stat("speed")
        speed2 = pokemon2.eff_stat("speed")
        
        item1 = pokemon1.volatile.get("held_item", "")
        item2 = pokemon2.volatile.get("held_item", "")
        
        if item1 == "quick_claw" and random.random() < 0.2:
            return ["first", "second"]
        if item2 == "quick_claw" and random.random() < 0.2:
            return ["second", "first"]
        
        if self.field.get("trick_room", 0) > 0:
            if speed1 != speed2:
                return ["first", "second"] if speed1 < speed2 else ["second", "first"]
        else:
            if speed1 != speed2:
                return ["first", "second"] if speed1 > speed2 else ["second", "first"]
        
        return random.choice([["first", "second"], ["second", "first"]])
    
    def _process_entry_hazards(self, pokemon: BattlePokemon, is_player: bool) -> List[str]:
        lines = []
        
        spikes_key = "spikes_player" if is_player else "spikes_wild"
        spikes_layers = self.field.get(spikes_key, 0)
        
        if spikes_layers > 0:
            if "flying" in pokemon.types or pokemon.get_effective_ability() == "levitate":
                return lines
            
            if pokemon.get_effective_ability() == "magic_guard":
                return lines
            
            damage_ratios = {1: 0.125, 2: 0.1666, 3: 0.25}
            damage = max(1, int(pokemon.stats["hp"] * damage_ratios.get(spikes_layers, 0.125)))
            
            actual = pokemon.take_damage(damage, ignore_substitute=True)
            lines.append(f"⚠️ {pokemon.display_name} foi ferido por Spikes! ({actual} de dano)")
        
        return lines
    
    async def _fetch_move(self, move_id: str) -> MoveData:
        from __main__ import pm
        
        key = _slug(move_id)
        if not key:
            raise ValueError("Invalid move_id")
        
        if key in self.move_cache:
            return self.move_cache[key]
        
        move_data = await pm.service.get_move(key)
        normalized = _normalize_move(move_data)
        self.move_cache[key] = normalized
        
        from data.effect_mapper import effect_mapper
        effect_entries = getattr(move_data, "effect_entries", [])
        
        for entry in effect_entries:
            if entry.language.name == "en":
                self.effect_cache[key] = effect_mapper.get(entry.short_effect, {})
                break
        
        if key not in self.effect_cache:
            self.effect_cache[key] = {}
        
        return normalized
    
    def _get_effect_data(self, move_id: str) -> Dict[str, Any]:
        return self.effect_cache.get(_slug(move_id), {})
    
    def _check_move_restrictions(self, user: BattlePokemon, move_id: str, move_data: MoveData) -> Optional[str]:
        if user.volatile.get("must_recharge"):
            user.volatile["must_recharge"] = False
            return f"⚡ {user.display_name} precisa recarregar!"
        
        if user.volatile.get("flinch"):
            return f"😰 {user.display_name} se encolheu!"
        
        if user.volatile.get("disable", 0) > 0:
            disabled_move = user.volatile.get("disable_move")
            if disabled_move and _slug(disabled_move) == _slug(move_id):
                return f"🚫 {move_data.name} está desabilitado!"
        
        if user.volatile.get("encore", 0) > 0:
            encore_move = user.volatile.get("encore_move")
            if encore_move and _slug(encore_move) != _slug(move_id):
                return f"👏 {user.display_name} deve usar {encore_move}!"
        
        if user.volatile.get("taunt", 0) > 0 and move_data.dmg_class == "status":
            return f"😤 {user.display_name} está provocado e não pode usar movimentos de status!"
        
        if user.volatile.get("torment"):
            last_move = user.volatile.get("torment_last_move")
            if last_move and _slug(last_move) == _slug(move_id):
                return f"😈 {user.display_name} não pode repetir o mesmo movimento!"
        
        if user.volatile.get("imprisoned_moves"):
            if _slug(move_id) in user.volatile["imprisoned_moves"]:
                return f"🔒 {move_data.name} está selado!"
        
        if user.volatile.get("attract") or user.volatile.get("attracted"):
            if random.random() < 0.5:
                return f"💕 {user.display_name} está apaixonado e não consegue atacar!"
        
        effect_data = self._get_effect_data(move_id)
        if user.volatile.get("heal_block", 0) > 0:
            if effect_data.get("type") == "heal" or "heal" in str(move_data.name).lower():
                return f"🚫 {user.display_name} não pode usar movimentos de cura!"
        
        return None
    
    async def _execute_move(
        self,
        user: BattlePokemon,
        target: BattlePokemon,
        move_data: MoveData,
        move_id: Optional[str]
    ) -> List[str]:
        is_struggle = move_id == "__struggle__"
        
        if move_id and not is_struggle:
            pp = user.get_pp(move_id)
            if pp is not None and pp <= 0:
                return [f"❌ {user.display_name} não tem PP para {move_data.name}!"]
            user.dec_pp(move_id)
            user.volatile["last_move_used"] = move_id
            user.volatile["last_move_type"] = move_data.type_name.lower()
            
            if user.volatile.get("torment"):
                user.volatile["torment_last_move"] = move_id
        
        effect_data = self._get_effect_data(move_id or "tackle")
        
        is_multi_target = TargetingSystem.is_multi_target_move(effect_data, move_data.name)
        
        if not is_multi_target:
            redirect_target = TargetingSystem.get_redirect_target(
                allies=self.battle_context.get_opponents(user),
                original_target=target,
                is_single_target=True
            )
            
            if redirect_target and redirect_target != target:
                target = redirect_target
                return [f"🎯 {target.display_name} atraiu o ataque!"] + await self._execute_move(user, target, move_data, move_id)
        
        if target.volatile.get("protect") and move_data.dmg_class != "status":
            return [BattleMessages.protected(target.display_name)]
        
        if target.volatile.get("kings_shield") and move_data.dmg_class != "status":
            if effect_data.get("makes_contact"):
                user.modify_stat_stage("atk", -1)
                return [
                    BattleMessages.protected(target.display_name),
                    f"   └─ ⚔️ Ataque de {user.display_name} foi reduzido pelo contato!"
                ]
            return [BattleMessages.protected(target.display_name)]
        
        if target.volatile.get("spiky_shield") and move_data.dmg_class != "status":
            if effect_data.get("makes_contact"):
                damage = max(1, user.stats["hp"] // 8)
                user.take_damage(damage, ignore_substitute=True)
                return [
                    BattleMessages.protected(target.display_name),
                    f"   └─ 🔱 {user.display_name} foi machucado pelos espinhos! ({damage} de dano)"
                ]
            return [BattleMessages.protected(target.display_name)]
        
        if target.volatile.get("baneful_bunker") and move_data.dmg_class != "status":
            if effect_data.get("makes_contact"):
                result = StatusHandler.apply_status_effect(user, "poison")
                return [
                    BattleMessages.protected(target.display_name),
                    result if result else f"   └─ ☠️ {user.display_name} foi envenenado!"
                ]
            return [BattleMessages.protected(target.display_name)]
        
        if target.is_semi_invulnerable():
            two_turn_move = target.volatile.get("two_turn_move", "")
            
            if two_turn_move == "dig" and _slug(move_id) in ["earthquake", "magnitude"]:
                pass
            elif two_turn_move in ["fly", "bounce"] and _slug(move_id) in ["gust", "twister"]:
                pass
            elif two_turn_move == "dive" and _slug(move_id) in ["surf", "whirlpool"]:
                pass
            elif two_turn_move == "fly" and _slug(move_id) == "thunder":
                pass
            else:
                return [f"💨 {user.display_name} errou! {target.display_name} está inacessível!"]
        
        if move_data.accuracy is not None and not effect_data.get("bypass_accuracy", False):
            accuracy = move_data.accuracy
            
            if user.volatile.get("mind_reader_target") == target:
                accuracy = None
                user.volatile["mind_reader_target"] = None
                user.volatile["mind_reader_turns"] = 0
            
            user_ability = user.get_effective_ability()
            target_ability = target.get_effective_ability()
            if user_ability == "no_guard" or target_ability == "no_guard":
                accuracy = None
            
            if accuracy is not None:
                acc_stage = user.stages.get("accuracy", 0)
                eva_stage = target.stages.get("evasion", 0)
                
                if target.volatile.get("foresight") or target.volatile.get("identified") or target.volatile.get("miracle_eye"):
                    eva_stage = min(0, eva_stage)
                
                if user_ability == "keen_eye":
                    eva_stage = 0
                if user_ability == "unaware":
                    acc_stage = 0
                    eva_stage = 0
                
                if self.field.get("gravity", 0) > 0:
                    acc_stage += 2
                
                stage_diff = acc_stage - eva_stage
                stage_multiplier = max(3, 3 + stage_diff) / max(3, 3 - stage_diff)
                
                final_accuracy = accuracy * stage_multiplier
                
                if random.randint(1, 100) > int(final_accuracy):
                    return [BattleMessages.miss(user.display_name, move_data.name)]
        
        if move_data.dmg_class == "status" or move_data.power == 0:
            return await self._apply_status_move(user, target, move_data, effect_data)
        
        return await self._apply_damage_move(user, target, move_data, effect_data, is_struggle)
    
    async def _apply_damage_move(
        self,
        user: BattlePokemon,
        target: BattlePokemon,
        move_data: MoveData,
        effect_data: Dict[str, Any],
        is_struggle: bool
    ) -> List[str]:
        lines = []
        multi_hit = effect_data.get("multi_hit", {})
        hits = 1
        
        if multi_hit:
            min_hits = multi_hit.get("min", 1)
            max_hits = multi_hit.get("max", 1)
            if max_hits > 1:
                if user.get_effective_ability() == "skill_link":
                    hits = max_hits
                else:
                    roll = random.random()
                    if roll < 0.35:
                        hits = 2
                    elif roll < 0.70:
                        hits = 3
                    elif roll < 0.85:
                        hits = 4
                    else:
                        hits = 5
        
        total_damage = 0
        first_multiplier, first_crit = 1.0, False
        actual_hits = 0
        
        for i in range(hits):
            if target.fainted:
                break
            
            damage, multiplier, is_crit = await self.damage_calculator.calculate(
                user, target, move_data, effect_data
            )
            
            if i == 0:
                first_multiplier, first_crit = multiplier, is_crit
            
            if multiplier == 0.0 and not is_struggle:
                return [BattleMessages.no_effect(user.display_name, move_data.name)]
            
            if target.status["name"] == "freeze" and move_data.type_name.lower() == "fire" and damage > 0:
                target.status = {"name": None, "counter": 0}
                lines.append(f"🔥 {target.display_name} descongelou!")
            
            if effect_data.get("wake_up_slap") and target.status["name"] == "sleep":
                target.status = {"name": None, "counter": 0}
                lines.append(f"👋 {target.display_name} acordou!")
            
            if effect_data.get("smelling_salts") and target.status["name"] == "paralysis":
                target.status = {"name": None, "counter": 0}
                lines.append(f"👃 {target.display_name} se recuperou da paralisia!")
            
            actual_damage = target.take_damage(damage)
            total_damage += actual_damage
            actual_hits += 1
            
            target.volatile["last_damage_taken"] = actual_damage
            target.volatile["was_hit_this_turn"] = True
            
            if move_data.dmg_class == "physical":
                target.volatile["last_physical_damage"] = actual_damage
            elif move_data.dmg_class == "special":
                target.volatile["last_special_damage"] = actual_damage
            
            if target.fainted:
                if target.volatile.get("destiny_bond"):
                    user.current_hp = 0
                    lines.append(f"👻 Destiny Bond ativado! {user.display_name} também caiu!")
                
                if target.volatile.get("grudge") and not is_struggle:
                    last_move_used = user.volatile.get("last_move_used")
                    if last_move_used:
                        for move in user.moves:
                            if move.get("id") == last_move_used:
                                move["pp"] = 0
                                lines.append(f"👻 Grudge ativou! PP de {move_data.name} foi drenado!")
                                break
                
                break
        
        if is_struggle:
            lines.insert(0, f"💢 {user.display_name} não tem PP!")
            lines.insert(1, f"Usou **Struggle**! ({total_damage} de dano)")
        else:
            lines.insert(0, BattleMessages.damage(user.display_name, move_data.name, total_damage))
        
        detail_line = BattleMessages.details(actual_hits if actual_hits > 1 else None, first_crit, first_multiplier)
        if detail_line:
            lines.insert(1, detail_line)
        
        if target.fainted:
            lines.append(BattleMessages.fainted(target.display_name))
        
        recoil_damage = self._calculate_recoil(total_damage, effect_data, is_struggle, user)
        if recoil_damage:
            lines.append(recoil_damage)
        
        drain_healing = self._calculate_drain(total_damage, effect_data, user)
        if drain_healing:
            lines.append(drain_healing)
        
        if effect_data.get("recharge"):
            user.volatile["must_recharge"] = True
        
        self._update_move_counters(user, move_data, effect_data, did_hit=True)
        
        for effect in effect_data.get("effects", []):
            effect_results = self.effect_handler.apply_effect(user, target, effect, total_damage, move_data)
            if effect_results:
                lines.extend(effect_results)
        
        if user.volatile.get("rage") or user.volatile.get("rage_active"):
            if total_damage > 0:
                user.modify_stat_stage("atk", 1)
                lines.append(f"   └─ 😡 Ataque de {user.display_name} aumentou pela Rage!")
        
        return lines
    
    def _update_move_counters(
        self, 
        user: BattlePokemon, 
        move_data: MoveData, 
        effect_data: Dict[str, Any],
        did_hit: bool
    ) -> None:
        move_id = _slug(move_data.name)
        
        if move_id == "rollout":
            if did_hit:
                user.volatile["rollout_count"] = user.volatile.get("rollout_count", 0) + 1
            else:
                user.volatile["rollout_count"] = 0
        
        if move_id in ["ice_ball", "iceball"]:
            if did_hit:
                user.volatile["ice_ball_count"] = user.volatile.get("ice_ball_count", 0) + 1
            else:
                user.volatile["ice_ball_count"] = 0
        
        if move_id in ["fury_cutter", "furycutter"]:
            if did_hit:
                user.volatile["fury_cutter_count"] = user.volatile.get("fury_cutter_count", 0) + 1
            else:
                user.volatile["fury_cutter_count"] = 0
        
        if move_id in ["echoed_voice", "echoedvoice"]:
            if did_hit:
                user.volatile["echoed_voice_count"] = user.volatile.get("echoed_voice_count", 0) + 1
            else:
                user.volatile["echoed_voice_count"] = 0
        
        user.volatile["last_move_hit"] = did_hit
    
    def _calculate_recoil(
        self,
        total_damage: int,
        effect_data: Dict[str, Any],
        is_struggle: bool,
        user: BattlePokemon
    ) -> Optional[str]:
        if user.get_effective_ability() == "rock_head" and not is_struggle:
            return None
        
        if is_struggle:
            recoil = max(1, int(user.stats["hp"] * BattleConstants.STRUGGLE_RECOIL_RATIO))
            actual = user.take_damage(recoil, ignore_substitute=True)
            return BattleMessages.recoil(user.display_name, actual)
        
        if effect_data.get("recoil"):
            recoil = max(1, int(total_damage * effect_data["recoil"]))
            actual = user.take_damage(recoil, ignore_substitute=True)
            return BattleMessages.recoil(user.display_name, actual)
        
        return None
    
    def _calculate_drain(
        self,
        total_damage: int,
        effect_data: Dict[str, Any],
        user: BattlePokemon
    ) -> Optional[str]:
        if effect_data.get("drain"):
            drain = max(1, int(total_damage * effect_data["drain"]))
            
            if user.volatile.get("held_item") == "big_root":
                drain = int(drain * 1.3)
            
            actual = user.heal(drain)
            if actual > 0:
                return BattleMessages.drain(user.display_name, actual)
        return None
    
    async def _apply_status_move(
        self,
        user: BattlePokemon,
        target: BattlePokemon,
        move_data: MoveData,
        effect_data: Dict[str, Any]
    ) -> List[str]:
        lines = [f"✨ {user.display_name} usou **{move_data.name}**!"]
        has_effect = False
        
        if target.volatile.get("magic_coat"):
            lines.append(f"   └─ ✨ {target.display_name} refletiu com Magic Coat!")
            user, target = target, user
        
        if effect_data.get("target") == "self" and target.volatile.get("snatch"):
            lines.append(f"   └─ 🎯 {target.display_name} roubou o movimento com Snatch!")
            user, target = target, user
        
        effects = effect_data.get("effects", [])
        
        if effects:
            for effect in effects:
                result = self.effect_handler.apply_effect(user, target, effect, 0, move_data)
                if result:
                    has_effect = True
                    lines.extend(result)
                    
                    if effect.get("type") == "transform":
                        self.must_redraw_image = True
        elif move_data.stat_changes:
            for stat_change in move_data.stat_changes:
                stat, stages = stat_change[0], stat_change[1]
                is_self_buff = stat_change[2] if len(stat_change) > 2 else (stages > 0)
                
                affected_pokemon = user if is_self_buff else target
                effect = {"type": "stat_change", "stat": stat, "stages": stages}
                result = self.effect_handler.apply_effect(user, affected_pokemon, effect, 0, move_data)
                if result:
                    has_effect = True
                    lines.extend(result)
        
        if not has_effect:
            lines.append(BattleMessages.failed())
        
        return lines
    
    async def _execute_turn_action(
        self,
        is_player_turn: bool,
        move_id: str,
        move_data: MoveData,
        user: BattlePokemon,
        target: BattlePokemon
    ) -> List[str]:
        user.volatile["moved_this_turn"] = False
        
        action_blocked, pre_messages = StatusHandler.check_pre_action(user)
        if action_blocked:
            return pre_messages
        
        confusion_blocked, confusion_messages = StatusHandler.check_confusion(user)
        if confusion_blocked:
            return pre_messages + confusion_messages
        
        restriction_msg = self._check_move_restrictions(user, move_id, move_data)
        if restriction_msg:
            return pre_messages + confusion_messages + [restriction_msg]
        
        move_result = await self._execute_move(user, target, move_data, move_id)
        
        user.volatile["moved_this_turn"] = True
        
        return pre_messages + confusion_messages + move_result
    
    def _get_move_priority(self, move_data: MoveData, user: BattlePokemon) -> int:
        base_priority = move_data.priority
        
        priority_map = {
            "follow_me": 2,
            "followme": 2,
            "rage_powder": 2,
            "ragepowder": 2,
            "spotlight": 3,
            "helping_hand": 5,
            "helpinghand": 5,
            "protect": 4,
            "detect": 4,
            "quick_guard": 3,
            "quickguard": 3,
            "wide_guard": 3,
            "wideguard": 3,
            "fake_out": 3,
            "fakeout": 3,
            "extremespeed": 2,
            "aqua_jet": 1,
            "aquajet": 1,
            "mach_punch": 1,
            "machpunch": 1,
            "bullet_punch": 2,
            "bulletpunch": 2,
            "sucker_punch": 1,
            "suckerpunch": 1
        }
        
        move_slug = move_data.name.lower().replace(" ", "_").replace("-", "_")
        if move_slug in priority_map:
            base_priority = priority_map[move_slug]
        
        ability = user.get_effective_ability()
        
        if ability == "prankster" and move_data.dmg_class == "status":
            base_priority += 1
        
        if ability == "gale_wings" and move_data.type_name.lower() == "flying":
            if user.current_hp == user.stats["hp"]:
                base_priority += 1
        
        if user.volatile.get("stall_counter", 0) > 0 and move_slug in ["protect", "detect", "endure"]:
            return -7
        
        return base_priority
    
    async def _process_end_of_turn(self, participants: List[BattlePokemon]) -> None:
        for pokemon in participants:
            if pokemon.fainted:
                continue
            
            pokemon.volatile["follow_me"] = False
            pokemon.volatile["rage_powder"] = False
            pokemon.volatile["spotlight"] = False
            pokemon.volatile["wide_guard"] = False
            pokemon.volatile["quick_guard"] = False
            pokemon.volatile["protect"] = False
            pokemon.volatile["endure"] = False
            pokemon.volatile["kings_shield"] = False
            pokemon.volatile["spiky_shield"] = False
            pokemon.volatile["baneful_bunker"] = False
            pokemon.volatile["magic_coat"] = False
            pokemon.volatile["snatch"] = False
            pokemon.volatile["was_hit_this_turn"] = False
            pokemon.volatile["moved_this_turn"] = False
            pokemon.volatile["last_damage_taken"] = 0
        
        for pokemon in participants:
            if pokemon.fainted:
                continue
            
            if pokemon.volatile.get("leech_seed"):
                seeder = pokemon.volatile.get("leech_seed_by")
                if seeder and not seeder.fainted:
                    drain = max(1, pokemon.stats["hp"] // 8)
                    actual_drain = pokemon.take_damage(drain, ignore_substitute=True)
                    actual_heal = seeder.heal(actual_drain)
                    self.lines.append(
                        f"🌱 {pokemon.display_name} perdeu {actual_drain} HP para Leech Seed!"
                    )
                    if actual_heal > 0:
                        self.lines.append(f"   └─ {seeder.display_name} recuperou {actual_heal} HP!")
            
            if pokemon.volatile.get("bind", 0) > 0:
                bind_damage = pokemon.volatile.get("bind_damage", pokemon.stats["hp"] // 16)
                actual = pokemon.take_damage(bind_damage, ignore_substitute=True)
                bind_type = pokemon.volatile.get("bind_type") or "Bind"
                bind_name = bind_type.replace("_", " ").title()
                self.lines.append(
                    f"🎯 {pokemon.display_name} sofreu {actual} de dano de {bind_name}!"
                )
            
            if pokemon.volatile.get("ingrain"):
                heal = max(1, pokemon.stats["hp"] // 16)
                actual = pokemon.heal(heal)
                if actual > 0:
                    self.lines.append(
                        f"🌿 {pokemon.display_name} recuperou {actual} HP com Ingrain!"
                    )
            
            if pokemon.volatile.get("aqua_ring"):
                heal = max(1, pokemon.stats["hp"] // 16)
                actual = pokemon.heal(heal)
                if actual > 0:
                    self.lines.append(
                        f"💧 {pokemon.display_name} recuperou {actual} HP com Aqua Ring!"
                    )
            
            if pokemon.volatile.get("wish", 0) > 0:
                pokemon.volatile["wish"] -= 1
                if pokemon.volatile["wish"] == 0:
                    wish_hp = pokemon.volatile.get("wish_hp", pokemon.stats["hp"] // 2)
                    actual = pokemon.heal(wish_hp)
                    if actual > 0:
                        self.lines.append(
                            f"⭐ O desejo de {pokemon.display_name} se realizou! (+{actual} HP)"
                        )
            
            if pokemon.volatile.get("nightmare") and pokemon.status.get("name") == "sleep":
                damage = max(1, pokemon.stats["hp"] // 4)
                actual = pokemon.take_damage(damage, ignore_substitute=True)
                self.lines.append(
                    f"😱 {pokemon.display_name} está tendo pesadelos! ({actual} de dano)"
                )
            
            if pokemon.volatile.get("curse"):
                damage = max(1, pokemon.stats["hp"] // 4)
                actual = pokemon.take_damage(damage, ignore_substitute=True)
                self.lines.append(
                    f"👻 {pokemon.display_name} foi amaldiçoado! ({actual} de dano)"
                )
            
            if pokemon.volatile.get("perish_count", -1) >= 0:
                pokemon.volatile["perish_count"] -= 1
                count = pokemon.volatile["perish_count"]
                
                if count == 0:
                    pokemon.current_hp = 0
                    self.lines.append(
                        f"🎵 {pokemon.display_name} desmaiou pela Perish Song!"
                    )
                elif count > 0:
                    self.lines.append(
                        f"🎵 Perish count de {pokemon.display_name}: {count}"
                    )
        
        for pokemon in participants:
            if pokemon.fainted:
                continue
            
            if pokemon.volatile.get("bind", 0) > 0:
                pokemon.volatile["bind"] -= 1
                if pokemon.volatile["bind"] <= 0:
                    pokemon.volatile["bind"] = 0
                    pokemon.volatile["bind_by"] = None
                    self.lines.append(f"   └─ {pokemon.display_name} se libertou!")
            
            if pokemon.volatile.get("yawn", 0) > 0:
                pokemon.volatile["yawn"] += 1
                if pokemon.volatile["yawn"] >= 2:
                    pokemon.volatile["yawn"] = 0
                    result = StatusHandler.apply_status_effect(pokemon, "sleep")
                    if result:
                        self.lines.append(result)
            
            for key in ["encore", "disable", "taunt", "uproar", "magnet_rise", "telekinesis", "heal_block", "embargo"]:
                if pokemon.volatile.get(key, 0) > 0:
                    pokemon.volatile[key] -= 1
                    if pokemon.volatile[key] <= 0:
                        effect_names = {
                            "encore": "Encore",
                            "taunt": "Taunt",
                            "uproar": "Uproar"
                        }
                        if key in effect_names:
                            self.lines.append(
                                f"   └─ {effect_names[key]} de {pokemon.display_name} acabou!"
                            )
            
            for key in ["light_screen", "reflect", "safeguard", "mist"]:
                if pokemon.volatile.get(key, 0) > 0:
                    pokemon.volatile[key] -= 1
                    if pokemon.volatile[key] <= 0:
                        effect_names = {
                            "light_screen": "Light Screen",
                            "reflect": "Reflect",
                            "safeguard": "Safeguard",
                            "mist": "Mist"
                        }
                        self.lines.append(
                            f"   └─ {effect_names[key]} de {pokemon.display_name} acabou!"
                        )
    
    async def _process_weather_effects(self, participants: List[BattlePokemon]) -> None:
        if not self.weather["type"] or self.weather["turns"] <= 0:
            return
        
        self.weather["turns"] -= 1
        
        if self.weather["turns"] == 0:
            self.lines.append("🌤️ O clima voltou ao normal!")
            self.weather["type"] = None
            return
        
        weather_type = self.weather["type"]
        
        if weather_type == "sandstorm":
            for pokemon in participants:
                if pokemon.fainted:
                    continue
                
                types = pokemon.get_effective_types()
                ability = pokemon.get_effective_ability()
                
                if any(t in types for t in ["rock", "ground", "steel"]):
                    continue
                if ability in ["sand_veil", "sand_rush", "sand_force", "overcoat", "magic_guard"]:
                    continue
                
                damage = max(1, int(pokemon.stats["hp"] * BattleConstants.SANDSTORM_DAMAGE_RATIO))
                actual = pokemon.take_damage(damage, ignore_substitute=True)
                self.lines.append(
                    f"🌪️ {pokemon.display_name} sofreu {actual} de dano da tempestade de areia!"
                )
        
        elif weather_type == "hail":
            for pokemon in participants:
                if pokemon.fainted:
                    continue
                
                types = pokemon.get_effective_types()
                ability = pokemon.get_effective_ability()
                
                if "ice" in types:
                    continue
                if ability in ["snow_cloak", "ice_body", "overcoat", "magic_guard"]:
                    continue
                
                damage = max(1, int(pokemon.stats["hp"] * BattleConstants.HAIL_DAMAGE_RATIO))
                actual = pokemon.take_damage(damage, ignore_substitute=True)
                self.lines.append(
                    f"❄️ {pokemon.display_name} sofreu {actual} de dano do granizo!"
                )
                
                if ability == "ice_body":
                    heal = max(1, pokemon.stats["hp"] // 16)
                    actual_heal = pokemon.heal(heal)
                    if actual_heal > 0:
                        self.lines.append(
                            f"   └─ Ice Body curou {actual_heal} HP!"
                        )
    
    async def _process_field_effects(self) -> None:
        if self.field.get("trick_room", 0) > 0:
            self.field["trick_room"] -= 1
            if self.field["trick_room"] <= 0:
                self.field["trick_room"] = 0
                self.lines.append("🔄 Trick Room acabou!")
        
        if self.field.get("gravity", 0) > 0:
            self.field["gravity"] -= 1
            if self.field["gravity"] <= 0:
                self.field["gravity"] = 0
                self.lines.append("⬇️ Gravity voltou ao normal!")
        
        if self.field.get("mud_sport", 0) > 0:
            self.field["mud_sport"] -= 1
        
        if self.field.get("water_sport", 0) > 0:
            self.field["water_sport"] -= 1
