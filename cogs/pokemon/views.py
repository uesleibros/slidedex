import discord
from sdk.calculations import iv_percent, calculate_stats
from sdk.constants import STAT_KEYS, STAT_LABELS
from sdk.items.constants import ITEM_EMOJIS
from utilities.formatting import format_pokemon_display, format_happiness_status, format_nature_info, format_item_display
from typing import Dict, List, Tuple
from datetime import datetime
from sdk.toolkit import Toolkit

class PokemonListLayout(discord.ui.LayoutView):
    def __init__(self, pokemons: List, current_page: int = 0, per_page: int = 20):
        super().__init__()
        self.pokemons = pokemons
        self.per_page = per_page
        self.current_page = current_page
        self._total_len = len(pokemons)
        self.total_pages = max(1, (self._total_len - 1) // per_page + 1) if self._total_len else 1
        self._max_page = self.total_pages - 1
        
        self._displays = tuple(
            f"`{str(p['id']).zfill(3)}`　{format_pokemon_display(p, show_fav=True)}　•　Lv. {p['level']}　•　{iv_percent(p['ivs'])}%"
            for p in pokemons
        )
        
        self._prev_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
        self._prev_btn.callback = self._prev
        self._next_btn = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
        self._next_btn.callback = self._next
        
        self._header = discord.ui.TextDisplay("### Seus Pokémon")
        self._sep = discord.ui.Separator()
        self._empty = discord.ui.TextDisplay("Sem Pokémon disponíveis.")
        self._footer_fmt = "-# Mostrando {}–{} de {}"
        
        action_row = self._action_row = discord.ui.ActionRow()
        action_row.add_item(self._prev_btn)
        action_row.add_item(self._next_btn)
        
        self._build()

    def _build(self):
        self.clear_items()
        
        idx = self.current_page * self.per_page
        end = min(idx + self.per_page, self._total_len)
        
        c = discord.ui.Container()
        c.add_item(self._header)
        c.add_item(self._sep)
        
        displays = self._displays
        if displays:
            TextDisplay = discord.ui.TextDisplay
            for i in range(idx, end):
                c.add_item(TextDisplay(displays[i]))
        else:
            c.add_item(self._empty)
        
        c.add_item(self._sep)
        pagination = self._footer_fmt.format(idx + 1, end, self._total_len) if self._total_len else "-# Nenhum pokémon"
        c.add_item(discord.ui.TextDisplay(pagination))
        
        self.add_item(c)
        
        self._prev_btn.disabled = not self.current_page
        self._next_btn.disabled = self.current_page >= self._max_page
        
        self.add_item(self._action_row)

    async def _prev(self, interaction: discord.Interaction):
        if self.current_page:
            self.current_page -= 1
            self._build()
            await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        if self.current_page < self._max_page:
            self.current_page += 1
            self._build()
            await interaction.response.edit_message(view=self)

class PokemonInfoLayout(discord.ui.LayoutView):
    def __init__(self, current_pokemon: Dict, current_index: int, total_pages: int, tk: Toolkit):
        super().__init__()
        self.current_pokemon = current_pokemon
        self.current_index = current_index
        self.total_pages = total_pages
        self.tk = tk
        self.show_iv = True
        
        self._stat_keys = STAT_KEYS
        self._stat_labels = STAT_LABELS
        self._separator = discord.ui.Separator()
        
        self._cache_pokemon_data()
        
        self._toggle_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, custom_id="toggle_stats")
        self._toggle_btn.callback = self._toggle
        
        self._build()

    def _cache_pokemon_data(self):
        p = self.current_pokemon
        base = self._base_stats = p['base_stats']
        ivs = self._ivs = p["ivs"]
        evs = self._evs = p.get("evs", {})
        level = self._level = p["level"]
        
        self._stats = calculate_stats(base, ivs, evs, level, p["nature"])
        self._iv_total = sum(ivs.values())
        self._ev_total = sum(evs.values())
        self._iv_percent = round(self._iv_total * 0.537634408602151, 2)
        self._ev_percent = round(self._ev_total * 0.196078431372549, 2)
        
        current_exp = p.get("exp", 0)
        growth = self._growth_type = p.get("growth_type")
        
        exp_current = self.tk.get_exp_for_level(growth, level)
        
        if level >= 100:
            self._exp_next = exp_current
            self._exp_needed = 0
            self._exp_progress = 100.0
        else:
            exp_next = self._exp_next = self.tk.get_exp_for_level(growth, level + 1)
            needed = self._exp_needed = exp_next - exp_current
            self._exp_progress = round((current_exp - exp_current) / needed * 100, 1) if needed else 0
        
        self._pokemon_id = p['id']
        self._species_id = p['species_id']
        self._current_hp = p.get("current_hp") if p.get("current_hp") is not None else self._stats["hp"]
        
        self._types_str = ' / '.join(t.title() for t in p['types'])
        self._nature_info = format_nature_info(p['nature'])
        self._happiness_status = format_happiness_status(p['happiness'])
        self._ability = str(p.get('ability') or '-').replace('-', ' ').title()
        self._region = p['region'].replace('-', ' ').title()
        self._held_item = format_item_display(p.get('held_item'))
        self._caught_with = ITEM_EMOJIS.get(p.get('caught_with'), 'poke-ball')
        self._caught_at = datetime.fromisoformat(p['caught_at']).strftime('%d/%m/%Y às %H:%M')
        
        self._moves_data = tuple(
            f"**{m['id'].replace('-', ' ').title()}** ({m['pp']}/{m['pp_max']} PP)"
            for m in p.get("moves", [])
        )
        
        pokemon_data = self.tk.api.get_pokemon(self._species_id)
        self._future_moves = self.tk.api.get_future_moves(pokemon_data, level)

    def _build(self):
        self.clear_items()
        
        p = self.current_pokemon
        stats = self._stats
        
        c = discord.ui.Container()
        TextDisplay = discord.ui.TextDisplay
        
        c.add_item(TextDisplay(
            f"### Level {self._level} {format_pokemon_display(p, show_fav=True, show_poke=False)}\n"
            f"├ **ID do Pokemon:** {self._pokemon_id}\n"
            f"└ **ID da Espécie:** {self._species_id}\n"
        ))

        c.add_item(self._separator)
        
        sec = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://stats.png"))
        sec.add_item(TextDisplay(
            f"-# **Especificações**\n"
            f"<:CometShard:1424200074463805551> **Experiência:** {p.get('exp', 0)}/{self._exp_next} | Próximo: {self._exp_needed} XP ({self._exp_progress}%)\n"
            f":leaves: **Natureza:** {self._nature_info}\n"
            f"<:speechbubble_heart:1424195141199204467> **Amizade:** {self._happiness_status}\n"
            f":kite: **Tipo de Crescimento:** {self._growth_type.replace('-', ' ').title()}\n"
            f"🧬 **Habilidade:** {self._ability}\n"
            f":rock: **Tipos:** {self._types_str}\n"
            f"<:research_encounter:1424202205757444096> **Região:** {self._region}\n"
            f":empty_nest: **Item Segurado:** {self._held_item}\n"
            f"🧺 **Capturado com**: {self._caught_with}"
        ))
        
        c.add_item(sec)
        c.add_item(self._separator)

        stats_lines = []
        base = self._base_stats
        stat_keys = self._stat_keys
        stat_labels = self._stat_labels
        hp_val = self._current_hp
        
        if self.show_iv:
            ivs = self._ivs
            stats_lines.append(f"<:stats:1424204552910929920> **IV Total:** {self._iv_total}/186 ({self._iv_percent}%)")
            
            for key in stat_keys:
                b = base.get(key, 0)
                iv = ivs.get(key, 0)
                final = stats[key]
                
                if key == "hp":
                    stats_lines.append(f"<:stats:1424204552910929920> **HP:** {hp_val}/{final} | Base: {b} | IV: {iv}")
                else:
                    stats_lines.append(f"<:stats:1424204552910929920> **{stat_labels[key]}:** {final} | Base: {b} | IV: {iv}")
            
            sec = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://iv.png"))
            self._toggle_btn.label = "Mostrar EVs"
        else:
            evs = self._evs
            stats_lines.append(f"<:stats:1424204552910929920> **EV Total:** {self._ev_total}/510 ({self._ev_percent}%)")
            
            for key in stat_keys:
                b = base.get(key, 0)
                ev = evs.get(key, 0)
                final = stats[key]
                
                if key == "hp":
                    stats_lines.append(f"<:stats:1424204552910929920> **HP:** {hp_val}/{final} | Base: {b} | EV: {ev}")
                else:
                    stats_lines.append(f"<:stats:1424204552910929920> **{stat_labels[key]}:** {final} | Base: {b} | EV: {ev}")
            
            sec = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://ev.png"))
            self._toggle_btn.label = "Mostrar IVs"

        sec.add_item(TextDisplay(f"-# **Estatísticas**\n{chr(10).join(stats_lines)}"))
        c.add_item(sec)

        row = discord.ui.ActionRow()
        row.add_item(self._toggle_btn)
        c.add_item(row)
        c.add_item(self._separator)

        sec = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://special_move.png"))
        sec.add_item(TextDisplay(f"-# **Seus Movimentos**\n{chr(10).join(self._moves_data)}"))
        c.add_item(sec)
        
        c.add_item(self._separator)
        c.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://pokemon.png")))
        c.add_item(self._separator)
        c.add_item(TextDisplay(f"-# Capturado em: {self._caught_at}"))

        self.add_item(c)

    async def _toggle(self, interaction: discord.Interaction):
        self.show_iv = not self.show_iv
        self._build()
        await interaction.response.edit_message(view=self)


