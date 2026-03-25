from dataclasses import dataclass, field
from typing import Any

@dataclass
class ConditionalTrait:
    id: str
    trait: str
    delta: float
    description: str
    condition_type: str
    condition_key: str
    condition_op: str
    condition_value: Any

@dataclass
class CharacterData:
    id: str
    name: str
    traits: dict[str, float]         # trait_name → current_value
    emotions: dict[str, float]        # emotion_name → current_value
    conditionals: list[ConditionalTrait] = field(default_factory=list)