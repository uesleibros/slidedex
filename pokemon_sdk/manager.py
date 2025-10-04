import discord
import random
import aiopoke
from typing import List, Optional, Dict
from utils.formatting import format_pokemon_display
from .services import PokeAPIService
from .calculations import generate_pokemon_data, calculate_stats, iv_percent
from .constants import NATURES, REGIONS_GENERATION
from helpers.growth import GrowthRate

class EvolutionChoiceView(discord.ui.View):
    def __init__(
        self,
        owner_id: str,
        pokemon_id: int,
        current_pokemon: dict,
        evolution_species_id: int,
        evolution_name: str,
        manager
    ):
        super().__init__(timeout=60.0)
        self.owner_id = owner_id
        self.pokemon_id = pokemon_id
        self.current_pokemon = current_pokemon
        self.evolution_species_id = evolution_species_id
        self.evolution_name = evolution_name
        self.manager = manager
        self.answered = False
        self.message = None
        
        evolve_button = discord.ui.Button(
            label=f"Evoluir para {evolution_name}",
            style=discord.ButtonStyle.success,
            emoji="✨",
            custom_id="evolve"
        )
        evolve_button.callback = self._evolve_callback
        self.add_item(evolve_button)
        
        cancel_button = discord.ui.Button(
            label="Agora Não",
            style=discord.ButtonStyle.secondary,
            emoji="⏭️",
            custom_id="cancel"
        )
        cancel_button.callback = self._cancel_callback
        self.add_item(cancel_button)
        
        block_button = discord.ui.Button(
            label="Nunca Evoluir",
            style=discord.ButtonStyle.danger,
            emoji="🚫",
            custom_id="block"
        )
        block_button.callback = self._block_callback
        self.add_item(block_button)
    
    async def _evolve_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
            return
        
        if self.answered:
            await interaction.response.send_message("Já foi respondido!", ephemeral=True)
            return
        
        self.answered = True
        
        await interaction.response.edit_message(
            content=f"<@{self.owner_id}> ✨ Evoluindo...",
            view=None
        )
        
        try:
            result = await self.manager.evolve_pokemon(
                self.owner_id,
                self.pokemon_id,
                self.evolution_species_id
            )
            
            old_name = self.current_pokemon.get("name", "").title()
            
            await interaction.edit_original_response(
                content=f"<@{self.owner_id}> 🎉 **{old_name}** evoluiu para **{self.evolution_name}**!"
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"<@{self.owner_id}> ❌ Erro ao evoluir: {e}"
            )
        
        self.stop()
    
    async def _cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
            return
        
        if self.answered:
            await interaction.response.send_message("Já foi respondido!", ephemeral=True)
            return
        
        self.answered = True
        
        current_name = self.current_pokemon.get("name", "").title()
        
        await interaction.response.edit_message(
            content=f"<@{self.owner_id}> ⏭️ {current_name} não evoluiu. (Tentará novamente no próximo nível)",
            view=None
        )
        
        self.stop()
    
    async def _block_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
            return
        
        if self.answered:
            await interaction.response.send_message("Já foi respondido!", ephemeral=True)
            return
        
        self.answered = True
        
        self.manager.tk.block_evolution(self.owner_id, self.pokemon_id, True)
        
        current_name = self.current_pokemon.get("name", "").title()
        
        await interaction.response.edit_message(
            content=f"<@{self.owner_id}> 🚫 {current_name} nunca evoluirá. (Use `/desbloquear` para reverter)",
            view=None
        )
        
        self.stop()
    
    async def on_timeout(self):
        if not self.answered and self.message:
            for item in self.children:
                item.disabled = True
            
            current_name = self.current_pokemon.get("name", "").title()
            
            await self.message.edit(
                content=f"<@{self.owner_id}> Tempo esgotado! {current_name} não evoluiu. (Tentará novamente no próximo nível)",
                view=None
            )

