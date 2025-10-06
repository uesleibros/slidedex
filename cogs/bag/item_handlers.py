from typing import Dict, Optional, Tuple
from pokemon_sdk.calculations import calculate_max_hp
from .item_effects import get_item_effect, ItemEffect

class ItemHandler:
    def __init__(self, toolkit, pm):
        self.toolkit = toolkit
        self.pm = pm
    
    async def use_healing_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
        effect = get_item_effect(item_id)
        if not effect or effect.type not in ["heal", "berry"]:
            raise ValueError("Item não é curativo")
        
        max_hp = calculate_max_hp(
            pokemon["base_stats"]["hp"],
            pokemon["ivs"]["hp"],
            pokemon["evs"]["hp"],
            pokemon["level"]
        )
        current_hp = pokemon.get("current_hp", max_hp)
        
        if current_hp >= max_hp:
            raise ValueError("HP já está cheio")
        
        if effect.amount:
            heal_amount = effect.amount
        elif effect.percent:
            heal_amount = int(max_hp * effect.percent)
        else:
            raise ValueError("Efeito de cura inválido")
        
        new_hp = min(current_hp + heal_amount, max_hp)
        healed = new_hp - current_hp
        
        self.toolkit.set_current_hp(uid, pokemon_id, new_hp)
        self.toolkit.remove_item(uid, item_id, 1)
        
        if item_id in ["energy-powder", "energy-root"]:
            if item_id == "energy-powder":
                self.toolkit.decrease_happiness_energy_powder(uid, pokemon_id)
            else:
                self.toolkit.decrease_happiness_energy_root(uid, pokemon_id)
        elif effect.type == "berry":
            self.toolkit.increase_happiness_berry(uid, pokemon_id)
        
        return {
            "healed": healed,
            "current_hp": new_hp,
            "max_hp": max_hp
        }
    
    async def use_revive_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
        effect = get_item_effect(item_id)
        if not effect or effect.type != "revive":
            raise ValueError("Item não é revive")
        
        current_hp = pokemon.get("current_hp", 1)
        if current_hp > 0:
            raise ValueError("Pokémon não está desmaiado")
        
        max_hp = calculate_max_hp(
            pokemon["base_stats"]["hp"],
            pokemon["ivs"]["hp"],
            pokemon["evs"]["hp"],
            pokemon["level"]
        )
        
        restored_hp = int(max_hp * effect.percent)
        
        self.toolkit.set_current_hp(uid, pokemon_id, restored_hp)
        self.toolkit.remove_item(uid, item_id, 1)
        
        if item_id == "revival-herb":
            self.toolkit.decrease_happiness_revival_herb(uid, pokemon_id)
        
        return {
            "restored_hp": restored_hp,
            "max_hp": max_hp
        }
    
    async def use_pp_item(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict, move_slot: Optional[int] = None) -> Dict:
        effect = get_item_effect(item_id)
        if not effect or effect.type not in ["pp_restore", "pp_boost"]:
            raise ValueError("Item não restaura PP")
        
        moves = pokemon.get("moves", [])
        if not moves:
            raise ValueError("Pokémon não tem movimentos")
        
        if effect.type == "pp_restore":
            updated = False
            for move in moves:
                if effect.all_moves or move["pp"] < move["pp_max"]:
                    move["pp"] = min(move["pp"] + effect.amount, move["pp_max"])
                    updated = True
            
            if not updated:
                raise ValueError("PP já está no máximo")
            
            self.toolkit.set_moves(uid, pokemon_id, moves)
            self.toolkit.remove_item(uid, item_id, 1)
            
            return {"moves": moves}
        
        elif effect.type == "pp_boost":
            if len(moves) == 1:
                move_idx = 0
            elif move_slot and 1 <= move_slot <= len(moves):
                move_idx = move_slot - 1
            else:
                raise ValueError(f"Especifique o slot do movimento (1-{len(moves)})")
            
            move = moves[move_idx]
            current_pp_ups = move.get("pp_ups", 0)
            max_pp_ups = effect.amount if item_id == "pp-max" else 3
            
            if current_pp_ups >= max_pp_ups:
                raise ValueError("Movimento já está no máximo de PP Ups")
            
            boost_amount = move["pp_max"] // 5
            move["pp_max"] += boost_amount
            move["pp"] = min(move["pp"] + boost_amount, move["pp_max"])
            move["pp_ups"] = current_pp_ups + 1
            
            self.toolkit.set_moves(uid, pokemon_id, moves)
            self.toolkit.remove_item(uid, item_id, 1)
            
            return {"move": move, "move_name": move["id"]}
    
    async def use_vitamin(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Dict:
        effect = get_item_effect(item_id)
        if not effect or effect.type != "vitamin":
            raise ValueError("Item não é vitamina")
        
        current_evs = pokemon.get("evs", {})
        current_stat_ev = current_evs.get(effect.stat, 0)
        
        if current_stat_ev >= 100:
            raise ValueError(f"Limite de EVs (100) atingido para {effect.stat}")
        
        total_evs = sum(current_evs.values())
        if total_evs >= 510:
            raise ValueError("Limite total de EVs (510) atingido")
        
        ev_gain = min(10, 100 - current_stat_ev, 510 - total_evs)
        
        new_evs = current_evs.copy()
        new_evs[effect.stat] = current_stat_ev + ev_gain
        
        self.toolkit.set_evs(uid, pokemon_id, new_evs)
        self.toolkit.remove_item(uid, item_id, 1)
        self.toolkit.increase_happiness_vitamin(uid, pokemon_id)
        
        return {
            "stat": effect.stat,
            "ev_gain": ev_gain,
            "new_ev": new_evs[effect.stat],
            "total_evs": sum(new_evs.values())
        }
    
    async def use_evolution_stone(self, uid: str, pokemon_id: int, item_id: str, pokemon: Dict) -> Optional[Dict]:
        evolution_data = await self.pm.check_evolution(uid, pokemon_id, trigger="use-item")
        
        if not evolution_data or evolution_data.get("item") != item_id:
            raise ValueError("Pokémon não pode evoluir com este item")
        
        self.toolkit.remove_item(uid, item_id, 1)
        evolved = await self.pm.evolve_pokemon(uid, pokemon_id, evolution_data["species_id"])
        
        return {"evolved": evolved, "from_species": pokemon["species_id"]}
