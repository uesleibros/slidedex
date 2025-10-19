from typing import Final

class Gender:
    MALE = "Male"
    FEMALE = "Female"
    
    LABELS: Final[dict[str, str]] = {
        MALE: "<:sign_male:1426401235606700165> Masculino",
        FEMALE: "<:sign_female:1426401284994367539> Feminino"
    }
    
    _GENDER_MAP: Final[dict[str, str]] = {
        "male": MALE,
        "m": MALE,
        "masculino": MALE,
        "female": FEMALE,
        "f": FEMALE,
        "feminino": FEMALE,
    }
    
    @classmethod
    def normalize(cls, gender: str) -> str:
        return cls._GENDER_MAP.get((gender or "").strip().lower(), cls.MALE)
    
    @classmethod
    def get_label(cls, value: str) -> str:
        return cls.LABELS.get(value, value)