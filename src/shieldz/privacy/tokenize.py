"""HMAC-SHA256 tokens for account identifiers (ADR D10).

A plain hash of an account number can be reversed by hashing every possible number. A keyed
HMAC cannot, without the pepper. The pepper lives only in artifacts/keys/ and is never committed.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from functools import lru_cache
from pathlib import Path

from shieldz import config

PEPPER_BYTES = 32
TOKEN_HEX_CHARS = 32  # 128 bits: ample for linking, no need for the full digest


def load_pepper(path: Path | None = None) -> bytes:
    """Read the pepper, creating it on first run. Safe if two processes start at once."""
    path = path or config.pepper_file()
    try:
        return bytes.fromhex(path.read_text().strip())
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    pepper = os.urandom(PEPPER_BYTES)
    # Write a private temp file, then hard-link it into place: the link is atomic, so a process
    # that loses the race can never read a half-written pepper.
    tmp = path.with_name(f".{path.name}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(pepper.hex())
    try:
        os.link(tmp, path)
    except FileExistsError:  # lost the race: use the winner's pepper
        return bytes.fromhex(path.read_text().strip())
    finally:
        os.unlink(tmp)
    return pepper


def normalize_id(value: str) -> str:
    """Spacing, dashes and case must not change the token: '5021 3344-7788' == '502133447788'."""
    normalized = "".join(ch for ch in value if ch.isalnum()).casefold()
    if not normalized:
        raise ValueError("identifier has no alphanumeric characters")
    return normalized


class Tokenizer:
    def __init__(self, pepper: bytes) -> None:
        if len(pepper) < 16:
            raise ValueError("pepper too short")
        self._pepper = pepper

    def __repr__(self) -> str:
        return "Tokenizer(<pepper hidden>)"

    def token(self, identifier: str) -> str:
        digest = hmac.new(self._pepper, normalize_id(identifier).encode(), hashlib.sha256)
        return digest.hexdigest()[:TOKEN_HEX_CHARS]


@lru_cache(maxsize=4)
def _tokenizer_for(path: Path) -> Tokenizer:
    return Tokenizer(load_pepper(path))


def default_tokenizer() -> Tokenizer:
    """The tokenizer for the configured pepper file (cached per path)."""
    return _tokenizer_for(config.pepper_file())
