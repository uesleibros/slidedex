from typing import Optional
from datetime import datetime
from sdk.database import Database
from sdk.constants import PARTY_LIMIT, MOVES_LIMIT, STAT_KEYS

class PokemonRepository:
    def __init__(self, db: Database):
        self.db = db
        self._index: dict[tuple[str, int], int] = {}
        self._rebuild_index()
    
    def _rebuild_index(self) -> None:
        self._index.clear()
        pokemon_list = self.db.get("pokemon")
        
        for i, p in enumerate(pokemon_list):
            key = (p["owner_id"], p["id"])
            self._index[key] = i
    
    def _get_index(self, owner_id: str, pokemon_id: int) -> int:
        key = (owner_id, pokemon_id)
        
        if key not in self._index:
            raise ValueError(f"Pokemon not found: {pokemon_id}")
        
        return self._index[key]
    
    def create(self, owner_id: str, data: dict) -> dict:
        pokemon_list = self.db.get("pokemon")
        users = self.db.get("users")
        
        user = users[owner_id]
        user["last_pokemon_id"] += 1
        pokemon_id = user["last_pokemon_id"]
        
        pokemon = {
            "id": pokemon_id,
            "owner_id": owner_id,
            "caught_at": datetime.utcnow().isoformat(),
            "current_hp": None,
            "on_party": False,
            "is_favorite": False,
            "evolution_blocked": False,
            "background": "lab",
            "moves": [],
            "evs": {k: 0 for k in STAT_KEYS},
            "status": {"name": None, "counter": 0},
            **data
        }
        
        pokemon_list.append(pokemon)
        self._index[(owner_id, pokemon_id)] = len(pokemon_list) - 1
        self.db.save()
        
        return pokemon.copy()
    
    def get(self, owner_id: str, pokemon_id: int) -> dict:
        idx = self._get_index(owner_id, pokemon_id)
        pokemon_list = self.db.get("pokemon")
        return pokemon_list[idx].copy()
    
    def update(self, owner_id: str, pokemon_id: int, updates: dict) -> dict:
        idx = self._get_index(owner_id, pokemon_id)
        pokemon_list = self.db.get("pokemon")
        
        pokemon_list[idx].update(updates)
        self.db.save()
        
        return pokemon_list[idx].copy()
    
    def delete(self, owner_id: str, pokemon_id: int) -> None:
        idx = self._get_index(owner_id, pokemon_id)
        pokemon_list = self.db.get("pokemon")
        
        del pokemon_list[idx]
        self._rebuild_index()
        self.db.save()
    
    def get_all_by_owner(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id]
    
    def get_party(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        party = [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and p.get("on_party", False)]
        party.sort(key=lambda p: p.get("party_pos", 999))
        return party
    
    def get_box(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and not p.get("on_party", False)]
    
    def count_party(self, owner_id: str) -> int:
        pokemon_list = self.db.get("pokemon")
        return sum(1 for p in pokemon_list if p["owner_id"] == owner_id and p.get("on_party", False))
    
    def can_add_to_party(self, owner_id: str) -> bool:
        return self.count_party(owner_id) < PARTY_LIMIT
    
    def move_to_party(self, owner_id: str, pokemon_id: int) -> dict:
        if not self.can_add_to_party(owner_id):
            raise ValueError(f"Party is full ({PARTY_LIMIT}/{PARTY_LIMIT})")
        
        return self.update(owner_id, pokemon_id, {"on_party": True})
    
    def move_to_box(self, owner_id: str, pokemon_id: int) -> dict:
        return self.update(owner_id, pokemon_id, {"on_party": False})
    
    def reorder_party(self, owner_id: str, order: list[int]) -> list[dict]:
        party = self.get_party(owner_id)
        current_ids = [p["id"] for p in party]
        
        if len(order) != len(current_ids):
            raise ValueError(f"Order length mismatch: got {len(order)}, expected {len(current_ids)}")
        
        if set(order) != set(current_ids):
            raise ValueError("Order IDs don't match current party")
        
        for pos, pid in enumerate(order, start=1):
            self.update(owner_id, pid, {"party_pos": pos})
        
        return [self.get(owner_id, pid) for pid in order]
    
    def swap_party_positions(self, owner_id: str, pos_a: int, pos_b: int) -> list[dict]:
        party = self.get_party(owner_id)
        
        if not (1 <= pos_a <= len(party) and 1 <= pos_b <= len(party)):
            raise ValueError(f"Invalid positions: {pos_a}, {pos_b} (party size: {len(party)})")
        
        ids = [p["id"] for p in party]
        ids[pos_a - 1], ids[pos_b - 1] = ids[pos_b - 1], ids[pos_a - 1]
        
        return self.reorder_party(owner_id, ids)
    
    def set_nickname(self, owner_id: str, pokemon_id: int, nickname: Optional[str]) -> dict:
        return self.update(owner_id, pokemon_id, {"nickname": nickname})
    
    def set_held_item(self, owner_id: str, pokemon_id: int, item_id: Optional[str]) -> dict:
        return self.update(owner_id, pokemon_id, {"held_item": item_id})
    
    def set_favorite(self, owner_id: str, pokemon_id: int, is_favorite: bool) -> dict:
        return self.update(owner_id, pokemon_id, {"is_favorite": is_favorite})
    
    def toggle_favorite(self, owner_id: str, pokemon_id: int) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        return self.set_favorite(owner_id, pokemon_id, not pokemon.get("is_favorite", False))
    
    def set_background(self, owner_id: str, pokemon_id: int, background: str) -> dict:
        return self.update(owner_id, pokemon_id, {"background": background})
    
    def set_shiny(self, owner_id: str, pokemon_id: int, is_shiny: bool) -> dict:
        return self.update(owner_id, pokemon_id, {"is_shiny": is_shiny})
    
    def set_level(self, owner_id: str, pokemon_id: int, level: int) -> dict:
        return self.update(owner_id, pokemon_id, {"level": max(1, min(level, 100))})
    
    def set_nature(self, owner_id: str, pokemon_id: int, nature: str) -> dict:
        return self.update(owner_id, pokemon_id, {"nature": nature})
    
    def set_ability(self, owner_id: str, pokemon_id: int, ability: str) -> dict:
        return self.update(owner_id, pokemon_id, {"ability": ability})
    
    def set_gender(self, owner_id: str, pokemon_id: int, gender: str) -> dict:
        return self.update(owner_id, pokemon_id, {"gender": gender})
    
    def set_hp(self, owner_id: str, pokemon_id: int, current_hp: Optional[int]) -> dict:
        return self.update(owner_id, pokemon_id, {"current_hp": current_hp})
    
    def set_status(self, owner_id: str, pokemon_id: int, status_name: Optional[str], counter: int = 0) -> dict:
        return self.update(owner_id, pokemon_id, {"status": {"name": status_name, "counter": counter}})
    
    def clear_status(self, owner_id: str, pokemon_id: int) -> dict:
        return self.set_status(owner_id, pokemon_id, None, 0)
    
    def set_happiness(self, owner_id: str, pokemon_id: int, happiness: int) -> dict:
        return self.update(owner_id, pokemon_id, {"happiness": max(0, min(happiness, 255))})
    
    def add_happiness(self, owner_id: str, pokemon_id: int, amount: int) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        new_happiness = max(0, min(pokemon.get("happiness", 70) + amount, 255))
        return self.set_happiness(owner_id, pokemon_id, new_happiness)
    
    def set_ivs(self, owner_id: str, pokemon_id: int, ivs: dict[str, int]) -> dict:
        return self.update(owner_id, pokemon_id, {"ivs": ivs})
    
    def set_evs(self, owner_id: str, pokemon_id: int, evs: dict[str, int]) -> dict:
        return self.update(owner_id, pokemon_id, {"evs": evs})
    
    def add_evs(self, owner_id: str, pokemon_id: int, ev_gains: dict[str, int]) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        current_evs = pokemon.get("evs", {k: 0 for k in STAT_KEYS})
        new_evs = {k: current_evs.get(k, 0) + ev_gains.get(k, 0) for k in STAT_KEYS}
        return self.set_evs(owner_id, pokemon_id, new_evs)
    
    def set_moves(self, owner_id: str, pokemon_id: int, moves: list[dict]) -> dict:
        if len(moves) > MOVES_LIMIT:
            raise ValueError(f"Too many moves: {len(moves)}/{MOVES_LIMIT}")
        return self.update(owner_id, pokemon_id, {"moves": moves})
    
    def add_move(self, owner_id: str, pokemon_id: int, move_id: str, pp: int, pp_max: int) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        moves = pokemon.get("moves", [])
        
        if len(moves) >= MOVES_LIMIT:
            raise ValueError(f"Move slots full ({MOVES_LIMIT}/{MOVES_LIMIT})")
        
        if any(m["id"] == move_id for m in moves):
            return pokemon
        
        moves.append({"id": move_id, "pp": pp, "pp_max": pp_max})
        return self.set_moves(owner_id, pokemon_id, moves)
    
    def remove_move(self, owner_id: str, pokemon_id: int, move_id: str) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        moves = [m for m in pokemon.get("moves", []) if m["id"] != move_id]
        return self.set_moves(owner_id, pokemon_id, moves)
    
    def replace_move(self, owner_id: str, pokemon_id: int, old_move_id: str, new_move_id: str, pp: int, pp_max: int) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        moves = pokemon.get("moves", [])
        
        for i, move in enumerate(moves):
            if move["id"] == old_move_id:
                moves[i] = {"id": new_move_id, "pp": pp, "pp_max": pp_max}
                break
        
        return self.set_moves(owner_id, pokemon_id, moves)
    
    def has_move(self, owner_id: str, pokemon_id: int, move_id: str) -> bool:
        pokemon = self.get(owner_id, pokemon_id)
        return any(m["id"] == move_id for m in pokemon.get("moves", []))
    
    def set_move_pp(self, owner_id: str, pokemon_id: int, move_id: str, pp: int) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        moves = pokemon.get("moves", [])
        
        for move in moves:
            if move["id"] == move_id:
                move["pp"] = max(0, min(pp, move["pp_max"]))
                break
        
        return self.set_moves(owner_id, pokemon_id, moves)
    
    def restore_pp(self, owner_id: str, pokemon_id: int, move_id: Optional[str] = None) -> dict:
        pokemon = self.get(owner_id, pokemon_id)
        moves = pokemon.get("moves", [])
        
        for move in moves:
            if move_id is None or move["id"] == move_id:
                move["pp"] = move["pp_max"]
        
        return self.set_moves(owner_id, pokemon_id, moves)
    
    def heal(self, owner_id: str, pokemon_id: int, max_hp: int) -> dict:
        self.restore_pp(owner_id, pokemon_id)
        self.clear_status(owner_id, pokemon_id)
        return self.set_hp(owner_id, pokemon_id, max_hp)
    
    def heal_party(self, owner_id: str) -> list[dict]:
        from sdk.calculations import StatCalculator
        
        party = self.get_party(owner_id)
        healed = []
        
        for pokemon in party:
            max_hp = StatCalculator.calculate_hp(
                pokemon["base_stats"]["hp"],
                pokemon["ivs"]["hp"],
                pokemon["evs"]["hp"],
                pokemon["level"]
            )
            healed.append(self.heal(owner_id, pokemon["id"], max_hp))
        
        return healed
    
    def block_evolution(self, owner_id: str, pokemon_id: int, blocked: bool = True) -> dict:
        return self.update(owner_id, pokemon_id, {"evolution_blocked": blocked})
    
    def is_evolution_blocked(self, owner_id: str, pokemon_id: int) -> bool:
        pokemon = self.get(owner_id, pokemon_id)
        return pokemon.get("evolution_blocked", False)
    
    def transfer(self, owner_id: str, pokemon_id: int, new_owner_id: str) -> dict:
        idx = self._get_index(owner_id, pokemon_id)
        pokemon_list = self.db.get("pokemon")
        users = self.db.get("users")
        
        pokemon = pokemon_list[idx]
        
        del self._index[(owner_id, pokemon_id)]
        
        new_user = users[new_owner_id]
        new_user["last_pokemon_id"] += 1
        new_id = new_user["last_pokemon_id"]
        
        pokemon["id"] = new_id
        pokemon["owner_id"] = new_owner_id
        pokemon["on_party"] = False
        pokemon["happiness"] = 70
        
        self._index[(new_owner_id, new_id)] = idx
        self.db.save()
        
        return pokemon.copy()
    
    def get_favorites(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and p.get("is_favorite", False)]
    
    def get_by_species(self, owner_id: str, species_id: int) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and p["species_id"] == species_id]
    
    def get_shinies(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and p.get("is_shiny", False)]
    
    def get_legendaries(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and p.get("is_legendary", False)]
    
    def get_mythicals(self, owner_id: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        return [p.copy() for p in pokemon_list if p["owner_id"] == owner_id and p.get("is_mythical", False)]
    
    def has_caught_species(self, owner_id: str, species_id: int) -> bool:
        pokemon_list = self.db.get("pokemon")
        return any(p["owner_id"] == owner_id and p["species_id"] == species_id for p in pokemon_list)
    
    def search(self, owner_id: str, query: str) -> list[dict]:
        pokemon_list = self.db.get("pokemon")
        query_lower = query.lower()
        results = []
        
        for p in pokemon_list:
            if p["owner_id"] != owner_id:
                continue
            
            if p.get("name") and query_lower in p["name"].lower():
                results.append(p.copy())
            elif p.get("nickname") and query_lower in p["nickname"].lower():
                results.append(p.copy())
        
        return results
    
    def count_stats(self, owner_id: str) -> dict:
        pokemon_list = self.db.get("pokemon")
        
        stats = {
            "total": 0,
            "party": 0,
            "box": 0,
            "favorites": 0,
            "shinies": 0,
            "legendaries": 0,
            "mythicals": 0
        }
        
        for p in pokemon_list:
            if p["owner_id"] != owner_id:
                continue
            
            stats["total"] += 1
            
            if p.get("on_party", False):
                stats["party"] += 1
            else:
                stats["box"] += 1
            
            if p.get("is_favorite", False):
                stats["favorites"] += 1
            if p.get("is_shiny", False):
                stats["shinies"] += 1
            if p.get("is_legendary", False):
                stats["legendaries"] += 1
            if p.get("is_mythical", False):
                stats["mythicals"] += 1
        
        return stats