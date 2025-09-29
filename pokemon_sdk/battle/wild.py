import discord
import aiopoke
import random
import asyncio
from __main__ import pm
from typing import List, Dict, Any, Optional
from utils.canvas import compose_battle_async
from pokemon_sdk.calculations import calculate_stats
from utils.preloaded import preloaded_textures
from utils.pokemon_emojis import get_app_emoji

# --- Constantes e Helpers ---
TYPE_CHART = { "normal":{"immune":{"ghost"}},"fire":{"not":{"fire","water","rock","dragon"}},"water":{"not":{"water","grass","dragon"}},"grass":{"not":{"fire","grass","poison","flying","bug","dragon","steel"}},"electric":{"immune":{"ground"}},"ice":{"not":{"fire","water","ice","steel"}},"fighting":{"immune":{"ghost"}},"poison":{"immune":{"steel"}},"ground":{"immune":{"flying"}},"psychic":{"immune":{"dark"}},"ghost":{"immune":{"normal"}},"dragon":{"immune":{"fairy"}}}
STAT_ALIASES = {"hp":["hp"],"atk":["atk","attack"],"def":["def","defense"],"sp_atk":["sp_atk","spa","special-attack"],"sp_def":["sp_def","spd","special-defense"],"speed":["speed","spe"]}

def _obj(**kw): return type("O", (), kw)()
def _stage_multiplier(s: int) -> float: return (2+s)/2 if s>=0 else 2/(2-s)
def _get_stat(stats: dict, key: str) -> int:
	for alias in STAT_ALIASES.get(key,[]):
		if alias in stats: return int(stats[alias])
	return 1
def _hp_bar(c: int, t: int, l: int=10) -> str:
	p = c/t; f=int(l*p); b='█'*f+'░'*(l-f); color="🟢" if p>0.5 else "🟡" if p>0.2 else "🔴"; return f"{color} `[{b}]`"

class _Meta:
	def __init__(self): self.ailment,self.ailment_chance,self.flinch_chance,self.drain,self.recoil,self.min_hits,self.max_hits,self.healing = _obj(name="none"),0,0,0,0,1,1,0
class _Struggle: power,accuracy,priority,name,damage_class,type,stat_changes,effect_chance,meta=50,None,0,"Struggle",_obj(name="physical"),_obj(name="normal"),[],None,_Meta()
class _FallbackMove:
	def __init__(self, name, power=0, acc=100, prio=0, dmg="status", type_name="normal", sc=None):
		self.name,self.power,self.accuracy,self.priority = name,power,acc,prio
		self.damage_class, self.type, self.stat_changes, self.effect_chance, self.meta = _obj(name=dmg),_obj(name=type_name),sc or [],None,_Meta()

class BattlePokemon:
	def __init__(self, raw: Dict, api_data: aiopoke.Pokemon, species_data: aiopoke.PokemonSpecies):
		self.raw, self.species_id, self.name, self.level = raw, raw["species_id"], raw.get("name"), raw["level"]
		self.stats = calculate_stats(pm.service.get_base_stats(api_data), raw["ivs"], raw["evs"], self.level, raw["nature"])
		self.current_hp = raw.get("current_hp") or self.stats["hp"]
		self.moves = raw.get("moves") or [{"id":"tackle","pp":35,"pp_max":35}]
		self.api_data, self.species_data, self.is_shiny = api_data, species_data, raw.get("is_shiny",False)
		self.stages = {s:0 for s in STAT_ALIASES}
		self.status, self.volatile = {"name":None,"counter":0}, {"flinch":False,"confuse":0}
		self.sprites = api_data.sprites.front_shiny if self.is_shiny else api_data.sprites.front_default, \
					   api_data.sprites.back_shiny if self.is_shiny else api_data.sprites.back_default
	@property
	def fainted(self) -> bool: return self.current_hp <= 0
	def eff_stat(self, key: str) -> int:
		val = max(1, int(_get_stat(self.stats, key) * _stage_multiplier(self.stages[key])))
		if key=="speed" and self.status["name"]=="paralysis": val = int(val*0.5)
		return max(1, val)
	def dec_pp(self, move_id: str):
		for m in self.moves:
			if str(m["id"]).lower()==str(move_id).lower() and "pp" in m: m["pp"]=max(0,int(m["pp"])-1)
	def get_pp(self, move_id: str) -> Optional[int]:
		for m in self.moves:
			if str(m["id"]).lower()==str(move_id).lower(): return int(m.get("pp",0))
	def set_status(self, name:str, turns:Optional[int]=None)->bool:
		if self.status["name"]: return False
		self.status={"name":name,"counter":turns or (random.randint(1,3) if name=="sleep" else 0)}; return True
	def status_tag(self)->str:
		tags = {"burn":"BRN","poison":"PSN","paralysis":"PAR","sleep":"SLP","freeze":"FRZ"}
		return f" [{tags[self.status['name']]}]" if self.status["name"] in tags else ""
	def types(self) -> List[str]: return [t.type.name.lower() for t in self.api_data.types]

