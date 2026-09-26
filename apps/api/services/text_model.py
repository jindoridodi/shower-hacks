from typing import Protocol


class TextModel(Protocol):
    def generate(self, prompt: str) -> str: ...
