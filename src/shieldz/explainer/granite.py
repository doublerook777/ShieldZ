"""IBM Granite 4.0 350M GGUF explainer via llama-cpp-python on s390x (LinuxONE).

Implements the Generator protocol required by the Explainer Worker.
CPU threads are capped so generation does not starve the real-time API.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MODEL_PATH = Path(
    os.environ.get("SHIELDZ_GRANITE_PATH", "/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf")
)


# Generation time is linear in tokens (3.8 tok/s on the VM). Two or three short sentences fit in
# about 50 tokens; 80 made every explanation ~21 s.
DEFAULT_MAX_TOKENS = int(os.environ.get("SHIELDZ_LLM_MAX_TOKENS", "56"))
SENTENCE_END = ".!?\u0964"  # \u0964 is the Devanagari danda used in Hindi


def trim_to_sentence(text: str) -> str:
    """A token cap can stop mid-sentence: cut back to the last full sentence if there is one."""
    text = text.strip()
    if not text or text[-1] in SENTENCE_END:
        return text
    cut = max(text.rfind(c) for c in SENTENCE_END)
    return text[: cut + 1] if cut >= 10 else text


class GraniteGenerator:
    """Granite LLM wrapper for generating scam/fraud warning explanations."""

    name: str = "granite-4.0-h-350m"

    def __init__(
        self,
        model_path: Path | str | None = None,
        n_ctx: int = 512,
        n_threads: int = 2,
    ) -> None:
        import llama_cpp

        path = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
        if not path.exists():
            # Check fallback in repo or artifacts
            alt_candidates = [
                Path("/home/jovyan/shared/ShieldZ/artifacts/models/granite.gguf"),
                Path.home() / "granite-4.0-h-350m-base-be.f16.gguf",
            ]
            for cand in alt_candidates:
                if cand.exists():
                    path = cand
                    break

        if not path.exists():
            raise FileNotFoundError(f"Granite GGUF model not found at {path}")

        self.model_path = str(path)
        self.n_threads = int(os.environ.get("SHIELDZ_LLM_THREADS", n_threads))
        self.llm = llama_cpp.Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_threads=self.n_threads,
            verbose=False,
        )

    @property
    def cache_tag(self) -> str:
        """Part of the prompt-cache key: changing any of these must not serve old text."""
        return f"{self.name}|max{DEFAULT_MAX_TOKENS}|t0"

    def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        """Generate a calm explanation from a validated prompt (temperature 0: reproducible)."""
        response = self.llm(
            prompt,
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
            temperature=0.0,
            repeat_penalty=1.1,
            stop=["\n"],  # one line: "Simple words: ..." is a single paragraph
        )
        return trim_to_sentence(response["choices"][0]["text"])