class WildBattle:
	def __init__(self, player_party: List[Dict], wild: Dict, user_id: str, interaction: discord.Interaction):
		self.user_id, self.interaction, self.player_party_raw, self.wild_raw = user_id, interaction, player_party, wild
		self.active_player_idx, self.ended, self.turn, self.must_redraw_image = 0, False, 1, True
		self.lock, self.move_cache, self.player_team, self.lines = asyncio.Lock(), {}, [], []
	@property
	def player_active(self) -> BattlePokemon: return self.player_team[self.active_player_idx]
	async def setup(self):
		wild_api = await pm.service.get_pokemon(self.wild_raw["species_id"])
		wild_species = await pm.service.get_species(self.wild_raw["species_id"])
		self.wild = BattlePokemon(self.wild_raw, wild_api, wild_species)
		for p in self.player_party_raw:
			api_p, species_p = await pm.service.get_pokemon(p["species_id"]), await pm.service.get_species(p["species_id"])
			self.player_team.append(BattlePokemon(p, api_p, species_p))
	async def _compose_image(self):
		p_sprite = await self.player_active.sprites[1].read() if self.player_active.sprites[1] else None
		w_sprite = await self.wild.sprites[0].read() if self.wild.sprites[0] else None
		return discord.File(await compose_battle_async(p_sprite, w_sprite, preloaded_textures["battle"]), "battle.png")
	def _hp_line(self, p: BattlePokemon) -> str:
		emoji, bar = get_app_emoji(f"p_{p.species_id}"), _hp_bar(p.current_hp, p.stats['hp'])
		return f"{emoji} {p.name.title()}{p.status_tag()} Lv{p.level}\n{bar} {max(0,p.current_hp)}/{p.stats['hp']}"
	def _embed(self) -> discord.Embed:
		desc = f"{self._hp_line(self.player_active)}\nvs\n{self._hp_line(self.wild)}\n\n" + "\n".join(self.lines)
		return discord.Embed(title=f"Batalha Selvagem - Turno {self.turn}", description=desc, color=discord.Color.green()).set_image(url="attachment://battle.png")
	async def start(self):
		self.actions_view = WildBattleView(self)
		self.lines, self.message = ["A batalha começou!"], await self.interaction.channel.send(embed=self._embed(), file=await self._compose_image(), view=self.actions_view)
		self.must_redraw_image = False
	async def refresh(self):
		if not self.message: return
		args = {"embed": self._embed(), "view": self.actions_view}
		if self.must_redraw_image: args["attachments"], self.must_redraw_image = [await self._compose_image()], False
		await self.message.edit(**args)
	async def _get_move(self, move_id: str):
		key = str(move_id).strip().lower().replace(" ", "-")
		if key in self.move_cache: return self.move_cache[key]
		try: move = await pm.service.get_move(key); self.move_cache[key]=move; return move
		except: return None
	def _pre_action(self, user: BattlePokemon) -> Optional[List[str]]:
		if user.volatile["flinch"]: user.volatile["flinch"]=False; return [f"{user.name.title()} recuou!"]
		s_name, s_counter = user.status["name"], user.status["counter"]
		if s_name == "sleep":
			if s_counter > 1: user.status["counter"]-=1; return [f"{user.name.title()} está dormindo..."]
			user.status={"name":None,"counter":0}; return [f"{user.name.title()} acordou!"]
		if s_name == "freeze":
			if random.random() < 0.2: user.status={"name":None,"counter":0}; return [f"{user.name.title()} descongelou!"]
			return [f"{user.name.title()} está congelado!"]
		if s_name == "paralysis" and random.random() < 0.25: return [f"{user.name.title()} está paralisado!"]
		return None
	def _confusion(self, user: BattlePokemon) -> Optional[List[str]]:
		if user.volatile["confuse"] <= 0: return None
		user.volatile["confuse"] -= 1
		if random.random() < 0.33:
			dmg = max(1, int(((((2*user.level/5+2)*40*(user.eff_stat("atk")/max(1,user.eff_stat("def"))))/50)+2)*random.uniform(0.9,1.0)))
			user.current_hp = max(0, user.current_hp-dmg)
			return [f"{user.name.title()} está confuso e se atingiu, causando {dmg} de dano."]
		return [f"{user.name.title()} está confuso..."]
	def _secondary_effects(self, user: BattlePokemon, target: BattlePokemon, move, total_dmg: int) -> List[str]:
		out, meta = [], getattr(move, "meta", _Meta())
		if random.randint(1,100) <= meta.flinch_chance: target.volatile["flinch"]=True; out.append("O alvo recuou!")
		if meta.drain!=0 and total_dmg>0:
			amt = max(1,int(total_dmg*abs(meta.drain)/100))
			if meta.drain>0: user.current_hp=min(user.stats["hp"],user.current_hp+amt); out.append(f"{user.name.title()} recuperou {amt} HP!")
			else: user.current_hp=max(0,user.current_hp-amt); out.append(f"{user.name.title()} sofreu {amt} de recuo!")
		if meta.healing > 0 and getattr(move.damage_class,"name","")=="status":
			heal=max(1,int(user.stats["hp"]*meta.healing/100)); user.current_hp=min(user.stats["hp"],user.current_hp+heal); out.append(f"{user.name.title()} curou {heal} HP!")
		ail_name, ail_chance = meta.ailment.name, meta.ailment_chance or getattr(move, "effect_chance", 0)
		if ail_name!="none" and random.randint(1,100) <= ail_chance:
			tt, applied = target.types(), False
			if ail_name=="poison" and not any(t in tt for t in ["steel","poison"]): applied=target.set_status("poison")
			elif ail_name=="burn" and "fire" not in tt: applied=target.set_status("burn")
			elif ail_name=="freeze" and "ice" not in tt: applied=target.set_status("freeze")
			elif ail_name=="paralysis" and "ground" not in tt: applied=target.set_status("paralysis")
			elif ail_name=="sleep": applied=target.set_status("sleep")
			elif ail_name=="confusion": target.volatile["confuse"]=max(target.volatile["confuse"], random.randint(2,4)); applied=True
			if applied:
				status_texts = {
					'burn': 'foi queimado',
					'poison': 'foi envenenado',
					'paralysis': 'ficou paralisado',
					'sleep': 'adormeceu',
					'freeze': 'foi congelado',
					'confusion': 'ficou confuso'
				}
				text = status_texts.get(ail_name, "sofreu um efeito desconhecido")
				out.append(f"O alvo {text}!")
		return out
	async def _calc_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move):
		power = int(getattr(move, "power", 0) or 0)
		if power <= 0: return 0, 1.0, False
		dmg_class = getattr(move.damage_class, "name", "physical")
		atk = attacker.eff_stat("sp_atk") if dmg_class=="special" else attacker.eff_stat("atk")
		defn = defender.eff_stat("sp_def") if dmg_class=="special" else defender.eff_stat("def")
		if attacker.status["name"]=="burn" and dmg_class=="physical": atk=int(atk*0.5)
		base = ((((2*attacker.level/5)+2)*power*(atk/max(1,defn)))/50)+2
		type_mult = _type_multiplier(getattr(move.type, "name", "normal"), defender.types())
		if type_mult == 0: return 0, 0, False
		stab = 1.5 if getattr(move.type, "name", "").lower() in attacker.types() else 1.0
		crit = random.random() < 0.0625
		damage = int(base * stab * type_mult * random.uniform(0.9, 1.0) * (1.5 if crit else 1.0))
		return max(1, damage), type_mult, crit
	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, move, move_id: str) -> List[str]:
		mname = move.name.replace("-"," ").title()
		if move_id != "__struggle__":
			if user.get_pp(move_id) == 0: return [f"{user.name.title()} não tem mais PP para {mname}!"]
			user.dec_pp(move_id)
		if not (getattr(move,"accuracy",None) is None or random.randint(1,100)<=move.accuracy): return [f"{user.name.title()} usou {mname}, mas errou!"]
		if getattr(move.damage_class, "name", "")=="status":
			out, sc = [], getattr(move, "stat_changes", [])
			if sc and (not getattr(move,"effect_chance",None) or random.randint(1,100)<=move.effect_chance):
				for s in sc:
					stat, delta = {"attack":"atk","defense":"def","special-attack":"sp_atk","special-defense":"sp_def","speed":"speed"}.get(s.stat.name), s.change
					if stat:
						tgt=user if delta>0 else target; tgt.stages[stat]=max(-6,min(6,tgt.stages[stat]+delta))
						out.append(f"O {stat.upper()} de {tgt.name.title()} {'aumentou' if delta>0 else 'diminuiu'}!")
			out.extend(self._secondary_effects(user, target, move, 0))
			return [f"{user.name.title()} usou {mname}!" + ((" " + " ".join(out)) if out else " Mas falhou.")]
		lines, total_dmg = [], 0
		for i in range(random.randint(getattr(move.meta,"min_hits",1) or 1, getattr(move.meta,"max_hits",1) or 1)):
			dmg, eff, crit = await self._calc_damage(user, target, move)
			if eff==0: return [f"{user.name.title()} usou {mname}! Não teve efeito."]
			if target.status["name"]=="freeze" and getattr(move.type,"name","").lower()=="fire" and dmg>0:
				target.status={"name":None,"counter":0}; lines.append(f"{target.name.title()} descongelou!")
			target.current_hp = max(0, target.current_hp-dmg)
			total_dmg += dmg
			if i==0: first_eff, first_crit = eff, crit
			if target.fainted: break
		txt = f"{user.name.title()} usou {mname}! Causou {total_dmg} de dano."
		if first_crit: txt+=" Acerto crítico!"
		if first_eff>1: txt+=" É super eficaz!"
		if 0<first_eff<1: txt+=" Não foi muito eficaz..."
		lines.append(txt)
		lines.extend(self._secondary_effects(user, target, move, total_dmg))
		return lines
	def _eot_effects(self) -> List[str]:
		lines = []
		for p, who in [(self.player_active,"Seu"),(self.wild,"O selvagem")]:
			if p.fainted: continue
			if p.status["name"] in ["burn","poison"]:
				dmg=max(1,p.stats["hp"]//(16 if p.status["name"]=="burn" else 8)); p.current_hp-=dmg
				lines.append(f"{who} {p.name.title()} sofreu {dmg} de dano de {p.status['name']}!")
		return lines
	async def _act(self, is_player: bool, move_id: str, move_obj) -> List[str]:
		user, target = (self.player_active, self.wild) if is_player else (self.wild, self.player_active)
		lines = self._pre_action(user) or []
		if any("não agiu" in l or "dormindo" in l or "congelado" in l or "paralisado" in l for l in lines): return lines
		conf = self._confusion(user)
		if conf and any("se atingiu" in l for l in conf): return lines+conf
		return lines + (conf or []) + await self._use_move(user, target, move_obj, move_id)
	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended: return
			player_move = await self._get_move(move_id)
			if player_move is None:
				sc = [_obj(stat=_obj(name="attack"), change=-1)] if move_id.lower()=="growl" else None
				player_move = _FallbackMove(name=move_id.title(), power=40, dmg="physical") if move_id.lower() in ["tackle","scratch","pound"] else \
							  _FallbackMove(name=move_id.title(), sc=sc)
			enemy_move_id = random.choice([m["id"] for m in self.wild.moves if m["pp"]>0] or ["__struggle__"])
			enemy_move = _Struggle() if enemy_move_id=="__struggle__" else await self._get_move(enemy_move_id)
			p_prio, e_prio = getattr(player_move,"priority",0) or 0, getattr(enemy_move,"priority",0) or 0
			order = ["player","enemy"] if p_prio>e_prio or (p_prio==e_prio and self.player_active.eff_stat("speed") > self.wild.eff_stat("speed")) else ["enemy","player"]
			lines=[]
			for side in order:
				if self.player_active.fainted or self.wild.fainted: continue
				lines.extend(await self._act(side=="player", move_id if side=="player" else enemy_move_id, player_move if side=="player" else enemy_move))
				if self.wild.fainted: await self._on_win(); self.lines=lines; await self.refresh(); return
				if self.player_active.fainted: await self._on_faint(); self.lines=lines; await self.refresh(); return
			lines.extend(self._eot_effects())
			if self.wild.fainted: await self._on_win()
			elif self.player_active.fainted: await self._on_faint()
			if not self.ended: self.turn += 1
			self.lines=lines; await self.refresh()
	async def switch_active(self, new_idx: int, consume_turn: bool = True):
		async with self.lock:
			if self.ended or new_idx == self.active_player_idx or not(0<=new_idx<len(self.player_team)) or self.player_team[new_idx].fainted: return
			self.active_player_idx = new_idx; self.must_redraw_image=True
			lines = [f"Você trocou para {self.player_active.name.title()}!"]
			if consume_turn:
				enemy_move_id = random.choice([m["id"] for m in self.wild.moves if m["pp"] > 0] or ["__struggle__"])
				lines.extend(await self._act(False, enemy_move_id, await self._get_move(enemy_move_id)))
				lines.extend(self._eot_effects())
				if self.player_active.fainted: await self._on_faint()
				if not self.ended: self.turn+=1
			self.lines=lines; await self.refresh()
	async def attempt_capture(self):
		if self.player_active.fainted:
			self.lines,self.actions_view.force_switch_mode = ["Troque de Pokémon antes!"],True; await self.refresh(); return
		max_hp, current_hp, cr = self.wild.stats["hp"], self.wild.current_hp, self.wild.species_data.capture_rate
		status_bonus = 2.5 if self.wild.status["name"] in ["sleep","freeze"] else 1.5 if self.wild.status["name"] else 1.0
		a = ((3*max_hp - 2*current_hp) * cr * status_bonus) / (3*max_hp)
		if random.randint(1, 255) <= a:
			xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
			pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
			pm.repo.tk.add_pokemon(owner_id=self.user_id, **self.wild_raw)
			self.ended=True; self.lines=[f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp} XP."]; self.actions_view.disable_all()
			await self.refresh(); await self.interaction.channel.send(f"🎉 Capturou {self.wild.name.title()}! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")
		else:
			lines = ["A Pokébola balançou... mas o Pokémon escapou!"]
			enemy_move_id = random.choice([m["id"] for m in self.wild.moves if m["pp"] > 0] or ["__struggle__"])
			lines.extend(await self._act(False, enemy_move_id, await self._get_move(enemy_move_id)))
			lines.extend(self._eot_effects())
			if self.player_active.fainted: await self._on_faint()
			if not self.ended: self.turn+=1
			self.lines=lines; await self.refresh()
	async def _on_win(self):
		xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
		self.ended=True; self.lines=[f"O Pokémon selvagem caiu! {self.player_active.name.title()} ganhou {xp} XP."]; self.actions_view.disable_all()
		await self.refresh(); await self.interaction.channel.send(f"🏆 Vitória! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")
	async def _on_faint(self):
		if not any(not p.fainted for p in self.player_team):
			self.ended=True; self.lines=["Todos os seus Pokémon desmaiaram. Derrota!"]; self.actions_view.disable_all()
			await self.refresh(); await self.interaction.channel.send("💀 Você foi derrotado...")
			return
		self.actions_view.force_switch_mode=True; self.lines=["Seu Pokémon desmaiou! Escolha outro."]

class MovesView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout:float=60.0):
		super().__init__(timeout=timeout); self.battle=battle
		for mv in battle.player_active.moves:
			btn = discord.ui.Button(style=discord.ButtonStyle.primary, label=f"{mv['id'].replace('-',' ').title()} ({mv['pp']}/{mv['pp_max']})", disabled=mv['pp']<=0)
			btn.callback = self._make_cb(mv["id"]); self.add_item(btn)
		back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar"); back.callback=self.back_cb; self.add_item(back)
	async def back_cb(self, i: discord.Interaction):
		if str(i.user.id)!=self.battle.user_id: return await i.response.send_message("Não é sua batalha!",ephemeral=True)
		await i.response.edit_message(view=self.battle.actions_view)
	def _make_cb(self, move_id: str):
		async def _cb(i: discord.Interaction):
			if str(i.user.id)!=self.battle.user_id or self.battle.ended or self.battle.actions_view.force_switch_mode: return
			await i.response.defer(); await self.battle.handle_player_move(move_id)
		return _cb

