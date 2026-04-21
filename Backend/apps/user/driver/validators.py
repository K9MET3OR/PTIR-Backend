from apps.user.utils import validar_nif, validar_senha


def validate_driver_registration_payload(data):
    """Validates required fields and format for driver registration."""
    required = ('email', 'nome', 'nif', 'genero', 'n_carta')
    missing = [field for field in required if not data.get(field)]
    if missing:
        return f"Campos obrigatórios em falta: {', '.join(missing)}"

    nif = str(data.get('nif', '')).strip()
    if not validar_nif(nif):
        return 'NIF inválido.'

    # Password validation (only if provided, since drivers may have auto-generated passwords)
    password = data.get('password', '')
    if password and not validar_senha(password):
        return 'Palavra-passe deve conter dígitos e letras, mínimo 6 caracteres.'

    return None
