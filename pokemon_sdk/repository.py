from typing import List, Optional, Dict
from .models import Pokemon

class PokemonRepository:
	def __init__(self, toolkit):
		self.tk = toolkit

	def add(self, owner_id: str, species_id: int, ivs: Dict, nature: str, ability: str, gender: str, shiny: bool, level: int, moves: List[Dict], on_party: bool, current_hp: int, held_item: Optional[str] = None, nickname: Optional[str] = None, exp: int = 0) -> Pokemon:
		d = self.tk.add_pokemon(
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
			exp=exp
		)
		return Pokemon.from_dict(d)

	def get(self, owner_id: str, pokemon_id: int) -> Pokemon:
		d = self.tk.get_pokemon(owner_id, pokemon_id)
		return Pokemon.from_dict(d)

	def list(self, owner_id: str, on_party: Optional[bool] = None) -> List[Pokemon]:
		if on_party is None:
			data = self.tk.list_pokemon_by_owner(owner_id)
		else:
			data = self.tk.get_user_pokemon(owner_id, on_party=on_party)
		return [Pokemon.from_dict(x) for x in data]

	def move_to_party(self, owner_id: str, pokemon_id: int) -> Pokemon:
		d = self.tk.move_to_party(owner_id, pokemon_id)
		return Pokemon.from_dict(d)

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Pokemon:
		d = self.tk.move_to_box(owner_id, pokemon_id)
		return Pokemon.from_dict(d)

	def set_current_hp(self, owner_id: str, pokemon_id: int, current_hp: int) -> Pokemon:
		val = self.tk.set_current_hp(owner_id, pokemon_id, current_hp)
		d = self.tk.get_pokemon(owner_id, pokemon_id)
		return Pokemon.from_dict(d)

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> Pokemon:
		self.tk.set_moves(owner_id, pokemon_id, moves)
		d = self.tk.get_pokemon(owner_id, pokemon_id)
		return Pokemon.from_dict(d)

	def restore_pp(self, owner_id: str, pokemon_id: int) -> Pokemon:
		self.tk.restore_pp(owner_id, pokemon_id)
		d = self.tk.get_pokemon(owner_id, pokemon_id)
		return Pokemon.from_dict(d)

	def transfer(self, owner_id: str, pokemon_id: int, new_owner_id: str) -> Pokemon:
		d = self.tk.transfer_pokemon(owner_id, pokemon_id, new_owner_id)
		return Pokemon.from_dict(d)

	def release(self, owner_id: str, pokemon_id: int) -> bool:
		return self.tk.release_pokemon(owner_id, pokemon_id)