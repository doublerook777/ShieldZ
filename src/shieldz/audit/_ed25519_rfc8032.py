"""Pure-Python Ed25519 implementation following RFC 8032.

Zero external dependencies (uses standard library `hashlib` and `os`).
Used as fallback when C-accelerated `cryptography` is not installed (e.g. on laptops).
Passes all RFC 8032 §7.1 test vectors.
Compatible with standard PKCS#8 / SubjectPublicKeyInfo PEM formats used by OpenSSL.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re

# ---------------------------------------------------------------------------
# Curve parameters (Edwards25519)
# ---------------------------------------------------------------------------

P: int = 2**255 - 19
L: int = 2**252 + 27742317777372353535851937790883648493
D: int = -121665 * pow(121666, P - 2, P) % P
I: int = pow(2, (P - 1) // 4, P)  # noqa: E741


def _inv(x: int) -> int:
    return pow(x, P - 2, P)


def _recover_x(y: int, sign: int) -> int:
    if y >= P:
        raise ValueError("y coordinate out of range")
    x2 = (y * y - 1) * _inv(D * y * y + 1) % P
    if x2 == 0:
        if sign:
            raise ValueError("Invalid x coordinate")
        return 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = (x * I) % P
    if (x * x - x2) % P != 0:
        raise ValueError("Cannot recover x on curve")
    if (x & 1) != sign:
        x = P - x
    return x


# Base point B
_By: int = 4 * _inv(5) % P
_Bx: int = _recover_x(_By, 0)
B_POINT: tuple[int, int] = (_Bx, _By)


# ---------------------------------------------------------------------------
# Point arithmetic
# ---------------------------------------------------------------------------


def _point_add(p1: tuple[int, int], p2: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = p1
    x2, y2 = p2
    x3 = (x1 * y2 + y1 * x2) * _inv(1 + D * x1 * x2 * y1 * y2) % P
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - D * x1 * x2 * y1 * y2) % P
    return (x3, y3)


def _point_mul(s: int, p: tuple[int, int]) -> tuple[int, int]:
    r = (0, 1)
    base = p
    while s > 0:
        if s & 1:
            r = _point_add(r, base)
        base = _point_add(base, base)
        s >>= 1
    return r


def _encode_point(p: tuple[int, int]) -> bytes:
    x, y = p
    b = bytearray(y.to_bytes(32, "little"))
    if x & 1:
        b[31] |= 0x80
    return bytes(b)


def _decode_point(b: bytes) -> tuple[int, int]:
    if len(b) != 32:
        raise ValueError("Encoded point must be 32 bytes")
    sign = (b[31] >> 7) & 1
    y = int.from_bytes(bytes([b[i] for i in range(31)] + [b[31] & 0x7F]), "little")
    x = _recover_x(y, sign)
    return (x, y)


# ---------------------------------------------------------------------------
# Key derivation & signing (RFC 8032 §5.1.5, §5.1.6)
# ---------------------------------------------------------------------------


def _clamp(h: bytes) -> int:
    a_bytes = bytearray(h[:32])
    a_bytes[0] &= 248
    a_bytes[31] &= 127
    a_bytes[31] |= 64
    return int.from_bytes(a_bytes, "little")


def public_key_from_seed(seed: bytes) -> bytes:
    """Derive 32-byte public key from 32-byte private key seed."""
    if len(seed) != 32:
        raise ValueError("Seed must be 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = _clamp(h)
    point_a = _point_mul(a, B_POINT)
    return _encode_point(point_a)


def sign(seed: bytes, message: bytes) -> bytes:
    """Sign *message* using 32-byte private key *seed*. Returns 64-byte signature."""
    if len(seed) != 32:
        raise ValueError("Seed must be 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = _clamp(h)
    pub = _encode_point(_point_mul(a, B_POINT))

    prefix = h[32:]
    r_hash = hashlib.sha512(prefix + message).digest()
    r = int.from_bytes(r_hash, "little") % L

    point_r = _point_mul(r, B_POINT)
    r_bytes = _encode_point(point_r)

    k_hash = hashlib.sha512(r_bytes + pub + message).digest()
    k = int.from_bytes(k_hash, "little") % L

    s = (r + k * a) % L
    return r_bytes + s.to_bytes(32, "little")


def verify(pubkey_bytes: bytes, message: bytes, signature: bytes) -> bool:
    """Verify 64-byte *signature* on *message* using 32-byte *pubkey_bytes*."""
    if len(pubkey_bytes) != 32 or len(signature) != 64:
        return False
    r_bytes = signature[:32]
    s_bytes = signature[32:]
    s = int.from_bytes(s_bytes, "little")
    if s >= L:
        return False

    try:
        point_a = _decode_point(pubkey_bytes)
        point_r = _decode_point(r_bytes)
    except ValueError:
        return False

    k_hash = hashlib.sha512(r_bytes + pubkey_bytes + message).digest()
    k = int.from_bytes(k_hash, "little") % L

    # Check S*B == R + k*A
    sb = _point_mul(s, B_POINT)
    ka = _point_mul(k, point_a)
    r_plus_ka = _point_add(point_r, ka)
    return sb == r_plus_ka


# ---------------------------------------------------------------------------
# PEM serialization (compatible with OpenSSL / python-cryptography)
# ---------------------------------------------------------------------------

# PKCS#8 prefix for Ed25519: 16 bytes
_PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")
# SPKI prefix for Ed25519: 12 bytes
_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def export_private_key_pem(seed: bytes) -> bytes:
    """Export 32-byte seed as PKCS#8 unencrypted PEM."""
    der = _PKCS8_PREFIX + seed
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
    body = "\n".join(lines)
    return f"-----BEGIN PRIVATE KEY-----\n{body}\n-----END PRIVATE KEY-----\n".encode()


