import orjson
from pathlib import Path
from typing import Optional, Union, TypeAlias
from dataclasses import dataclass
from functools import lru_cache
import logging

Identifier: TypeAlias = Union[str, int]

@dataclass(frozen=True)
class DataPaths:
    BASE: Path = Path("data/api")
    POKEMON: Path = BASE / "pokemon.json"
    SPECIES: Path = BASE / "pokemon-species.json"
    MOVES: Path = BASE / "moves.json"
    ITEMS: Path = BASE / "items.json"
    EVOLUTION_CHAIN: Path = BASE / "evolution-chain.json"
    SPRITES: Path = BASE / "sprites"

@dataclass(frozen=True)
class SpriteVariant:
    orientation: str
    shiny: bool
    gender: Optional[str] = None
    
    def generate_filenames(self, pokemon_id: int) -> tuple[str, ...]:
        id_str = str(pokemon_id).zfill(3)
        base = f"{id_str}_{self.orientation}"
        
        if self.gender == "female":
            if self.shiny:
                return (f"{base}_shiny_female.png", f"{base}_shiny.png", f"{base}_default.png")
            return (f"{base}_female.png", f"{base}_default.png")
        
        if self.shiny:
            return (f"{base}_shiny.png", f"{base}_default.png")
        
        return (f"{base}_default.png",)

class APIService:
    DEFAULT_PP = 35
    DEFAULT_MOVE_LIMIT = 4
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._sprites_base = DataPaths.SPRITES
    
    @staticmethod
    @lru_cache(maxsize=4)
    def _load_json_raw(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()
    
    @staticmethod
    @lru_cache(maxsize=4)
    def _parse_and_index(path: str) -> tuple[dict, dict]:
        data = orjson.loads(APIService._load_json_raw(path))
        
        id_index = {}
        name_index = {}
        
        for item in data:
            item_id = item.get("id")
            item_name = item.get("name")
            
            if item_id is not None:
                id_index[item_id] = item
            if item_name is not None:
                name_index[item_name] = item
        
        return id_index, name_index
    
    @lru_cache(maxsize=1024)
    def _find_sprite_path(self, pokemon_id: int, orientation: str, is_shiny: bool, gender: Optional[str]) -> Optional[str]:
        variant = SpriteVariant(orientation, is_shiny, gender if gender == "female" else None)
        
        for filename in variant.generate_filenames(pokemon_id):
            sprite_path = self._sprites_base / filename
            if sprite_path.exists():
                return str(sprite_path)
        
        return None
    
    def get_pokemon_sprite(self, poke: dict) -> tuple[Optional[str], Optional[str]]:
        pokemon_id = int(poke["species_id"])
        gender = poke.get("gender", "").lower() if poke.get("gender") else None
        is_shiny = poke.get("is_shiny", False)
        
        gender_key = gender if gender == "female" else None
        
        front = self._find_sprite_path(pokemon_id, "front", is_shiny, gender_key)
        back = self._find_sprite_path(pokemon_id, "back", is_shiny, gender_key)
        
        return (front, back)
    
    def get_pokemon(self, identifier: Identifier) -> Optional[dict]:
        id_index, name_index = self._parse_and_index(str(DataPaths.POKEMON))
        
        if isinstance(identifier, int):
            return id_index.get(identifier)
        
        if isinstance(identifier, str):
            if identifier.isdigit():
                return id_index.get(int(identifier))
            return name_index.get(identifier.lower())
        
        return None
    
    def get_move(self, identifier: Identifier) -> Optional[dict]:
        id_index, name_index = self._parse_and_index(str(DataPaths.MOVES))
        
        if isinstance(identifier, int):
            return id_index.get(identifier)
        
        if isinstance(identifier, str):
            if identifier.isdigit():
                return id_index.get(int(identifier))
            return name_index.get(identifier.lower())
        
        return None
    
    def get_item(self, identifier: Identifier) -> Optional[dict]:
        id_index, name_index = self._parse_and_index(str(DataPaths.ITEMS))
        
        if isinstance(identifier, int):
            return id_index.get(identifier)
        
        if isinstance(identifier, str):
            if identifier.isdigit():
                return id_index.get(int(identifier))
            return name_index.get(identifier.lower())
        
        return None
    
    @lru_cache(maxsize=256)
    def get_species(self, species_id: int) -> Optional[dict]:
        id_index, _ = self._parse_and_index(str(DataPaths.SPECIES))
        species = id_index.get(species_id)
        
        if species:
            self._inject_evolution_chain_id(species)
        
        return species
    
    def get_all_species(self, start: int = 1, end: int = 386) -> list[dict]:
        id_index, _ = self._parse_and_index(str(DataPaths.SPECIES))
        
        results = []
        for species_id in range(start, end + 1):
            species = id_index.get(species_id)
            if species:
                self._inject_evolution_chain_id(species)
                results.append(species)
        
        return results
    
    @lru_cache(maxsize=128)
    def get_evolution_chain(self, chain_id: int) -> Optional[dict]:
        id_index, _ = self._parse_and_index(str(DataPaths.EVOLUTION_CHAIN))
        return id_index.get(chain_id)
    
    @staticmethod
    def get_base_stats(poke: dict) -> dict[str, int]:
        return {stat["stat"]["name"]: stat["base_stat"] for stat in poke["stats"]}
    
    def get_level_up_moves(
        self, 
        poke: dict, 
        max_level: Optional[int] = None, 
        min_level: Optional[int] = None
    ) -> list[tuple[str, int]]:
        moves_data = {}
        
        for move_entry in poke["moves"]:
            if move_entry["move_learn_method"] != "level-up":
                continue
            
            level = move_entry.get("level_learned_at")
            if level is None:
                continue
            if max_level is not None and level > max_level:
                continue
            if min_level is not None and level <= min_level:
                continue
            
            move_name = move_entry["name"]
            if move_name not in moves_data or level > moves_data[move_name]:
                moves_data[move_name] = level
        
        return sorted(moves_data.items(), key=lambda x: (x[1], x[0]))
    
    def select_level_up_moves(self, poke: dict, level: int) -> list[dict]:
        moves = self.get_level_up_moves(poke, max_level=level)
        
        if not moves:
            return []
        
        last_moves = moves[-self.DEFAULT_MOVE_LIMIT:]
        return [self._create_move_data(move_name) for move_name, _ in last_moves]
    
    def get_future_moves(self, poke: dict, current_level: int) -> list[tuple[int, str]]:
        moves = self.get_level_up_moves(poke, min_level=current_level)
        return [(level, name) for name, level in moves]
    
    def _create_move_data(self, move_name: str) -> dict:
        move = self.get_move(move_name)
        pp = move["pp"] if move else self.DEFAULT_PP
        
        return {"id": move_name, "pp": pp, "pp_max": pp}
    
    def _inject_evolution_chain_id(self, species: dict) -> None:
        evo_chain = species.get("evolution_chain")
        if evo_chain and "url" in evo_chain and "id" not in evo_chain:
            evo_chain["id"] = int(evo_chain["url"].rstrip('/').split('/')[-1])
    
    @staticmethod
    def _extract_id_from_url(url: str) -> int:
        return int(url.rstrip('/').split('/')[-1])
