"""Implementación autónoma de TOTP (RFC 6238 / RFC 4226) compatible con Google Authenticator y Authy."""

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from typing import List, Tuple


def generate_totp_secret() -> str:
    """Genera un secreto aleatorio en Base32 (16 bytes = 26-32 caracteres)."""
    random_bytes = os.urandom(20)
    return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")


def get_totp_uri(secret: str, username: str, issuer: str = "LABFIX ERP") -> str:
    """Genera el URI estándar otpauth:// para escanear en apps autenticadoras."""
    clean_user = username.replace(" ", "%20")
    clean_issuer = issuer.replace(" ", "%20")
    return f"otpauth://totp/{clean_issuer}:{clean_user}?secret={secret}&issuer={clean_issuer}&algorithm=SHA1&digits=6&period=30"


def generate_totp_code(secret: str, time_step: int = 30, for_time: float | None = None) -> str:
    """Calcula el código TOTP de 6 dígitos actual a partir del secreto Base32."""
    if for_time is None:
        for_time = time.time()

    # Normalizar padding base32
    secret_upper = secret.upper().replace(" ", "")
    padding = len(secret_upper) % 8
    if padding != 0:
        secret_upper += "=" * (8 - padding)

    key = base64.b32decode(secret_upper)
    counter = int(for_time // time_step)
    counter_bytes = struct.pack(">Q", counter)

    hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code_int = struct.unpack(">I", hmac_hash[offset : offset + 4])[0] & 0x7FFFFFFF
    token = code_int % 1000000
    return f"{token:06d}"


def verify_totp_code(secret: str, code: str, tolerance: int = 1) -> bool:
    """Verifica si el código ingresado coincide dentro de una ventana de tolerancia de ±1 paso (30s)."""
    if not secret or not code:
        return False
    clean_code = str(code).strip().replace(" ", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    now = time.time()
    for drift in range(-tolerance, tolerance + 1):
        target_time = now + (drift * 30)
        expected = generate_totp_code(secret, for_time=target_time)
        if hmac.compare_digest(expected, clean_code):
            return True
    return False


def generate_backup_codes(count: int = 8) -> Tuple[List[str], List[str]]:
    """Genera pares de códigos de respaldo legibles (texto plano para el usuario, hashes para la BD)."""
    plain_codes = []
    hashed_codes = []
    for _ in range(count):
        # Generar código tipo XXXX-XXXX
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}"
        plain_codes.append(code)
        # Hashing con SHA256
        h = hashlib.sha256(code.encode("utf-8")).hexdigest()
        hashed_codes.append(h)
    return plain_codes, hashed_codes


def verify_and_consume_backup_code(code_input: str, hashed_codes_list: List[str]) -> Tuple[bool, List[str]]:
    """Verifica si el código de respaldo es válido y lo consume de la lista."""
    clean = code_input.strip().upper().replace(" ", "")
    h = hashlib.sha256(clean.encode("utf-8")).hexdigest()
    if h in hashed_codes_list:
        remaining = [c for c in hashed_codes_list if c != h]
        return True, remaining
    return False, hashed_codes_list

