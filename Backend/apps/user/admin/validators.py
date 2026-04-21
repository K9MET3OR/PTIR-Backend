from apps.user.utils import validar_nif, validar_senha


def validate_admin_payload(data):
    required = ('username', 'email', 'password', 'name', 'nif')
    missing = [field for field in required if not data.get(field)]
    if missing:
        return f"Campos obrigatorios em falta: {', '.join(missing)}"

    nif = str(data.get('nif', '')).strip()
    if not validar_nif(nif):
        return 'NIF invalido.'

    password = data.get('password', '')
    if not validar_senha(password):
        return 'Palavra-passe deve conter dígitos e letras, mínimo 6 caracteres.'

    return None
