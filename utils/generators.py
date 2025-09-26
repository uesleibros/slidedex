import random

def choose_ability(pokemon_data: dict) -> str:
    regular = [a["ability"]["name"] for a in pokemon_data.get("abilities", []) if not a.get("is_hidden")]
    if regular:
        return random.choice(regular)
    all_abilities = pokemon_data.get("abilities", [])
    return all_abilities[0]["ability"]["name"] if all_abilities else "unknown"

def roll_gender(species_data: dict) -> str:
    gr = species_data.get("gender_rate", -1)
    if gr == -1:
        return "Genderless"
    female_chance = gr * 12.5
    return "Female" if random.random() * 100 < female_chance else "Male"

def get_types(pokemon_data: dict):
    return [t["type"]["name"] for t in sorted(pokemon_data.get("types", []), key=lambda x: x.get("slot", 0))]

def select_level_up_moves(pokemon_data: dict, level: int):
    target_groups = ["firered-leafgreen", "emerald", "ruby-sapphire"]
    candidates = {}
    for m in pokemon_data.get("moves", []):
        best_level = -1
        for v in m.get("version_group_details", []):
            if v.get("move_learn_method", {}).get("name") != "level-up":
                continue
            if v.get("version_group", {}).get("name") not in target_groups:
                continue
            ll = v.get("level_learned_at", 0)
            if ll <= level and ll > best_level:
                best_level = ll
        if best_level >= 0:
            name = m.get("move", {}).get("name")
            if name:
                if name not in candidates or best_level > candidates[name]:
                    candidates[name] = best_level
    sorted_moves = sorted(candidates.items(), key=lambda x: (x[1], x[0]))
    return [mv for mv, _lvl in sorted_moves[-4:]]

def choose_held_item(pokemon_data: dict):
    items = pokemon_data.get("held_items", [])
    pool = []
    for it in items:
        item_name = it.get("item", {}).get("name")
        if not item_name:
            continue
        max_rarity = 0
        for vd in it.get("version_details", []):
            vn = vd.get("version", {}).get("name", "")
            if vn in {"firered", "leafgreen", "emerald"}:
                r = vd.get("rarity", 0)
                if r > max_rarity:
                    max_rarity = r
        if max_rarity > 0:
            pool.append((item_name, max_rarity))
    if not pool or random.random() >= 0.45:
        return None
    total = sum(w for _, w in pool)
    roll = random.randint(1, total)
    acc = 0
    for name, w in pool:
        acc += w
        if roll <= acc:
            return name
    return None