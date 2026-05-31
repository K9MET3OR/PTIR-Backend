from apps.user.utils import validar_nif, validar_senha


def validate_client_payload(data):
    required = ('username', 'email', 'password', 'name', 'nif', 'genero')
    missing = [field for field in required if not data.get(field)]
    if missing:
        return f"Campos obrigatorios em falta: {', '.join(missing)}"

    nif = str(data.get('nif', '')).strip()
    if not validar_nif(nif):
        return 'NIF invalido.'

    genero = str(data.get('genero', '')).strip().lower()
    if genero not in ('feminino', 'masculino'):
        return "Genero invalido. Deve ser 'feminino' ou 'masculino'."

    password = data.get('password', '')
    if not validar_senha(password):
        return 'Palavra-passe deve conter dígitos e letras, mínimo 6 caracteres.'

    return None
