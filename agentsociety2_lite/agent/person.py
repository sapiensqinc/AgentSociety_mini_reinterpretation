"""PersonAgent — profile-based agent with personality."""

from .base import AgentBase


class PersonAgent(AgentBase):
    """An agent with a rich personal profile (name, age, personality, bio, etc.)."""

    def _build_system_prompt(self) -> str:
        parts = [f"You are {self._name}."]
        profile_keys = ["age", "personality", "bio", "location", "background",
                        "occupation", "strategy", "custom_fields"]
        for key in profile_keys:
            if key in self._profile:
                val = self._profile[key]
                if isinstance(val, dict):
                    for k, v in val.items():
                        parts.append(f"{k}: {v}")
                else:
                    parts.append(f"Your {key}: {val}")
        # Include any other keys not in the standard list
        for key, val in self._profile.items():
            if key not in ["name"] + profile_keys:
                parts.append(f"Your {key}: {val}")
        return " ".join(parts)
