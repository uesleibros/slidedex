import discord
from sdk.calculations import iv_percent, calculate_stats
from sdk.constants import STAT_KEYS, STAT_LABELS
from sdk.items.constants import ITEM_EMOJIS
from utilities.formatting import format_pokemon_display, format_happiness_status, format_nature_info, format_item_display
from typing import Dict, List, Tuple
from sdk.toolkit import Toolkit

class PokemonListLayout(discord.ui.LayoutView):
    def __init__(self, pokemons: List, current_page: int = 0, per_page: int = 20):
        super().__init__()
        self.pokemons = pokemons
        self.per_page = per_page
        self.current_page = current_page
        self.total_pages = max(1, (len(pokemons) - 1) // per_page + 1)
        
        self._precomputed_displays = [
            f"`{str(p['id']).zfill(3)}`　{format_pokemon_display(p, show_fav=True)}　•　Lv. {p['level']}　•　{iv_percent(p['ivs'])}%"
            for p in pokemons
        ]
        
        self._prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
        self._prev_button.callback = self.previous_page
        
        self._next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
        self._next_button.callback = self.next_page
        
        self.build_page()

    def build_page(self):
        self.clear_items()

        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.pokemons))

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay("### Seus Pokémon"))
        container.add_item(discord.ui.Separator())

        for display in self._precomputed_displays[start_idx:end_idx]:
            container.add_item(discord.ui.TextDisplay(display))

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(f"-# Mostrando {start_idx+1}–{end_idx} de {len(self.pokemons)}"))

        self.add_item(container)

        self._prev_button.disabled = self.current_page == 0
        self._next_button.disabled = self.current_page >= self.total_pages - 1
        
        action_row = discord.ui.ActionRow()
        action_row.add_item(self._prev_button)
        action_row.add_item(self._next_button)
        self.add_item(action_row)

    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.build_page()
            await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.build_page()
            await interaction.response.edit_message(view=self)


