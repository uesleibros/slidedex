from typing import List, Optional, Dict

class PokemonRepository:
    def __init__(self, toolkit):
        self.tk = toolkit

    def add(self, owner_id: str, species_id: int, ivs: Dict, nature: str,
            ability: str, gender: str, shiny: bool, level: int,
            moves: List[Dict], on_party: bool, current_hp: int,
            held_item: Optional[str] = None, nickname: Optional[str] = None,
            name: Optional[str] = None,
            exp: int = 0) -> Dict:
        return self.tk.add_pokemon(
            owner_id=owner_id,
            species_id=species_id,
            ivs=ivs,
            nature=nature,
            ability=ability,
            gender=gender,
            shiny=shiny,
            level=level,
            moves=moves,
            on_party=on_party,
            current_hp=current_hp,
            held_item=held_item,
            nickname=nickname,
            name=name,
            exp=exp
        )

    def get(self, owner_id: str, pokemon_id: int) -> Dict:
        return self.tk.get_pokemon(owner_id, pokemon_id)

    def list(self, owner_id: str, on_party: Optional[bool] = None) -> List[Dict]:
        if on_party is None:
            return self.tk.list_pokemon_by_owner(owner_id)
        return self.tk.get_user_pokemon(owner_id, on_party=on_party)

    def move_to_party(self, owner_id: str, pokemon_id: int) -> Dict:
        return self.tk.move_to_party(owner_id, pokemon_id)

    def move_to_box(self, owner_id: str, pokemon_id: int) -> Dict:
        return self.tk.move_to_box(owner_id, pokemon_id)

    def set_current_hp(self, owner_id: str, pokemon_id: int, current_hp: int) -> Dict:
        self.tk.set_current_hp(owner_id, pokemon_id, current_hp)
        return self.tk.get_pokemon(owner_id, pokemon_id)

    def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> Dict:
        self.tk.set_moves(owner_id, pokemon_id, moves)
        return self.tk.get_pokemon(owner_id, pokemon_id)

    def restore_pp(self, owner_id: str, pokemon_id: int) -> Dict:
        self.tk.restore_pp(owner_id, pokemon_id)
        return self.tk.get_pokemon(owner_id, pokemon_id)

    def transfer(self, owner_id: str, pokemon_id: int, new_owner_id: str) -> Dict:
        return self.tk.transfer_pokemon(owner_id, pokemon_id, new_owner_id)

    def release(self, owner_id: str, pokemon_id: int) -> bool:
        return self.tk.release_pokemon(owner_id, pokemon_id)