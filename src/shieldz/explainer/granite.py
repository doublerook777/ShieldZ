"""IBM Granite 4.0 350M GGUF explainer via llama-cpp-python on s390x (LinuxONE).

Implements the Generator protocol required by the Explainer Worker.
CPU threads are capped so generation does not starve the real-time API.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

DEFAULT_MODEL_PATH = Path(
    os.environ.get("SHIELDZ_GRANITE_PATH", "/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf")
)


class GraniteGenerator:
    """Granite LLM wrapper for generating scam/fraud warning explanations."""

    name: str = "granite-4.0-h-350m"

    def __init__(
        self,
        model_path: Optional[Path | str] = None,
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

    def generate(self, prompt: str, max_tokens: int = 80) -> str:
        """Generate calm explanation from validated prompt."""
        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.2,
            stop=["\n\n\n", "Decision:", "User:", "###", "Risk:"],
        )
        return response["choices"][0]["text"].strip()