class PokemonInfoLayout(discord.ui.LayoutView):
    def __init__(self, current_pokemon: Dict, current_index: int, total_pages: int, tk: Toolkit):
        super().__init__()
        self.current_pokemon = current_pokemon
        self.current_index = current_index
        self.total_pages = total_pages
        self.tk = tk
        self.show_iv = True
        
        self._cache_pokemon_data()
        
        self._toggle_stats_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, custom_id="toggle_stats")
        self._toggle_stats_btn.callback = self.toggle_stats
        
        self.build_page()

    def _cache_pokemon_data(self):
        pokemon = self.current_pokemon
        base_stats = pokemon['base_stats']
        ivs = pokemon["ivs"]
        evs = pokemon.get("evs", {})
        
        self._cached_stats = calculate_stats(base_stats, ivs, evs, pokemon["level"], pokemon["nature"])
        self._cached_iv_total = sum(ivs.values())
        self._cached_ev_total = sum(evs.values())
        self._cached_iv_percent = round((self._cached_iv_total / 186) * 100, 2)
        self._cached_ev_percent = round((self._cached_ev_total / 510) * 100, 2)
        
        current_level = pokemon["level"]
        current_exp = pokemon.get("exp", 0)
        growth_type = pokemon.get("growth_type")
        
        exp_current_level = self.tk.get_exp_for_level(growth_type, current_level)
        
        if current_level >= 100:
            self._exp_next_level = exp_current_level
            self._exp_needed = 0
            self._exp_progress = 100.0
        else:
            self._exp_next_level = self.tk.get_exp_for_level(growth_type, current_level + 1)
            self._exp_needed = self._exp_next_level - exp_current_level
            self._exp_progress = round(((current_exp - exp_current_level) / self._exp_needed) * 100, 1) if self._exp_needed > 0 else 0
        
        pokemon_data = self.tk.api.get_pokemon(pokemon["species_id"])
        self._future_moves = self.tk.api.get_future_moves(pokemon_data, current_level)

    def build_page(self):
        self.clear_items()
        pokemon = self.current_pokemon
        stats = self._cached_stats
        current_hp = pokemon.get("current_hp") if pokemon.get("current_hp") is not None else stats["hp"]

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(
            f"### Level {pokemon['level']} {format_pokemon_display(pokemon, show_fav=True, show_poke=False)}\n"
            f"ℹ️ **ID do Pokemon:** {pokemon['id']}\n"
            f"└ **ID da Espécie:** {pokemon['species_id']}\n"
        ))

        container.add_item(discord.ui.Separator())
        
        stats_section = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://stats.png"))
        stats_section.add_item(discord.ui.TextDisplay(
            "-# **Especificações**\n"
            f"<:CometShard:1424200074463805551> **Experiência:** {pokemon.get('exp', 0)}/{self._exp_next_level} | Próximo: {self._exp_needed} XP ({self._exp_progress}%)\n"
            f":leaves: **Natureza:** {format_nature_info(pokemon['nature'])}\n"
            f"<:speechbubble_heart:1424195141199204467> **Amizade:** {format_happiness_status(pokemon['happiness'])}\n"
            f":kite: **Tipo de Crescimento:** {pokemon['growth_type'].replace('-', ' ').title()}\n"
            f"🧬 **Habilidade:** {str(pokemon.get('ability') or '-').replace('-', ' ').title()}\n"
            f":rock: **Tipos:** {' / '.join(t.title() for t in pokemon['types'])}\n"
            f"<:research_encounter:1424202205757444096> **Região:** {pokemon['region'].replace('-', ' ').title()}\n"
            f":empty_nest: **Item Segurado:** {format_item_display(pokemon.get('held_item'))}\n"
            f"🧺 **Capturado com**: {ITEM_EMOJIS.get(pokemon.get('caught_with'), 'poke-ball')}"
        ))
        
        container.add_item(stats_section)
        container.add_item(discord.ui.Separator())

        base_stats = pokemon['base_stats']
        
        if self.show_iv:
            ivs = pokemon["ivs"]
            stats_lines = [f"<:stats:1424204552910929920> **IV Total:** {self._cached_iv_total}/186 ({self._cached_iv_percent}%)"]
            
            for key in STAT_KEYS:
                base = base_stats.get(key, 0)
                iv = ivs.get(key, 0)
                final = stats[key]
                
                if key == "hp":
                    stats_lines.append(f"<:stats:1424204552910929920> **HP:** {current_hp}/{final} | Base: {base} | IV: {iv}")
                else:
                    stats_lines.append(f"<:stats:1424204552910929920> **{STAT_LABELS[key]}:** {final} | Base: {base} | IV: {iv}")
            
            stats_section = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://iv.png"))
            self._toggle_stats_btn.label = "Mostrar EVs"
        else:
            evs = pokemon.get("evs", {})
            stats_lines = [f"<:stats:1424204552910929920> **EV Total:** {self._cached_ev_total}/510 ({self._cached_ev_percent}%)"]
            
            for key in STAT_KEYS:
                base = base_stats.get(key, 0)
                ev = evs.get(key, 0)
                final = stats[key]
                
                if key == "hp":
                    stats_lines.append(f"<:stats:1424204552910929920> **HP:** {current_hp}/{final} | Base: {base} | EV: {ev}")
                else:
                    stats_lines.append(f"<:stats:1424204552910929920> **{STAT_LABELS[key]}:** {final} | Base: {base} | EV: {ev}")
            
            stats_section = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://ev.png"))
            self._toggle_stats_btn.label = "Mostrar IVs"

        stats_section.add_item(discord.ui.TextDisplay(f"-# **Estatísticas**\n{'\n'.join(stats_lines)}"))
        container.add_item(stats_section)

        stats_action_row = discord.ui.ActionRow()
        stats_action_row.add_item(self._toggle_stats_btn)
        container.add_item(stats_action_row)

        container.add_item(discord.ui.Separator())

        moves_lines = [f"**{move['id'].replace('-', ' ').title()}** ({move['pp']}/{move['pp_max']} PP)" for move in pokemon.get("moves", [])]
        moves_section = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://special_move.png"))
        self._toggle_moves_btn.label = "Mostrar Próximos Movimentos"

        moves_section.add_item(discord.ui.TextDisplay(f"-# **Seus Movimentos**\n{'\n'.join(moves_lines)}"))
        container.add_item(moves_section)
        
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://pokemon.png")))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(f"-# Pokémon {self.current_index + 1} de {self.total_pages}"))

        self.add_item(container)

    async def toggle_stats(self, interaction: discord.Interaction):
        self.show_iv = not self.show_iv
        self.build_page()
        await interaction.response.edit_message(view=self)
    
    async def toggle_future_moves(self, interaction: discord.Interaction):
        self.show_future_moves = not self.show_future_moves
        self.build_page()
        await interaction.response.edit_message(view=self)