class MoveChoiceView(discord.ui.View):
    def __init__(
        self,
        owner_id: str,
        pokemon_id: int,
        new_move_id: str,
        new_move_name: str,
        pp_max: int,
        current_moves: List[Dict],
        pokemon: dict,
        manager
    ):
        super().__init__(timeout=60.0)
        self.owner_id = owner_id
        self.pokemon_id = pokemon_id
        self.new_move_id = new_move_id
        self.new_move_name = new_move_name
        self.pp_max = pp_max
        self.current_moves = current_moves
        self.pokemon = pokemon
        self.manager = manager
        self.answered = False
        self.message = None
        
        for idx, move in enumerate(current_moves):
            move_id = move["id"]
            move_name = move_id.replace("-", " ").title()
            
            button = discord.ui.Button(
                label=f"Esquecer {move_name}",
                style=discord.ButtonStyle.primary,
                custom_id=f"forget_{idx}"
            )
            button.callback = self._create_callback(move_id)
            self.add_item(button)
        
        cancel_button = discord.ui.Button(
            label="Cancelar",
            style=discord.ButtonStyle.secondary,
            custom_id="cancel"
        )
        cancel_button.callback = self._cancel_callback
        self.add_item(cancel_button)
    
    def _create_callback(self, move_to_forget: str):
        async def callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.owner_id:
                await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
                return
            
            if self.answered:
                await interaction.response.send_message("Já foi respondido!", ephemeral=True)
                return
            
            self.answered = True
            
            self.manager.tk.learn_move(
                self.owner_id,
                self.pokemon_id,
                self.new_move_id,
                self.pp_max,
                replace_move_id=move_to_forget
            )
            
            move_forgotten_name = move_to_forget.replace("-", " ").title()
            
            await interaction.response.edit_message(
                content=f"<@{self.owner_id}> {format_pokemon_display(self.pokemon, bold_name=True)} Esqueceu **{move_forgotten_name}** e Aprendeu **{self.new_move_name}**!",
                view=None
            )
            
            self.stop()
        
        return callback
    
    async def _cancel_callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
            return
        
        if self.answered:
            await interaction.response.send_message("Já foi respondido!", ephemeral=True)
            return
        
        self.answered = True
        
        await interaction.response.edit_message(
            content=f"<@{self.owner_id}> {format_pokemon_display(self.pokemon, bold_name=True)} Não aprendeu **{self.new_move_name}**.",
            view=None
        )
        
        self.stop()
    
    async def on_timeout(self):
        if not self.answered and self.message:
            for item in self.children:
                item.disabled = True
            
            await self.message.edit(
                content=f"<@{self.owner_id}> Tempo esgotado! {format_pokemon_display(self.pokemon, bold_name=True)} não aprendeu **{self.new_move_name}**.",
                view=None
            )

