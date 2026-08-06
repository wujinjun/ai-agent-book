"""Deterministic fake used by the prompt regression runner."""


class DeterministicPromptModel:
    def run(self, rendered_prompt: str) -> dict[str, str | float]:
        if "退款" in rendered_prompt:
            return {"category": "billing", "confidence": 1.0}
        if "登录" in rendered_prompt:
            return {"category": "access", "confidence": 1.0}
        return {"category": "other", "confidence": 0.5}