def export_public_key_pem(pub: bytes) -> bytes:
    """Export 32-byte pubkey as SubjectPublicKeyInfo PEM."""
    der = _SPKI_PREFIX + pub
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
    body = "\n".join(lines)
    return f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----\n".encode()


def import_private_key_pem(pem: bytes) -> bytes:
    """Extract 32-byte seed from PKCS#8 PEM or raw hex/bytes."""
    text = pem.decode("utf-8", errors="ignore")
    pattern = r"-----BEGIN PRIVATE KEY-----\s*([A-Za-z0-9+/=\s]+)\s*-----END PRIVATE KEY-----"
    match = re.search(pattern, text)
    if match:
        b64_data = re.sub(r"\s+", "", match.group(1))
        der = base64.b64decode(b64_data)
        if der.startswith(_PKCS8_PREFIX) and len(der) == len(_PKCS8_PREFIX) + 32:
            return der[len(_PKCS8_PREFIX) :]
        if len(der) >= 32:
            return der[-32:]
    # If not PEM, try raw 32 bytes
    if len(pem) == 32:
        return pem
    raise ValueError("Invalid Ed25519 private key PEM")


def import_public_key_pem(pem: bytes) -> bytes:
    """Extract 32-byte public key from SPKI PEM or raw hex/bytes."""
    text = pem.decode("utf-8", errors="ignore")
    pattern = r"-----BEGIN PUBLIC KEY-----\s*([A-Za-z0-9+/=\s]+)\s*-----END PUBLIC KEY-----"
    match = re.search(pattern, text)
    if match:
        b64_data = re.sub(r"\s+", "", match.group(1))
        der = base64.b64decode(b64_data)
        if der.startswith(_SPKI_PREFIX) and len(der) == len(_SPKI_PREFIX) + 32:
            return der[len(_SPKI_PREFIX) :]
        if len(der) >= 32:
            return der[-32:]
    if len(pem) == 32:
        return pem
    raise ValueError("Invalid Ed25519 public key PEM")


def generate_keypair_pem() -> tuple[bytes, bytes]:
    """Generate a random keypair and return (private_pem, public_pem)."""
    seed = os.urandom(32)
    pub = public_key_from_seed(seed)
    return export_private_key_pem(seed), export_public_key_pem(pub)


def sign_pem(privkey_pem: bytes, message: bytes) -> bytes:
    """Sign message with private key PEM."""
    seed = import_private_key_pem(privkey_pem)
    return sign(seed, message)


def verify_pem(pubkey_pem: bytes, message: bytes, signature: bytes) -> bool:
    """Verify signature with public key PEM."""
    pub = import_public_key_pem(pubkey_pem)
    return verify(pub, message, signature)
