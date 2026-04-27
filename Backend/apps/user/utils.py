"""Utility functions shared across the users app."""

import re


def validar_nif(nif: str) -> bool:
    """
    Validates a Portuguese NIF.

    Rules:
      - Must be exactly 9 decimal digits.
      - All digits must be positive (0-9).
    """
    if not nif or not re.match(r'^\d{9}$', str(nif)):
        return False

    return True


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