class PokemonManager:
	def __init__(self, toolkit):
		self.tk = toolkit
		self.service = PokeAPIService()

	async def _build_pokemon_data(
	    self,
	    species_id: int,
	    level: int = 5,
	    forced_gender: Optional[str] = None,
	    ivs: Optional[Dict[str, int]] = None,
	    nature: Optional[str] = None,
	    ability: Optional[str] = None,
	    moves: Optional[List[Dict]] = None,
	    shiny: Optional[bool] = None,
	    held_item: Optional[str] = None,
	    nickname: Optional[str] = None,
	    owner_id: str = "wild",
	    on_party: bool = False
	) -> Dict:
	    poke: aiopoke.Pokemon = await self.service.get_pokemon(species_id)
	    species: aiopoke.PokemonSpecies = await self.service.get_species(species_id)
	    base_stats = self.service.get_base_stats(poke)
	
	    growth_type: str = species.growth_rate.name
	    pkm_name = poke.name
		happiness: int = species.base_happiness
	
	    final_ivs = ivs or {k: random.randint(0, 31) for k in base_stats.keys()}
	    final_nature = nature or random.choice(list(NATURES.keys()))
	
	    is_legendary: bool = species.is_legendary
	    is_mythical: bool = species.is_mythical
	    poke_types: list = [x.type.name for x in poke.types]
	    poke_region: str = REGIONS_GENERATION.get(species.generation.name, "generation-i")
	
	    final_level = min(max(level, 1), 100)
	    
	    gen = generate_pokemon_data(base_stats, level=final_level, nature=final_nature, ivs=final_ivs)
	    final_ability = ability or self.service.choose_ability(poke)
	    final_moves = moves or self.service.select_level_up_moves(poke, final_level)
	    final_gender = self.service.roll_gender(species, forced=forced_gender)
	    final_shiny = shiny if shiny is not None else self.service.roll_shiny()
	
	    exp = GrowthRate.calculate_exp(growth_type, final_level)
	    
	    del poke
	    del species
	    del base_stats
	
	    return {
	        "id": 0,
	        "species_id": species_id,
	        "owner_id": owner_id,
	        "level": gen["level"],
	        "exp": exp,
	        "ivs": gen["ivs"],
	        "evs": gen["evs"],
	        "nature": gen["nature"],
	        "ability": final_ability,
	        "gender": final_gender,
	        "is_shiny": final_shiny,
	        "held_item": held_item,
	        "caught_at": "",
	        "types": poke_types,
	        "region": poke_region,
	        "is_legendary": is_legendary,
	        "is_mythical": is_mythical,
	        "moves": final_moves,
			"happiness": happiness,
	        "growth_type": growth_type,
	        "base_stats": gen["stats"],
	        "current_hp": gen["current_hp"],
	        "on_party": on_party,
	        "nickname": nickname,
	        "name": pkm_name
	    }

	async def generate_temp_pokemon(self, **kwargs) -> Dict:
		return await self._build_pokemon_data(**kwargs)

	async def create_pokemon(
		self,
		owner_id: str,
		species_id: int,
		level: int = 5,
		on_party: bool = True,
		**kwargs
	) -> Dict:
		pkmn = await self._build_pokemon_data(
			species_id=species_id,
			level=level,
			owner_id=owner_id,
			on_party=on_party,
			**kwargs
		)

		created = self.tk.add_pokemon(
			owner_id=pkmn["owner_id"],
			species_id=pkmn["species_id"],
			ivs=pkmn["ivs"],
			nature=pkmn["nature"],
			ability=pkmn["ability"],
			gender=pkmn["gender"],
			shiny=pkmn["is_shiny"],
			level=pkmn["level"],
			moves=pkmn["moves"],
			is_legendary=pkmn["is_legendary"],
			is_mythical=pkmn["is_mythical"],
			types=pkmn["types"],
			region=pkmn["region"],
			on_party=pkmn["on_party"],
			current_hp=pkmn["current_hp"],
			growth_type=pkmn["growth_type"],
			held_item=pkmn["held_item"],
			nickname=pkmn["nickname"],
			happiness=pkmn["happiness"],
			base_stats=pkmn["base_stats"],
			name=pkmn["name"],
			exp=pkmn["exp"]
		)

		return created
	
	async def check_evolution(self, owner_id: str, pokemon_id: int, trigger: str = "level-up") -> Optional[Dict]:
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if self.tk.is_evolution_blocked(owner_id, pokemon_id):
			return None
		
		species = await self.service.get_species(pokemon["species_id"])
		
		if not species.evolves_from_species:
			chain = await self.service.client.get_evolution_chain(species.evolution_chain.id)
		else:
			chain = await self.service.client.get_evolution_chain(species.evolution_chain.id)
		
		def find_current_in_chain(chain_link, current_species_id):
			if chain_link.species.name == current_species_id or chain_link.species.url.split('/')[-2] == str(current_species_id):
				return chain_link
			
			for evo in chain_link.evolves_to:
				result = find_current_in_chain(evo, current_species_id)
				if result:
					return result
			return None
		
		current_link = find_current_in_chain(chain.chain, pokemon["species_id"])
		
		if not current_link or not current_link.evolves_to:
			return None
		
		for evolution in current_link.evolves_to:
			for detail in evolution.evolution_details:
				if detail.trigger.name != trigger:
					continue
				
				if detail.min_level and pokemon["level"] < detail.min_level:
					continue
				
				if detail.item and not pokemon.get("held_item"):
					continue
				
				if detail.item and pokemon.get("held_item") != detail.item.name:
					continue
				
				if detail.min_happiness and detail.min_happiness > 0:
					continue
				
				if detail.time_of_day and detail.time_of_day not in ["", None]:
					continue
				
				evolution_species_id = int(evolution.species.url.split('/')[-2])
				evolution_name = evolution.species.name.title()
				
				return {
					"species_id": evolution_species_id,
					"name": evolution_name,
					"trigger": detail.trigger.name,
					"min_level": detail.min_level,
					"item": detail.item.name if detail.item else None
				}
		
		return None
	
	async def evolve_pokemon(self, owner_id: str, pokemon_id: int, new_species_id: int) -> Dict:
	    old_pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
	    
	    new_poke = await self.service.get_pokemon(new_species_id)
	    new_species = await self.service.get_species(new_species_id)
	    new_base_stats = self.service.get_base_stats(new_poke)
	    
	    new_types = [t.type.name for t in new_poke.types]
	    is_legendary = new_species.is_legendary
	    is_mythical = new_species.is_mythical
	    growth_type = new_species.growth_rate.name
	    region = REGIONS_GENERATION.get(new_species.generation.name, "generation-i")
	    
	    new_ability = self.service.choose_ability(new_poke)
	    
	    final_moves = old_pokemon["moves"].copy()
	    
	    old_max_hp = old_pokemon["base_stats"]["hp"]
	    old_current_hp = old_pokemon.get("current_hp", old_max_hp)
	    hp_percent = old_current_hp / old_max_hp if old_max_hp > 0 else 1.0
	    
	    new_max_hp = new_base_stats["hp"]
	    new_current_hp = int(new_max_hp * hp_percent)
	    
	    self.tk.set_level(owner_id, pokemon_id, old_pokemon["level"])
	    
	    updated_pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
	    updated_pokemon["species_id"] = new_species_id
	    updated_pokemon["name"] = new_poke.name
	    updated_pokemon["types"] = new_types
	    updated_pokemon["base_stats"] = new_base_stats
	    updated_pokemon["ability"] = new_ability
	    updated_pokemon["is_legendary"] = is_legendary
	    updated_pokemon["is_mythical"] = is_mythical
	    updated_pokemon["growth_type"] = growth_type
	    updated_pokemon["region"] = region
	    updated_pokemon["current_hp"] = new_current_hp
	    
	    idx = self.tk._get_pokemon_index(owner_id, pokemon_id)
	    self.tk.db["pokemon"][idx] = updated_pokemon
	    self.tk._save()
	    
	    self.tk.set_moves(owner_id, pokemon_id, final_moves)
	    
	    del new_poke
	    del new_species
	    del new_base_stats
	    
	    return self.tk.get_pokemon(owner_id, pokemon_id)
	
	async def process_evolution(
		self,
		owner_id: str,
		pokemon_id: int,
		message: Optional[discord.Message] = None
	) -> Optional[Dict]:
		evolution_data = await self.check_evolution(owner_id, pokemon_id, trigger="level-up")
		
		if not evolution_data:
			return None
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if message:
			view = EvolutionChoiceView(
				owner_id=owner_id,
				pokemon_id=pokemon_id,
				current_pokemon=pokemon,
				evolution_species_id=evolution_data["species_id"],
				evolution_name=evolution_data["name"],
				manager=self
			)
			
			content = (
				f"<@{owner_id}> ✨ {format_pokemon_display(pokemon, bold_name=True)} pode evoluir para **{evolution_data['name']}**!\n"
				f"Você quer evoluir?\n"
				f"-# Você tem até 1 minuto para decidir."
			)
			
			sent_message = await message.channel.send(content=content, view=view)
			view.message = sent_message
			
			return evolution_data
		
		return evolution_data
	
	async def process_level_up(
	    self,
	    owner_id: str,
	    pokemon_id: int,
	    levels_gained: List[int],
	    message: Optional[discord.Message] = None
	) -> Dict:
	    if not levels_gained:
	        return {
	            "learned": [],
	            "needs_choice": [],
	            "levels_gained": [],
	            "evolution": None
	        }
	    
	    pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
	    poke = await self.service.get_pokemon(pokemon["species_id"])
	    
	    all_moves = self.service.get_level_up_moves(poke)
	    
	    new_moves = {}
	    for move_id, level in all_moves:
	        if level in levels_gained:
	            new_moves[move_id] = level
	    
	    learned = []
	    needs_choice = []
	    
	    sorted_moves = sorted(new_moves.items(), key=lambda x: x[1])
	    
	    for move_id, level in sorted_moves:
	        pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
	        
	        if self.tk.has_move(owner_id, pokemon_id, move_id):
	            continue
	        
	        try:
	            move_detail = await self.service.get_move(move_id)
	            pp_max = move_detail.pp if move_detail.pp else 10
	        except:
	            pp_max = 10
	        
	        if self.tk.can_learn_move(owner_id, pokemon_id):
	            self.tk.learn_move(owner_id, pokemon_id, move_id, pp_max)
	            learned.append({
	                "id": move_id,
	                "name": move_id.replace("-", " ").title(),
	                "level": level,
	                "pp_max": pp_max
	            })
	        else:
	            needs_choice.append({
	                "id": move_id,
	                "name": move_id.replace("-", " ").title(),
	                "level": level,
	                "pp_max": pp_max
	            })
	            
	            if message:
	                pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
	                await self._handle_move_choice(message, owner_id, pokemon_id, move_id, pp_max, pokemon)
	    
	    del poke
	    
	    evolution_data = None
	    if message:
	        evolution_data = await self.process_evolution(owner_id, pokemon_id, message)
	    
	    return {
	        "learned": learned,
	        "needs_choice": needs_choice,
	        "levels_gained": levels_gained,
	        "evolution": evolution_data
	    }

	async def _handle_move_choice(
		self,
		message: discord.Message,
		owner_id: str,
		pokemon_id: int,
		new_move_id: str,
		pp_max: int,
		pokemon: Dict
	) -> None:
		new_move_name = new_move_id.replace("-", " ").title()
		
		current_moves = pokemon.get("moves", [])
		
		view = MoveChoiceView(
			owner_id=owner_id,
			pokemon_id=pokemon_id,
			new_move_id=new_move_id,
			new_move_name=new_move_name,
			pp_max=pp_max,
			current_moves=current_moves,
			pokemon=pokemon,
			manager=self
		)
		
		content = f"<@{owner_id}> {format_pokemon_display(pokemon, bold_name=True)} Quer aprender **{new_move_name}**, mas já conhece 4 movimentos.\nEscolha um movimento para esquecer ou cancele para não aprender **{new_move_name}**.\n-# Você tem até 1 minuto para fazer sua escolha."
		
		sent_message = await message.channel.send(content=content, view=view)
		view.message = sent_message

	async def add_experience(
	    self,
	    owner_id: str,
	    pokemon_id: int,
	    exp_gain: int,
	    notify_message: Optional[discord.Message] = None
	) -> Dict:
	    result = self.tk.add_exp(owner_id, pokemon_id, exp_gain)
	    
	    if result.get("max_level_reached") and result.get("old_level") < 100:
	        if notify_message:
	            pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
	            await notify_message.channel.send(
	                f"🎉 {format_pokemon_display(pokemon, bold_name=True)} atingiu o **nível máximo 100**!"
	            )
	    
	    levels_gained = result.get("levels_gained", [])
	    
	    if levels_gained:
	        move_result = await self.process_level_up(owner_id, pokemon_id, levels_gained, notify_message)
	        result["move_learning"] = move_result
	    else:
	        result["move_learning"] = {
	            "learned": [],
	            "needs_choice": [],
	            "levels_gained": [],
	            "evolution": None
	        }
	    
	    return result

	async def _send_level_up_notification(
		self,
		message: discord.Message,
		exp_result: Dict,
		move_result: Dict
	) -> None:
		pokemon = self.tk.get_pokemon(exp_result["owner_id"], exp_result["id"])
		
		lines = []
		
		for level in move_result.get("levels_gained", []):
			lines.append(f"{format_pokemon_display(pokemon, bold_name=True)} Subiu para o nivel **{level}**!")
		
		if move_result.get("learned"):
			lines.append("")
			lines.append("Moves Aprendidos:")
			for move_info in move_result["learned"]:
				lines.append(f"  - {move_info['name']} (Nv. {move_info['level']})")
		
		if lines:
			await message.channel.send("\n".join(lines))
		
	def get_party(self, user_id: str) -> List[Dict]:
		return self.tk.get_user_pokemon(user_id, on_party=True)

	def get_box(self, user_id: str) -> List[Dict]:
		return self.tk.get_user_pokemon(user_id, on_party=False)

	def list_all(self, user_id: str) -> List[Dict]:
		return self.tk.list_pokemon_by_owner(user_id)

	async def heal(self, owner_id: str, pokemon_id: int) -> Dict:
		p = self.tk.get_pokemon(owner_id, pokemon_id)
		poke = await self.service.get_pokemon(p["species_id"])
		base_stats = self.service.get_base_stats(poke)
		stats = calculate_stats(base_stats, p["ivs"], p["evs"], p["level"], p["nature"])

		del poke
		del base_stats
		del p

		return self.tk.set_current_hp(owner_id, pokemon_id, stats["hp"])

	def move_to_party(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.tk.move_to_party(owner_id, pokemon_id)

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.tk.move_to_box(owner_id, pokemon_id)

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> Dict:
		return self.tk.set_moves(owner_id, pokemon_id, moves)

	def iv_percent(self, p: Dict, decimals: int = 2) -> float:
		return iv_percent(p["ivs"], decimals)

	async def close(self):
		await self.service.close()