class SwitchView(discord.ui.View):
	def __init__(self, battle: WildBattle, force_only: bool=False, timeout:float=60.0):
		super().__init__(timeout=timeout); self.battle=battle
		for i, p in enumerate(battle.player_team):
			btn = discord.ui.Button(style=discord.ButtonStyle.success, label=f"{i+1}. {p.name.title()} ({max(0,p.current_hp)}/{p.stats['hp']})", disabled=p.fainted or i==battle.active_player_idx)
			btn.callback = self._make_cb(i); self.add_item(btn)
		if not force_only: back = discord.ui.Button(style=discord.ButtonStyle.secondary,label="Voltar"); back.callback=self.back_cb; self.add_item(back)
	async def back_cb(self, i: discord.Interaction):
		if str(i.user.id)!=self.battle.user_id: return await i.response.send_message("Não é sua batalha!",ephemeral=True)
		await i.response.edit_message(view=self.battle.actions_view)
	def _make_cb(self, idx: int):
		async def _cb(i: discord.Interaction):
			if str(i.user.id)!=self.battle.user_id or self.battle.ended: return
			await i.response.defer(); await self.battle.switch_active(idx, consume_turn=not self.battle.actions_view.force_switch_mode)
			self.battle.actions_view.force_switch_mode=False
		return _cb

class WildBattleView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout=60.0): super().__init__(timeout=timeout); self.battle,self.user_id,self.force_switch_mode=battle,battle.user_id,False
	def disable_all(self):
		for item in self.children: item.disabled=True
	@discord.ui.button(style=discord.ButtonStyle.primary,emoji="⚔️",label="Lutar")
	async def fight(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id or self.battle.ended: return
		await i.response.edit_message(view=SwitchView(self.battle,True) if self.force_switch_mode else MovesView(self.battle))
	@discord.ui.button(style=discord.ButtonStyle.success,emoji="🔁",label="Trocar")
	async def switch(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id or self.battle.ended: return
		await i.response.edit_message(view=SwitchView(self.battle))
	@discord.ui.button(style=discord.ButtonStyle.secondary,emoji="<:PokeBall:1345558169090265151>",label="Capturar")
	async def capture(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id or self.battle.ended: return
		if self.force_switch_mode or self.player_active.fainted: return await i.response.send_message("Troque de Pokémon!",ephemeral=True)
		await i.response.defer(); await self.battle.attempt_capture()

