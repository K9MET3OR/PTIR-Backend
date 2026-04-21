"""Utility functions shared across the users app."""

import re


def validar_nif(nif: str) -> bool:
    """
    Validates a Portuguese NIF using the mod-11 check-digit algorithm.

    Rules:
      - Must be exactly 9 decimal digits.
      - First digit must be 1–9.
      - Check digit (9th) = 0 if (sum mod 11) < 2, else 11 − (sum mod 11),
        where sum = Σ digit[i] × (9 − i) for i in 0..7.
    """
    if not nif or not re.match(r'^\d{9}$', str(nif)):
        return False

    digits = [int(d) for d in str(nif)]

    if digits[0] == 0:
        return False

    total = sum(d * (9 - i) for i, d in enumerate(digits[:8]))
    remainder = total % 11
    expected_check = 0 if remainder < 2 else 11 - remainder

    return digits[8] == expected_check


def validar_senha(senha: str) -> bool:
    """
    Validates a password according to requirements.
    
    Rules:
      - Minimum 6 characters
      - Must contain at least one digit
      - Must contain at least one letter
    """
    if not senha or len(senha) < 6:
        return False
    
    has_digit = bool(re.search(r'\d', senha))
    has_letter = bool(re.search(r'[a-zA-Z]', senha))
    
    return has_digit and has_letter
