def fmt_name(s: str) -> str:
    return s.replace("-", " ").title()

def format_poke_id(pid: int) -> str:
    return str(pid).zfill(3)